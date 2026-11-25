from __future__ import annotations

from enum import Enum

from dbtmini.config import ProjectConfig
from dbtmini.errors import ConfigError


class Materialization(str, Enum):
    TABLE = "table"
    VIEW = "view"

    @classmethod
    def from_Str(cls, value: str) -> Materialization:
        try:
            normalized = value.lower().strip()
            return cls(normalized)
        except ValueError:
            raise ConfigError(
                message=f"""Unsupported materialization:
                {cls.TABLE.name}, {cls.VIEW.name} is supported Only
                """
            )


def quote_identifier(name: str) -> str:
    quoted = name.replace('"', '""')

    return f'"{quoted}"'


def build_relation_name(schema: str, model_name: str) -> str:

    quoted_schema = quote_identifier(name=schema)
    quoted_model_name = quote_identifier(name=model_name)

    return f"{quoted_schema}.{quoted_model_name}"


def _strip_trailing_colons(sql: str) -> str:
    trailing = sql.strip().strip("\n").strip(";")
    return trailing


def build_create_statement(
    model_name: str, sql: str, materialization: Materialization, schema: str
) -> str:
    relation = build_relation_name(schema=schema, model_name=model_name)
    kind = materialization.value.upper()
    clean_sql = _strip_trailing_colons(sql=sql)
    create = f"""CREATE OR REPLACE {kind} {relation} AS ({clean_sql});"""

    return create


def build_drop_statement(
    model_name: str, materialization: Materialization, schema: str
) -> str:
    relation = build_relation_name(schema=schema, model_name=model_name)
    kind = materialization.value.upper()

    drop = f""" DROP {kind} IF EXISTS {relation};"""
    return drop


def build_switch_statement(
    model_name: str, switch_materialization: Materialization, sql: str, schema: str
) -> list[str]:
    statements: list[str] = []

    switches = (
        Materialization.TABLE
        if switch_materialization == Materialization.VIEW
        else Materialization.VIEW
    )
    statements.append(build_drop_statement(model_name, switches, schema))
    statements.append(
        build_create_statement(model_name, sql, switch_materialization, schema)
    )

    return statements


def resolve_materialization(
    config: ProjectConfig,
    folder: str | None = None,
    model_materialization: str | None = None,
    cli_materialization: str | None = None,
) -> Materialization:

    resolve = config._resolve_materialization(
        folder, model_materialization, cli_materialization
    )
    return Materialization.from_Str(resolve)
