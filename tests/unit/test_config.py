from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from dbtmini.config import ProjectConfig, _project_directory, _resolve_paths
from dbtmini.errors import ConfigError


def test_resolve_relative_paths(tmp_path: Path) -> None:
    result = _resolve_paths(raw_dir="models", base_dir=tmp_path)

    assert result == tmp_path / "models"


def test_resolve_absolute_paths(tmp_path: Path) -> None:
    abs_path = (tmp_path / "extra_models").resolve()
    result = _resolve_paths(raw_dir=str(abs_path), base_dir=tmp_path)

    assert result == abs_path


def test_default_values(sample_config: ProjectConfig, tmp_path: Path) -> None:
    assert sample_config.database == ":memory:"
    assert sample_config.schema == "main"
    assert sample_config.default_materialization == "view"
    assert sample_config.target_path == tmp_path / "target"
    assert sample_config.name == "sample_project"


def test_immmutability(sample_config: ProjectConfig) -> None:
    with pytest.raises(FrozenInstanceError):
        setattr(sample_config, "name", "new_sample_project")


def test_materialization_default(sample_config: ProjectConfig) -> None:
    result = sample_config._resolve_materialization()
    assert result == "view"


def test_folder_override_hit(sample_config: ProjectConfig) -> None:
    result = sample_config._resolve_materialization(folder="marts")
    assert result == "table"


def test_folder_override_miss(sample_config: ProjectConfig) -> None:
    result = sample_config._resolve_materialization(folder="staging")
    assert result == "view"


def test_model_config_override(sample_config: ProjectConfig) -> None:
    result = sample_config._resolve_materialization(
        folder="marts", model_materialization="view"
    )
    assert result == "view"


def test_cli_config_override(sample_config: ProjectConfig) -> None:
    result = sample_config._resolve_materialization(
        folder="marts", model_materialization="view", cli_materialization="table"
    )
    assert result == "table"


def test_invalid_cli_materialization(sample_config: ProjectConfig) -> None:
    with pytest.raises(ConfigError, match="Invalid materialization"):
        sample_config._resolve_materialization(cli_materialization="incremental")


def test_load_project_by_directory(tmp_path: Path) -> None:
    config_file = tmp_path / "dbtmini_project.yml"
    config_file.write_text('name: "my_project"\nschema: "dev"\n', encoding="utf-8")

    result = _project_directory(tmp_path)
    assert result["name"] == "my_project"
    assert result["schema"] == "dev"


def test_load_project_by_file_path(tmp_path: Path) -> None:
    config_file = tmp_path / "custom_config.yml"
    config_file.write_text('name: "direct_file_project"\n', encoding="utf-8")

    result = _project_directory(config_file)
    assert result["name"] == "direct_file_project"


def test_load_example_project(example_project_dir: Path) -> None:
    result = _project_directory(example_project_dir)

    assert result["name"] == "example_project"
    assert result["schema"] == "main"
    assert result["models"]["materialized"] == "view"
    assert result["models"]["marts"]["materialized"] == "table"


def test_missing_config_directory(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        _project_directory(tmp_path)


def test_missing_config_file_path(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        _project_directory(tmp_path / "nonexistent.yml")


def test_malformed_yaml(tmp_path: Path) -> None:
    config_file = tmp_path / "dbtmini_project.yml"
    config_file.write_text("name: [unclosed\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="Failed"):
        _project_directory(config_file)


def test_empty_yaml_file(tmp_path: Path) -> None:
    config_file = tmp_path / "dbtmini_project.yml"
    config_file.write_text("", encoding="utf-8")

    with pytest.raises(ConfigError, match="must be a dictionary"):
        _project_directory(config_file)


def test_non_dict_yaml_list(tmp_path: Path) -> None:
    config_file = tmp_path / "dbtmini_project.yml"
    config_file.write_text("- item1\n- item2\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="must be a dictionary"):
        _project_directory(config_file)


def test_missing_required_name(tmp_path: Path) -> None:
    config_file = tmp_path / "dbtmini_project.yml"
    config_file.write_text('schema: "main"\n', encoding="utf-8")

    with pytest.raises(ConfigError, match="Missing required key 'name'"):
        _project_directory(config_file)


def test_non_string_name(tmp_path: Path) -> None:
    config_file = tmp_path / "dbtmini_project.yml"
    config_file.write_text("name: 123\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="must be a string"):
        _project_directory(config_file)


def test_unknown_project_key(tmp_path: Path) -> None:
    config_file = tmp_path / "dbtmini_project.yml"
    config_file.write_text('name: "proj"\nunknown_key: true\n', encoding="utf-8")

    with pytest.raises(ConfigError, match="Invalid key"):
        _project_directory(config_file)
