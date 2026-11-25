import duckdb

from dbtmini.models import TestSpec
from dbtmini.tests_runner import (
    TestResult,
    TestStatus,
    format_test_summary,
    generate_not_null,
    generate_unique,
    run_tests,
)


def test_generate_not_null_sql() -> None:
    test = TestSpec(name="customers", column="email", test_type="not_null")
    sql = generate_not_null(test, schema="analytics")
    assert sql == 'SELECT "email" FROM "analytics"."customers" WHERE "email" IS NULL'


def test_generate_unique_sql() -> None:
    test = TestSpec(name="orders", column="order_id", test_type="unique")
    sql = generate_unique(test, schema="main")
    assert '"order_id"' in sql
    assert '"main"."orders"' in sql
    assert "HAVING COUNT(*) > 1" in sql


def test_run_tests_not_null_pass(db_conn: duckdb.DuckDBPyConnection) -> None:
    db_conn.execute("CREATE SCHEMA IF NOT EXISTS main;")
    db_conn.execute("CREATE TABLE main.customers (id INT, email VARCHAR);")
    db_conn.execute(
        "INSERT INTO main.customers VALUES (1, 'a@example.com'), (2, 'b@example.com');"
    )

    specs = [TestSpec(name="customers", column="email", test_type="not_null")]
    results = run_tests(db_conn, specs, schema="main")

    assert len(results) == 1
    assert results[0].status == TestStatus.PASS
    assert results[0].message == "PASSED"


def test_run_tests_not_null_fail(db_conn: duckdb.DuckDBPyConnection) -> None:
    db_conn.execute("CREATE SCHEMA IF NOT EXISTS main;")
    db_conn.execute("CREATE TABLE main.users (id INT, email VARCHAR);")
    db_conn.execute("INSERT INTO main.users VALUES (1, 'a@example.com'), (2, NULL);")

    specs = [TestSpec(name="users", column="email", test_type="not_null")]
    results = run_tests(db_conn, specs, schema="main")

    assert len(results) == 1
    assert results[0].status == TestStatus.FAIL
    assert results[0].message == "Got 1 failure(s)"


def test_run_tests_unique_pass(db_conn: duckdb.DuckDBPyConnection) -> None:
    db_conn.execute("CREATE SCHEMA IF NOT EXISTS main;")
    db_conn.execute("CREATE TABLE main.items (id INT);")
    db_conn.execute("INSERT INTO main.items VALUES (1), (2), (3);")

    specs = [TestSpec(name="items", column="id", test_type="unique")]
    results = run_tests(db_conn, specs, schema="main")

    assert len(results) == 1
    assert results[0].status == TestStatus.PASS


def test_run_tests_unique_fail(db_conn: duckdb.DuckDBPyConnection) -> None:
    db_conn.execute("CREATE SCHEMA IF NOT EXISTS main;")
    db_conn.execute("CREATE TABLE main.items (id INT);")
    db_conn.execute("INSERT INTO main.items VALUES (1), (2), (2), (3);")

    specs = [TestSpec(name="items", column="id", test_type="unique")]
    results = run_tests(db_conn, specs, schema="main")

    assert len(results) == 1
    assert results[0].status == TestStatus.FAIL
    assert results[0].message == "Got 1 failure(s)"


def test_run_tests_error_missing_table(db_conn: duckdb.DuckDBPyConnection) -> None:
    db_conn.execute("CREATE SCHEMA IF NOT EXISTS main;")
    specs = [TestSpec(name="non_existent", column="id", test_type="not_null")]
    results = run_tests(db_conn, specs, schema="main")

    assert len(results) == 1
    assert results[0].status == TestStatus.ERROR


def test_run_tests_unknown_test_type(db_conn: duckdb.DuckDBPyConnection) -> None:
    specs = [TestSpec(name="orders", column="id", test_type="accepted_values")]
    results = run_tests(db_conn, specs, schema="main")

    assert len(results) == 1
    assert results[0].status == TestStatus.ERROR
    assert results[0].message == "Unknown test_type"


def test_format_test_summary() -> None:
    results = [
        TestResult(
            test_name="not_null_customers_id",
            status=TestStatus.PASS,
            duration=0.012,
            message="PASSED",
        ),
        TestResult(
            test_name="unique_customers_id",
            status=TestStatus.FAIL,
            duration=0.015,
            message="Got 1 failure(s)",
        ),
        TestResult(
            test_name="not_null_missing_col",
            status=TestStatus.ERROR,
            duration=0.005,
            message="Column not found",
        ),
    ]

    summary = format_test_summary(results)
    assert "Passed: 1 | Failed: 1" in summary
    assert "Errors: 1 | Total: 3" in summary
    assert "not_null_customers_id" in summary
    assert "PASS" in summary
    assert "FAIL" in summary
