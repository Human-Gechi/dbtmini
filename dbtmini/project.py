from __future__ import annotations

import re
import warnings
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml

from dbtmini.errors import ProjectError
from dbtmini.models import Model, TestSpec

MODEL_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")
CONFIG_PATTERN = re.compile(
    r"config\s*\(\s*(?:materialized)\s*=\s*['\"](\w+)['\"]\s*\)"
)


def _extract_config(sql_text: str) -> dict[str, Any]:
    """Look for {{ config(materilzed='table') }}
    or {{ config(materialized='view') }}"""
    config: dict[str, Any] = {}
    match = CONFIG_PATTERN.search(sql_text)
    if match:
        config["materialized"] = match.group(1).lower()
    return config


def _normalize_paths(paths: str | Path | Sequence[str | Path]) -> list[Path]:
    if isinstance(paths, (str, Path)):
        return [Path(paths)]
    return [Path(p) for p in paths]


def _validate_model_name(name: str, file_path: Path) -> None:
    """
    Check that a model name follows dbt naming conventions.
    Model names must consist of only alphanumeric characters and underscores,
    and cannot start with a number.

    Args:
        name: The model name to validate.
        file_path: The file path of the model, used for error reporting.

    Raises:
        ProjectError: If the model name is invalid.
    """

    if not MODEL_NAME_PATTERN.match(name):
        raise ProjectError(
            message=f"""Invalid model name '{name}'.
            Only letters, digits, and underscores are allowed.""",
            file_path=file_path,
            model_name=name,
        )


def _get_relative_folder(file_path: Path, base_path: Path) -> str:
    rel_parent = file_path.relative_to(base_path).parent
    return "" if rel_parent == Path(".") else rel_parent.as_posix()


def discover_models(
    model_paths: str | Path | Sequence[str | Path],
    folder: str = "models",
) -> list[Model]:
    normalized_paths = _normalize_paths(model_paths)
    models: list[Model] = []
    seen_models: dict[str, Path] = {}

    for base_path in normalized_paths:
        if (base_path / folder).is_dir():
            base_path = base_path / folder
        elif not base_path.is_dir():
            continue

        for file_path in base_path.rglob("*.sql"):
            if any(part.startswith(".") for part in file_path.parts):
                continue
            if not file_path.is_file():
                continue

            name = file_path.stem
            _validate_model_name(name, file_path)

            # Reject duplicate model names across folders
            if name in seen_models:
                prev_path = seen_models[name]
                raise ProjectError(
                    message=f"""Duplicate model '{name}' found in '{prev_path}'
                    and '{file_path}'""",
                    file_path=file_path,
                    model_name=name,
                )
            seen_models[name] = file_path

            sql_text = file_path.read_text(encoding="utf-8")
            folder_name = _get_relative_folder(file_path, base_path)
            config = _extract_config(sql_text)

            models.append(
                Model(
                    name=name,
                    file_path=file_path,
                    sql_text=sql_text,
                    folder=folder_name,
                    config=config,
                )
            )

    if not models:
        warnings.warn(
            "No models found in configured model paths.", UserWarning, stacklevel=2
        )

    return sorted(models, key=lambda m: m.name)


def discover_seeds(
    seed_paths: str | Path | Sequence[str | Path],
    folder: str = "seeds",
) -> dict[str, Path]:
    normalized_paths = _normalize_paths(seed_paths)
    seeds: dict[str, Path] = {}

    for base_path in normalized_paths:
        # If parent project directory was passed, check for child 'seeds' directory
        if (base_path / folder).is_dir():
            base_path = base_path / folder
        elif not base_path.is_dir():
            continue

        for file_path in base_path.rglob("*.csv"):
            if any(part.startswith(".") for part in file_path.parts):
                continue
            if file_path.is_file():
                seed_name = file_path.stem
                seeds[seed_name] = file_path

    return seeds


def discover_tests(
    test_paths: str | Path | Sequence[str | Path],
    folder: str = "tests",
) -> list[TestSpec]:

    normalized_paths = _normalize_paths(test_paths)
    tests: list[TestSpec] = []

    for base_path in normalized_paths:
        if (base_path / folder).is_dir():
            base_path = base_path / folder
        elif not base_path.is_dir():
            continue

        for file_path in base_path.glob("*.yml"):
            content = file_path.read_text(encoding="utf-8")
            if not content.strip():
                continue
            data = yaml.safe_load(content)
            if not isinstance(data, dict):
                continue

            model_list = data.get("models", [])
            for model in model_list:
                model_name = model.get("name", "")
                columns = model.get("columns", [])
                for col in columns:
                    col_name = col.get("name", "")
                    test_list = col.get("tests", [])
                    for t in test_list:
                        test_type = t if isinstance(t, str) else list(t.keys())[0]
                        if test_type not in ("not_null", "unique"):
                            raise ProjectError(
                                message=f"""Unsupported test '{test_type}'
                                for column '{col_name}'.
                                Allowed: 'not_null', 'unique'""",
                                file_path=file_path,
                                model_name=model_name,
                            )
                        tests.append(
                            TestSpec(
                                name=model_name, column=col_name, test_type=test_type
                            )
                        )
    return tests


# def discover_project(
#    project_dir: str | Path,
#    model_folder: str = "models",
#    seed_folder: str = "seeds",
# ) -> tuple[list[Model], dict[str, Path]]:

#    path = Path(project_dir)
#    models = discover_models(path, folder=model_folder)
#   seeds = discover_seeds(path, folder=seed_folder)
#   return models, seeds
