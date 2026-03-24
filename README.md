# Pluggable Executive Assistant

This repo is a versioned learning project for AI agents. We are building one usable app at a time:

- V1: single-agent personal assistant
- V2: long-term memory, checkpoints, and self-reflection
- V3: multi-agent swarm with a meta-agent
- V4: pluggable business domains like HR or Finance
- V5: production-ready open-source product

The current codebase implements the V1 foundation: a Streamlit chat app, one LangGraph-driven personal assistant plugin, short session memory, local document retrieval, and a few practical tools.

By default, the repo is now ready to run with a Gemini API key. OpenAI is still supported through the same provider layer.

## What V1 already does

- Chat in a clean Streamlit UI
- Answer with context from `data/docs`
- Remember the last few conversations in `data/memory/conversations.json`
- Use three tools:
  - `calculator`
  - `save_note`
  - `quick_web_search`
- Run locally or inside Docker
- Keep a plugin-first structure so later versions add capabilities without rewrites

## Architecture

The repo is intentionally split into:

- `assistant_core/`: shared runtime pieces like config, orchestration, memory, retrieval, and tools
- `plugins/`: domain-specific assistant modes
- `data/`: user-owned knowledge, notes, memory, and vector cache
- `app.py`: Streamlit interface

Today there is only one built-in plugin: `personal`. The plugin loader is already dynamic, so V4 can add more modes by dropping in new plugin folders.

## Quick Start

1. Create a virtual environment with Python 3.13 or Docker.
2. Copy `.env.example` to `.env`.
3. Add your `GOOGLE_API_KEY`.
4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Start the app:

```bash
streamlit run app.py
```

6. Open the URL Streamlit prints, usually `http://localhost:8501`.

If you want to use OpenAI instead, set `MODEL_PROVIDER=openai` and add `OPENAI_API_KEY` instead.

## Docker

Build and run with Docker Compose:

```bash
docker compose up --build
```

Your local `data/` folder is mounted into the container, so notes, remembered sessions, and the FAISS index stick around.

## Learning Path

If you want to learn while building, move through the code in this order:

1. `app.py`: see how the UI collects input and calls the orchestrator.
2. `assistant_core/orchestrator.py`: see how LangGraph handles the tool loop.
3. `plugins/personal/plugin.py`: see how prompt context is assembled from memory and docs.
4. `assistant_core/retrieval/knowledge_base.py`: see how local retrieval and FAISS indexing work.
5. `assistant_core/tools/`: see how tool calling is exposed to the model.

## Repo Structure

```text
.
├── app.py
├── assistant_core/
├── data/
├── plugins/
├── Dockerfile
├── ROADMAP.md
└── requirements.txt
```

## Next Versions

See `ROADMAP.md` for the release-by-release plan and why each version exists.
