from typing import Any

from jinja2 import Environment, StrictUndefined, TemplateSyntaxError, UndefinedError

from dbtmini.errors import RenderError
from dbtmini.models import Model, ParseResult


def create_environment() -> Environment:
    return Environment(undefined=StrictUndefined, autoescape=False)


def build_dependencies(model: Model, env: Environment | None = None) -> ParseResult:
    dependencies: set[str] = set()
    captured_config: dict[str, Any] = {}

    def _ref(model_name: str) -> str:
        dependencies.add(model_name)
        return model_name

    def config(**kwargs: Any) -> str:
        captured_config.update(kwargs)
        return ""

    if env is None:
        env = create_environment()

    try:
        template = env.from_string(model.sql_text)
        template.render(ref=_ref, config=config)
    except TemplateSyntaxError as e:
        raise RenderError(
            message=f"Jinja syntax error: {e.message}",
            ref_variant="syntax",
            file_path=model.file_path,
            line=e.lineno,
            model_name=model.name,
        )
    except UndefinedError as e:
        raise RenderError(
            message=f"Undefined variable in Jinja: {e.message}",
            ref_variant="undefined_variable",
            file_path=model.file_path,
            model_name=model.name,
        )

    return ParseResult(
        model_name=model.name,
        dependencies=frozenset(dependencies),
        config=captured_config,
    )


def render_model(
    model: Model,
    known_models: set[str],
    schema: str = "main",
    env: Environment | None = None,
) -> str:
    if env is None:
        env = create_environment()

    def _ref(model_name: str) -> str:
        if model_name not in known_models:
            raise RenderError(
                message=f"Model '{model.name}' references unknown model '{model_name}'",
                ref_variant="undefined_ref",
                file_path=model.file_path,
                model_name=model.name,
            )
        return f'"{schema}"."{model_name}"'

    def _config(**kwargs: Any) -> str:
        return ""

    try:
        template = env.from_string(model.sql_text)
        rendered_sql = template.render(ref=_ref, config=_config)
    except TemplateSyntaxError as e:
        raise RenderError(
            message=f"Jinja syntax error: {e.message}",
            ref_variant="syntax",
            file_path=model.file_path,
            line=e.lineno,
            model_name=model.name,
        )
    except UndefinedError as e:
        raise RenderError(
            message=f"Undefined variable in Jinja: {e.message}",
            ref_variant="undefined_variable",
            file_path=model.file_path,
            model_name=model.name,
        )

    return rendered_sql.strip()
