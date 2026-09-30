from pathlib import Path

from code_assistant_agent.agent_tools import (
    create_repository_tools,
)
from code_assistant_agent.config import RepositoryConfig


def get_tool_by_name(tools, name: str):
    return next(tool for tool in tools if tool.name == name)


def test_create_repository_tools_returns_expected_tools(
    tmp_path: Path,
) -> None:
    config = RepositoryConfig(root=tmp_path)

    tools = create_repository_tools(config)

    assert [tool.name for tool in tools] == [
        "list_files",
        "read_file",
        "read_file_lines",
        "search_code",
    ]


def test_list_files_tool_invokes_repository_logic(
    tmp_path: Path,
) -> None:
    (tmp_path / "main.py").write_text(
        "print('hello')",
        encoding="utf-8",
    )

    config = RepositoryConfig(root=tmp_path)
    tools = create_repository_tools(config)
    list_files = get_tool_by_name(tools, "list_files")

    result = list_files.invoke(
        {
            "relative_directory": ".",
            "max_files": 10,
        }
    )

    assert result == ["main.py"]


def test_read_file_tool_invokes_repository_logic(
    tmp_path: Path,
) -> None:
    (tmp_path / "main.py").write_text(
        "print('hello')",
        encoding="utf-8",
    )

    config = RepositoryConfig(root=tmp_path)
    tools = create_repository_tools(config)
    read_file = get_tool_by_name(tools, "read_file")

    result = read_file.invoke(
        {
            "relative_path": "main.py",
        }
    )

    assert result == "print('hello')"


def test_search_code_tool_returns_json_compatible_results(
    tmp_path: Path,
) -> None:
    (tmp_path / "service.py").write_text(
        "class PaymentService:\n"
        "    pass\n",
        encoding="utf-8",
    )

    config = RepositoryConfig(root=tmp_path)
    tools = create_repository_tools(config)
    search_code = get_tool_by_name(tools, "search_code")

    result = search_code.invoke(
        {
            "query": "PaymentService",
        }
    )

    assert result == [
        {
            "path": "service.py",
            "line_number": 1,
            "line": "class PaymentService:",
        }
    ]

def test_read_file_lines_tool_returns_numbered_lines(
    tmp_path: Path,
) -> None:
    (tmp_path / "service.py").write_text(
        "first\nsecond\nthird\n",
        encoding="utf-8",
    )

    config = RepositoryConfig(root=tmp_path)
    tools = create_repository_tools(config)
    read_lines = get_tool_by_name(
        tools,
        "read_file_lines",
    )

    result = read_lines.invoke(
        {
            "relative_path": "service.py",
            "start_line": 2,
            "end_line": 3,
        }
    )

    assert result == (
        "    2 | second\n"
        "    3 | third"
    )