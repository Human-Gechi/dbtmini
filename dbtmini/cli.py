from pathlib import Path

import duckdb
import typer

from dbtmini.config import ProjectConfig, _project_directory, _resolve_paths
from dbtmini.dag import topological_sort
from dbtmini.errors import DbtminiError
from dbtmini.executor import execute_project
from dbtmini.project import discover_models, discover_seeds, discover_tests
from dbtmini.renderer import build_dependencies, render_model
from dbtmini.results import format_summary_results, write_run_results
from dbtmini.tests_runner import TestStatus, format_test_summary, run_tests

app = typer.Typer(help="dbtmini CLI")


def _load_config(
    project_dir: Path,
    target_schema: str | None = None,
    database: str | None = None,
) -> ProjectConfig:
    project_config = _project_directory(project_dir)
    models_config = project_config.get("models", {})
    default_mat = "view"

    folder_overrides: dict[str, str] = {}
    if isinstance(models_config, dict):
        if "materialized" in models_config and isinstance(
            models_config["materialized"], str
        ):
            default_mat = models_config["materialized"]

        for folder, settings in models_config.items():
            if isinstance(settings, dict) and "materialized" in settings:
                folder_overrides[folder] = settings["materialized"]

    raw_model_paths = project_config.get("model-paths") or project_config.get(
        "model_paths", ["models"]
    )
    raw_seed_paths = project_config.get("seed-paths") or project_config.get(
        "seed_paths", ["seeds"]
    )
    raw_test_paths = project_config.get("test-paths") or project_config.get(
        "test_paths", ["tests"]
    )
    raw_target_path = project_config.get("target-path") or project_config.get(
        "target_path", "target"
    )

    return ProjectConfig(
        name=project_config["name"],
        project_path=project_dir.resolve(),
        model_paths=tuple(_resolve_paths(p, project_dir) for p in raw_model_paths),
        seed_paths=tuple(_resolve_paths(p, project_dir) for p in raw_seed_paths),
        test_paths=tuple(_resolve_paths(p, project_dir) for p in raw_test_paths),
        target_path=_resolve_paths(raw_target_path, project_dir),
        database=database or project_config.get("database", ":memory:"),
        schema=target_schema or project_config.get("schema", "main"),
        default_materialization=default_mat,
        folder_overrides=folder_overrides,
    )


@app.command(name="compile")
def dbtmini_compile(
    project_dir: Path = typer.Option(
        Path("example_project"),
        "--project-dir",
        "-d",
        help="Path to project directory",
    ),
    target_schema: str = typer.Option("main", "--schema", "-s", help="Target schema"),
) -> None:
    try:
        models = discover_models(model_paths=project_dir)
        seeds = discover_seeds(seed_paths=project_dir)

        known_models = {m.name for m in models} | set(seeds.keys())

        dependencies: dict[str, set[str]] = {}
        for seed_name in seeds:
            dependencies[seed_name] = set()

        for model in models:
            parse_res = build_dependencies(model)
            dependencies[model.name] = set(parse_res.dependencies)

        # 4. Topological Sort via DAG
        build_order = topological_sort(dependencies)

        model_order = [name for name in build_order if name not in seeds]
        typer.echo("-> ".join(model_order))

        target_dir = project_dir / "target" / "compiled"
        for model in models:
            compiled_sql = render_model(
                model=model,
                known_models=known_models,
                schema=target_schema,
            )

            out_folder = target_dir / model.folder if model.folder else target_dir
            out_folder.mkdir(parents=True, exist_ok=True)
            (out_folder / f"{model.name}.sql").write_text(
                compiled_sql, encoding="utf-8"
            )

        typer.echo("Compilation complete.")

    except DbtminiError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=2)


@app.command(name="run")
def dbtmini_run(
    project_dir: Path = typer.Option(
        Path("example_project"),
        "--project-dir",
        "-d",
        help="Path to project directory",
    ),
    target_schema: str | None = typer.Option(
        None,
        "--schema",
        "-s",
        help="Target schema can override project config file",
    ),
    database: str | None = typer.Option(
        None,
        "--database",
        help="Database can override project config file",
    ),
) -> None:
    try:
        config = _load_config(project_dir, target_schema, database)

        models = discover_models(model_paths=config.model_paths)
        seeds = discover_seeds(seed_paths=config.seed_paths)

        dependencies: dict[str, set[str]] = {s: set() for s in seeds}
        for model in models:
            parse_res = build_dependencies(model=model)
            dependencies[model.name] = set(parse_res.dependencies)

        build_order = topological_sort(dependencies)
        execution_order = [name for name in build_order if name not in seeds]
        models_dict = {m.name: m for m in models}

        conn = duckdb.connect(config.database)
        try:
            run_result = execute_project(
                conn=conn,
                config=config,
                models=models_dict,
                execution_order=execution_order,
                seeds=seeds,
            )
        finally:
            conn.close()
        typer.echo(format_summary_results(run_result=run_result))

        write_run_results(run_results=run_result, target_path=config.target_path)
        if run_result.error_count != 0:
            raise typer.Exit(1)
    except DbtminiError as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(2)


@app.command(name="test")
def dbtmini_test(
    project_dir: Path = typer.Option(
        Path("example_project"),
        "--project-dir",
        "-d",
        help="Path to project directory",
    ),
    target_schema: str | None = typer.Option(
        None,
        "--schema",
        "-s",
        help="Target schema can override project config file",
    ),
    database: str | None = typer.Option(
        None,
        "--database",
        help="Database can override project config file",
    ),
) -> None:
    config = _load_config(project_dir, target_schema, database)
    tests = discover_tests(test_paths=config.test_paths)

    conn = duckdb.connect(config.database)
    try:
        test_results = run_tests(conn=conn, test_specs=tests, schema=config.schema)
    finally:
        conn.close()

    typer.echo(format_test_summary(test_results=test_results))

    has_failures = any(r.status != TestStatus.PASS for r in test_results)
    if has_failures:
        raise typer.Exit(1)


@app.command(name="build")
def dbtmini_build(
    project_dir: Path = typer.Option(
        Path("example_project"),
        "--project-dir",
        "-d",
        help="Path to project directory",
    ),
    target_schema: str | None = typer.Option(
        None,
        "--schema",
        "-s",
        help="Target schema can override project config file",
    ),
    database: str | None = typer.Option(
        None,
        "--database",
        help="Database can override project config file",
    ),
) -> None:
    try:
        config = _load_config(project_dir, target_schema, database)

        models = discover_models(model_paths=config.model_paths)
        seeds = discover_seeds(seed_paths=config.seed_paths)
        tests = discover_tests(test_paths=config.test_paths)

        dependencies: dict[str, set[str]] = {s: set() for s in seeds}
        for model in models:
            parse_res = build_dependencies(model=model)
            dependencies[model.name] = set(parse_res.dependencies)

        build_order = topological_sort(dependencies)
        execution_order = [name for name in build_order if name not in seeds]
        models_dict = {m.name: m for m in models}

        conn = duckdb.connect(config.database)
        try:
            run_result = execute_project(
                conn=conn,
                config=config,
                models=models_dict,
                execution_order=execution_order,
                seeds=seeds,
            )
            typer.echo("RUNNING dbtmini run")
            typer.echo(format_summary_results(run_result=run_result))
            write_run_results(run_results=run_result, target_path=config.target_path)
            typer.echo()

            typer.echo("RUNNING dbtmini test")
            typer.echo()
            test_results = run_tests(conn=conn, test_specs=tests, schema=config.schema)
            typer.echo(format_test_summary(test_results=test_results))
        finally:
            conn.close()

        has_failures = (run_result.error_count != 0) or any(
            r.status != TestStatus.PASS for r in test_results
        )
        if has_failures:
            raise typer.Exit(1)
    except DbtminiError as e:
        typer.echo(f"Error: {e}")
        raise typer.Exit(2)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
