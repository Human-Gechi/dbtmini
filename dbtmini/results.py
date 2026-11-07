from dataclasses import dataclass, field
from enum import Enum

from dbtmini.materialization import Materialization
from dbtmini.seeds import SeedResult


class RunStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class ModelResult:
    model_name: str
    status: RunStatus
    duration: float
    materialization: Materialization
    message: str = ""


@dataclass(frozen=True)
class RunResult:
    result: list[ModelResult]
    elasped_time: float
    seed_results: list[SeedResult] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.result if r.status == RunStatus.SUCCESS)

    @property
    def error_count(self) -> int:
        return sum(1 for r in self.result if r.status == RunStatus.ERROR)

    @property
    def total_count(self) -> int:
        return len(self.result)
