# dbtmini Architecture

`dbtmini` is a lightweight, local-first version of dbt (data build tool) built with **Python**, **Jinja2**, **DuckDB**, and **Typer**. It reads SQL models, CSV seeds, and YAML tests from your project folder, figures out the right order to run them, executes everything in DuckDB, and checks data quality.

---

## High-Level Data Flow

Every run moves through `dbtmini` in clear, separate stages:

```text
+--------------------------+
| 1. Config & Discovery    |  dbtmini_project.yml, *.sql, *.csv, *.yml
+--------------------------+
             |
             v
+--------------------------+
| 2. Dependency Parsing    |  Jinja2 Pass 1: extract ref() & config()
+--------------------------+
             |
             v
+--------------------------+
| 3. DAG Ordering          |  Topological sort & cycle detection
+--------------------------+
             |
             v
+--------------------------+
| 4. SQL Rendering         |  Jinja2 Pass 2: replace ref() -> "schema"."model"
+--------------------------+
             |
             v
+--------------------------+
| 5. DuckDB Execution      |  Load seeds & create/switch views and tables
+--------------------------+
             |
             v
+--------------------------+
| 6. Data Tests & Results  |  not_null / unique checks & run_results_*.json
+--------------------------+
```

---

## Core Modules (`dbtmini/`)

Each file inside `dbtmini/` owns one job so the codebase stays easy to read and test:

| Module | Responsibility | Key Components |
| :--- | :--- | :--- |
| [cli.py](../dbtmini/cli.py) | Command-line interface built with Typer | `app`, `dbtmini_compile`, `dbtmini_run`, `dbtmini_test`, `dbtmini_build` |
| [config.py](../dbtmini/config.py) | Loads and validates `dbtmini_project.yml` | `ProjectConfig`, `_project_directory`, `_resolve_paths` |
| [models.py](../dbtmini/models.py) | Immutable data structures passed between modules | `Model`, `TestSpec`, `ParseResult` |
| [project.py](../dbtmini/project.py) | Scans folders for models, seeds, and tests | `discover_models`, `discover_seeds`, `discover_tests` |
| [renderer.py](../dbtmini/renderer.py) | Two-pass Jinja2 parser and SQL renderer | `create_environment`, `build_dependencies`, `render_model` |
| [dag.py](../dbtmini/dag.py) | Orders models and catches cycles/missing refs | `topological_sort`, `_find_cycle_path` |
| [materialization.py](../dbtmini/materialization.py) | Resolves `view`/`table` rules and generates DDL | `Materialization`, `resolve_materialization`, `build_create_statement`, `build_drop_statement`, `build_switch_statement` |
| [seeds.py](../dbtmini/seeds.py) | Validates CSV files and loads them into DuckDB | `SeedResult`, `load_seed`, `load_seeds` |
| [executor.py](../dbtmini/executor.py) | Runs seeds and models against DuckDB in order | `execute_project`, `_get_existing_relation_type` |
| [tests_runner.py](../dbtmini/tests_runner.py) | Builds and runs data quality SQL checks | `TestStatus`, `TestResult`, `TEST_REGISTRY`, `run_tests`, `format_test_summary` |
| [results.py](../dbtmini/results.py) | Tracks outcomes, prints tables, saves JSON logs | `RunStatus`, `ModelResult`, `RunResult`, `write_run_results`, `format_summary_results` |
| [errors.py](../dbtmini/errors.py) | Structured errors with stage, file, and model context | `DbtminiError`, `ConfigError`, `ProjectError`, `RenderError`, `DagError`, `CycleError`, `ExecutionError` |

---

## Key Architectural Decisions

### 1. Immutable Data Containers
`ProjectConfig`, `Model`, `TestSpec`, `ParseResult`, `SeedResult`, `ModelResult`, `RunResult`, and `TestResult` are all frozen dataclasses (`@dataclass(frozen=True)`). Once created, they cannot be accidentally modified by downstream steps.

### 2. Two-Pass Jinja2 Rendering
Instead of parsing SQL with fragile regexes to find `{{ ref('...') }}`, `dbtmini` uses Jinja2 itself in two passes:
- **Pass 1 (`build_dependencies`)**: Runs the template with a collector `_ref()` function that records every referenced model name and captures `{{ config(...) }}` values.
- **Pass 2 (`render_model`)**: Runs the template again with a rendering `_ref()` function that validates the target exists and outputs `"<schema>"."<model_name>"`.

### 3. Safe Materialization Switching in DuckDB
DuckDB raises a `Catalog Error` if you run `DROP TABLE IF EXISTS` on an existing `VIEW` (or `DROP VIEW IF EXISTS` on an existing `TABLE`). To stay idempotent across repeated runs, `execute_project` queries `information_schema.tables` first:
- If the object does not exist or already matches the target type (`view` or `table`), it runs `CREATE OR REPLACE ...`.
- Only when the object switches type (e.g., from `view` to `table`) does it call `build_switch_statement` to drop the old object type before creating the new one.

### 4. Structured Error Handling
All expected failures inherit from `DbtminiError` so the CLI can format clean error messages (`[stage] file:line model 'name': message`) and return consistent exit codes:
- `0`: All models and tests succeeded.
- `1`: One or more models had execution errors or one or more tests did not pass.
- `2`: A `DbtminiError` occurred (invalid config, bad SQL/Jinja, missing `ref`, or dependency cycle).

---

## Standard Project Layout

A typical `dbtmini` project (such as [example_project](../example_project)) follows this folder structure:

```text
example_project/
├── dbtmini_project.yml      # Project config (name, paths, database, schema, materializations)
├── models/                  # SQL transformation models
│   ├── staging/             # Clean/rename raw seed tables (usually views)
│   ├── intermediate/        # Reusable joins and aggregations
│   └── marts/               # Final analytics models (often tables)
├── seeds/                   # Static CSV files loaded as tables
├── tests/                   # YAML files defining not_null and unique checks
└── target/                  # Generated outputs (compiled SQL & run_results_*.json)
```
