# Implementation Steps

## Step 1: Run the scaffold

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

## Step 2: Confirm REST endpoints

Open:

```txt
http://localhost:8000/admin/
http://localhost:8000/api/repositories/
http://localhost:8000/api/research/sessions/list/
```

## Step 3: Test one research session

Use Postman or curl with:

```json
{
  "repo_url": "https://github.com/tiangolo/fastapi",
  "question": "How does FastAPI handle dependency injection internally?",
  "options": {
    "max_steps": 8,
    "reuse_previous_findings": true,
    "include_tool_logs": true,
    "stream_events": true
  }
}
```

## Step 4: Implement real code tools

Start with:

- `apps/agent/tools/code_tools.py`
- `apps/agent/tools/database_tools.py`

Improve search by adding ripgrep or AST-based parsing.

## Step 5: Implement LangGraph

Replace the mock runner in `apps/agent/runner.py` with `apps/agent/graph.py`.

Suggested graph:

```txt
load_context -> plan -> tool_executor -> evaluate -> answer_writer
```

## Step 6: Add real LLM calls

Implement `apps/agent/llm.py` using Anthropic or OpenAI.

## Step 7: Improve WebSocket flow

For true realtime UX, move agent execution to a worker process or Celery. The current scaffold shows event publishing and WebSocket structure, but the long-running agent should eventually run outside the HTTP request.

## Step 8: Prepare submission

Before submitting, make sure you have:

- Public GitHub repo
- Clear README
- `DECISIONS.md` completed honestly
- 5–10 minute video walkthrough
- Demo data or instructions for generating sample records
