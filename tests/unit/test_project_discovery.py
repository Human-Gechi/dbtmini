from pathlib import Path

import pytest

from dbtmini.errors import ProjectError
from dbtmini.project import discover_models, discover_seeds, discover_tests


def test_discover_models_basic(tmp_path: Path) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()

    (models_dir / "orders.sql").write_text(
        "SELECT * FROM raw_orders;", encoding="utf-8"
    )
    (models_dir / "customers.sql").write_text(
        "SELECT * FROM raw_customers;", encoding="utf-8"
    )

    models = discover_models(model_paths=[models_dir])

    assert len(models) == 2
    assert models[0].name == "customers"
    assert models[1].name == "orders"
    assert models[0].sql_text == "SELECT * FROM raw_customers;"
    assert models[1].sql_text == "SELECT * FROM raw_orders;"


def test_discover_models_nested_folders(tmp_path: Path) -> None:
    models_dir = tmp_path / "models"
    marts_dir = models_dir / "marts"
    staging_dir = models_dir / "staging" / "core"
    marts_dir.mkdir(parents=True)
    staging_dir.mkdir(parents=True)

    (models_dir / "root_model.sql").write_text("SELECT 1;", encoding="utf-8")
    (marts_dir / "dim_users.sql").write_text("SELECT 2;", encoding="utf-8")
    (staging_dir / "stg_users.sql").write_text("SELECT 3;", encoding="utf-8")

    models = discover_models(model_paths=[models_dir])
    by_name = {m.name: m for m in models}

    assert by_name["root_model"].folder == ""
    assert by_name["dim_users"].folder == "marts"
    assert by_name["stg_users"].folder == "staging/core"


def test_discover_models_extract_config(tmp_path: Path) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()

    sql_with_config = "{{ config(materialized='table') }}\nSELECT * FROM raw_data;"
    (models_dir / "table_model.sql").write_text(sql_with_config, encoding="utf-8")
    (models_dir / "plain_model.sql").write_text("SELECT 1;", encoding="utf-8")

    models = discover_models(model_paths=[models_dir])
    by_name = {m.name: m for m in models}

    assert by_name["table_model"].config == {"materialized": "table"}
    assert by_name["plain_model"].config == {}


def test_discover_models_duplicate_name_error(tmp_path: Path) -> None:
    models_dir = tmp_path / "models"
    dir1 = models_dir / "folder1"
    dir2 = models_dir / "folder2"
    dir1.mkdir(parents=True)
    dir2.mkdir(parents=True)

    (dir1 / "same_model.sql").write_text("SELECT 1;", encoding="utf-8")
    (dir2 / "same_model.sql").write_text("SELECT 2;", encoding="utf-8")

    with pytest.raises(ProjectError, match="Duplicate model 'same_model' found"):
        discover_models(model_paths=[models_dir])


def test_discover_models_invalid_name_error(tmp_path: Path) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()

    (models_dir / "invalid-model-name.sql").write_text("SELECT 1;", encoding="utf-8")

    with pytest.raises(ProjectError, match="Invalid model name 'invalid-model-name'"):
        discover_models(model_paths=[models_dir])


def test_discover_models_ignores_hidden_and_non_sql(tmp_path: Path) -> None:
    models_dir = tmp_path / "models"
    models_dir.mkdir()

    (models_dir / "valid_model.sql").write_text("SELECT 1;", encoding="utf-8")
    (models_dir / ".hidden_model.sql").write_text("SELECT 2;", encoding="utf-8")
    (models_dir / "notes.txt").write_text("Documentation", encoding="utf-8")
    (models_dir / "README.md").write_text("# Readme", encoding="utf-8")

    models = discover_models(model_paths=[models_dir])

    assert len(models) == 1
    assert models[0].name == "valid_model"


def test_discover_models_empty_warning(tmp_path: Path) -> None:
    empty_dir = tmp_path / "empty_models"
    empty_dir.mkdir()

    with pytest.warns(UserWarning, match="No models found in configured model paths"):
        models = discover_models(model_paths=[empty_dir])

    assert models == []


def test_discover_seeds_basic(tmp_path: Path) -> None:
    seeds_dir = tmp_path / "seeds"
    seeds_dir.mkdir()

    (seeds_dir / "raw_customers.csv").write_text("id,name\n1,Alice\n", encoding="utf-8")
    (seeds_dir / "raw_orders.csv").write_text("id,amount\n1,100\n", encoding="utf-8")

    seeds = discover_seeds(seed_paths=[seeds_dir])

    assert set(seeds.keys()) == {"raw_customers", "raw_orders"}
    assert seeds["raw_customers"] == seeds_dir / "raw_customers.csv"
    assert seeds["raw_orders"] == seeds_dir / "raw_orders.csv"


def test_discover_seeds_ignores_hidden_and_non_csv(tmp_path: Path) -> None:
    seeds_dir = tmp_path / "seeds"
    seeds_dir.mkdir()

    (seeds_dir / "valid_seed.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    (seeds_dir / ".hidden_seed.csv").write_text("x,y\n3,4\n", encoding="utf-8")
    (seeds_dir / "notes.txt").write_text("seed notes", encoding="utf-8")

    seeds = discover_seeds(seed_paths=[seeds_dir])

    assert list(seeds.keys()) == ["valid_seed"]


def test_discover_tests_basic(tmp_path: Path) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()

    schema_yml = """
models:
  - name: customers
    columns:
      - name: customer_id
        tests:
          - not_null
          - unique
"""
    (tests_dir / "tests.yml").write_text(schema_yml, encoding="utf-8")

    test_specs = discover_tests(test_paths=[tests_dir])

    assert len(test_specs) == 2
    assert test_specs[0].name == "customers"
    assert test_specs[0].column == "customer_id"
    assert test_specs[0].test_type == "not_null"

    assert test_specs[1].name == "customers"
    assert test_specs[1].column == "customer_id"
    assert test_specs[1].test_type == "unique"


def test_discover_tests_unsupported_test_error(tmp_path: Path) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()

    schema_yml = """
models:
  - name: customers
    columns:
      - name: status
        tests:
          - accepted_values:
              values: ['active', 'inactive']
"""
    (tests_dir / "tests.yml").write_text(schema_yml, encoding="utf-8")

    with pytest.raises(ProjectError, match="Unsupported test 'accepted_values'"):
        discover_tests(test_paths=[tests_dir])


def test_discover_tests_empty_or_non_dict_yaml(tmp_path: Path) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()

    (tests_dir / "empty.yml").write_text("", encoding="utf-8")
    (tests_dir / "list.yml").write_text("- item1\n- item2\n", encoding="utf-8")

    test_specs = discover_tests(test_paths=[tests_dir])
    assert test_specs == []
