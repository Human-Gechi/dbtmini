import pytest

from dbtmini.config import ProjectConfig
from dbtmini.errors import ConfigError
from dbtmini.materialization import (
    Materialization,
    _strip_trailing_colons,
    build_create_statement,
    build_drop_statement,
    build_relation_name,
    build_switch_statement,
    quote_identifier,
    resolve_materialization,
)


def test_valid_materialization_strings() -> None:
    assert Materialization.from_Str("view") is Materialization.VIEW
    assert Materialization.from_Str("table") is Materialization.TABLE


def test_materialization_casing_and_whitespacing() -> None:
    assert Materialization.from_Str(" VIEW") is Materialization.VIEW
    assert Materialization.from_Str("Table\n") is Materialization.TABLE


def test_unsupported_materialization() -> None:
    with pytest.raises(ConfigError, match="Unsupported materialization"):
        Materialization.from_Str("incremental")


def test_quote_identifier_present() -> None:
    result = quote_identifier(name="main")
    assert result == '"main"'


def test_quote_identifier_escaping() -> None:
    result = quote_identifier(name='my"table')
    assert result == '"my""table"'


def test_build_relation_name() -> None:
    result = build_relation_name(schema="main", model_name="stg_customers")
    assert result == '"main"."stg_customers"'


def test_trailing_new_lines() -> None:
    sql = "SELECT * FROM orders\n"
    result = _strip_trailing_colons(sql)
    assert result == "SELECT * FROM orders"


def test_trailing_colons() -> None:
    sql = "SELECT 1;;;"
    result = _strip_trailing_colons(sql)
    assert result == "SELECT 1"


def test_build_create_statement_table() -> None:
    sql = "SELECT id, name FROM raw_users;"
    statement = build_create_statement("users", sql, Materialization.TABLE, "analytics")
    assert (
        statement
        == """CREATE OR REPLACE TABLE "analytics"."users"
        AS (SELECT id, name FROM raw_users);"""
    )


def test_build_create_statement_view() -> None:
    sql = "SELECT 1\n"
    statement = build_create_statement("stg_orders", sql, Materialization.VIEW, "main")
    assert statement == 'CREATE OR REPLACE VIEW "main"."stg_orders" AS (SELECT 1);'


def test_build_drop_statement_table() -> None:
    statement = build_drop_statement("users", Materialization.TABLE, "analytics")
    assert statement == ' DROP TABLE IF EXISTS "analytics"."users";'


def test_build_drop_statement_view() -> None:
    statement = build_drop_statement("orders", Materialization.VIEW, "main")
    assert statement == ' DROP VIEW IF EXISTS "main"."orders";'


def test_build_switch_statement_to_table() -> None:
    statement = build_switch_statement(
        "customers", Materialization.TABLE, "SELECT * FROM raw", "main"
    )
    assert len(statement) == 2
    assert statement[0] == ' DROP VIEW IF EXISTS "main"."customers";'
    assert (
        statement[1]
        == 'CREATE OR REPLACE TABLE "main"."customers" AS (SELECT * FROM raw);'
    )


def test_build_switch_statement_to_view() -> None:
    statement = build_switch_statement(
        "customers", Materialization.VIEW, "SELECT * FROM raw", "main"
    )
    assert len(statement) == 2
    assert statement[0] == ' DROP TABLE IF EXISTS "main"."customers";'
    assert (
        statement[1]
        == 'CREATE OR REPLACE VIEW "main"."customers" AS (SELECT * FROM raw);'
    )


def test_resolve_materialization_default(sample_config: ProjectConfig) -> None:
    assert resolve_materialization(sample_config) is Materialization.VIEW


def test_resolve_materialization_folder_override(sample_config: ProjectConfig) -> None:
    assert (
        resolve_materialization(sample_config, folder="marts") is Materialization.TABLE
    )


def test_resolve_materialization_model_override(sample_config: ProjectConfig) -> None:
    assert (
        resolve_materialization(
            sample_config, folder="marts", model_materialization="view"
        )
        is Materialization.VIEW
    )


def test_resolve_materialization_cli_override(sample_config: ProjectConfig) -> None:
    assert (
        resolve_materialization(
            sample_config,
            folder="marts",
            model_materialization="view",
            cli_materialization="table",
        )
        is Materialization.TABLE
    )


def test_resolve_materialization_invalid(sample_config: ProjectConfig) -> None:
    with pytest.raises(ConfigError, match="Unsupported materialization"):
        resolve_materialization(sample_config, cli_materialization="invalid_type")
