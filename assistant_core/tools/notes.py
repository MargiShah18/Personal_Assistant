from __future__ import annotations

from datetime import datetime
from pathlib import Path

from langchain_core.tools import tool


def build_save_note_tool(notes_file: Path):
    @tool("save_note")
    def save_note(note: str) -> str:
        """Save a short note for the user when they explicitly ask to store something."""
        cleaned_note = note.strip()
        if not cleaned_note:
            return "No note was saved because the note was empty."

        notes_file.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
        with notes_file.open("a", encoding="utf-8") as handle:
            handle.write(f"## {timestamp}\n- {cleaned_note}\n\n")
        return f"Saved note to {notes_file.name}."

    return save_note

