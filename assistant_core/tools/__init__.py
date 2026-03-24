from assistant_core.config import Settings
from assistant_core.tools.calculator import calculator
from assistant_core.tools.notes import build_save_note_tool
from assistant_core.tools.web_search import build_web_search_tool


def build_personal_tools(settings: Settings):
    return [
        calculator,
        build_save_note_tool(settings.notes_file),
        build_web_search_tool(),
    ]

