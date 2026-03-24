# Product Roadmap

This project is being built like a real product: each version is usable on its own, and each version extends the same codebase instead of replacing it.

## Build Principles

- Keep every version deployable
- Prefer additive changes over rewrites
- Separate core runtime from domain plugins from day 1
- Make each version teach one new layer of agent engineering

## V1: Basic MVP

### Goal

Ship a single-agent personal assistant that already feels useful.

### What we build

- Streamlit chat UI
- One `personal` plugin
- LangGraph orchestration with tool calling
- Local document retrieval from `data/docs`
- Basic conversation memory across the last few chats
- A few practical tools and Docker support

### What you learn

- How an agent loop is structured
- How tools are exposed to an LLM
- How RAG works in a small local setup
- How prompt context is assembled from memory plus documents

### Exit criteria

- You can ask it to summarize your notes
- You can ask it to plan your day
- It can use your stored documents and remembered sessions to ground answers

## V2: Stateful and Reliable Agent

### Goal

Turn the assistant into something that remembers long-term preferences and can continue work later.

### Planned additions

- Long-term memory provider
- Checkpointed tasks and resumable threads
- Reflection and answer-repair loop
- First supporting sub-agent for research
- Better chat history UX

### What you learn

- Different memory types
- Short-term vs long-term state
- Self-critique and retry patterns
- Durable execution

## V3: Multi-Agent Swarm

### Goal

Introduce coordinated specialists with a meta-agent that decides when to delegate.

### Planned additions

- Meta-agent / manager
- Specialist workers
- Reporting agent
- Knowledge graph for relationships between goals, people, and projects
- Tracing and observability

### What you learn

- Agent coordination
- Delegation strategies
- Observability and debugging in agent systems
- Structured knowledge representation

## V4: Real Plugin Ecosystem

### Goal

Use one shared platform for multiple assistant domains.

### Planned additions

- Full plugin contracts
- Multiple assistant modes in the UI
- Real external integrations
- Finance, HR, and other domain plugins

### What you learn

- Multi-tenant design patterns
- Contracts and plugin architecture
- Permissioned tool execution
- Domain-specific agent customization

## V5: Production Product

### Goal

Turn the repo into a polished open-source project or portfolio-ready product.

### Planned additions

- Tests and docs
- CI/CD
- Multi-user support
- Cost tracking
- Human approval steps
- Exportable reports

### What you learn

- Production hardening
- Deployment workflows
- Safety and approval patterns
- Maintaining an open-source product

## Immediate Implementation Sequence

This is the order we should use in the repo right now:

1. Stabilize V1 so it runs reliably end to end.
2. Add a couple of focused tests around memory and tools.
3. Improve the Streamlit UX once the agent loop is solid.
4. Start V2 by replacing simple memory with a longer-lived memory layer.

