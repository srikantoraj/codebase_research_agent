# Codebase Research Agent

A Django + DRF backend scaffold for a take-home task: an AI agent that researches a GitHub repository and answers technical questions using code evidence.

This starter intentionally avoids Docker and is structured for a traditional Django deployment with Nginx, Gunicorn, Daphne, PostgreSQL, Redis, and systemd.

## What is included

- Django project structure with split settings
- DRF API skeleton
- Repository, research session, finding, tool call, file summary, and realtime event models
- LangGraph/LangChain-ready agent module structure
- Tool-calling placeholders for code exploration and database interaction
- Django Channels WebSocket scaffold for live agent progress
- Nginx, Gunicorn, Daphne, and systemd deployment templates
- Seed/demo script placeholders

## Local setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Run ASGI locally with Daphne

```bash
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

## API example

```bash
curl -X POST http://localhost:8000/api/research/sessions/ \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/tiangolo/fastapi",
    "question": "How does FastAPI handle dependency injection internally?",
    "options": {
      "max_steps": 8,
      "reuse_previous_findings": true,
      "include_tool_logs": true,
      "stream_events": true
    }
  }'
```

## WebSocket endpoint

```txt
ws://localhost:8000/ws/research/sessions/{session_id}/
```

## Suggested implementation order

1. Install dependencies and run migrations.
2. Confirm admin and REST endpoints work.
3. Implement repository cloning in `apps/repositories/services.py`.
4. Implement code tools in `apps/agent/tools/code_tools.py`.
5. Implement database tools in `apps/agent/tools/database_tools.py`.
6. Replace the mock `AgentRunner` with LangGraph workflow.
7. Add real LLM calls in `apps/agent/llm.py`.
8. Stream events from the agent using `AgentEventPublisher`.
9. Add demo questions and record your video walkthrough.

## Important note

This is a scaffold. It is intentionally organized like a senior backend project, but the core AI-agent logic should be implemented step by step.
# codebase_research_agent
