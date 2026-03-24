from __future__ import annotations

import html
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

import streamlit as st

from assistant_core.config import get_settings
from assistant_core.llm import MissingModelCredentialsError, credentials_help_text
from assistant_core.memory.conversation_store import ConversationStore
from assistant_core.orchestrator import AssistantOrchestrator


settings = get_settings()
conversation_store = ConversationStore(
    settings.memory_file,
    timezone_name=settings.timezone,
)


def _default_messages() -> list[dict[str, str]]:
    return []


def _initialize_state() -> None:
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid4())
    if "messages" not in st.session_state:
        st.session_state.messages = _default_messages()
    if "last_run" not in st.session_state:
        st.session_state.last_run = None
    if "history_edit_session_id" not in st.session_state:
        st.session_state.history_edit_session_id = None
    if "history_rename_value" not in st.session_state:
        st.session_state.history_rename_value = ""
    if "history_delete_session_id" not in st.session_state:
        st.session_state.history_delete_session_id = None


def _truncate(text: str, limit: int = 34) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 1] + "…"


def _current_title() -> str:
    saved_session = conversation_store.get_session(st.session_state.session_id)
    if saved_session:
        return str(saved_session["title"])

    first_user_message = next(
        (
            message["content"]
            for message in st.session_state.messages
            if message.get("role") == "user" and message.get("content")
        ),
        "",
    )
    if first_user_message:
        return _truncate(first_user_message, 54)
    return "New chat"


def _clear_history_ui_state() -> None:
    st.session_state.history_edit_session_id = None
    st.session_state.history_rename_value = ""
    st.session_state.history_delete_session_id = None


def _reset_chat() -> None:
    _clear_history_ui_state()
    st.session_state.session_id = str(uuid4())
    st.session_state.messages = _default_messages()
    st.session_state.last_run = None


def _load_chat(session_id: str) -> None:
    session = conversation_store.get_session(session_id)
    if not session:
        return
    _clear_history_ui_state()
    st.session_state.session_id = str(session["session_id"])
    st.session_state.messages = session["messages"]
    st.session_state.last_run = None


def _start_rename(session_id: str, current_title: str) -> None:
    st.session_state.history_edit_session_id = session_id
    st.session_state.history_rename_value = current_title
    st.session_state.history_delete_session_id = None


def _start_delete(session_id: str) -> None:
    st.session_state.history_delete_session_id = session_id
    st.session_state.history_edit_session_id = None
    st.session_state.history_rename_value = ""


def _updated_local_date(raw_timestamp: str) -> date | None:
    if not raw_timestamp:
        return None
    try:
        parsed = datetime.fromisoformat(raw_timestamp)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(ZoneInfo(settings.timezone)).date()


def _group_label_for_date(raw_timestamp: str) -> str:
    local_date = _updated_local_date(raw_timestamp)
    if local_date is None:
        return "Unknown date"

    today = datetime.now(ZoneInfo(settings.timezone)).date()
    if local_date == today:
        return "Today"
    if local_date == today - timedelta(days=1):
        return "Yesterday"
    if local_date.year == today.year:
        return local_date.strftime("%b %d")
    return local_date.strftime("%b %d, %Y")


def _group_sessions_by_date(
    sessions: list[dict[str, str | int]],
) -> dict[str, list[dict[str, str | int]]]:
    grouped_sessions: dict[str, list[dict[str, str | int]]] = {}
    for session in sessions:
        label = _group_label_for_date(str(session.get("updated_at_raw", "")))
        grouped_sessions.setdefault(label, []).append(session)
    return grouped_sessions


def _message_count_label(message_count: int) -> str:
    if message_count == 1:
        return "1 message"
    return f"{message_count} messages"


def _current_chat_summary(
    current_session: dict[str, str | int] | None,
) -> tuple[str, str]:
    if current_session:
        return (
            str(current_session["title"]),
            f"{_message_count_label(int(current_session['message_count']))} | Updated {current_session['updated_at']}",
        )
    if st.session_state.messages:
        return (
            _current_title(),
            "In progress | This chat will save after the first successful reply.",
        )
    return ("New chat", "Fresh chat | Start a conversation to save it here.")


def _render_rename_form(session_id: str) -> None:
    with st.form(key=f"rename_form_{session_id}", clear_on_submit=False):
        st.text_input("Chat name", key="history_rename_value")
        save_col, cancel_col = st.columns(2)
        with save_col:
            save_clicked = st.form_submit_button(
                "Save",
                use_container_width=True,
                type="primary",
            )
        with cancel_col:
            cancel_clicked = st.form_submit_button(
                "Cancel",
                use_container_width=True,
            )

        if save_clicked:
            if conversation_store.rename_session(
                session_id,
                st.session_state.history_rename_value,
            ):
                _clear_history_ui_state()
                st.rerun()
            st.warning("Add a non-empty title before saving.")

        if cancel_clicked:
            _clear_history_ui_state()
            st.rerun()


def _delete_session(session_id: str) -> None:
    if not conversation_store.delete_session(session_id):
        _clear_history_ui_state()
        return
    if session_id == st.session_state.session_id:
        _reset_chat()
        return
    _clear_history_ui_state()


def _render_session_overflow_menu(session: dict[str, str | int]) -> None:
    session_id = str(session["session_id"])
    with st.popover("⋮", use_container_width=True):
        if st.button(
            "Rename",
            key=f"rename_{session_id}",
            use_container_width=True,
        ):
            _start_rename(session_id, str(session["title"]))
            st.rerun()
        if st.button(
            "Delete",
            key=f"delete_{session_id}",
            use_container_width=True,
        ):
            _start_delete(session_id)
            st.rerun()


def _render_session_actions(session: dict[str, str | int]) -> None:
    session_id = str(session["session_id"])

    if st.session_state.history_edit_session_id == session_id:
        _render_rename_form(session_id)
        return

    if st.session_state.history_delete_session_id == session_id:
        st.markdown(
            '<div class="history-confirm">Delete this chat from memory?</div>',
            unsafe_allow_html=True,
        )
        confirm_col, cancel_col = st.columns(2)
        with confirm_col:
            if st.button(
                "Delete forever",
                key=f"confirm_delete_{session_id}",
                use_container_width=True,
                type="primary",
            ):
                _delete_session(session_id)
                st.rerun()
        with cancel_col:
            if st.button(
                "Cancel",
                key=f"cancel_delete_{session_id}",
                use_container_width=True,
            ):
                _clear_history_ui_state()
                st.rerun()
        return


def _render_history_item(session: dict[str, str | int]) -> None:
    session_id = str(session["session_id"])
    editing = st.session_state.history_edit_session_id == session_id
    deleting = st.session_state.history_delete_session_id == session_id

    if editing or deleting:
        if st.button(
            _truncate(str(session["title"]), 48),
            key=f"open_{session_id}",
            use_container_width=True,
            type="secondary",
        ):
            _load_chat(session_id)
            st.rerun()
    else:
        title_col, menu_col = st.columns([5.35, 1], gap="small")
        with title_col:
            if st.button(
                _truncate(str(session["title"]), 40),
                key=f"open_{session_id}",
                use_container_width=True,
                type="secondary",
            ):
                _load_chat(session_id)
                st.rerun()
        with menu_col:
            _render_session_overflow_menu(session)

    st.markdown(
        f'<div class="history-meta">{html.escape(str(session["updated_at"]))} | {html.escape(_message_count_label(int(session["message_count"])))}</div>',
        unsafe_allow_html=True,
    )
    _render_session_actions(session)


def _render_current_chat_card(
    current_session: dict[str, str | int] | None,
) -> None:
    current_title, current_meta = _current_chat_summary(current_session)
    if current_session:
        session_id = str(current_session["session_id"])
        editing = st.session_state.history_edit_session_id == session_id
        deleting = st.session_state.history_delete_session_id == session_id
        card_html = f"""
                <div class="history-current-card">
                  <div class="history-current-badge">Current chat</div>
                  <div class="history-current-title">{html.escape(_truncate(current_title, 54))}</div>
                  <div class="history-current-meta">{html.escape(current_meta)}</div>
                </div>
                """
        if editing or deleting:
            st.markdown(card_html, unsafe_allow_html=True)
        else:
            card_col, menu_col = st.columns([5.35, 1], gap="small")
            with card_col:
                st.markdown(card_html, unsafe_allow_html=True)
            with menu_col:
                _render_session_overflow_menu(current_session)
    else:
        st.markdown(
            f"""
            <div class="history-current-card">
              <div class="history-current-badge">Current chat</div>
              <div class="history-current-title">{html.escape(_truncate(current_title, 54))}</div>
              <div class="history-current-meta">{html.escape(current_meta)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if current_session:
        _render_session_actions(current_session)


@st.cache_resource
def get_orchestrator() -> AssistantOrchestrator:
    return AssistantOrchestrator(settings)


def _inject_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&display=swap');

        :root {
          --bg: #05070b;
          --panel: #0b0f16;
          --panel-soft: #101622;
          --panel-hover: #141c2a;
          --line: #1b2433;
          --text: #f3f7ff;
          --muted: #8994a8;
          --glow: #41d7ff;
          --glow-soft: rgba(65, 215, 255, 0.16);
          --assistant: #0f1622;
          --user: #122031;
        }

        html, body, [class*="css"] {
          font-family: "Space Grotesk", "Avenir Next", sans-serif;
        }

        .stApp, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
          background: var(--bg);
        }

        .stApp header {
          background: transparent;
        }

        .block-container {
          max-width: 1240px;
          padding-top: 1rem;
          padding-bottom: 1rem;
        }

        [data-testid="stSidebar"] {
          border-right: 1px solid var(--line);
        }

        [data-testid="stSidebar"] > div:first-child {
          background: linear-gradient(180deg, #07090e 0%, #0b0f16 100%);
        }

        [data-testid="stSidebar"] * {
          color: var(--text);
        }

        .sidebar-head {
          padding: 0.2rem 0 1rem;
        }

        .sidebar-kicker {
          color: var(--muted);
          font-size: 0.75rem;
          text-transform: uppercase;
          letter-spacing: 0.12em;
          margin-bottom: 0.35rem;
        }

        .sidebar-title {
          font-size: 1.15rem;
          font-weight: 700;
          color: var(--text);
          margin-bottom: 1rem;
        }

        .history-meta {
          color: var(--muted);
          font-size: 0.78rem;
          margin: 0.15rem 0 0.55rem 0.2rem;
        }

        .history-empty {
          color: var(--muted);
          font-size: 0.9rem;
          line-height: 1.6;
        }

        .history-group {
          margin-top: 0.65rem;
        }

        .history-group-label {
          color: var(--muted);
          font-size: 0.76rem;
          text-transform: uppercase;
          letter-spacing: 0.11em;
          margin: 1rem 0 0.5rem;
        }

        .history-current-card {
          margin: 0.85rem 0 0.75rem;
          padding: 0.9rem 0.95rem;
          border-radius: 16px;
          border: 1px solid #29466d;
          background:
            linear-gradient(180deg, rgba(18, 27, 42, 0.96), rgba(10, 16, 24, 0.96));
          box-shadow:
            inset 0 0 0 1px rgba(65, 215, 255, 0.08),
            0 0 22px rgba(65, 215, 255, 0.08);
        }

        .history-current-badge {
          color: var(--glow);
          font-size: 0.72rem;
          text-transform: uppercase;
          letter-spacing: 0.14em;
          margin-bottom: 0.45rem;
        }

        .history-current-title {
          color: var(--text);
          font-size: 0.98rem;
          font-weight: 700;
          line-height: 1.45;
        }

        .history-current-meta {
          color: var(--muted);
          font-size: 0.78rem;
          margin-top: 0.45rem;
          line-height: 1.55;
        }

        .chat-title {
          color: var(--muted);
          font-size: 0.88rem;
          letter-spacing: 0.04em;
          text-transform: uppercase;
          margin-bottom: 1rem;
        }

        .empty-shell {
          min-height: 68vh;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          text-align: center;
          padding: 2rem 1.2rem 0;
        }

        .empty-orb {
          width: 108px;
          height: 108px;
          border-radius: 999px;
          background:
            radial-gradient(circle at center, rgba(255, 255, 255, 0.96) 0%, rgba(65, 215, 255, 0.92) 16%, rgba(65, 215, 255, 0.18) 34%, rgba(65, 215, 255, 0.04) 58%, rgba(65, 215, 255, 0.00) 72%);
          box-shadow:
            0 0 28px rgba(65, 215, 255, 0.45),
            0 0 88px rgba(65, 215, 255, 0.20),
            inset 0 0 34px rgba(255, 255, 255, 0.24);
          position: relative;
          margin-bottom: 1.3rem;
        }

        .empty-orb::after {
          content: "";
          position: absolute;
          inset: 18px;
          border-radius: 999px;
          border: 1px solid rgba(255, 255, 255, 0.22);
          box-shadow: 0 0 26px rgba(65, 215, 255, 0.32);
        }

        .empty-title {
          color: var(--text);
          font-size: clamp(2rem, 4vw, 3.2rem);
          font-weight: 700;
          letter-spacing: -0.04em;
          margin-bottom: 0.65rem;
        }

        .empty-copy {
          color: var(--muted);
          font-size: 1rem;
          line-height: 1.75;
          max-width: 42rem;
        }

        .setup-copy {
          color: #ffb4b4;
          font-size: 0.95rem;
          margin-top: 1rem;
        }

        div[data-testid="stChatMessage"] {
          background: transparent;
          border: none;
          padding: 0;
          margin-bottom: 0.8rem;
        }

        div[data-testid="stChatMessageContent"] {
          background: var(--assistant);
          border: 1px solid var(--line);
          border-radius: 18px;
          padding: 0.95rem 1rem;
        }

        div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) div[data-testid="stChatMessageContent"] {
          background: var(--user);
          border-color: #233248;
        }

        div[data-testid="stChatMessageAvatarAssistant"] {
          background: linear-gradient(180deg, #0f1726, #0b1018);
          color: var(--glow);
          border: 1px solid #233248;
        }

        div[data-testid="stChatMessageAvatarUser"] {
          background: linear-gradient(180deg, #0f1726, #0b1018);
          color: #ffffff;
          border: 1px solid #233248;
        }

        div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
        div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li {
          color: var(--text);
          line-height: 1.75;
          font-size: 1rem;
        }

        div[data-testid="stChatInput"] {
          background: #090d13;
          border: 1px solid #1f2a3d;
          border-radius: 22px;
          box-shadow: 0 0 0 1px rgba(65, 215, 255, 0.05), 0 18px 40px rgba(0, 0, 0, 0.45);
        }

        div[data-testid="stChatInput"] textarea {
          color: var(--text) !important;
          font-size: 1rem !important;
          line-height: 1.6 !important;
        }

        div[data-testid="stChatInput"] textarea::placeholder {
          color: var(--muted) !important;
        }

        .stButton > button {
          width: 100%;
          min-height: 38px;
          border-radius: 12px;
          border: 1px solid var(--line);
          background: var(--panel);
          color: var(--text);
          box-shadow: none;
          text-align: left;
          font-weight: 500;
          transition: 140ms ease;
          display: flex;
          align-items: center;
          justify-content: flex-start;
          padding: 0.55rem 0.8rem;
        }

        .stTextInput > div > div > input {
          background: #090d13;
          border: 1px solid #1f2a3d;
          border-radius: 12px;
          color: var(--text);
        }

        .stTextInput label,
        .stForm label {
          color: var(--muted) !important;
          font-size: 0.8rem !important;
          letter-spacing: 0.04em;
          text-transform: uppercase;
        }

        .stButton > button:hover {
          background: var(--panel-hover);
          border-color: #2b3850;
          color: #ffffff;
        }

        .stButton > button p,
        .stButton > button span,
        .stButton > button div {
          text-align: left !important;
          justify-content: flex-start !important;
        }

        .stButton > button[kind="primary"] {
          background: linear-gradient(180deg, #0c121d, #0a1018);
          border-color: #29466d;
          box-shadow: 0 0 0 1px rgba(65, 215, 255, 0.05), 0 0 28px rgba(65, 215, 255, 0.08);
        }

        .stButton > button[kind="primary"]:hover {
          border-color: #3b79b5;
          box-shadow: 0 0 0 1px rgba(65, 215, 255, 0.09), 0 0 34px rgba(65, 215, 255, 0.12);
        }

        [data-testid="stSidebar"] .stButton > button[kind="secondary"] {
          background: transparent;
          border-color: transparent;
        }

        [data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {
          background: #101622;
          border-color: #1f2a3d;
        }

        [data-testid="stSidebar"] .stButton > button[kind="primary"] {
          background: #121b2a;
          border-color: #29466d;
          box-shadow: inset 0 0 0 1px rgba(65, 215, 255, 0.08);
        }

        [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
          background: #162133;
          border-color: #3b79b5;
        }

        .history-confirm {
          color: #ffb4b4;
          font-size: 0.82rem;
          margin: 0.15rem 0 0.55rem 0.2rem;
        }

        [data-testid="stSidebar"] [data-testid="stPopoverButton"] {
          min-height: 38px;
          padding: 0.35rem 0.25rem;
          justify-content: center;
          border-radius: 10px;
          border-color: transparent;
          background: transparent;
        }

        [data-testid="stSidebar"] [data-testid="stPopoverButton"]:hover {
          background: var(--panel-hover);
          border-color: #1f2a3d;
        }

        [data-testid="stSidebar"] [data-testid="stPopoverButton"] p {
          font-size: 1.05rem;
          font-weight: 600;
          letter-spacing: 0.02em;
          text-align: center !important;
        }

        /*
         * Popover trigger = label row + StyledPopoverExpansionIcon (material expand_more).
         * Hiding svg alone is unreliable; hide the icon column (last flex child of the row).
         */
        [data-testid="stSidebar"] [data-testid="stPopoverButton"] > * > *:last-child {
          display: none !important;
        }

        [data-testid="stSidebar"] [data-testid="stPopoverButton"] svg {
          display: none !important;
        }

        [data-testid="stSidebar"]
          [data-testid="stPopoverButton"]
          [data-testid="stMarkdownContainer"]
          ~ div {
          display: none !important;
        }

        @media (max-width: 900px) {
          .empty-shell {
            min-height: 56vh;
            padding-top: 1.4rem;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar() -> None:
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-head">
              <div class="sidebar-kicker">Personal Assistant</div>
              <div class="sidebar-title">Chats</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("New chat", use_container_width=True, type="primary"):
            _reset_chat()
            st.rerun()

        saved_sessions = conversation_store.list_sessions()
        current_session = next(
            (
                session
                for session in saved_sessions
                if session["session_id"] == st.session_state.session_id
            ),
            None,
        )
        _render_current_chat_card(current_session)

        earlier_sessions = [
            session
            for session in saved_sessions
            if session["session_id"] != st.session_state.session_id
        ]
        if not earlier_sessions:
            st.markdown(
                '<div class="history-empty">No earlier chats yet. Once you finish a conversation, it will show up here. Use the ⋮ menu on a chat to rename or delete it.</div>',
                unsafe_allow_html=True,
            )
            return

        with st.container():
            for group_label, sessions in _group_sessions_by_date(earlier_sessions).items():
                st.markdown(
                    f'<div class="history-group-label">{html.escape(group_label)}</div>',
                    unsafe_allow_html=True,
                )
                for session in sessions:
                    _render_history_item(session)


def _render_empty_state() -> None:
    setup_note = ""
    if not settings.has_model_credentials:
        setup_note = (
            f'<div class="setup-copy">{credentials_help_text(settings)}</div>'
        )

    st.markdown(
        f"""
        <div class="empty-shell">
          <div class="empty-orb"></div>
          <div class="empty-title">Start a conversation</div>
          <div class="empty-copy">
            Ask your assistant to plan, summarize, calculate, or research.
          </div>
          {setup_note}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_chat() -> None:
    if not st.session_state.messages:
        _render_empty_state()
        return

    st.markdown(
        f'<div class="chat-title">{_current_title()}</div>',
        unsafe_allow_html=True,
    )
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def main() -> None:
    st.set_page_config(
        page_title=settings.project_name,
        layout="wide",
        initial_sidebar_state="expanded",
    )

    _inject_css()
    _initialize_state()
    _render_sidebar()
    _render_chat()

    user_prompt = st.chat_input(
        "Ask your assistant to plan, summarize, calculate, or research",
        disabled=not settings.has_model_credentials,
    )
    if not user_prompt:
        return

    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                result = get_orchestrator().run(
                    messages=st.session_state.messages,
                    session_id=st.session_state.session_id,
                )
            except MissingModelCredentialsError as exc:
                st.error(str(exc))
                return
            except Exception as exc:  # noqa: BLE001
                st.error(f"Assistant error: {exc}")
                return
        st.markdown(result.content)

    st.session_state.messages.append({"role": "assistant", "content": result.content})
    st.session_state.last_run = {
        "generated_at": result.context.generated_at,
        "memory_context": result.context.memory_context,
        "knowledge_context": result.context.knowledge_context,
    }
    st.rerun()


if __name__ == "__main__":
    main()
