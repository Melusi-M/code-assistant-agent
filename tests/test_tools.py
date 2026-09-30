from pathlib import Path

import pytest

from code_assistant_agent.config import RepositoryConfig
from code_assistant_agent.tools import (
    RepositoryAccessError,
    resolve_repository_path,
)

from code_assistant_agent.tools import (
    BinaryFileError,
    CodeSearchMatch,
    FileTooLargeError,
    RepositoryAccessError,
    list_repository_files,
    read_repository_file,
    resolve_repository_path,
    search_repository_code,
    read_repository_lines,

)


def test_repository_config_resolves_valid_directory(
    tmp_path: Path,
) -> None:
    config = RepositoryConfig(root=tmp_path)

    assert config.root == tmp_path.resolve()


def test_repository_config_rejects_missing_directory(
    tmp_path: Path,
) -> None:
    missing_directory = tmp_path / "missing"

    with pytest.raises(
        ValueError,
        match="Repository does not exist",
    ):
        RepositoryConfig(root=missing_directory)


def test_repository_config_rejects_file(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "example.py"
    file_path.write_text("print('hello')", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="not a directory",
    ):
        RepositoryConfig(root=file_path)

def test_resolve_repository_path_accepts_child_path(
    tmp_path: Path,
) -> None:
    source_directory = tmp_path / "src"
    source_directory.mkdir()

    config = RepositoryConfig(root=tmp_path)

    result = resolve_repository_path(
        config,
        "src/example.py",
    )

    assert result == (tmp_path / "src/example.py").resolve()


def test_resolve_repository_path_rejects_parent_traversal(
    tmp_path: Path,
) -> None:
    config = RepositoryConfig(root=tmp_path)

    with pytest.raises(
        RepositoryAccessError,
        match="escapes repository root",
    ):
        resolve_repository_path(
            config,
            "../secret.txt",
        )


def test_resolve_repository_path_rejects_absolute_path(
    tmp_path: Path,
) -> None:
    config = RepositoryConfig(root=tmp_path)
    absolute_path = (tmp_path.parent / "secret.txt").resolve()

    with pytest.raises(
        RepositoryAccessError,
        match="must be relative",
    ):
        resolve_repository_path(
            config,
            str(absolute_path),
        )

def test_list_repository_files_returns_relative_paths(
    tmp_path: Path,
) -> None:
    source_directory = tmp_path / "src"
    source_directory.mkdir()

    (source_directory / "main.py").write_text(
        "print('hello')",
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text(
        "# Example",
        encoding="utf-8",
    )

    config = RepositoryConfig(root=tmp_path)

    result = list_repository_files(config)

    assert result == [
        "README.md",
        "src/main.py",
    ]


def test_list_repository_files_skips_ignored_directories(
    tmp_path: Path,
) -> None:
    git_directory = tmp_path / ".git"
    git_directory.mkdir()

    virtual_environment = tmp_path / ".venv"
    virtual_environment.mkdir()

    source_directory = tmp_path / "src"
    source_directory.mkdir()

    (git_directory / "config").write_text(
        "git configuration",
        encoding="utf-8",
    )
    (virtual_environment / "dependency.py").write_text(
        "dependency",
        encoding="utf-8",
    )
    (source_directory / "app.py").write_text(
        "application",
        encoding="utf-8",
    )

    config = RepositoryConfig(root=tmp_path)

    result = list_repository_files(config)

    assert result == ["src/app.py"]


def test_list_repository_files_skips_sensitive_files(
    tmp_path: Path,
) -> None:
    (tmp_path / ".env").write_text(
        "API_KEY=secret",
        encoding="utf-8",
    )
    (tmp_path / ".env.local").write_text(
        "LOCAL_SECRET=secret",
        encoding="utf-8",
    )
    (tmp_path / ".env.example").write_text(
        "API_KEY=placeholder",
        encoding="utf-8",
    )
    (tmp_path / "private.pem").write_text(
        "private key",
        encoding="utf-8",
    )
    (tmp_path / "main.py").write_text(
        "print('safe')",
        encoding="utf-8",
    )

    config = RepositoryConfig(root=tmp_path)

    result = list_repository_files(config)

    assert result == [
        ".env.example",
        "main.py",
    ]


def test_list_repository_files_enforces_limit(
    tmp_path: Path,
) -> None:
    for number in range(5):
        (tmp_path / f"file_{number}.py").write_text(
            f"VALUE = {number}",
            encoding="utf-8",
        )

    config = RepositoryConfig(root=tmp_path)

    result = list_repository_files(
        config,
        max_files=2,
    )

    assert result == [
        "file_0.py",
        "file_1.py",
    ]


def test_list_repository_files_rejects_file_as_directory(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "main.py"
    file_path.write_text(
        "print('hello')",
        encoding="utf-8",
    )

    config = RepositoryConfig(root=tmp_path)

    with pytest.raises(
        NotADirectoryError,
        match="not a directory",
    ):
        list_repository_files(
            config,
            relative_directory="main.py",
        )

def test_read_repository_file_returns_text(
    tmp_path: Path,
) -> None:
    (tmp_path / "main.py").write_text(
        "def main():\n    return 'hello'\n",
        encoding="utf-8",
    )

    config = RepositoryConfig(root=tmp_path)

    result = read_repository_file(
        config,
        "main.py",
    )

    assert result == "def main():\n    return 'hello'\n"


def test_read_repository_file_truncates_long_content(
    tmp_path: Path,
) -> None:
    (tmp_path / "large.txt").write_text(
        "abcdefghij",
        encoding="utf-8",
    )

    config = RepositoryConfig(root=tmp_path)

    result = read_repository_file(
        config,
        "large.txt",
        max_characters=5,
    )

    assert result.startswith("abcde")
    assert "Content truncated" in result


def test_read_repository_file_rejects_sensitive_file(
    tmp_path: Path,
) -> None:
    (tmp_path / ".env").write_text(
        "API_KEY=secret",
        encoding="utf-8",
    )

    config = RepositoryConfig(root=tmp_path)

    with pytest.raises(
        RepositoryAccessError,
        match="sensitive files",
    ):
        read_repository_file(
            config,
            ".env",
        )


def test_read_repository_file_rejects_binary_content(
    tmp_path: Path,
) -> None:
    (tmp_path / "image.bin").write_bytes(
        b"\x89PNG\x00binary-data"
    )

    config = RepositoryConfig(root=tmp_path)

    with pytest.raises(
        BinaryFileError,
        match="Binary files cannot be read",
    ):
        read_repository_file(
            config,
            "image.bin",
        )


def test_read_repository_file_rejects_missing_file(
    tmp_path: Path,
) -> None:
    config = RepositoryConfig(root=tmp_path)

    with pytest.raises(
        FileNotFoundError,
        match="File does not exist",
    ):
        read_repository_file(
            config,
            "missing.py",
        )


def test_read_repository_file_rejects_directory(
    tmp_path: Path,
) -> None:
    source_directory = tmp_path / "src"
    source_directory.mkdir()

    config = RepositoryConfig(root=tmp_path)

    with pytest.raises(
        IsADirectoryError,
        match="Path is not a file",
    ):
        read_repository_file(
            config,
            "src",
        )

def test_search_repository_code_returns_matching_lines(
    tmp_path: Path,
) -> None:
    (tmp_path / "service.py").write_text(
        "class PaymentService:\n"
        "    def process_payment(self):\n"
        "        return 'processed'\n",
        encoding="utf-8",
    )

    config = RepositoryConfig(root=tmp_path)

    result = search_repository_code(
        config,
        "process_payment",
    )

    assert result == [
        CodeSearchMatch(
            path="service.py",
            line_number=2,
            line="def process_payment(self):",
        )
    ]


def test_search_repository_code_is_case_insensitive_by_default(
    tmp_path: Path,
) -> None:
    (tmp_path / "service.py").write_text(
        "class PaymentService:\n"
        "    pass\n",
        encoding="utf-8",
    )

    config = RepositoryConfig(root=tmp_path)

    result = search_repository_code(
        config,
        "paymentservice",
    )

    assert len(result) == 1
    assert result[0].line_number == 1


def test_search_repository_code_supports_case_sensitive_search(
    tmp_path: Path,
) -> None:
    (tmp_path / "service.py").write_text(
        "PaymentService = object()\n"
        "paymentservice = object()\n",
        encoding="utf-8",
    )

    config = RepositoryConfig(root=tmp_path)

    result = search_repository_code(
        config,
        "PaymentService",
        case_sensitive=True,
    )

    assert result == [
        CodeSearchMatch(
            path="service.py",
            line_number=1,
            line="PaymentService = object()",
        )
    ]


def test_search_repository_code_enforces_result_limit(
    tmp_path: Path,
) -> None:
    (tmp_path / "service.py").write_text(
        "result = 1\n"
        "result = 2\n"
        "result = 3\n",
        encoding="utf-8",
    )

    config = RepositoryConfig(root=tmp_path)

    result = search_repository_code(
        config,
        "result",
        max_results=2,
    )

    assert len(result) == 2
    assert result[0].line_number == 1
    assert result[1].line_number == 2


def test_search_repository_code_rejects_empty_query(
    tmp_path: Path,
) -> None:
    config = RepositoryConfig(root=tmp_path)

    with pytest.raises(
        ValueError,
        match="Search query cannot be empty",
    ):
        search_repository_code(
            config,
            "   ",
        )

def test_read_repository_lines_returns_numbered_range(
    tmp_path: Path,
) -> None:
    (tmp_path / "service.py").write_text(
        "line one\n"
        "line two\n"
        "line three\n"
        "line four\n",
        encoding="utf-8",
    )

    config = RepositoryConfig(root=tmp_path)

    result = read_repository_lines(
        config,
        "service.py",
        start_line=2,
        end_line=3,
    )

    assert result == (
        "    2 | line two\n"
        "    3 | line three"
    )


def test_read_repository_lines_enforces_maximum_lines(
    tmp_path: Path,
) -> None:
    (tmp_path / "service.py").write_text(
        "one\ntwo\nthree\nfour\n",
        encoding="utf-8",
    )

    config = RepositoryConfig(root=tmp_path)

    result = read_repository_lines(
        config,
        "service.py",
        start_line=1,
        end_line=4,
        max_lines=2,
    )

    assert result == (
        "    1 | one\n"
        "    2 | two"
    )


def test_read_repository_lines_rejects_invalid_range(
    tmp_path: Path,
) -> None:
    (tmp_path / "service.py").write_text(
        "one\ntwo\n",
        encoding="utf-8",
    )

    config = RepositoryConfig(root=tmp_path)

    with pytest.raises(
        ValueError,
        match="end_line must be",
    ):
        read_repository_lines(
            config,
            "service.py",
            start_line=2,
            end_line=1,
        )


def test_read_repository_lines_rejects_start_beyond_file(
    tmp_path: Path,
) -> None:
    (tmp_path / "service.py").write_text(
        "one\ntwo\n",
        encoding="utf-8",
    )

    config = RepositoryConfig(root=tmp_path)

    with pytest.raises(
        ValueError,
        match="exceeds the file",
    ):
        read_repository_lines(
            config,
            "service.py",
            start_line=10,
        )