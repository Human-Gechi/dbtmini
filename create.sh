#!/usr/bin/env bash

set -euo pipefail

BASE="${1:-.}"

if [ ! -d "$BASE" ]; then
  echo "Error: base folder '$BASE' does not exist." >&2
  exit 1
fi

cd "$BASE"
echo "Creating structure in: $(pwd)"

# ---------- directories ----------
mkdir -p \
  .github/workflows \
  docs \
  dbtmini \
  tests/unit \
  tests/integration \
  tests/fixtures/valid_project/models \
  tests/fixtures/cyclic_project/models \
  tests/fixtures/missing_ref_project/models \
  tests/fixtures/duplicate_names_project/models \
  tests/fixtures/bad_sql_project/models \
  tests/fixtures/failing_test_project/models \
  example_project/seeds \
  example_project/models/staging \
  example_project/models/intermediate \
  example_project/models/marts \
  example_project/tests

# ---------- empty files (created only if missing) ----------
files=(
  # root
  README.md
  LICENSE
  CHANGELOG.md
  pyproject.toml
  .pre-commit-config.yaml
  .github/workflows/ci.yml

  # docs
  docs/architecture.md
  docs/design-decisions.md
  docs/how-it-works.md

  # package
  dbtmini/__init__.py
  dbtmini/__main__.py
  dbtmini/cli.py
  dbtmini/config.py
  dbtmini/project.py
  dbtmini/models.py
  dbtmini/renderer.py
  dbtmini/dag.py
  dbtmini/seeds.py
  dbtmini/executor.py
  dbtmini/materialization.py
  dbtmini/tests_runner.py
  dbtmini/results.py
  dbtmini/logging_setup.py
  dbtmini/errors.py

  # tests
  tests/conftest.py
  tests/unit/test_config.py
  tests/unit/test_project_discovery.py
  tests/unit/test_renderer.py
  tests/unit/test_dag.py
  tests/unit/test_materialization.py
  tests/unit/test_tests_runner.py
  tests/unit/test_results.py
  tests/integration/test_end_to_end.py
  tests/integration/test_cli.py

  # fixture projects (config file in each)
  tests/fixtures/valid_project/dbtmini_project.yml
  tests/fixtures/cyclic_project/dbtmini_project.yml
  tests/fixtures/missing_ref_project/dbtmini_project.yml
  tests/fixtures/duplicate_names_project/dbtmini_project.yml
  tests/fixtures/bad_sql_project/dbtmini_project.yml
  tests/fixtures/failing_test_project/dbtmini_project.yml

  # example project
  example_project/dbtmini_project.yml
  example_project/seeds/raw_customers.csv
  example_project/seeds/raw_orders.csv
  example_project/seeds/raw_payments.csv
  example_project/models/staging/stg_customers.sql
  example_project/models/staging/stg_orders.sql
  example_project/models/staging/stg_payments.sql
  example_project/models/intermediate/int_customer_orders.sql
  example_project/models/intermediate/int_customer_payments.sql
  example_project/models/marts/dim_customers.sql
  example_project/models/marts/fct_orders.sql
  example_project/tests/tests.yml
)

for f in "${files[@]}"; do
  [ -e "$f" ] || touch "$f"
done

# ---------- .gitignore (only if missing) ----------
if [ ! -e .gitignore ]; then
  cat > .gitignore << 'GITIGNORE'
# Python
__pycache__/
*.py[cod]
*.egg-info/
build/
dist/
.venv/
venv/

# Tooling caches
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
coverage.xml

# dbtmini generated output
example_project/target/
*.duckdb
*.duckdb.wal

# OS / editor
.DS_Store
.idea/
.vscode/
GITIGNORE
fi

echo "Done. Files and folders created."
if command -v tree >/dev/null 2>&1; then
  tree -a -I '.git|.venv' -L 3
fi