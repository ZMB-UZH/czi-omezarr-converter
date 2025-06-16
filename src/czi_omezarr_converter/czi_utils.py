from collections.abc import Generator
from pathlib import Path
from typing import Any

import numpy as np
from bioio import BioImage
from fractal_converters_tools import (
    OriginDict,
    # PlatePathBuilder,
    Point,
    SimplePathBuilder,
    Tile,
    TiledImage,
    Vector,
)
from ngio import PixelSize


class cziTileLoader:
    """czi tile loader"""

    def __init__(self, path: str, scene_id: int, m: int):
        """Initialize cziTileLoader."""
        self.path = path
        self.scene_id = scene_id
        self.m = m

    @property
    def dtype(self):
        """Get the data type of the tile."""
        img = BioImage(
            self.path,
            reconstruct_mosaic=False,
            include_subblock_metadata=True,
            use_aicspylibczi=True,
        )
        return img.dtype

    def load(self) -> np.ndarray:
        """Load the tile data."""
        img = BioImage(
            self.path,
            reconstruct_mosaic=False,
            include_subblock_metadata=True,
            use_aicspylibczi=True,
        )
        img.set_scene(self.scene_id)
        data_xr = img.xarray_dask_data
        if "M" in data_xr.dims:
            data_xr = data_xr.isel(M=self.m)
        if data_xr.dims != ("T", "C", "Z", "Y", "X"):  # pragma: no cover
            raise ValueError(
                f"Data must have dimension order T, C, Z, Y, X. Found: {data_xr.dims}"
            )
        return data_xr.data.compute()


def build_tiles(czi_path: str | Path, scene_id: int) -> Generator[Tile, Any, None]:
    """Build tiles from czi scene."""
    img = BioImage(
        czi_path,
        reconstruct_mosaic=False,
        include_subblock_metadata=True,
        use_aicspylibczi=True,
    )
    img.set_scene(scene_id)

    shape_x = img.dims.X
    shape_y = img.dims.Y
    shape_z = img.dims.Z
    shape_c = img.dims.C
    shape_t = img.dims.T

    # scale factors [um]/[px]
    scale_x = img.physical_pixel_sizes.X
    scale_y = img.physical_pixel_sizes.Y
    scale_z = (
        img.physical_pixel_sizes.Z if img.physical_pixel_sizes.Z is not None else 1
    )
    # TODO: check if this is correct
    scale_t = img.time_interval if img.time_interval is not None else 1

    # [um]
    length_x = shape_x * scale_x
    length_y = shape_y * scale_y
    length_z = shape_z * scale_z
    length_t = shape_t * scale_t

    if "M" in img.dims.order:
        for m in range(img.dims.M):
            y_start_index, x_start_index = img.get_mosaic_tile_position(
                m, T=0, C=0, Z=0
            )
            # TODO: check if this is consistent with other data.
            # otherwise: handle with AdvancedComputeOptions
            y_start_index = -y_start_index
            top_l = Point(
                x=x_start_index * scale_x,
                y=y_start_index * scale_y,
                z=0,
                c=0,
                t=0,
            )
            diag = Vector(x=length_x, y=length_y, z=length_z, c=shape_c, t=length_t)
            pixel_size = PixelSize(x=scale_x, y=scale_y, z=scale_z)
            # TODO: read the stage positions from the metadata
            origin = OriginDict(
                x_micrometer_original=x_start_index * scale_x,
                y_micrometer_original=y_start_index * scale_y,
                z_micrometer_original=0,
            )
            tile_loader = cziTileLoader(path=czi_path, scene_id=scene_id, m=m)
            tile = Tile(
                top_l=top_l,
                diag=diag,
                pixel_size=pixel_size,
                origin=origin,
                data_loader=tile_loader,
            )
            yield tile
    else:
        top_l = Point(
            x=0,
            y=0,
            z=0,
            c=0,
            t=0,
        )
        diag = Vector(x=length_x, y=length_y, z=length_z, c=shape_c, t=length_t)
        pixel_size = PixelSize(x=scale_x, y=scale_y, z=scale_z)
        # TODO: read the stage positions from the metadata
        origin = OriginDict(
            x_micrometer_original=0,
            y_micrometer_original=0,
            z_micrometer_original=0,
        )
        tile_loader = cziTileLoader(path=czi_path, scene_id=scene_id, m=None)
        tile = Tile(
            top_l=top_l,
            diag=diag,
            pixel_size=pixel_size,
            origin=origin,
            data_loader=tile_loader,
        )
        yield tile


def build_tiled_image(
    czi_path: str | Path,
    zarr_name: str | None = None,
    acquisition_id: int | None = None,
    scene_id: int = 0,
    plate: bool = False,
):
    """Build a tiled image from a czi-BioImage object."""
    img = BioImage(
        czi_path,
        reconstruct_mosaic=False,
        include_subblock_metadata=True,
        use_aicspylibczi=True,
    )
    img.set_scene(scene_id)
    channel_names = img.channel_names
    # TODO: check with other test data if this is reasonable
    wavelength_ids = [name.split("-")[0] for name in channel_names]

    if plate:
        # TODO:
        raise NotImplementedError("Plate mode is not implemented yet.")
    else:
        if acquisition_id is not None:
            acquisition_id = None
            # TODO: add support for acquisition_id
            # (needs to be implemented in SimplePathBuilder in fractal_converters_tools)
        _path_builder = SimplePathBuilder(
            path=zarr_name,
        )

    # Build tiles
    tiled_image = TiledImage(
        name="some_name",  # TODO: set a proper name
        path_builder=_path_builder,
        channel_names=channel_names,
        wavelength_ids=wavelength_ids,
    )
    for tile in build_tiles(czi_path, scene_id):
        tiled_image.add_tile(tile)

    return tiled_image


def parse_czi_acquisition(
    acq_path: str | Path,
    plate_name: str | None = None,
    acquisition_id: int | None = None,
) -> list[TiledImage]:
    """Parse czi acquisition and return list of tiled images."""
    if not Path(acq_path).exists():
        raise FileNotFoundError(f"File not found: {acq_path}")

    if Path(acq_path).is_dir():
        raise NotImplementedError(
            "Parsing of CZI files in directories is not implemented yet. "
            "Please provide a single CZI file."
        )

    img = BioImage(
        acq_path,
        reconstruct_mosaic=False,
        include_subblock_metadata=True,
        use_aicspylibczi=True,
    )

    if len(img.scenes) > 1:
        raise NotImplementedError(
            "Parsing of CZI files with multiple scenes is not implemented yet."
        )

    if plate_name is None:
        plate_name = Path(acq_path).stem.replace(" ", "_")

    tiled_image = build_tiled_image(
        czi_path=acq_path,
        zarr_name=plate_name,
        acquisition_id=acquisition_id,
        scene_id=0,
        plate=False,
    )

    return [tiled_image]
