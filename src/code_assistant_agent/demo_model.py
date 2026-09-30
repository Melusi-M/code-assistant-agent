from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool


class DemoCodeModel:
    """Deterministic tool-calling model for tests and demos."""

    def __init__(self) -> None:
        self.available_tool_names: set[str] = set()

    def bind_tools(
        self,
        tools: list[BaseTool],
    ) -> "DemoCodeModel":
        self.available_tool_names = {
            tool.name for tool in tools
        }

        if "list_files" not in self.available_tool_names:
            raise ValueError(
                "DemoCodeModel requires the list_files tool"
            )

        return self

    def invoke(
        self,
        messages: list[AnyMessage],
    ) -> AIMessage:
        tool_messages = [
            message
            for message in messages
            if isinstance(message, ToolMessage)
        ]

        if not tool_messages:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "list_files",
                        "args": {
                            "relative_directory": ".",
                            "max_files": 50,
                        },
                        "id": "demo-list-files",
                        "type": "tool_call",
                    }
                ],
            )

        latest_tool_result = tool_messages[-1].content

        return AIMessage(
            content=(
                "Demo repository inspection completed.\n\n"
                "Discovered files:\n"
                f"{latest_tool_result}"
            )
        )