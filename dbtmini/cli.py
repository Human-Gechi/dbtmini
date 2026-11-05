from pathlib import Path

import typer

from dbtmini.dag import topological_sort
from dbtmini.errors import DbtminiError
from dbtmini.project import discover_models, discover_seeds
from dbtmini.renderer import build_dependencies, render_model

app = typer.Typer(help="dbtmini CLI")


@app.command()
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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
