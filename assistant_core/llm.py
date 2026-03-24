from __future__ import annotations

from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    GoogleGenerativeAIEmbeddings,
)
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from assistant_core.config import Settings


class MissingModelCredentialsError(RuntimeError):
    """Raised when the app has no model credentials configured."""


def build_chat_model(settings: Settings):
    if settings.model_provider == "gemini":
        if not settings.google_api_key:
            raise MissingModelCredentialsError(
                "GOOGLE_API_KEY is missing. Add it to your environment or .env file."
            )
        return ChatGoogleGenerativeAI(
            model=settings.active_chat_model,
            api_key=settings.google_api_key,
            temperature=0.2,
        )

    if not settings.openai_api_key:
        raise MissingModelCredentialsError(
            "OPENAI_API_KEY is missing. Add it to your environment or .env file."
        )

    model_kwargs = {
        "model": settings.active_chat_model,
        "api_key": settings.openai_api_key,
        "temperature": 0.2,
    }
    if settings.openai_base_url:
        model_kwargs["base_url"] = settings.openai_base_url

    return ChatOpenAI(**model_kwargs)


def build_embeddings(settings: Settings):
    if settings.model_provider == "gemini":
        if not settings.google_api_key:
            raise MissingModelCredentialsError(
                "GOOGLE_API_KEY is missing. Add it to your environment or .env file."
            )
        return GoogleGenerativeAIEmbeddings(
            model=settings.active_embedding_model,
            api_key=settings.google_api_key,
        )

    if not settings.openai_api_key:
        raise MissingModelCredentialsError(
            "OPENAI_API_KEY is missing. Add it to your environment or .env file."
        )

    embeddings_kwargs = {
        "model": settings.active_embedding_model,
        "api_key": settings.openai_api_key,
    }
    if settings.openai_base_url:
        embeddings_kwargs["base_url"] = settings.openai_base_url
    return OpenAIEmbeddings(**embeddings_kwargs)


def credentials_help_text(settings: Settings) -> str:
    if settings.model_provider == "gemini":
        return "Add `GOOGLE_API_KEY` to `.env` or your environment, then rerun the app."
    return "Add `OPENAI_API_KEY` to `.env` or your environment, then rerun the app."
