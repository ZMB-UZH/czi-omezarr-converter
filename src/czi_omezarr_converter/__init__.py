"""
Zeiss .czi to OME-Zarr converter
"""
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("czi-omezarr-converter")
except PackageNotFoundError:
    __version__ = "uninstalled"