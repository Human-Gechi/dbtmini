import time
from dataclasses import dataclass
from enum import Enum

import duckdb

from dbtmini.materialization import build_relation_name, quote_identifier
from dbtmini.models import TestSpec


class TestStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class TestResult:
    test_name: str
    status: TestStatus
    duration: float
    message: str | None


def generate_not_null(test: TestSpec, schema: str) -> str:
    quoted_column = quote_identifier(test.column)
    relation = build_relation_name(schema=schema, model_name=test.name)

    sql_statement = (
        f"""SELECT {quoted_column} FROM {relation} WHERE {quoted_column} IS NULL;"""
    )

    return sql_statement


def generate_unique(test: TestSpec, schema: str) -> str:
    quoted_column = quote_identifier(test.column)
    relation = build_relation_name(schema=schema, model_name=test.name)

    sql_statement = f"""
            SELECT
            {quoted_column}, COUNT(*) as n_records
            FROM {relation}
                WHERE {quoted_column} IS NOT NULL
            GROUP BY {quoted_column}
            HAVING COUNT(*) > 1;"""

    return sql_statement


TEST_REGISTRY = {"not_null": generate_not_null, "unique": generate_unique}


def run_tests(
    conn: duckdb.DuckDBPyConnection, test_specs: list[TestSpec], schema: str
) -> list[TestResult]:
    results: list[TestResult] = []

    for test in test_specs:
        test_name = f"{test.test_type}_{test.name}_{test.column}"
        generator = TEST_REGISTRY.get(test.test_type)

        if not generator:
            results.append(
                TestResult(
                    test_name=test_name,
                    status=TestStatus.ERROR,
                    duration=0.0,
                    message="Unknown test_type",
                )
            )
            continue

        sql = generator(test, schema)
        t0 = time.perf_counter()

        try:
            count_query = f"SELECT COUNT(*) FROM ({sql});"
            result = conn.execute(count_query).fetchone()
            failures = result[0] if result else 0
            duration = time.perf_counter() - t0

            if failures == 0:
                status = TestStatus.PASS
                message = "PASSED"
            else:
                status = TestStatus.FAIL
                message = f"Got {failures} failure(s)"

        except duckdb.Error as e:
            duration = time.perf_counter() - t0
            status = TestStatus.ERROR
            message = str(e).splitlines()[0]

        results.append(
            TestResult(
                test_name=test_name,
                status=status,
                duration=duration,
                message=message,
            )
        )

    return results


def format_test_summary(test_results: list[TestResult]) -> str:
    lines: list[str] = []

    divider = "-" * 70

    lines.append(f"{'TEST':<40} {'STATUS':<10} {'TIME':<10} MESSAGE")
    lines.append(divider)

    pass_count = sum(1 for r in test_results if r.status == TestStatus.PASS)
    fail_count = sum(1 for r in test_results if r.status == TestStatus.FAIL)
    error_count = sum(1 for r in test_results if r.status == TestStatus.ERROR)

    for r in test_results:
        duration_str = f"{r.duration:.3f}s"
        lines.append(
            f"""{r.test_name:<40} {r.status.value.upper():<10}
            {duration_str:<10} {r.message or ""}"""
        )

    lines.append(divider)
    lines.append(
        f"""Passed: {pass_count} | Failed: {fail_count}
        | Errors: {error_count} | Total: {len(test_results)}"""
    )

    return "\n".join(lines)
