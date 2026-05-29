"""LLM interface for the cocktail recommendation agent."""

import os
from langchain_openai import ChatOpenAI

from src.config import LLM_MODEL


def get_llm() -> ChatOpenAI:
    """
    Get a ChatOpenAI instance configured for OpenRouter.

    The LLM is configured to call OpenRouter's API endpoint with custom headers
    for identification. API key and optional site URL/name come from environment variables.
    """
    return ChatOpenAI(
        model=LLM_MODEL,
        openai_api_key=os.environ["OPENROUTER_API_KEY"],
        openai_api_base="https://openrouter.ai/api/v1",
        default_headers={
            "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", ""),
            "X-Title": os.getenv("OPENROUTER_SITE_NAME", "cocktail-agent"),
        },
    )
