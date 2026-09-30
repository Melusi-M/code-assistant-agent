import pytest
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
)

from code_assistant_agent.nodes import (
    REVIEWER_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    create_model_node,
    create_reviewer_node,
)


class FakeModel:
    def __init__(self, response: AIMessage):
        self.response = response
        self.received_messages = []

    def invoke(self, messages):
        self.received_messages = messages
        return self.response


def test_model_node_adds_system_prompt() -> None:
    model = FakeModel(
        AIMessage(content="Repository inspected.")
    )
    node = create_model_node(model)

    node(
        {
            "messages": [
                HumanMessage(
                    content="Explain the repository."
                )
            ]
        }
    )

    assert isinstance(
        model.received_messages[0],
        SystemMessage,
    )
    assert (
        model.received_messages[0].content
        == SYSTEM_PROMPT
    )


def test_model_node_passes_conversation_to_model() -> None:
    user_message = HumanMessage(
        content="Where is PaymentService defined?"
    )
    model = FakeModel(
        AIMessage(content="I will search for it.")
    )
    node = create_model_node(model)

    node({"messages": [user_message]})

    assert model.received_messages[1] == user_message


def test_model_node_returns_ai_message_update() -> None:
    response = AIMessage(
        content="PaymentService is in service.py."
    )
    model = FakeModel(response)
    node = create_model_node(model)

    result = node(
        {
            "messages": [
                HumanMessage(content="Find PaymentService")
            ]
        }
    )

    assert result == {
        "messages": [response],
    }

def test_reviewer_node_receives_draft_and_evidence() -> None:
    draft = AIMessage(
        content="Draft repository finding."
    )
    reviewed = AIMessage(
        content="Corrected repository finding."
    )
    model = FakeModel(reviewed)
    node = create_reviewer_node(model)

    result = node(
        {
            "messages": [
                HumanMessage(
                    content="Review this repository."
                ),
                draft,
            ]
        }
    )

    assert isinstance(
        model.received_messages[0],
        SystemMessage,
    )
    assert (
        model.received_messages[0].content
        == REVIEWER_SYSTEM_PROMPT
    )
    assert model.received_messages[-1] == draft
    assert result == {
        "messages": [reviewed],
    }


def test_reviewer_node_rejects_tool_calls() -> None:
    response = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "read_file",
                "args": {
                    "relative_path": "main.py",
                },
                "id": "review-call-1",
                "type": "tool_call",
            }
        ],
    )
    model = FakeModel(response)
    node = create_reviewer_node(model)

    with pytest.raises(
        TypeError,
        match="must not request tools",
    ):
        node(
            {
                "messages": [
                    HumanMessage(
                        content="Review the draft."
                    )
                ]
            }
        )