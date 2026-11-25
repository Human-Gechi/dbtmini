# How dbtmini Works

Think of `dbtmini` like a kitchen assembly line:
1. First, it reads your settings and collects all your recipes (SQL models, CSV files, and tests).
2. Next, it checks which dishes depend on other dishes so everything is prepared in the right order.
3. Then, it cooks each step inside **DuckDB** (creating tables and views).
4. Finally, it runs quality checks on the finished data and prints a report.

---

## Step 1: Read the Project Settings

When you run `dbtmini run`, `dbtmini test`, or `dbtmini build`, `cli.py` calls `_load_config` to read `dbtmini_project.yml`.

- It checks that the file is a valid YAML dictionary and includes a string `name`.
- It rejects unknown settings keys so typos fail early with a `ConfigError`.
- It resolves relative folders (`model-paths`, `seed-paths`, `test-paths`, `target-path`) and records database settings (`database`, `schema`) and materialization defaults (`view` or `table`).

---

## Step 2: Discover Models, Seeds, and Tests

Next, [project.py](../dbtmini/project.py) scans your folders:

- **Models (`discover_models`)**: Finds every `*.sql` file inside `models/` (skipping hidden folders). It checks that file names only use letters, numbers, and underscores, rejects duplicate model names across folders, and reads any inline `{{ config(materialized='...') }}`.
- **Seeds (`discover_seeds`)**: Finds every `*.csv` file inside `seeds/`.
- **Tests (`discover_tests`)**: Reads `*.yml` files inside `tests/` and collects `not_null` and `unique` checks for each model column. Any unsupported test type raises a `ProjectError`.

---

## Step 3: Build the Dependency Graph & Sort Order

Before running any SQL, `dbtmini` needs to know what order to run your models in. For example, if `dim_customers` selects from `{{ ref('stg_customers') }}`, then `stg_customers` must be built first.

```text
  cli.py                    renderer.py                    dag.py
    |                            |                            |
    |--- build_dependencies() -->|                            |
    |        (Jinja Pass 1)      |                            |
    |<-- ParseResult ------------|                            |
    |                                                         |
    |--- topological_sort(dependencies) --------------------->|
    |<-- Ordered list (parents before children) --------------|
```

1. **Pass 1 (`build_dependencies`)**: Each model's SQL is evaluated with Jinja2 (`StrictUndefined`). Every call to `{{ ref('other_model') }}` records `other_model` as an upstream dependency. Jinja syntax errors or undefined variables fail immediately with a `RenderError`.
2. **Topological Sort (`topological_sort`)**: [dag.py](../dbtmini/dag.py) uses **Kahn's algorithm** (with a min-heap for deterministic alphabetical tie-breaking):
   - Seeds have no upstream dependencies, so they are always ready first.
   - If a model references a name that does not exist, it raises `DagError`.
   - If models form a loop (e.g., `A -> B -> A`), it traces the loop and raises `CycleError`.

---

## Step 4: Compile SQL (`dbtmini compile`)

In **Pass 2 (`render_model`)**, Jinja2 runs again—this time replacing every `{{ ref('name') }}` with a quoted DuckDB table/view name like `"main"."name"`, and stripping out `{{ config(...) }}` blocks.

If you run `dbtmini compile`, the pipeline prints the execution order and saves the plain SQL files to `target/compiled/` without touching DuckDB.

<img width="936" height="56" alt="image" src="https://github.com/user-attachments/assets/f83cc8ee-7838-4957-925c-aa55a41d4cb6" />

<img width="297" height="269" alt="image" src="https://github.com/user-attachments/assets/8aaad70d-bd9b-42ec-9e42-5140ffcc177c" />



---

## Step 5: Load Seeds & Execute Models (`dbtmini run`)

When you run `dbtmini run`, [executor.py](../dbtmini/executor.py) opens a DuckDB connection and runs `execute_project`:

1. **Create schema**: Runs `CREATE SCHEMA IF NOT EXISTS "<schema>";`.
2. **Load CSV seeds (`load_seeds`)**: Validates each CSV file is non-empty and has both a header and data rows, then runs `CREATE OR REPLACE TABLE "<schema>"."<seed>" AS SELECT * FROM read_csv(...)`.
3. **Choose materialization (`resolve_materialization`)**: For each model in sorted order, `dbtmini` picks `view` or `table` using this priority order (highest wins):
   - CLI override (if passed)
   - Model-level `{{ config(materialized='...') }}` inside the `.sql` file
   - Folder-level rule in `dbtmini_project.yml` (e.g. `models.marts.materialized: "table"`)
   - Project default (`models.materialized`, which defaults to `view`)
4. **Create or switch in DuckDB**: `dbtmini` checks `information_schema.tables` to see if the relation already exists:
   - If it does not exist yet or is already the same type (`VIEW` vs `BASE TABLE`), it runs `CREATE OR REPLACE VIEW/TABLE ...`.
   - If the model switched type (for example, from `view` to `table`), it runs `DROP <old_type> IF EXISTS` first and then `CREATE OR REPLACE <new_type>`.
5. **Print summary & save JSON**: [results.py](../dbtmini/results.py) formats the summary table and writes a timestamped log to `target/run_results_<timestamp>.json`.

<img width="1207" height="214" alt="image" src="https://github.com/user-attachments/assets/e3d92573-53b0-483e-9922-c942d5e2f04a" />


---

## Step 6: Run Data Quality Tests (`dbtmini test`)

When you run `dbtmini test`, [tests_runner.py](../dbtmini/tests_runner.py) converts every rule from `tests/*.yml` into a SQL query that looks for **bad rows**:

- **`not_null`**: `SELECT "<col>" FROM "<schema>"."<model>" WHERE "<col>" IS NULL`
- **`unique`**: `SELECT "<col>", COUNT(*) as n_records FROM "<schema>"."<model>" WHERE "<col>" IS NOT NULL GROUP BY "<col>" HAVING COUNT(*) > 1`

Each query is wrapped in `SELECT COUNT(*) FROM (...);`:
- `0` bad rows -> `PASS`
- `1+` bad rows -> `FAIL` (reports how many failures were found)
- DuckDB error (e.g. missing table/column) -> `ERROR`

<img width="946" height="426" alt="image" src="https://github.com/user-attachments/assets/64054982-ad7f-4fb2-9198-05f861ea701d" />

---

## Step 7: Run Everything Together (`dbtmini build`)

`dbtmini build` combines `run` and `test` on the same DuckDB connection:
1. Loads seeds and builds all models in topological order (`execute_project`).
2. Prints the run summary and writes `target/run_results_*.json`.
3. Immediately runs all schema tests (`run_tests`) and prints the test summary.
4. Exits with code `1` if any model failed or any test did not pass (`0` if everything succeeded, `2` if a `DbtminiError` stopped execution).
<img width="1264" height="672" alt="image" src="https://github.com/user-attachments/assets/64fc4ea3-2fad-4c4d-b12d-6d43cbadb597" />

