from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from zoneinfo import ZoneInfo

from assistant_core.config import Settings, get_settings
from assistant_core.memory.conversation_store import ConversationStore
from assistant_core.plugins.base import AssistantPlugin, PluginContext
from assistant_core.retrieval.knowledge_base import KnowledgeBase
from assistant_core.tools import build_personal_tools


@dataclass
class PersonalAssistantPlugin(AssistantPlugin):
    settings: Settings
    plugin_id: str = "personal"
    display_name: str = "Personal Assistant"
    memory_store: ConversationStore = field(init=False)
    knowledge_base: KnowledgeBase = field(init=False)

    def __post_init__(self) -> None:
        self.memory_store = ConversationStore(
            self.settings.memory_file,
            timezone_name=self.settings.timezone,
        )
        self.knowledge_base = KnowledgeBase(self.settings)

    def build_tools(self, settings: Settings):
        return build_personal_tools(settings)

    def build_context(self, user_query: str, session_id: str) -> PluginContext:
        generated_at = datetime.now(ZoneInfo(self.settings.timezone)).strftime(
            "%A, %B %d, %Y at %I:%M %p %Z"
        )
        memory_context = self.memory_store.render_recent_sessions(
            current_session_id=session_id,
            limit=self.settings.max_recent_sessions,
        )
        knowledge_context, knowledge_sources = self.knowledge_base.build_context(
            query=user_query,
            limit=self.settings.retrieval_k,
        )
        system_prompt = (
            "You are the Personal mode plugin inside a pluggable executive assistant.\n"
            "Help with planning, note summarization, prioritization, small research, and next actions.\n"
            "Use the user's document context and remembered sessions when they are relevant.\n"
            "If remembered sessions or retrieved documents are irrelevant, ignore them.\n"
            "Use tools deliberately:\n"
            "- Use calculator for arithmetic, comparisons, and quick estimates.\n"
            "- Use save_note only when the user explicitly asks to save, store, or remember a note.\n"
            "- Use quick_web_search only for time-sensitive public facts.\n"
            "Never invent personal facts that are missing from the context.\n"
            "Be practical, calm, concise, and action-oriented.\n\n"
            f"Current local time: {generated_at}\n\n"
            "Recent remembered sessions:\n"
            f"{memory_context}\n\n"
            "Relevant personal documents:\n"
            f"{knowledge_context}\n"
        )
        return PluginContext(
            system_prompt=system_prompt,
            memory_context=memory_context,
            knowledge_context=knowledge_context,
            knowledge_sources=knowledge_sources,
            generated_at=generated_at,
        )

    def persist_conversation(
        self, session_id: str, messages: list[dict[str, object]]
    ) -> None:
        self.memory_store.upsert_session(session_id, messages)


@lru_cache(maxsize=1)
def get_plugin() -> PersonalAssistantPlugin:
    return PersonalAssistantPlugin(get_settings())
