import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

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

    @property
    def exit_code(self) -> int:
        return 1 if self.error_count > 0 else 0


def write_run_results(run_results: RunResult, target_path: Path) -> Path:
    target_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_naming = f"run_results_{timestamp}.json"
    destination = target_path / file_naming
    with open(destination, mode="w", encoding="utf-8") as file:
        json.dump(asdict(run_results), file, indent=2, default=str)

    return destination


def format_summary_results(run_result: RunResult) -> str:
    lines: list[str] = []

    divider = "-" * 65

    lines.append(f"{'MODEL':<25} {'STATUS':<12} {'TIME':<12} MESSAGE")
    lines.append(divider)

    for model in run_result.result:
        duration_str = f"{model.duration:.3f}s"
        row = f"""{model.model_name:<25} {model.status.value.upper():<12}
        {duration_str:<12} {model.message}"""
        lines.append(row)

    lines.append(divider)
    footer = (
        f"Summary: {run_result.success_count} passed, "
        f"{run_result.error_count} failed, "
        f"{run_result.total_count} total | "
        f"Total time: {run_result.elasped_time:.2f}s"
    )
    lines.append(footer)

    return "\n".join(lines)
