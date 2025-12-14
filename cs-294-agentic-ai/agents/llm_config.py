"""
LLM Configuration and Initialization

This module provides utilities for initializing LLM instances based on
environment configuration. Supports OpenAI, Anthropic, and Google Gemini.
"""
import os
from typing import Optional
from langchain_core.language_models import BaseChatModel


def get_llm(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> BaseChatModel:
    """
    Get LLM instance based on provider configuration.

    Args:
        provider: LLM provider ('openai', 'anthropic', 'google').
                 Defaults to DEFAULT_LLM_PROVIDER env var.
        model: Model name. Defaults to DEFAULT_MODEL env var.
        temperature: Temperature for generation. Defaults to LLM_TEMPERATURE env var.
        max_tokens: Max tokens for generation. Defaults to LLM_MAX_TOKENS env var.

    Returns:
        Initialized LLM instance

    Raises:
        ValueError: If provider is not supported or API key is missing
    """
    # Get configuration from environment or use defaults
    provider = provider or os.getenv("DEFAULT_LLM_PROVIDER", "google")
    model = model or os.getenv("DEFAULT_MODEL", "gemini-pro")
    temperature = temperature if temperature is not None else float(os.getenv("LLM_TEMPERATURE", "0.1"))
    max_tokens = max_tokens if max_tokens is not None else int(os.getenv("LLM_MAX_TOKENS", "2000"))

    provider = provider.lower()

    # Initialize based on provider
    if provider == "google":
        return _get_google_llm(model, temperature, max_tokens)
    elif provider == "openai":
        return _get_openai_llm(model, temperature, max_tokens)
    elif provider == "anthropic":
        return _get_anthropic_llm(model, temperature, max_tokens)
    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider}. "
            f"Supported providers: google, openai, anthropic"
        )


def _get_google_llm(model: str, temperature: float, max_tokens: int) -> BaseChatModel:
    """Initialize Google Gemini LLM"""
    from langchain_google_genai import ChatGoogleGenerativeAI

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY environment variable is required for Google Gemini. "
            "Please set it in your .env file."
        )

    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=temperature,
        max_output_tokens=max_tokens,
        convert_system_message_to_human=True  # Gemini doesn't support system messages natively
    )


def _get_openai_llm(model: str, temperature: float, max_tokens: int) -> BaseChatModel:
    """Initialize OpenAI LLM"""
    from langchain_openai import ChatOpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY environment variable is required for OpenAI. "
            "Please set it in your .env file."
        )

    return ChatOpenAI(
        model=model,
        openai_api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens
    )


def _get_anthropic_llm(model: str, temperature: float, max_tokens: int) -> BaseChatModel:
    """Initialize Anthropic Claude LLM"""
    from langchain_anthropic import ChatAnthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable is required for Anthropic. "
            "Please set it in your .env file."
        )

    return ChatAnthropic(
        model=model,
        anthropic_api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens
    )


# Convenience function for getting default LLM
def get_default_llm() -> BaseChatModel:
    """
    Get default LLM instance based on environment configuration.

    Returns:
        Initialized LLM instance with default settings from environment
    """
    return get_llm()
