from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb

from dbtmini.errors import ProjectError
from dbtmini.materialization import build_relation_name


@dataclass(frozen=True)
class SeedResult:
    name: str
    file_path: Path
    row_count: int
    columns: tuple[str, ...]


def _validate_csv(file_path: Path) -> None:
    if not file_path.is_file():
        raise ProjectError(message=f"{file_path} is not a file", file_path=file_path)

    file_content = file_path.read_text(encoding="utf-8")
    if not file_content:
        raise ProjectError(
            message=f"Seed file '{file_path.name}' is empty", file_path=file_path
        )

    lines = file_content.splitlines()
    header = lines[0].strip()
    if not header:
        raise ProjectError(
            message=f"Seed file has no header row: {file_path}",
            file_path=file_path,
        )

    if len(lines) < 2:
        raise ProjectError(
            message=f"Seed file has a header but no data rows: {file_path}",
            file_path=file_path,
        )


def load_seed(
    conn: duckdb.DuckDBPyConnection, name: str, file_path: Path, schema: str = "main"
) -> SeedResult:

    _validate_csv(file_path)
    relation_name = build_relation_name(schema, name)

    normalised_path = file_path.resolve().as_posix()
    try:
        conn.execute(f"""
            CREATE OR REPLACE TABLE {relation_name} AS
            SELECT * FROM read_csv('{normalised_path}', header=true, strict_mode=false);
            """)
    except duckdb.Error as e:
        raise ProjectError(
            message=f"Failed to load seed '{name}' from {file_path}: {e}",
            file_path=file_path,
        )
    result = conn.execute(f"SELECT COUNT(*) FROM {relation_name}").fetchone()
    row_count = result[0] if result else 0

    columns_result = conn.execute(
        f"SELECT column_name FROM information_schema.columns "
        f"WHERE table_schema = '{schema}' AND table_name = '{name}' "
        f"ORDER BY ordinal_position"
    ).fetchall()
    columns = tuple(row[0] for row in columns_result)

    return SeedResult(
        name=name, file_path=file_path, row_count=row_count, columns=columns
    )


def load_seeds(
    conn: duckdb.DuckDBPyConnection, seeds: dict[str, Path], schema: str = "main"
) -> list[SeedResult]:
    results = []
    for name in sorted(seeds.keys()):
        file_path = seeds[name]

        result = load_seed(conn, name, file_path, schema)
        results.append(result)

    return results
