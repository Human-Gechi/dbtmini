import json
from pathlib import Path

from dbtmini.materialization import Materialization
from dbtmini.results import (
    ModelResult,
    RunResult,
    RunStatus,
    format_summary_results,
    write_run_results,
)


def test_run_result_counts_success() -> None:
    results = [
        ModelResult(
            model_name="stg_customers",
            status=RunStatus.SUCCESS,
            duration=0.05,
            materialization=Materialization.VIEW,
            message="OK",
        ),
        ModelResult(
            model_name="dim_customers",
            status=RunStatus.SUCCESS,
            duration=0.12,
            materialization=Materialization.TABLE,
            message="OK",
        ),
    ]
    run_result = RunResult(result=results, elasped_time=0.17)

    assert run_result.success_count == 2
    assert run_result.error_count == 0
    assert run_result.total_count == 2
    assert run_result.exit_code == 0


def test_run_result_counts_with_errors() -> None:
    results = [
        ModelResult(
            model_name="stg_orders",
            status=RunStatus.SUCCESS,
            duration=0.04,
            materialization=Materialization.VIEW,
            message="OK",
        ),
        ModelResult(
            model_name="fct_orders",
            status=RunStatus.ERROR,
            duration=0.02,
            materialization=Materialization.TABLE,
            message="Table error",
        ),
    ]
    run_result = RunResult(result=results, elasped_time=0.06)

    assert run_result.success_count == 1
    assert run_result.error_count == 1
    assert run_result.total_count == 2
    assert run_result.exit_code == 1


def test_write_run_results(tmp_path: Path) -> None:
    target_dir = tmp_path / "target"
    results = [
        ModelResult(
            model_name="stg_orders",
            status=RunStatus.SUCCESS,
            duration=0.04,
            materialization=Materialization.VIEW,
            message="OK",
        )
    ]
    run_result = RunResult(result=results, elasped_time=0.04)

    file_path = write_run_results(run_result, target_path=target_dir)

    assert file_path.exists()
    assert file_path.suffix == ".json"

    data = json.loads(file_path.read_text(encoding="utf-8"))
    assert data["elasped_time"] == 0.04
    assert len(data["result"]) == 1
    assert data["result"][0]["model_name"] == "stg_orders"


def test_format_summary_results() -> None:
    results = [
        ModelResult(
            model_name="stg_orders",
            status=RunStatus.SUCCESS,
            duration=0.042,
            materialization=Materialization.VIEW,
            message="OK",
        ),
        ModelResult(
            model_name="broken_model",
            status=RunStatus.ERROR,
            duration=0.015,
            materialization=Materialization.TABLE,
            message="Syntax error",
        ),
    ]
    run_result = RunResult(result=results, elasped_time=0.057)

    summary = format_summary_results(run_result)

    assert "MODEL" in summary
    assert "stg_orders" in summary
    assert "SUCCESS" in summary
    assert "broken_model" in summary
    assert "ERROR" in summary
    assert "Summary: 1 passed, 1 failed, 2 total" in summary
