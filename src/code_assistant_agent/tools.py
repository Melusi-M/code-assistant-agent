import os

from pathlib import Path
from dataclasses import dataclass

from code_assistant_agent.config import RepositoryConfig


IGNORED_DIRECTORY_NAMES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "build",
    "dist",
}

SENSITIVE_FILE_SUFFIXES = {
    ".key",
    ".pem",
    ".p12",
    ".pfx",
}

SENSITIVE_FILE_NAMES = {
    "credentials.json",
    "secrets.json",
}


MAX_FILE_SIZE_BYTES = 1_000_000
DEFAULT_MAX_CHARACTERS = 12_000

MAX_SEARCH_FILES = 5_000
MAX_MATCH_LINE_CHARACTERS = 300


@dataclass(frozen=True)
class CodeSearchMatch:
    path: str
    line_number: int
    line: str

class FileTooLargeError(ValueError):
    """Raised when a file exceeds the repository read limit."""


class BinaryFileError(ValueError):
    """Raised when a requested file appears to contain binary data."""


class RepositoryAccessError(ValueError):
    """Raised when repository access violates the configured boundary."""


def resolve_repository_path(
    config: RepositoryConfig,
    relative_path: str,
) -> Path:
    requested_path = Path(relative_path)

    if requested_path.is_absolute():
        raise RepositoryAccessError(
            "Tool paths must be relative to the repository root"
        )

    resolved_path = (config.root / requested_path).resolve()

    try:
        resolved_path.relative_to(config.root)
    except ValueError as error:
        raise RepositoryAccessError(
            f"Path escapes repository root: {relative_path}"
        ) from error

    return resolved_path


def is_sensitive_file(path: Path) -> bool:
    normalized_name = path.name.lower()

    if normalized_name == ".env":
        return True

    if (
        normalized_name.startswith(".env.")
        and normalized_name != ".env.example"
    ):
        return True

    if normalized_name in SENSITIVE_FILE_NAMES:
        return True

    return path.suffix.lower() in SENSITIVE_FILE_SUFFIXES


def list_repository_files(
    config: RepositoryConfig,
    relative_directory: str = ".",
    max_files: int = 200,
) -> list[str]:
    if max_files <= 0:
        raise ValueError("max_files must be greater than zero")

    start_directory = resolve_repository_path(
        config,
        relative_directory,
    )

    if not start_directory.exists():
        raise FileNotFoundError(
            f"Directory does not exist: {relative_directory}"
        )

    if not start_directory.is_dir():
        raise NotADirectoryError(
            f"Path is not a directory: {relative_directory}"
        )

    discovered_files: list[str] = []

    for current_root, directory_names, file_names in os.walk(
        start_directory
    ):
        directory_names[:] = sorted(
            directory_name
            for directory_name in directory_names
            if directory_name not in IGNORED_DIRECTORY_NAMES
        )

        for file_name in sorted(file_names):
            file_path = Path(current_root) / file_name

            if is_sensitive_file(file_path):
                continue

            relative_path = file_path.relative_to(config.root)
            discovered_files.append(relative_path.as_posix())

            if len(discovered_files) >= max_files:
                return discovered_files

    return discovered_files

def read_repository_file(
    config: RepositoryConfig,
    relative_path: str,
    max_characters: int = DEFAULT_MAX_CHARACTERS,
) -> str:
    if max_characters <= 0:
        raise ValueError(
            "max_characters must be greater than zero"
        )

    file_path = resolve_repository_path(
        config,
        relative_path,
    )

    if is_sensitive_file(file_path):
        raise RepositoryAccessError(
            f"Reading sensitive files is not allowed: {relative_path}"
        )

    if not file_path.exists():
        raise FileNotFoundError(
            f"File does not exist: {relative_path}"
        )

    if not file_path.is_file():
        raise IsADirectoryError(
            f"Path is not a file: {relative_path}"
        )

    file_size = file_path.stat().st_size

    if file_size > MAX_FILE_SIZE_BYTES:
        raise FileTooLargeError(
            f"File is too large to read: {relative_path} "
            f"({file_size} bytes)"
        )

    raw_content = file_path.read_bytes()

    if b"\x00" in raw_content:
        raise BinaryFileError(
            f"Binary files cannot be read: {relative_path}"
        )

    try:
        content = raw_content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise BinaryFileError(
            f"File is not valid UTF-8 text: {relative_path}"
        ) from error

    content = content.replace("\r\n", "\n").replace("\r", "\n")


    if len(content) <= max_characters:
        return content

    return (
        content[:max_characters]
        + "\n\n[Content truncated because it exceeded "
        + f"{max_characters} characters]"
    )

def search_repository_code(
    config: RepositoryConfig,
    query: str,
    relative_directory: str = ".",
    max_results: int = 50,
    case_sensitive: bool = False,
) -> list[CodeSearchMatch]:
    normalized_query = query.strip()

    if not normalized_query:
        raise ValueError("Search query cannot be empty")

    if max_results <= 0:
        raise ValueError("max_results must be greater than zero")

    repository_files = list_repository_files(
        config,
        relative_directory=relative_directory,
        max_files=MAX_SEARCH_FILES,
    )

    search_query = (
        normalized_query
        if case_sensitive
        else normalized_query.casefold()
    )

    matches: list[CodeSearchMatch] = []

    for relative_path in repository_files:
        try:
            content = read_repository_file(
                config,
                relative_path,
                max_characters=MAX_FILE_SIZE_BYTES,
            )
        except (BinaryFileError, FileTooLargeError):
            continue

        for line_number, line in enumerate(
            content.splitlines(),
            start=1,
        ):
            searchable_line = (
                line
                if case_sensitive
                else line.casefold()
            )

            if search_query not in searchable_line:
                continue

            displayed_line = line.strip()

            if len(displayed_line) > MAX_MATCH_LINE_CHARACTERS:
                displayed_line = (
                    displayed_line[:MAX_MATCH_LINE_CHARACTERS]
                    + "..."
                )

            matches.append(
                CodeSearchMatch(
                    path=relative_path,
                    line_number=line_number,
                    line=displayed_line,
                )
            )

            if len(matches) >= max_results:
                return matches

    return matches


def read_repository_lines(
    config: RepositoryConfig,
    relative_path: str,
    start_line: int = 1,
    end_line: int | None = None,
    max_lines: int = 200,
) -> str:
    if start_line <= 0:
        raise ValueError("start_line must be greater than zero")

    if max_lines <= 0:
        raise ValueError("max_lines must be greater than zero")

    if end_line is not None and end_line < start_line:
        raise ValueError(
            "end_line must be greater than or equal to start_line"
        )

    content = read_repository_file(
        config,
        relative_path,
        max_characters=MAX_FILE_SIZE_BYTES,
    )

    lines = content.splitlines()

    if start_line > len(lines):
        raise ValueError(
            f"start_line {start_line} exceeds the file's "
            f"{len(lines)} lines"
        )

    maximum_end_line = start_line + max_lines - 1

    selected_end_line = min(
        end_line if end_line is not None else maximum_end_line,
        maximum_end_line,
        len(lines),
    )

    selected_lines = lines[
        start_line - 1:selected_end_line
    ]

    return "\n".join(
        f"{line_number:>5} | {line}"
        for line_number, line in enumerate(
            selected_lines,
            start=start_line,
        )
    )
