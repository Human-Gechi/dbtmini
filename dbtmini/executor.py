from __future__ import annotations

import time
from pathlib import Path

import duckdb

from dbtmini.config import ProjectConfig
from dbtmini.errors import ExecutionError
from dbtmini.materialization import (
    Materialization,
    build_create_statement,
    build_switch_statement,
    resolve_materialization,
)
from dbtmini.models import Model
from dbtmini.renderer import render_model
from dbtmini.results import ModelResult, RunResult, RunStatus
from dbtmini.seeds import SeedResult, load_seeds


def _get_existing_relation_type(
    conn: duckdb.DuckDBPyConnection, schema: str, model_name: str
) -> str | None:
    """Return the existing relation type ('BASE TABLE' or 'VIEW') in DuckDB, or None."""
    row = conn.execute(
        "SELECT table_type FROM information_schema.tables "
        "WHERE table_schema = ? AND table_name = ?",
        [schema, model_name],
    ).fetchone()
    return row[0] if row else None


def execute_project(
    conn: duckdb.DuckDBPyConnection,
    config: ProjectConfig,
    models: dict[str, Model],
    execution_order: list[str],
    seeds: dict[str, Path],
) -> RunResult:

    conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{config.schema}";')

    seed_results: list[SeedResult] = load_seeds(conn, seeds=seeds, schema=config.schema)

    known_nodes: set[str] = set(models.keys()) | set(seeds.keys())

    start_time = time.perf_counter()
    model_results: list[ModelResult] = []

    for model_name in execution_order:
        model = models[model_name]

        rendered_sql = render_model(
            model=model,
            known_models=known_nodes,
            schema=config.schema,
        )

        model_mat = model.config.get("materialized")
        materialization = resolve_materialization(
            config=config,
            folder=model.folder,
            model_materialization=model_mat,
        )

        existing_type = _get_existing_relation_type(conn, config.schema, model_name)
        if existing_type is not None and (
            (existing_type.upper() == "VIEW")
            != (materialization == Materialization.VIEW)
        ):
            statements = build_switch_statement(
                model_name=model_name,
                switch_materialization=materialization,
                sql=rendered_sql,
                schema=config.schema,
            )
        else:
            statements = [
                build_create_statement(
                    model_name=model_name,
                    sql=rendered_sql,
                    materialization=materialization,
                    schema=config.schema,
                )
            ]

        t0 = time.perf_counter()
        try:
            for statement in statements:
                conn.execute(statement)
        except duckdb.Error as e:
            raise ExecutionError(
                message=f"Database execution error: {e}",
                file_path=model.file_path,
                model_name=model_name,
            ) from e
        duration = time.perf_counter() - t0

        # Record outcome
        model_results.append(
            ModelResult(
                model_name=model_name,
                status=RunStatus.SUCCESS,
                duration=duration,
                materialization=materialization,
                message="OK",
            )
        )

    elapsed_time = time.perf_counter() - start_time

    return RunResult(
        result=model_results, elasped_time=elapsed_time, seed_results=seed_results
    )
