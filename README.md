# dbtmini

A minimal implementation of dbt (data build tool) written in Python that runs SQL transformations, CSV seeds, and data quality tests on **DuckDB**.

---
## Repository Structure

```text
├── dbtmini/                       # Core package
│   ├── cli.py                     # Typer CLI commands (compile, run, test, build)
│   ├── config.py                  # Project YAML loader & ProjectConfig validation
│   ├── dag.py                     # Topological sorting (Kahn's algorithm) & cycle check
│   ├── errors.py                  # Custom error hierarchy (ConfigError, DagError, etc.)
│   ├── executor.py                # Runs seeds and models against DuckDB
│   ├── materialization.py         # View/table DDL generation & switching
│   ├── models.py                  # Model, TestSpec, and ParseResult dataclasses
│   ├── project.py                 # Discovers models, CSV seeds, and YAML tests
│   ├── renderer.py                # Two-pass Jinja2 parser & SQL renderer
│   ├── results.py                 # RunResult summaries and JSON log writer
│   ├── seeds.py                   # CSV validation and DuckDB seed loader
│   └── tests_runner.py            # SQL test generators (not_null, unique) & runner
├── example_project/               # Sample dbtmini project
│   ├── dbtmini_project.yml        # Project config
│   ├── models/
│   │   ├── staging/               # stg_customers.sql, stg_orders.sql, stg_payments.sql
│   │   ├── intermediate/          # int_customer_orders.sql, int_customer_payments.sql
│   │   └── marts/                 # dim_customers.sql, fct_orders.sql
│   ├── seeds/                     # customers.csv, orders.csv, payments.csv
│   ├── tests/
│   │   └── tests.yml              # Column data quality tests
│   └── target/                    # Generated outputs (gitignored)
│       ├── compiled/
│       │   ├── intermediate/      # int_customer_orders.sql, int_customer_payments.sql
│       │   ├── marts/             # dim_customers.sql, fct_orders.sql
│       │   └── staging/           # stg_customers.sql, stg_orders.sql, stg_payments.sql
│       └── run_results_*.json     # Execution logs (plus run_results.json)
├── tests/                         # Automated test suite
│   ├── conftest.py                # Shared pytest fixtures
│   ├── fixtures/                  # Sample valid and error-case projects
│   ├── unit/                      # Unit tests per core module
│   └── integration/               # CLI and end-to-end pipeline tests
├── docs/                          # Documentation
│   ├── architecture.md
│   ├── design-decisions.md
│   └── how-it-works.md
├── .gitignore
├── .pre-commit-config.yaml        # Pre-commit hooks (formatting, YAML checks, ruff, mypy)
├── CHANGELOG.md
├── pyproject.toml                 # Package metadata, scripts, ruff, mypy, and pytest config
├── requirements.txt               # Direct Python dependencies
└── README.md
```
## Documentation
Check te files for detailed documentation of the project.

- [Architecture](docs/architecture.md): High-level data flow, module responsibilities, and project layout.
- [How It Works](docs/how-it-works.md): Step-by-step walkthrough from config loading to DuckDB execution and testing.
- [Design Decisions](docs/design-decisions.md): Trade-offs and key differences between `dbtmini` and full dbt Core.


## Features

- **Jinja2 SQL Models**: Write modular `.sql` models with `{{ ref('model_name') }}` and inline `{{ config(materialized='view' | 'table') }}`.
- **DAG Dependency Resolution**: Automatically finds model dependencies, sorts them in execution order, and catches missing references or circular loops before running SQL.
- **CSV Seed Loading**: Discovers `*.csv` files in `seeds/` and loads them directly into DuckDB tables.
- **Safe Materializations**: Supports `view` and `table` materializations (configured via CLI, model config, folder overrides, or project defaults) and safely switches types across repeated runs.
- **Built-in Data Tests**: Runs `not_null` and `unique` checks from YAML files and reports clear pass/fail/error summaries.
- **CLI & Run Logs**: Provides `compile`, `run`, `test`, and `build` commands via Typer and saves timestamped JSON results under `target/run_results_*.json`.

---

## Requirements

- Python `>=3.11`

## Installation

Clone the repository, activate a virtual environment, and install `dbtmini` in editable mode:

```bash
git clone https://github.com/Human-Gechi/dbtmini.git
cd dbtmini

python -m venv venv
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# macOS / Linux:
# source venv/bin/activate

pip install -e ".[dev]"
```

---

## Quick Start

This repository includes a working sample project in [`example_project/`](example_project) with staging, intermediate, and mart models, CSV seeds, and schema tests.

Run the full pipeline (load seeds, build models, and run tests):

```bash
dbtmini build
```

Or run each step individually:

```bash
# 1. Resolve dependencies and write compiled SQL to target/compiled/
dbtmini compile

# 2. Load seeds and materialize models in DuckDB
dbtmini run

# 3. Run data quality tests against the database
dbtmini test
```
<img width="1207" height="214" alt="image" src="https://github.com/user-attachments/assets/d7d8862b-2ff2-418c-aad6-fb12acbba014" />

---

<img width="1264" height="672" alt="image" src="https://github.com/user-attachments/assets/53a4aaee-0603-4d17-bccd-00de16522c3e" />


### CLI Options

| Command | Supported Flags | Description |
| :--- | :--- | :--- |
| `dbtmini compile` | `--project-dir` (`-d`), `--schema` (`-s`) | Prints model execution order and writes rendered SQL to `target/compiled/`. |
| `dbtmini run` | `--project-dir` (`-d`), `--schema` (`-s`), `--database` | Loads seeds, runs all models in DuckDB, and saves `target/run_results_*.json`. |
| `dbtmini test` | `--project-dir` (`-d`), `--schema` (`-s`), `--database` | Runs `not_null` and `unique` YAML tests against DuckDB tables/views. |
| `dbtmini build` | `--project-dir` (`-d`), `--schema` (`-s`), `--database` | Runs `run` and `test` together on the same DuckDB connection. |

All commands default `--project-dir` to `example_project`. `--schema` and `--database` override the values in `dbtmini_project.yml`.

---

## Project Configuration

Each project is configured with a `dbtmini_project.yml` file:

```yaml
name: "example_project"
version: "0.1.0"

model-paths:
  - "models"
seed-paths:
  - "seeds"
test-paths:
  - "tests"
target-path: "target"

database: "dbtmini.duckdb"
schema: "main"

models:
  materialized: "view"       # Project default
  marts:
    materialized: "table"    # Folder-level override
```

### Writing a Model

Models live under `models/*.sql` and reference seeds or upstream models with `ref()`:

```sql
{{ config(materialized='view') }}

select
    id as customer_id,
    name,
    email
from {{ ref('customers') }}
```

### Writing Tests

Tests live under `tests/*.yml` and support `not_null` and `unique`:

```yaml
models:
  - name: stg_customers
    columns:
      - name: customer_id
        tests:
          - unique
          - not_null
```

---

### Pre-commit Hooks

This project uses `pre-commit` (configured in [`.pre-commit-config.yaml`](.pre-commit-config.yaml)) to automatically check trailing whitespace, file endings, YAML syntax, `ruff` lint/format, and `mypy` type checking before each commit.

Install the Git hooks once after cloning:

```bash
pre-commit install
```

Run all hooks manually across the repository:

```bash
pre-commit run --all-files
```
