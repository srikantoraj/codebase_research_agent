# Agent App Setup — OpenAI default, Anthropic optional

## Python
Use Python 3.12. Your old venv used Python 3.9, which caused type-hint and SSL warnings.

```bash
cd /Users/srikantorajbongshi/Desktop/cra
conda deactivate
mv venv venv_old_py39
python -m venv venv
source venv/bin/activate
python --version
```

Expected:

```txt
Python 3.12.7
```

## Install requirements
Copy the provided `requirements.txt` to your project root, then run:

```bash
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

## Environment
Copy `.env.agent.example` values into your `.env`.

Default provider is OpenAI:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o-mini
```

Anthropic is also supported:

```env
ANTHROPIC_API_KEY=your_key
ANTHROPIC_MODEL=claude-3-5-sonnet-latest
```

## Per-request provider selection
Default request uses OpenAI:

```json
{
  "repository_id": "your-repository-id",
  "question": "How does FastAPI handle dependency injection internally?",
  "run_agent": true,
  "options": {
    "max_steps": 8,
    "max_files_to_read": 8
  }
}
```

Use Anthropic for a specific run:

```json
{
  "repository_id": "your-repository-id",
  "question": "Where is task retry logic implemented?",
  "run_agent": true,
  "options": {
    "llm_provider": "anthropic",
    "model_name": "claude-3-5-sonnet-latest",
    "max_steps": 8,
    "max_files_to_read": 8
  }
}
```

## Patch research service
In `apps/research/services.py`, import:

```python
from apps.research.agent_bridge import AgentExecutionBridge
```

Then where your starter/mock runner currently executes, replace it with:

```python
if run_agent:
    AgentExecutionBridge.run_session(session.id)
    session.refresh_from_db()
```

## Flow

1. Research API creates `ResearchSession`.
2. `AgentExecutionBridge` calls `AgentRunner`.
3. LangGraph executes: `load_context -> plan -> research -> answer`.
4. Code tools search/read the repo.
5. Database tools save `ToolCallLog`, `Finding`, and `AgentEvent`.
6. Final answer is saved in `ResearchSession.final_answer`.

## Notes
This implementation intentionally uses a controlled LangGraph workflow instead of a fully autonomous infinite-loop agent. That is safer for a take-home task because it gives predictable cost, latency, and auditability.
