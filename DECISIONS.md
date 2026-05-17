# DECISIONS.md

## Architecture Overview

This project separates the API layer, persistence layer, repository operations, agent orchestration, and realtime progress streaming into independent modules.

- `apps/repositories` owns repository metadata and clone/update operations.
- `apps/research` owns research sessions, findings, tool-call logs, and API endpoints.
- `apps/agent` owns prompts, tool definitions, LangGraph workflow, context management, and final answer generation.
- `apps/realtime` owns WebSocket consumers and event broadcasting.

## Database Schema Rationale

The database is designed around a research workflow. A `Repository` can have many `ResearchSession` records. Each session stores the question, final answer, status, token usage, and execution timestamps. The agent writes `ToolCallLog` rows to record what it did and `Finding` rows to persist meaningful evidence found in the codebase. `AgentEvent` records are used both for realtime WebSocket updates and for later review.

## Agent Workflow

The intended workflow is:

1. Create a research session.
2. Load previous findings for the same repo.
3. Plan a search strategy.
4. Call tools such as `list_files`, `search_code`, `read_file`, and `save_finding`.
5. Stop when enough evidence is collected or when a max-step guard is reached.
6. Generate a final answer with file/function/line references.

## Context Management

The agent should search first and read only targeted files or line ranges. Large files should be truncated or summarized. File summaries can be cached in the database with content hashes.

## Cost and Latency Trade-offs

The first version should use a small number of tool calls and a strict `max_steps` limit. In production, long-running sessions would be moved to Celery or another worker queue.

## Realtime Design

Realtime progress is implemented with Django Channels. The agent emits domain events through an `AgentEventPublisher`. Each event is persisted to the database and also broadcast over WebSocket. This means progress can be shown live in a frontend, while the backend still keeps an auditable trail.

## What I Kept Simple

- No authentication or multi-user support.
- No frontend in the initial version.
- No Docker because the project is structured for traditional Nginx/Gunicorn/Daphne hosting.
- Minimal tests at the scaffold stage.

## What I Would Improve With More Time

- Add Celery for async research sessions.
- Add vector search for large repositories.
- Add more robust AST-based symbol extraction.
- Add better token accounting and cost reporting.
- Add richer UI for live agent activity.

## AI Tool Usage

Document here how you used ChatGPT, Claude Code, Cursor, Copilot, or other tools. Be honest about what was AI-generated, what was edited manually, and how you reviewed the output.
