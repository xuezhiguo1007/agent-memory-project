from __future__ import annotations

from langchain_openai import ChatOpenAI

from agent_memory_project.core.config import SETTINGS


def require_openai_config() -> None:
    if SETTINGS.openai_api_key:
        return
    raise RuntimeError(
        f"Missing OpenAI API key in config/{SETTINGS.env}.toml under [llm].openai_api_key."
    )


def create_chat_model(model_name: str | None = None) -> ChatOpenAI:
    require_openai_config()
    kwargs = {
        "model": model_name or SETTINGS.default_model,
        "temperature": 0.3,
        "api_key": SETTINGS.openai_api_key,
    }
    if SETTINGS.openai_base_url:
        kwargs["base_url"] = SETTINGS.openai_base_url
    return ChatOpenAI(**kwargs)
