from pathlib import Path


class DbtminiError(Exception):
    def __init__(
        self,
        message: str,
        *,
        model_name: str | None = None,
        file_path: str | Path | None = None,
        line: int | None = None,
        stage: str | None = None,
    ) -> None:
        self.message = message
        self.model_name = model_name
        self.file_path = str(file_path) if file_path else None
        self.line = line
        self.stage = stage

        # Build a human-readable error string
        details = []
        if self.stage:
            details.append(f"[{self.stage}]")
        if self.file_path:
            loc = f"{self.file_path}:{self.line}" if self.line else self.file_path
            details.append(loc)
        if self.model_name:
            details.append(f"model '{self.model_name}'")

        prefix = " ".join(details)
        full_message = f"{prefix}: {self.message}" if prefix else self.message
        super().__init__(full_message)


class ConfigError(DbtminiError):
    def __init__(
        self,
        message: str,
        *,
        file_path: str | Path | None = None,
        line: int | None = None,
        key: str | None = None,
        model_name: str | None = None,
    ) -> None:
        self.key = key
        super().__init__(
            message=message,
            file_path=file_path,
            line=line,
            stage="config",
            model_name=model_name,
        )


class RenderError(DbtminiError):
    def __init__(
        self,
        message: str,
        *,
        ref_variant: str,
        file_path: str | Path | None = None,
        line: int | None = None,
        model_name: str | None = None,
    ) -> None:
        self.ref_variant = ref_variant
        super().__init__(
            message=message,
            file_path=file_path,
            line=line,
            stage="execution",
            model_name=model_name,
        )


class ProjectError(DbtminiError):
    def __init__(
        self,
        message: str,
        *,
        file_path: str | Path | None = None,
        line: int | None = None,
        model_name: str | None = None,
    ) -> None:
        super().__init__(
            message=message,
            file_path=file_path,
            line=line,
            stage="project",
            model_name=model_name,
        )


class ExecutionError(DbtminiError):
    def __init__(
        self,
        message: str,
        *,
        file_path: str | Path | None = None,
        line: int | None = None,
        model_name: str | None = None,
    ) -> None:
        super().__init__(
            message=message,
            file_path=file_path,
            line=line,
            stage="execution",
            model_name=model_name,
        )


class DagError(DbtminiError):
    def __init__(
        self,
        message: str,
        *,
        file_path: str | Path | None = None,
        line: int | None = None,
        model_name: str | None = None,
    ) -> None:
        super().__init__(
            message=message,
            file_path=file_path,
            line=line,
            model_name=model_name,
        )


class CycleError(DbtminiError):
    def __init__(
        self,
        message: str,
        *,
        cycle_path: list[str],
        file_path: str | Path | None = None,
        line: int | None = None,
        model_name: str | None = None,
    ) -> None:
        self.cycle_path = cycle_path
        super().__init__(
            message=message, file_path=file_path, line=line, model_name=model_name
        )
