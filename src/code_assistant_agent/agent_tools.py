from dataclasses import asdict

from langchain_core.tools import BaseTool, tool

from code_assistant_agent.config import RepositoryConfig
from code_assistant_agent.tools import (
    list_repository_files,
    read_repository_file,
    read_repository_lines,
    search_repository_code,
)


def create_repository_tools(
    config: RepositoryConfig,
) -> list[BaseTool]:
    @tool("list_files")
    def list_files(
        relative_directory: str = ".",
        max_files: int = 200,
    ) -> list[str]:
        """List files inside the repository.

        Use this tool to understand the repository structure or discover
        relevant source files. Paths must be relative to the repository root.
        Secret files, generated files, dependencies, and caches are excluded.
        """
        return list_repository_files(
            config,
            relative_directory=relative_directory,
            max_files=max_files,
        )

    @tool("read_file")
    def read_file(
        relative_path: str,
        max_characters: int = 12_000,
    ) -> str:
        """Read a UTF-8 text file from the repository.

        Use this tool after discovering a relevant file. The path must be
        relative to the repository root. Sensitive, binary, and excessively
        large files cannot be read.
        """
        return read_repository_file(
            config,
            relative_path=relative_path,
            max_characters=max_characters,
        )

    @tool("read_file_lines")
    def read_file_lines(
        relative_path: str,
        start_line: int = 1,
        end_line: int | None = None,
        max_lines: int = 200,
    ) -> str:
        """Read a numbered line range from a repository text file.

        Use this tool for targeted inspection after search_code identifies
        relevant locations. Paths must be relative to the repository root.
        At most max_lines lines will be returned.
        """
        return read_repository_lines(
            config,
            relative_path=relative_path,
            start_line=start_line,
            end_line=end_line,
            max_lines=max_lines,
        )

    @tool("search_code")
    def search_code(
        query: str,
        relative_directory: str = ".",
        max_results: int = 50,
        case_sensitive: bool = False,
    ) -> list[dict[str, object]]:
        """Search repository text for a symbol, phrase, or code fragment.

        Returns the relative file path, line number, and matching line.
        Use this tool to locate definitions, usages, configuration values,
        errors, or other relevant code before reading complete files.
        """
        matches = search_repository_code(
            config,
            query=query,
            relative_directory=relative_directory,
            max_results=max_results,
            case_sensitive=case_sensitive,
        )

        return [asdict(match) for match in matches]

    return [
        list_files,
        read_file,
        read_file_lines,
        search_code,
    ]