from pathlib import Path

import duckdb
from typer.testing import CliRunner

from dbtmini.cli import _load_config, app
from dbtmini.dag import topological_sort
from dbtmini.executor import execute_project
from dbtmini.project import discover_models, discover_seeds, discover_tests
from dbtmini.renderer import build_dependencies
from dbtmini.tests_runner import TestStatus, run_tests


def test_end_to_end_example_project_pipeline(example_project_dir: Path) -> None:
    config = _load_config(example_project_dir)
    models = discover_models(config.model_paths)
    seeds = discover_seeds(config.seed_paths)
    tests = discover_tests(config.test_paths)

    assert len(models) == 7
    assert len(seeds) == 3

    dependencies: dict[str, set[str]] = {s: set() for s in seeds}
    for model in models:
        parse_res = build_dependencies(model)
        dependencies[model.name] = set(parse_res.dependencies)

    build_order = topological_sort(dependencies)
    execution_order = [name for name in build_order if name not in seeds]
    models_dict = {m.name: m for m in models}

    db_path = example_project_dir / "target" / "test_run.duckdb"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(db_path))

    try:
        # First execution run
        run_res_1 = execute_project(
            conn=conn,
            config=config,
            models=models_dict,
            execution_order=execution_order,
            seeds=seeds,
        )

        assert run_res_1.error_count == 0
        assert run_res_1.success_count == 7

        # Verify tables and views exist with rows
        cust_row = conn.execute('SELECT COUNT(*) FROM "main"."customers";').fetchone()
        assert cust_row is not None
        assert cust_row[0] == 5

        dim_row = conn.execute(
            'SELECT COUNT(*) FROM "main"."dim_customers";'
        ).fetchone()
        assert dim_row is not None
        assert dim_row[0] == 5

        # Verify idempotency: re-running does not crash or double rows
        run_res_2 = execute_project(
            conn=conn,
            config=config,
            models=models_dict,
            execution_order=execution_order,
            seeds=seeds,
        )
        assert run_res_2.error_count == 0
        assert run_res_2.success_count == 7

        cust_row_after = conn.execute(
            'SELECT COUNT(*) FROM "main"."customers";'
        ).fetchone()
        assert cust_row_after is not None
        assert cust_row_after[0] == 5

        # Run tests against the loaded schema
        test_results = run_tests(conn, tests, schema=config.schema)
        assert len(test_results) > 0
        pass_count = sum(1 for r in test_results if r.status == TestStatus.PASS)
        assert pass_count > 0

    finally:
        conn.close()


def test_cli_end_to_end_build(cli_runner: CliRunner, example_project_dir: Path) -> None:
    result = cli_runner.invoke(
        app,
        ["build", "--project-dir", str(example_project_dir), "--database", ":memory:"],
    )
    # The build runs models and then tests
    assert "RUNNING dbtmini run" in result.output
    assert "RUNNING dbtmini test" in result.output
    assert (example_project_dir / "target").exists()
