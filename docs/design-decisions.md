# Design Decisions & How dbtmini Differs from dbt

`dbtmini` keeps the core idea of dbt: you write modular SQL models with `ref()`, sort them in dependency order, run them in DuckDB, and test the results. At the same time, the codebase stays small enough to read and understand quickly.

To keep things simple, fast, and easy to follow, `dbtmini` makes several choices that make it very different from full **dbt Core**.

---

## Side-by-Side Comparison: dbt Core vs. dbtmini

| Area | Full dbt (dbt Core) | dbtmini |
| :--- | :--- | :--- |
| **Database Adapters** | Supports many warehouses (`Snowflake`, `BigQuery`, `Postgres`, `DuckDB`, etc.) via `profiles.yml` | **DuckDB only**, set up right inside `dbtmini_project.yml` or with CLI flags (`--database`, `--schema`) |
| **Execution Order** | Runs independent models at the same time using multiple threads | **Runs models one at a time** in dependency order (alphabetical order breaks ties) |
| **Materializations** | `view`, `table`, `incremental`, `ephemeral`, snapshots, and custom types | **`view` and `table` only** (anything else raises `ConfigError`) |
| **Seeds (CSV Files)** | Loaded separately with `dbt seed` (or as nodes in `dbt build`) | **Loaded automatically** from `seeds/*.csv` at the start of every `dbtmini run` and `dbtmini build` |
| **Sources vs. Refs** | Uses both `{{ source('raw', 'table') }}` and `{{ ref('model') }}` | **Only `{{ ref('name') }}`**, used for both models and CSV seeds |
| **Schemas** | Can write models into different schemas (`generate_schema_name`) | **One target schema** per run (`config.schema`, defaulting to `main`) |
| **Jinja Environment** | Full macros, packages (`packages.yml`), hooks, `var()`, `env_var()`, `is_incremental()` | **Minimal Jinja2 (`StrictUndefined`)** with only `ref()` and `config()` |
| **Data Tests** | 4 built-in tests, custom SQL tests, generic test macros, and packages (`dbt_utils`) | **2 built-in YAML tests only**: `not_null` and `unique` |
| **Node Selection** | Run subsets of models (`--select`, `--exclude`, tags, `state:modified`) | **Runs the whole project** every time (no `--select` or `--exclude` flags) |
| **Output Files** | `manifest.json`, `run_results.json`, `catalog.json`, `sources.json` | Compiled SQL in `target/compiled/` and timestamped `target/run_results_*.json` |

---

## Key Design Decisions Explained

### 1. DuckDB-Only, No Extra Setup
Full dbt splits project settings (`dbt_project.yml`) from database passwords and connection details (`profiles.yml`).

`dbtmini` drops `profiles.yml` completely. Database and schema settings live inside `dbtmini_project.yml` (defaulting to an in-memory `:memory:` database and `main` schema), and you can override them with `--database` and `--schema`. Everything runs locally right away with no accounts or servers to configure.

### 2. Seeds Work Like Normal `ref()` Models
In full dbt, you normally run `dbt seed` before `dbt run`.

In `dbtmini`, CSV seeds act as starting tables with no upstream dependencies. [executor.py](../dbtmini/executor.py) loads every CSV file into DuckDB at the start of `run` and `build`. Models query seeds using `{{ ref('customers') }}` just like any SQL model, so there is no need for `source()` or a separate `dbt seed` command.

### 3. Only `view` and `table` Materializations
Full dbt supports incremental loads, ephemeral CTEs, and snapshots, which need complex SQL rules for each database.

`dbtmini` limits [materialization.py](../dbtmini/materialization.py) to `view` and `table` (picking the setting from CLI > model `{{ config(...) }}` > folder rule > project default). To work cleanly when run multiple times, `execute_project` checks DuckDB's `information_schema.tables` first:
- Same type (or brand-new model): runs `CREATE OR REPLACE VIEW/TABLE ...`.
- Type changed (`view` <-> `table`): runs `DROP <old_type> IF EXISTS` first, then `CREATE OR REPLACE <new_type>`.

### 4. Simple Two-Pass Jinja2 (No Macros or `manifest.json`)
Full dbt builds a large `manifest.json` file with parsed SQL trees, macros, hooks, and third-party packages.

`dbtmini` keeps Jinja parsing lightweight and stateless inside [renderer.py](../dbtmini/renderer.py):
- **Pass 1 (`build_dependencies`)**: Runs the SQL template with a helper that records every `{{ ref(...) }}` name and `{{ config(...) }}` setting.
- **Pass 2 (`render_model`)**: Runs the template again and replaces each `{{ ref('name') }}` with `"<schema>"."<model_name>"`.
- Using Jinja's `StrictUndefined` ensures any typo or unknown variable stops right away with a `RenderError` instead of turning into an empty string.

### 5. Predictable, One-at-a-Time Execution
Full dbt runs independent branches across multiple threads to speed up cloud warehouse queries.

`dbtmini` runs models one by one in [dag.py](../dbtmini/dag.py) and [executor.py](../dbtmini/executor.py). When two or more models are ready at the same time, Kahn's algorithm uses a min-heap (`heapq`) so they always run in **alphabetical order**. This keeps the run order identical on every machine and avoids DuckDB write-lock issues.

### 6. Stop Right Away on SQL Errors
When a model fails in full dbt, unrelated branches keep running and downstream models are marked `skipped`.

In `dbtmini`, a DuckDB SQL error inside `execute_project` immediately raises an `ExecutionError` (showing the stage, file path, and model name) and exits with code `2`. Because runs are local and fast, stopping right away prevents a chain of follow-on errors.

### 7. Strict Checks Before Running SQL
Before touching DuckDB, [config.py](../dbtmini/config.py) and [project.py](../dbtmini/project.py) check for mistakes early:
- Only known keys in `ALLOWED_PROJECT_KEYS` are allowed in `dbtmini_project.yml`.
- Model names must only use letters, digits, and underscores (`^[a-zA-Z0-9_]+$`), with no duplicate names across folders.
- Unsupported test types in YAML fail when scanning files (`ProjectError`).
- Dependency loops and missing `ref()` targets fail during sorting (`CycleError` / `DagError`) before any SQL runs.

### 8. Simple `not_null` and `unique` Testing
Instead of macro-based tests and custom `.sql` test files, [tests_runner.py](../dbtmini/tests_runner.py) maps `"not_null"` and `"unique"` directly in `TEST_REGISTRY` to `SELECT COUNT(*) FROM (...)` queries in DuckDB. If any test does not return `PASS`, `dbtmini test` and `dbtmini build` exit with code `1`.

---

## Summary: What Was Left Out

| Kept in dbtmini | Left out (Full dbt only) |
| :--- | :--- |
| Two-pass Jinja `ref()` & `config()` | Macros, packages, `source()`, `var()` |
| Topological DAG & cycle check | Multi-threaded runs & `--select` |
| DuckDB views, tables, CSV seeds | Incremental, ephemeral, snapshots |
| YAML `not_null` & `unique` tests | Custom SQL tests & test packages |
| `dbtmini_project.yml` config | `profiles.yml` & cloud adapters |
| `target/compiled` & `run_results_*.json` | `manifest.json` & docs website |
