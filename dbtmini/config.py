from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from dbtmini.errors import ConfigError

VALID_MATERIALIZATIONS = {"view", "table"}
ALLOWED_PROJECT_KEYS = {
    "name",
    "version",
    "model-paths",
    "model_paths",
    "seed-paths",
    "seed_paths",
    "test-paths",
    "test_paths",
    "target-path",
    "target_path",
    "database",
    "schema",
    "models",
}


@dataclass(frozen=True)
class ProjectConfig:
    name: str
    project_path: Path
    model_paths: tuple[Path, ...]
    seed_paths: tuple[Path, ...]
    test_paths: tuple[Path, ...]
    target_path: Path
    database: str = ":memory:"
    schema: str = "main"
    default_materialization: str = "view"
    folder_overrides: dict[str, str] = field(default_factory=dict, hash=False)

    def _resolve_materialization(
        self,
        folder: str | None = None,
        model_materialization: str | None = None,
        cli_materialization: str | None = None,
    ) -> str:

        if cli_materialization:
            if cli_materialization not in VALID_MATERIALIZATIONS:
                raise ConfigError(
                    f"Invalid materialization: {cli_materialization}. "
                    f"Allowed: {', '.join(VALID_MATERIALIZATIONS)}"
                )
            return cli_materialization

        if model_materialization:
            return model_materialization
        if folder and folder in self.folder_overrides:
            return self.folder_overrides[folder]
        return self.default_materialization


def _resolve_paths(raw_dir: str, base_dir: Path) -> Path:
    p = Path(raw_dir)
    if p.is_absolute():
        return p
    else:
        return base_dir / p


def _project_directory(project_dir_or_file: str | Path) -> dict[str, Any]:
    """
    Load and validate a dbtmini project configuration file.
    Resolves the configuration file path, parses the YAML contents, verifies
    all required keys are present, and validates that field types and values match
    the expected schema.
    Args:
        project_dir_or_file: Path to the project directory containing
            'dbtmini_project.yml', or a direct path to the configuration file.
    Returns:
        dict[str, Any]: The parsed and validated project configuration dictionary.
    Raises:
        ConfigError: If the configuration file is missing, contains invalid YAML,
            has unknown keys, or fails schema validation.
    """
    target = Path(project_dir_or_file).resolve()
    if target.is_dir():
        project_file = target / "dbtmini_project.yml"
    else:
        project_file = target

    if not project_file.is_file():
        raise ConfigError(
            message="Project Configuration file not found", file_path=project_file
        )
    with open(project_file, "r", encoding="utf-8") as f:
        try:
            config_file = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigError(
                message=f"Failed to parse the config file: {e}", file_path=project_file
            )

        if not isinstance(config_file, dict):
            raise ConfigError(
                message="Project configuration must be a dictionary",
                file_path=project_file,
            )

        if "name" not in config_file:
            raise ConfigError(
                message="Missing required key 'name' in dbtmini project file."
            )
        if not isinstance(config_file["name"], str):
            raise ConfigError(message="Project name must be a string")

        for key in config_file.keys():
            if key not in ALLOWED_PROJECT_KEYS:
                raise ConfigError(message="Invalid key in dbtmini project file")
    return config_file
