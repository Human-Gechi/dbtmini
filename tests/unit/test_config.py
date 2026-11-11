from pathlib import Path

from dbtmini.config import _resolve_paths


def test_resolve_relative_paths(tmp_path: Path) -> None:
    result = _resolve_paths(raw_dir="models", base_dir=tmp_path)

    assert result == tmp_path / "models"


def test_resolve_absolute_paths(tmp_path: Path) -> None:
    abs_path = (tmp_path / "extra_models").resolve()
    result = _resolve_paths(raw_dir=str(abs_path), base_dir=tmp_path)

    assert result == abs_path
