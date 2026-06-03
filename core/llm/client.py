"""
LLM Client Factory

Provides configured instances of ChatOllama for different agent types.
"""

from langchain_ollama import ChatOllama
from config.settings import settings


def get_reasoning_model(temperature: float = 0.1) -> ChatOllama:
    """
    Returns the reasoning model (Llama 3.2 3B) configured for structured output.
    Low temperature (0.1) is used for deterministic extraction tasks.
    """
    return ChatOllama(
        model=settings.sdlc_reason_model,
        temperature=temperature,
        base_url=settings.ollama_host,
        # Request JSON format to help the model adhere to schema
        format="json", 
    )


def get_code_model(temperature: float = 0.2) -> ChatOllama:
    """
    Returns the code model (Qwen2.5-Coder 3B).
    Slightly higher temperature for creative code generation.
    """
    return ChatOllama(
        model=settings.sdlc_code_model,
        temperature=temperature,
        base_url=settings.ollama_host,
    )