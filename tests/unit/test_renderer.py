from pathlib import Path

import pytest
from jinja2 import Environment

from dbtmini.errors import RenderError
from dbtmini.models import Model
from dbtmini.renderer import build_dependencies, create_environment, render_model


def test_create_environment() -> None:
    env = create_environment()
    assert isinstance(env, Environment)
    assert env.autoescape is False


def test_build_dependencies_single_ref() -> None:
    model = Model(
        name="stg_orders",
        file_path=Path("stg_orders.sql"),
        sql_text="SELECT * FROM {{ ref('raw_orders') }};",
        folder="staging",
        config={},
    )
    res = build_dependencies(model)
    assert res.model_name == "stg_orders"
    assert res.dependencies == frozenset({"raw_orders"})
    assert res.config == {}


def test_build_dependencies_multiple_refs() -> None:
    model = Model(
        name="fct_orders",
        file_path=Path("fct_orders.sql"),
        sql_text="""
        SELECT *
        FROM {{ ref('orders') }} o
        JOIN {{ ref('customers') }} c ON o.customer_id = c.id
        LEFT JOIN {{ ref('payments') }} p ON o.id = p.order_id
        """,
        folder="marts",
        config={},
    )
    res = build_dependencies(model)
    assert res.dependencies == frozenset({"orders", "customers", "payments"})


def test_build_dependencies_duplicate_refs() -> None:
    model = Model(
        name="unioned",
        file_path=Path("unioned.sql"),
        sql_text="""
        SELECT * FROM {{ ref('base_table') }}
        UNION ALL
        SELECT * FROM {{ ref('base_table') }}
        """,
        folder="",
        config={},
    )
    res = build_dependencies(model)
    assert res.dependencies == frozenset({"base_table"})


def test_build_dependencies_captures_config() -> None:
    model = Model(
        name="dim_customers",
        file_path=Path("dim_customers.sql"),
        sql_text="{{ config(materialized='table') }}\nSELECT 1;",
        folder="marts",
        config={},
    )
    res = build_dependencies(model)
    assert res.config == {"materialized": "table"}


def test_build_dependencies_syntax_error() -> None:
    model = Model(
        name="broken_syntax",
        file_path=Path("broken_syntax.sql"),
        sql_text="SELECT * FROM {{ ref('orders' };",
        folder="",
        config={},
    )
    with pytest.raises(RenderError) as exc_info:
        build_dependencies(model)

    assert exc_info.value.ref_variant == "syntax"
    assert "Jinja syntax error" in exc_info.value.message


def test_build_dependencies_undefined_variable() -> None:
    model = Model(
        name="broken_var",
        file_path=Path("broken_var.sql"),
        sql_text="SELECT * FROM {{ unknown_var }};",
        folder="",
        config={},
    )
    with pytest.raises(RenderError) as exc_info:
        build_dependencies(model)

    assert exc_info.value.ref_variant == "undefined_variable"
    assert "Undefined variable in Jinja" in exc_info.value.message


def test_render_model_basic() -> None:
    model = Model(
        name="stg_orders",
        file_path=Path("stg_orders.sql"),
        sql_text="SELECT * FROM {{ ref('raw_orders') }};",
        folder="staging",
        config={},
    )
    rendered = render_model(
        model=model,
        known_models={"raw_orders"},
        schema="dev_schema",
    )
    assert rendered == 'SELECT * FROM "dev_schema"."raw_orders";'


def test_render_model_unknown_ref_raises_render_error() -> None:
    model = Model(
        name="stg_orders",
        file_path=Path("stg_orders.sql"),
        sql_text="SELECT * FROM {{ ref('missing_orders') }};",
        folder="staging",
        config={},
    )
    with pytest.raises(RenderError) as exc_info:
        render_model(
            model=model,
            known_models={"raw_orders"},
            schema="main",
        )

    assert exc_info.value.ref_variant == "undefined_ref"
    assert "references unknown model 'missing_orders'" in exc_info.value.message


def test_render_model_config_stripped() -> None:
    model = Model(
        name="table_model",
        file_path=Path("table_model.sql"),
        sql_text="{{ config(materialized='table') }}\nSELECT * FROM {{ ref('a') }};",
        folder="",
        config={},
    )
    rendered = render_model(
        model=model,
        known_models={"a"},
        schema="main",
    )
    assert rendered == 'SELECT * FROM "main"."a";'


def test_render_model_syntax_error() -> None:
    model = Model(
        name="broken_render_syntax",
        file_path=Path("broken.sql"),
        sql_text="SELECT * FROM {{ ref('a'",
        folder="",
        config={},
    )
    with pytest.raises(RenderError) as exc_info:
        render_model(model=model, known_models={"a"}, schema="main")

    assert exc_info.value.ref_variant == "syntax"


def test_render_model_undefined_variable() -> None:
    model = Model(
        name="broken_render_var",
        file_path=Path("broken.sql"),
        sql_text="SELECT * FROM {{ undeclared }};",
        folder="",
        config={},
    )
    with pytest.raises(RenderError) as exc_info:
        render_model(model=model, known_models=set(), schema="main")

    assert exc_info.value.ref_variant == "undefined_variable"
