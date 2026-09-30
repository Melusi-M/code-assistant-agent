from pathlib import Path
import pytest

from langgraph.errors import GraphRecursionError

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    ToolMessage,
)

from code_assistant_agent.agent_tools import (
    create_repository_tools,
)
from code_assistant_agent.config import RepositoryConfig
from code_assistant_agent.graph import build_graph


class FakeToolCallingModel:
    def __init__(
        self,
        responses: list[AIMessage],
    ) -> None:
        self.responses = list(responses)
        self.bound_tools = []
        self.received_messages = []

    def bind_tools(self, tools):
        self.bound_tools = tools
        return self

    def invoke(self, messages):
        self.received_messages.append(messages)

        if not self.responses:
            raise RuntimeError(
                "Fake model has no responses remaining"
            )

        return self.responses.pop(0)


def test_graph_ends_when_model_returns_final_answer(
    tmp_path: Path,
) -> None:
    model = FakeToolCallingModel(
        responses=[
            AIMessage(
                content="This repository contains Python code."
            )
        ]
    )
    tools = create_repository_tools(
        RepositoryConfig(root=tmp_path)
    )
    graph = build_graph(model, tools)

    result = graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content="What does this repository contain?"
                )
            ]
        }
    )

    assert (
        result["messages"][-1].content
        == "This repository contains Python code."
    )
    assert len(model.received_messages) == 1


def test_graph_executes_tool_and_returns_to_model(
    tmp_path: Path,
) -> None:
    (tmp_path / "main.py").write_text(
        "print('hello')",
        encoding="utf-8",
    )

    model = FakeToolCallingModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "list_files",
                        "args": {
                            "relative_directory": ".",
                            "max_files": 10,
                        },
                        "id": "call-1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(
                content="The repository contains main.py."
            ),
        ]
    )

    tools = create_repository_tools(
        RepositoryConfig(root=tmp_path)
    )
    graph = build_graph(model, tools)

    result = graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content="Which files are in this repository?"
                )
            ]
        }
    )

    messages = result["messages"]

    assert isinstance(messages[0], HumanMessage)
    assert messages[1].tool_calls[0]["name"] == "list_files"
    assert isinstance(messages[2], ToolMessage)
    assert "main.py" in messages[2].content
    assert (
        messages[3].content
        == "The repository contains main.py."
    )

    assert len(model.received_messages) == 2
    assert [tool.name for tool in model.bound_tools] == [
    "list_files",
    "read_file",
    "read_file_lines",
    "search_code",
   ]

def test_graph_stops_runaway_tool_loop(
    tmp_path: Path,
) -> None:
    responses = [
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "list_files",
                    "args": {
                        "relative_directory": ".",
                        "max_files": 10,
                    },
                    "id": f"loop-call-{number}",
                    "type": "tool_call",
                }
            ],
        )
        for number in range(10)
    ]

    model = FakeToolCallingModel(responses=responses)
    tools = create_repository_tools(
        RepositoryConfig(root=tmp_path)
    )
    graph = build_graph(model, tools)

    with pytest.raises(GraphRecursionError):
        graph.invoke(
            {
                "messages": [
                    HumanMessage(
                        content="Keep inspecting forever."
                    )
                ]
            },
            config={
                "recursion_limit": 3,
            },
        )

def test_graph_sends_draft_to_reviewer(
    tmp_path: Path,
) -> None:
    model = FakeToolCallingModel(
        responses=[
            AIMessage(
                content="Unverified draft answer."
            ),
            AIMessage(
                content="Verified final answer."
            ),
        ]
    )

    tools = create_repository_tools(
        RepositoryConfig(root=tmp_path)
    )

    graph = build_graph(
        model=model,
        repository_tools=tools,
        reviewer_model=model,
    )

    result = graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content="Find a repository issue."
                )
            ]
        }
    )

    assert (
        result["messages"][-2].content
        == "Unverified draft answer."
    )
    assert (
        result["messages"][-1].content
        == "Verified final answer."
    )
    assert len(model.received_messages) == 2