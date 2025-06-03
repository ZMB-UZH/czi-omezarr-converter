"""Contains the list of tasks available to fractal."""

from fractal_task_tools.task_models import (
    ConverterCompoundTask,
)

AUTHORS = "Flurin Sturzenegger"
DOCS_LINK = None
INPUT_MODELS = []

TASK_LIST = [
    ConverterCompoundTask(
        name="Convert czi to OME-Zarr",
        executable_init="convert_czi_init_task.py",
        executable="convert_czi_compute_task.py",
        meta_init={"cpus_per_task": 1, "mem": 4000},
        meta={"cpus_per_task": 1, "mem": 12000},
        category="Conversion",
        tags=[
            "Zeiss",
            "CZI",
            "Converter",
        ],
        docs_info="file:docs_info/convert_czi_task.md",
    ),
]
