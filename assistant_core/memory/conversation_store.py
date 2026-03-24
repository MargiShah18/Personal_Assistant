from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class ConversationStore:
    def __init__(self, file_path: Path, max_messages_per_session: int = 12) -> None:
        self.file_path = file_path
        self.max_messages_per_session = max_messages_per_session

    def upsert_session(self, session_id: str, messages: list[dict[str, str]]) -> None:
        cleaned_messages = [
            {
                "role": message["role"],
                "content": message["content"].strip(),
            }
            for message in messages
            if message.get("role") in {"user", "assistant"} and message.get("content", "").strip()
        ]
        if not any(message["role"] == "user" for message in cleaned_messages):
            return

        payload = self._load()
        payload[session_id] = {
            "session_id": session_id,
            "title": self._build_title(cleaned_messages),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "messages": cleaned_messages[-self.max_messages_per_session :],
        }
        self._write(payload)

    def render_recent_sessions(self, current_session_id: str, limit: int) -> str:
        payload = self._load()
        sessions = self._ordered_sessions(payload, exclude_session_id=current_session_id)

        if not sessions:
            return "No earlier sessions remembered yet."

        rendered_blocks: list[str] = []
        for session in sessions[:limit]:
            recent_turns = []
            for message in session["messages"][-4:]:
                label = "User" if message["role"] == "user" else "Assistant"
                flattened = " ".join(message["content"].split())
                recent_turns.append(f"{label}: {flattened[:220]}")

            rendered_blocks.append(
                "\n".join(
                    [
                        f"Title: {session.get('title', 'Untitled session')}",
                        f"Last updated: {self._format_timestamp(session.get('updated_at', ''))}",
                        *recent_turns,
                    ]
                )
            )
        return "\n\n".join(rendered_blocks)

    def list_sessions(self) -> list[dict[str, str | int]]:
        payload = self._load()
        sessions = self._ordered_sessions(payload)
        return [
            {
                "session_id": session["session_id"],
                "title": session.get("title", "Untitled session"),
                "updated_at": self._format_timestamp(session.get("updated_at", "")),
                "message_count": len(session.get("messages", [])),
            }
            for session in sessions
        ]

    def get_session(self, session_id: str) -> dict | None:
        payload = self._load()
        session = payload.get(session_id)
        if not session:
            return None

        messages = [
            {
                "role": message["role"],
                "content": message["content"],
            }
            for message in session.get("messages", [])
            if message.get("role") in {"user", "assistant"} and message.get("content")
        ]

        return {
            "session_id": session.get("session_id", session_id),
            "title": session.get("title", "Untitled session"),
            "updated_at": self._format_timestamp(session.get("updated_at", "")),
            "messages": messages,
        }

    def _load(self) -> dict[str, dict]:
        if not self.file_path.exists():
            return {}
        try:
            return json.loads(self.file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _write(self, payload: dict[str, dict]) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8"
        )

    def _ordered_sessions(
        self, payload: dict[str, dict], exclude_session_id: str | None = None
    ) -> list[dict]:
        sessions = [
            session
            for session_id, session in payload.items()
            if session.get("messages") and session_id != exclude_session_id
        ]
        sessions.sort(key=lambda session: session.get("updated_at", ""), reverse=True)
        return sessions

    def _build_title(self, messages: list[dict[str, str]]) -> str:
        first_user_message = next(
            (message["content"] for message in messages if message["role"] == "user"),
            "New conversation",
        )
        collapsed = " ".join(first_user_message.split())
        return collapsed[:60] + ("..." if len(collapsed) > 60 else "")

    def _format_timestamp(self, raw_timestamp: str) -> str:
        if not raw_timestamp:
            return "Unknown"
        try:
            parsed = datetime.fromisoformat(raw_timestamp)
        except ValueError:
            return raw_timestamp
        return parsed.astimezone().strftime("%Y-%m-%d %H:%M")
