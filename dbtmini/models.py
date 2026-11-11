from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional


@dataclass(frozen=True)  # Dataclass for Models
class Model:
    name: str
    file_path: Path | str
    sql_text: str
    folder: str = ""
    config: dict[str, Any] = field(default_factory=dict, hash=False)


@dataclass(frozen=True)
class TestSpec:  # Dataclass for tests run on models
    name: str
    column: str
    test_type: str
    severity: Optional[Literal["error", "warn"]] = "error"


@dataclass(frozen=True)
class ParseResult:  # result of the rendering from sql
    model_name: str
    dependencies: frozenset[str] = field(default_factory=frozenset)
    config: dict[str, Any] = field(default_factory=dict, hash=False)
