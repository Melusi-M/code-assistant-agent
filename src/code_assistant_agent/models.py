from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolActivity:
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class CodeAssistantResult:
    answer: str
    tool_activity: list[ToolActivity]