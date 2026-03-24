from dataclasses import dataclass

from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from assistant_core.config import Settings, get_settings
from assistant_core.llm import build_chat_model
from assistant_core.messages import (
    langchain_message_to_text,
    latest_user_text,
    ui_messages_to_langchain,
)
from assistant_core.plugins.base import PluginContext
from assistant_core.plugins.loader import get_plugin


@dataclass(frozen=True)
class AssistantRunResult:
    content: str
    context: PluginContext


class AssistantOrchestrator:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.plugin = get_plugin(self.settings.active_plugin)
        self.tools = self.plugin.build_tools(self.settings)
        self.model = build_chat_model(self.settings).bind_tools(self.tools)
        self.graph = self._build_graph()

    def _build_graph(self):
        tool_node = ToolNode(self.tools, handle_tool_errors=True)

        def call_model(
            state: MessagesState, config: RunnableConfig | None = None
        ) -> dict[str, list]:
            configurable = config.get("configurable", {}) if config else {}
            system_prompt = configurable.get("system_prompt", "You are a helpful assistant.")
            response = self.model.invoke(
                [SystemMessage(content=str(system_prompt)), *state["messages"]]
            )
            return {"messages": [response]}

        builder = StateGraph(MessagesState)
        builder.add_node("agent", call_model)
        builder.add_node("tools", tool_node)
        builder.add_edge(START, "agent")
        builder.add_conditional_edges("agent", tools_condition)
        builder.add_edge("tools", "agent")
        return builder.compile()

    def run(self, messages: list[dict[str, object]], session_id: str) -> AssistantRunResult:
        context = self.plugin.build_context(latest_user_text(messages), session_id)
        result = self.graph.invoke(
            {"messages": ui_messages_to_langchain(messages)},
            config={
                "configurable": {
                    "session_id": session_id,
                    "system_prompt": context.system_prompt,
                }
            },
        )
        final_message = result["messages"][-1]
        final_text = langchain_message_to_text(final_message)
        self.plugin.persist_conversation(
            session_id,
            [
                *messages,
                {
                    "role": "assistant",
                    "content": final_text,
                    "sources": context.knowledge_sources,
                },
            ],
        )
        return AssistantRunResult(content=final_text, context=context)
