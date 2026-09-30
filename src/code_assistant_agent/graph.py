from typing import Protocol

from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from code_assistant_agent.nodes import (
    ToolCallingModel,
    create_model_node,
    create_reviewer_node,
)
from code_assistant_agent.state import CodeAssistantState


class BindableModel(Protocol):
    def bind_tools(
        self,
        tools: list[BaseTool],
    ) -> ToolCallingModel:
        ...


def has_tool_calls(
    state: CodeAssistantState,
) -> bool:
    latest_message = state["messages"][-1]

    return (
        isinstance(latest_message, AIMessage)
        and bool(latest_message.tool_calls)
    )


def route_without_reviewer(
    state: CodeAssistantState,
) -> str:
    if has_tool_calls(state):
        return "tools"

    return "__end__"


def route_with_reviewer(
    state: CodeAssistantState,
) -> str:
    if has_tool_calls(state):
        return "tools"

    return "review"


def build_graph(
    model: BindableModel,
    repository_tools: list[BaseTool],
    reviewer_model: ToolCallingModel | None = None,
):
    bound_model = model.bind_tools(repository_tools)

    model_node = create_model_node(bound_model)
    tool_node = ToolNode(repository_tools)

    builder = StateGraph(CodeAssistantState)

    builder.add_node("model", model_node)
    builder.add_node("tools", tool_node)

    builder.add_edge(START, "model")
    builder.add_edge("tools", "model")

    if reviewer_model is None:
        builder.add_conditional_edges(
            "model",
            route_without_reviewer,
            {
                "tools": "tools",
                "__end__": END,
            },
        )
    else:
        reviewer_node = create_reviewer_node(
            reviewer_model
        )

        builder.add_node("review", reviewer_node)

        builder.add_conditional_edges(
            "model",
            route_with_reviewer,
            {
                "tools": "tools",
                "review": "review",
            },
        )

        builder.add_edge("review", END)

    return builder.compile()