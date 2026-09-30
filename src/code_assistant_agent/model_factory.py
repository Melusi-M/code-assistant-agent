import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from code_assistant_agent.demo_model import DemoCodeModel
from code_assistant_agent.graph import BindableModel


load_dotenv()


def create_model_from_environment(
    mode: str | None = None,
) -> BindableModel:
    selected_mode = (
        mode
        or os.getenv("CODE_ASSISTANT_MODE", "demo")
    ).strip().lower()

    if selected_mode == "demo":
        return DemoCodeModel()

    if selected_mode == "openai":
        return ChatOpenAI(
            model=os.getenv(
                "OPENAI_MODEL",
                "gpt-5.4-mini",
            )
        )

    raise ValueError(
        "CODE_ASSISTANT_MODE must be either "
        f"'demo' or 'openai', received: {selected_mode!r}"
    )