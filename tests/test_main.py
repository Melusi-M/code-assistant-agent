from pathlib import Path

import pytest

from code_assistant_agent.demo_model import DemoCodeModel
from code_assistant_agent.main import run_code_assistant
from code_assistant_agent.model_factory import (
    create_model_from_environment,
)

from code_assistant_agent.main import (
    execute_code_assistant,
    run_code_assistant,
)


def test_model_factory_defaults_to_demo(
    monkeypatch,
) -> None:
    monkeypatch.delenv(
        "CODE_ASSISTANT_MODE",
        raising=False,
    )

    model = create_model_from_environment()

    assert isinstance(model, DemoCodeModel)


def test_model_factory_rejects_unknown_mode() -> None:
    with pytest.raises(
        ValueError,
        match="must be either",
    ):
        create_model_from_environment("unknown")


def test_run_code_assistant_in_demo_mode(
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").write_text(
        "# Example repository",
        encoding="utf-8",
    )
    source_directory = tmp_path / "src"
    source_directory.mkdir()
    (source_directory / "main.py").write_text(
        "print('hello')",
        encoding="utf-8",
    )

    answer = run_code_assistant(
        repository_path=tmp_path,
        question="Which files are in this repository?",
        mode="demo",
    )

    assert "Demo repository inspection completed" in answer
    assert "README.md" in answer
    assert "src/main.py" in answer

def test_execute_code_assistant_records_tool_activity(
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").write_text(
        "# Example",
        encoding="utf-8",
    )

    result = execute_code_assistant(
        repository_path=tmp_path,
        question="Which files are in this repository?",
        mode="demo",
    )

    assert result.answer
    assert len(result.tool_activity) == 1
    assert result.tool_activity[0].name == "list_files"
    assert result.tool_activity[0].arguments == {
        "relative_directory": ".",
        "max_files": 50,
    }

def test_execute_code_assistant_rejects_invalid_step_limit(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        ValueError,
        match="max_steps must be greater than zero",
    ):
        execute_code_assistant(
            repository_path=tmp_path,
            question="Explain this repository",
            mode="demo",
            max_steps=0,
        )