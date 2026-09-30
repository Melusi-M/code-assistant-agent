import argparse
from pathlib import Path

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
)

from code_assistant_agent.agent_tools import (
    create_repository_tools,
)
from code_assistant_agent.config import RepositoryConfig
from code_assistant_agent.graph import build_graph
from code_assistant_agent.model_factory import (
    create_model_from_environment,
)
from code_assistant_agent.models import (
    CodeAssistantResult,
    ToolActivity,
)


def execute_code_assistant(
    repository_path: Path,
    question: str,
    mode: str | None = None,
    max_steps: int = 20,
) -> CodeAssistantResult:
    normalized_question = question.strip()

    if max_steps <= 0:
        raise ValueError("max_steps must be greater than zero")

    if not normalized_question:
        raise ValueError("Question cannot be empty")

    config = RepositoryConfig(root=repository_path)
    repository_tools = create_repository_tools(config)
    model = create_model_from_environment(mode)

    graph = build_graph(
        model=model,
        repository_tools=repository_tools,
        reviewer_model=model,
    )

    graph_result = graph.invoke(
        {
            "messages": [
                HumanMessage(
                    content=normalized_question,
                )
            ]
        },
        config={
        "recursion_limit": max_steps,
    },
    )

    messages = graph_result["messages"]
    final_message = messages[-1]

    if not isinstance(final_message, AIMessage):
        raise RuntimeError(
            "The graph did not finish with an AI response"
        )

    if not isinstance(final_message.content, str):
        raise RuntimeError(
            "The final AI response was not text"
        )

    tool_activity: list[ToolActivity] = []

    for message in messages:
        if not isinstance(message, AIMessage):
            continue

        for tool_call in message.tool_calls:
            tool_activity.append(
                ToolActivity(
                    name=tool_call["name"],
                    arguments=dict(
                        tool_call.get("args", {})
                    ),
                )
            )

    return CodeAssistantResult(
        answer=final_message.content,
        tool_activity=tool_activity,
    )


def run_code_assistant(
    repository_path: Path,
    question: str,
    mode: str | None = None,
    max_steps: int = 20,
) -> str:
    result = execute_code_assistant(
        repository_path=repository_path,
        question=question,
        mode=mode,
        max_steps=max_steps,
    )

    return result.answer


def create_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Ask repository-aware questions using a "
            "tool-calling code assistant."
        )
    )

    parser.add_argument(
        "--repo",
        type=Path,
        required=True,
        help="Path to the repository to inspect.",
    )

    parser.add_argument(
        "--question",
        required=True,
        help="Question to ask about the repository.",
    )

    parser.add_argument(
        "--mode",
        choices=["demo", "openai"],
        default=None,
        help=(
            "Model mode. Overrides CODE_ASSISTANT_MODE "
            "when provided."
        ),
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Display the repository tools selected by the agent.",
    )

    return parser


def main() -> None:
    parser = create_argument_parser()
    parser.add_argument(
    "--max-steps",
    type=int,
    default=20,
    help="Maximum number of LangGraph execution steps.",
)
    arguments = parser.parse_args()
    
    result = execute_code_assistant(
        repository_path=arguments.repo,
        question=arguments.question,
        mode=arguments.mode,
        max_steps=arguments.max_steps,
    )

    if arguments.verbose:
        print("\nTool activity")
        print("-" * 60)

        if not result.tool_activity:
            print("No tools were called.")

        for number, activity in enumerate(
            result.tool_activity,
            start=1,
        ):
            print(
                f"{number}. {activity.name}"
                f"({activity.arguments})"
            )

    print("\nCode Assistant")
    print("=" * 60)
    print(result.answer)


if __name__ == "__main__":
    main()