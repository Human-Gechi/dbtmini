from pathlib import Path

from typer.testing import CliRunner

from dbtmini.cli import app


def test_compile_valid_project(cli_runner: CliRunner, valid_project_dir: Path) -> None:
    result = cli_runner.invoke(
        app, ["compile", "--project-dir", str(valid_project_dir)]
    )
    assert result.exit_code == 0
    assert "Compilation complete" in result.output

    compiled_dir = valid_project_dir / "target" / "compiled"
    assert compiled_dir.exists()
    assert (compiled_dir / "model_a.sql").exists()


def test_compile_cyclic_project(
    cli_runner: CliRunner, cyclic_project_dir: Path
) -> None:
    result = cli_runner.invoke(
        app, ["compile", "--project-dir", str(cyclic_project_dir)]
    )
    assert result.exit_code == 2
    assert "Cycle detected" in result.output


def test_compile_missing_ref_project(
    cli_runner: CliRunner, missing_ref_project_dir: Path
) -> None:
    result = cli_runner.invoke(
        app, ["compile", "--project-dir", str(missing_ref_project_dir)]
    )
    assert result.exit_code == 2
    assert "non_existent_model" in result.output


def test_compile_duplicate_names_project(
    cli_runner: CliRunner, duplicate_names_project_dir: Path
) -> None:
    result = cli_runner.invoke(
        app, ["compile", "--project-dir", str(duplicate_names_project_dir)]
    )
    assert result.exit_code == 2
    assert "Duplicate model" in result.output


def test_run_valid_project(cli_runner: CliRunner, valid_project_dir: Path) -> None:
    result = cli_runner.invoke(app, ["run", "--project-dir", str(valid_project_dir)])
    assert result.exit_code == 0
    assert "MODEL" in result.output
    assert "SUCCESS" in result.output

    target_dir = valid_project_dir / "target"
    json_files = list(target_dir.glob("run_results_*.json"))
    assert len(json_files) >= 1


def test_run_cyclic_project(cli_runner: CliRunner, cyclic_project_dir: Path) -> None:
    result = cli_runner.invoke(app, ["run", "--project-dir", str(cyclic_project_dir)])
    assert result.exit_code == 2
    assert "Cycle detected" in result.output


def test_build_valid_project(cli_runner: CliRunner, valid_project_dir: Path) -> None:
    result = cli_runner.invoke(app, ["build", "--project-dir", str(valid_project_dir)])
    assert result.exit_code == 0
    assert "RUNNING dbtmini run" in result.output
    assert "RUNNING dbtmini test" in result.output


def test_build_failing_test_project(
    cli_runner: CliRunner, failing_test_project_dir: Path
) -> None:
    result = cli_runner.invoke(
        app, ["build", "--project-dir", str(failing_test_project_dir)]
    )
    assert result.exit_code == 1
    assert "FAIL" in result.output
