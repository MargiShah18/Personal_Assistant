from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from assistant_core.config import Settings


@dataclass(frozen=True)
class PluginContext:
    system_prompt: str
    memory_context: str
    knowledge_context: str
    generated_at: str


class AssistantPlugin(ABC):
    plugin_id: str
    display_name: str

    @abstractmethod
    def build_tools(self, settings: Settings):
        """Return the tools available to this plugin."""

    @abstractmethod
    def build_context(self, user_query: str, session_id: str) -> PluginContext:
        """Build the prompt context for the current turn."""

    @abstractmethod
    def persist_conversation(
        self, session_id: str, messages: list[dict[str, str]]
    ) -> None:
        """Persist the session after a successful assistant response."""

