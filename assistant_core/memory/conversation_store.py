from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ConversationStore:
    def __init__(
        self,
        file_path: Path,
        max_messages_per_session: int = 12,
        timezone_name: str | None = None,
    ) -> None:
        self.file_path = file_path
        self.max_messages_per_session = max_messages_per_session
        self.display_timezone = self._resolve_timezone(timezone_name)

    def upsert_session(self, session_id: str, messages: list[dict[str, object]]) -> None:
        cleaned_messages = [
            self._clean_message(message)
            for message in messages
            if message.get("role") in {"user", "assistant"} and message.get("content", "").strip()
        ]
        if not any(message["role"] == "user" for message in cleaned_messages):
            return

        payload = self._load()
        existing_session = payload.get(session_id, {})
        has_manual_title = (
            existing_session.get("title_source") == "manual"
            and bool(str(existing_session.get("title", "")).strip())
        )
        title = (
            str(existing_session.get("title", "")).strip()
            if has_manual_title
            else self._build_title(cleaned_messages)
        )
        payload[session_id] = {
            "session_id": session_id,
            "title": title,
            "title_source": "manual" if has_manual_title else "auto",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "messages": cleaned_messages[-self.max_messages_per_session :],
        }
        self._write(payload)

    def rename_session(self, session_id: str, title: str) -> bool:
        normalized_title = self._normalize_title(title)
        if not normalized_title:
            return False

        payload = self._load()
        session = payload.get(session_id)
        if not session:
            return False

        session["title"] = normalized_title
        session["title_source"] = "manual"
        self._write(payload)
        return True

    def delete_session(self, session_id: str) -> bool:
        payload = self._load()
        if session_id not in payload:
            return False
        del payload[session_id]
        self._write(payload)
        return True

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
                "updated_at_raw": session.get("updated_at", ""),
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
            self._clean_message(message)
            for message in session.get("messages", [])
            if message.get("role") in {"user", "assistant"} and message.get("content")
        ]

        return {
            "session_id": session.get("session_id", session_id),
            "title": session.get("title", "Untitled session"),
            "updated_at_raw": session.get("updated_at", ""),
            "updated_at": self._format_timestamp(session.get("updated_at", "")),
            "messages": messages,
        }

    def _clean_message(self, message: dict[str, object]) -> dict[str, object]:
        cleaned_message: dict[str, object] = {
            "role": str(message["role"]),
            "content": str(message["content"]).strip(),
        }
        cleaned_sources = self._clean_sources(message.get("sources"))
        if cleaned_sources:
            cleaned_message["sources"] = cleaned_sources
        return cleaned_message

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
        collapsed = self._normalize_title(first_user_message) or "New conversation"
        return collapsed[:60] + ("..." if len(collapsed) > 60 else "")

    def _format_timestamp(self, raw_timestamp: str) -> str:
        parsed = self._parse_timestamp(raw_timestamp)
        if parsed is None:
            if not raw_timestamp:
                return "Unknown"
            return raw_timestamp
        localized = self._to_display_timezone(parsed)
        return localized.strftime("%Y-%m-%d %H:%M")

    def _normalize_title(self, title: str) -> str:
        collapsed = " ".join(title.split())
        return collapsed[:80]

    def _clean_sources(self, sources: object) -> list[str]:
        if not isinstance(sources, list):
            return []
        cleaned_sources: list[str] = []
        for source in sources:
            normalized = " ".join(str(source).split())
            if normalized and normalized not in cleaned_sources:
                cleaned_sources.append(normalized[:120])
        return cleaned_sources

    def _parse_timestamp(self, raw_timestamp: str) -> datetime | None:
        if not raw_timestamp:
            return None
        try:
            parsed = datetime.fromisoformat(raw_timestamp)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed

    def _to_display_timezone(self, parsed: datetime) -> datetime:
        if self.display_timezone is None:
            return parsed.astimezone()
        return parsed.astimezone(self.display_timezone)

    def _resolve_timezone(self, timezone_name: str | None) -> ZoneInfo | None:
        if not timezone_name:
            return None
        try:
            return ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            return None
