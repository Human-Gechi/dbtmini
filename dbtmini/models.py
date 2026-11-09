from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional


@dataclass(frozen=True)
class Model:
    name: str
    file_path: Path | str
    sql_text: str
    folder: str = ""
    config: dict[str, Any] = field(default_factory=dict, hash=False)


@dataclass(frozen=True)
class TestSpec:
    name: str
    column: str
    test_type: Literal["not_null", "unique"]
    severity: Optional[Literal["error", "warn"]] = "error"


@dataclass(frozen=True)
class ParseResult:
    model_name: str
    dependencies: frozenset[str] = field(default_factory=frozenset)
    config: dict[str, Any] = field(default_factory=dict, hash=False)
