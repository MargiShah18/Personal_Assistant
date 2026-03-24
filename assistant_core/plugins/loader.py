from __future__ import annotations

import importlib
from functools import lru_cache
from pathlib import Path

from assistant_core.plugins.base import AssistantPlugin


PLUGIN_ROOT = Path(__file__).resolve().parents[2] / "plugins"


@lru_cache(maxsize=1)
def discover_plugins() -> dict[str, AssistantPlugin]:
    plugins: dict[str, AssistantPlugin] = {}
    for plugin_file in sorted(PLUGIN_ROOT.glob("*/plugin.py")):
        module_name = f"plugins.{plugin_file.parent.name}.plugin"
        module = importlib.import_module(module_name)
        if not hasattr(module, "get_plugin"):
            continue
        plugin = module.get_plugin()
        plugins[plugin.plugin_id] = plugin
    return plugins


def get_plugin(plugin_id: str) -> AssistantPlugin:
    plugins = discover_plugins()
    if plugin_id not in plugins:
        available = ", ".join(sorted(plugins)) or "none"
        raise KeyError(f"Unknown plugin '{plugin_id}'. Available plugins: {available}")
    return plugins[plugin_id]

