import shutil
from collections.abc import Iterator
from pathlib import Path

import duckdb
import pytest
from typer.testing import CliRunner

from dbtmini.config import ProjectConfig
from dbtmini.models import Model

TEST_DIR = Path(__file__).parent
FIXTURES_DIR = TEST_DIR / "fixtures"

EXAMPLE_PROJECT_DIR = TEST_DIR.parent / "example_project"


@pytest.fixture
def db_conn() -> Iterator[duckdb.DuckDBPyConnection]:
    conn = duckdb.connect(":memory:")
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


def _copy_project(source: Path, tmp_path: Path, name: str) -> Path:
    dest = tmp_path / name
    shutil.copytree(source, dest)

    return dest


@pytest.fixture
def example_project_dir(tmp_path: Path) -> Path:
    return _copy_project(EXAMPLE_PROJECT_DIR, tmp_path, "example_project")


@pytest.fixture
def valid_project_dir(tmp_path: Path) -> Path:
    return _copy_project(FIXTURES_DIR / "valid_project", tmp_path, "valid_project")


@pytest.fixture
def cyclic_project_dir(tmp_path: Path) -> Path:
    return _copy_project(FIXTURES_DIR / "cyclic_project", tmp_path, "cyclic_project")


@pytest.fixture
def duplicate_names_project_dir(tmp_path: Path) -> Path:
    return _copy_project(
        FIXTURES_DIR / "duplicate_names_project", tmp_path, "duplicate_names_project"
    )


@pytest.fixture
def failing_test_project_dir(tmp_path: Path) -> Path:
    return _copy_project(
        FIXTURES_DIR / "failing_test_project", tmp_path, "failing_test_project"
    )


@pytest.fixture
def missing_ref_project_dir(tmp_path: Path) -> Path:
    return _copy_project(
        FIXTURES_DIR / "missing_ref_project", tmp_path, "missing_ref_project"
    )


@pytest.fixture
def sample_config(tmp_path: Path) -> ProjectConfig:
    models_dir = tmp_path / "models"
    seeds_dir = tmp_path / "seeds"
    tests_dir = tmp_path / "tests"

    models_dir.mkdir()
    seeds_dir.mkdir()
    tests_dir.mkdir()

    return ProjectConfig(
        name="sample_project",
        project_path=tmp_path,
        model_paths=(models_dir,),
        seed_paths=(seeds_dir,),
        test_paths=(tests_dir,),
        target_path=tmp_path / "target",
        default_materialization="view",
        folder_overrides={"marts": "table"},
    )


@pytest.fixture
def graph() -> dict[str, set[str]]:
    return {
        "a": set(),
        "b": {"a"},
        "c": {"a"},
        "d": {"b", "c"},
    }


@pytest.fixture
def sample_model(tmp_path: Path) -> Model:
    sql = "SELECT * FROM {{ ref('data') }}"
    return Model(
        name="sample_model",
        file_path=tmp_path / "sample_model.sql",
        sql_text=sql,
        folder="staging",
        config={},
    )
