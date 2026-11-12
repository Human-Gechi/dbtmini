import pytest

from dbtmini.errors import ConfigError
from dbtmini.materialization import (
    Materialization,
    _strip_trailing_colons,
    build_relation_name,
    quote_identifier,
)


def test_valid_materialization_strings() -> None:
    assert Materialization.from_Str("view") is Materialization.VIEW
    assert Materialization.from_Str("table") is Materialization.TABLE


def test_materialization_casing_and_whitespacing() -> None:
    assert Materialization.from_Str(" VIEW") is Materialization.VIEW
    assert Materialization.from_Str("Table\n") is Materialization.TABLE


def test_unsupporte_materialization() -> None:
    with pytest.raises(ConfigError, match="Unsupported materialization"):
        Materialization.from_Str("incremental")


def test_quote_identifier_present() -> None:
    result = quote_identifier(name="main")
    assert result == '"main"'


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
