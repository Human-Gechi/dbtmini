from dataclasses import dataclass
from enum import Enum

from dbtmini.materialization import Materialization


class RunStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class ModelResult:
    model_name: str
    status: RunStatus
    duration: float
    materialization: Materialization
    message: str = ""


@dataclass
class RunResult:
    result = list[ModelResult]
    elasped_time: float
    success_count: int = 0
    error_count: int = 0
