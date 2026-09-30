from langchain_core.messages import (
    HumanMessage,
    ToolMessage,
)

from code_assistant_agent.agent_tools import (
    create_repository_tools,
)
from code_assistant_agent.config import RepositoryConfig
from code_assistant_agent.demo_model import DemoCodeModel


def test_demo_model_binds_repository_tools(
    tmp_path,
) -> None:
    tools = create_repository_tools(
        RepositoryConfig(root=tmp_path)
    )
    model = DemoCodeModel()

    result = model.bind_tools(tools)

    assert result is model
    assert model.available_tool_names == {
        "list_files",
        "read_file",
        "read_file_lines",
        "search_code",
    }


def test_demo_model_requests_file_listing_before_tool_result(
    tmp_path,
) -> None:
    tools = create_repository_tools(
        RepositoryConfig(root=tmp_path)
    )
    model = DemoCodeModel()
    model.bind_tools(tools)

    response = model.invoke(
        [
            HumanMessage(
                content="What files are in this repository?"
            )
        ]
    )

    assert response.content == ""
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0]["name"] == "list_files"


def test_demo_model_returns_answer_after_tool_result(
    tmp_path,
) -> None:
    tools = create_repository_tools(
        RepositoryConfig(root=tmp_path)
    )
    model = DemoCodeModel()
    model.bind_tools(tools)

    response = model.invoke(
        [
            HumanMessage(
                content="What files are in this repository?"
            ),
            ToolMessage(
                content='["README.md", "src/main.py"]',
                tool_call_id="demo-list-files",
            ),
        ]
    )

    assert "Demo repository inspection completed" in response.content
    assert "README.md" in response.content
    assert "src/main.py" in response.content