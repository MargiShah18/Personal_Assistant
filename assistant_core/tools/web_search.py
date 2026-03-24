from __future__ import annotations

from ddgs import DDGS
from langchain_core.tools import tool


def build_web_search_tool():
    @tool("quick_web_search")
    def quick_web_search(query: str) -> str:
        """Search the public web for current information when freshness matters."""
        cleaned_query = query.strip()
        if not cleaned_query:
            return "No web search was run because the query was empty."

        try:
            with DDGS(timeout=20) as ddgs:
                results = list(ddgs.text(cleaned_query, max_results=5))
        except Exception as exc:  # noqa: BLE001
            return f"Web search unavailable: {exc}"

        if not results:
            return "No public web results were found."

        rendered_results = []
        for item in results[:5]:
            title = item.get("title", "Untitled result")
            body = item.get("body", "No summary provided.")
            href = item.get("href", "No URL provided.")
            rendered_results.append(f"{title}\n{body}\nSource: {href}")
        return "\n\n".join(rendered_results)

    return quick_web_search
