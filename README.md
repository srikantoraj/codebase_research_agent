# Codebase Research Agent

A Django + Django REST Framework backend application that researches GitHub repositories and answers technical questions using real source-code evidence.

This project is designed as a backend-focused AI agent system. A user submits a repository URL and a technical question. The system clones or reuses the repository, searches the codebase, reads relevant source files, records tool calls and findings, and produces a structured answer with code references.

---

# Table of Contents

- [What This Project Does](#what-this-project-does)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Run Locally](#run-locally)
- [Local Environment Variables](#local-environment-variables)
- [Local URLs](#local-urls)
- [Production URLs](#production-urls)
- [How To Test Locally](#how-to-test-locally)
- [API Usage](#api-usage)
- [Request Body Formats](#request-body-formats)
- [Request Field Explanation](#request-field-explanation)
- [Options Explanation](#options-explanation)
- [Example Response](#example-response)
- [WebSocket Usage](#websocket-usage)
- [Project Structure](#project-structure)
- [App Responsibilities](#app-responsibilities)
- [How The System Works](#how-the-system-works)
- [Agent Workflow Summary](#agent-workflow-summary)
- [Why This Design Is Useful](#why-this-design-is-useful)
- [Good Demo Repositories](#good-demo-repositories)
- [Good Demo Questions](#good-demo-questions)
- [Notes For Evaluators](#notes-for-evaluators)

---

# What This Project Does

The main goal of this project is to build an AI-powered codebase research backend.

A user can ask questions like:

```txt
How does FastAPI handle dependency injection internally?
```

or:

```txt
Where is token signing implemented in this repository?
```

The system then:

1. Accepts a GitHub repository URL or existing repository ID
2. Creates a research session
3. Clones or syncs the repository if needed
4. Searches the codebase for relevant files, classes, functions, and terms
5. Reads selected source-code files or snippets
6. Saves tool calls and findings to the database
7. Uses an LLM to generate a final answer based on gathered evidence
8. Streams progress events over WebSocket when enabled
9. Returns a structured API response

---

# Key Features

- Repository-based research sessions
- GitHub repository cloning and syncing
- Source-code search tools
- File reading tools
- AI-assisted answer generation
- Evidence-based final answers
- Tool-call logging
- Findings storage
- Previous finding reuse
- WebSocket progress events
- OpenAI and Anthropic model support
- Clean Django app-based architecture
- Local SQLite support
- Production PostgreSQL support
- Optional Celery background execution
- Django Channels realtime event streaming

---

# Tech Stack

## Backend

- Django
- Django REST Framework
- Django Channels

## AI / Agent

- LangChain & LanGraph
- OpenAI & Anthropic
- Tool-calling architecture
- Source-code search tools
- Evidence-based answer generation

## Database

- SQLite for local development
- PostgreSQL for production

## Realtime

- WebSocket
- Django Channels
- Redis / Channels Redis

## Optional Background Jobs

- Celery
- Redis broker

## Production Runtime

- Gunicorn
- Daphne
- Nginx
- systemd

---

# Run Locally

This section explains how to clone and run the project on your local machine.

Recommended local mode:

```txt
Database: SQLite
Agent execution: sync mode
Celery worker: not required
Redis: recommended for WebSocket/Channels
```

For local development, use:

```json
"async": false
```

This allows the research agent to run directly inside the Django request/response flow without needing a Celery worker.

---

## 1. Clone Repository

```bash
git clone YOUR_REPOSITORY_URL
cd codebase_research_agent
```

Example:

```bash
git clone https://github.com/your-username/codebase_research_agent.git
cd codebase_research_agent
```

---

## 2. Create Virtual Environment

### macOS / Linux

```bash
python -m venv venv
source venv/bin/activate
```

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

---

## 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

If any package is missing, install the important packages manually:

```bash
pip install django djangorestframework django-environ
pip install channels channels-redis daphne
pip install openai anthropic
pip install celery redis
```

---

## 4. Create `.env`

Create a `.env` file in the project root.

```bash
cp .env.example .env
```

If `.env.example` does not exist yet, create `.env` manually:

```bash
touch .env
```

---

# Local Environment Variables

For local development, use SQLite and sync mode.

Example local `.env`:

```env
SECRET_KEY=local-secret-key
DEBUG=True

ALLOWED_HOSTS=localhost,127.0.0.1

CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000

DB_ENGINE=sqlite

REDIS_URL=redis://127.0.0.1:6379/0

CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0

REPO_STORAGE_DIR=storage/repos

LLM_PROVIDER=openai

OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5-mini

ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-3-5-sonnet-latest

AGENT_MAX_STEPS=8
AGENT_MAX_FILES_TO_READ=8
AGENT_MAX_FILE_CHARS=14000
```

---

## 5. Redis for Local WebSocket Support

If your Django settings use `channels_redis`, Redis should be running locally.

### macOS

```bash
brew install redis
brew services start redis
```

Check Redis:

```bash
redis-cli ping
```

Expected output:

```txt
PONG
```

### Ubuntu / Linux

```bash
sudo apt update
sudo apt install -y redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

Check Redis:

```bash
redis-cli ping
```

Expected output:

```txt
PONG
```

---

## 6. Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

---

## 7. Create Superuser

```bash
python manage.py createsuperuser
```

---

## 8. Create Repository Storage Folder

```bash
mkdir -p storage/repos
```

This folder is used to store cloned GitHub repositories locally.

---

## 9. Run Local Development Server

```bash
python manage.py runserver
```

Server should run at:

```txt
http://localhost:8000
```

---

## 10. Optional: Run ASGI Locally With Daphne

If you want to test ASGI/WebSocket behavior more directly:

```bash
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

Then use:

```txt
http://localhost:8000
ws://localhost:8000/ws/research/sessions/{session_id}/
```

---

## 11. Optional: Run Celery Locally

Celery is not required for the recommended local demo flow.

Only run Celery if you want to test asynchronous background jobs using:

```json
"async": true
```

Start Celery:

```bash
celery -A config worker --loglevel=info
```

Recommended local testing option:

```json
"async": false
```

This avoids needing Celery during local testing.

---

# Local URLs

```txt
Base URL:
http://localhost:8000

Admin:
http://localhost:8000/admin/

API Root:
http://localhost:8000/api/

Repositories:
http://localhost:8000/api/repositories/

Research Sessions:
http://localhost:8000/api/research/sessions/

WebSocket:
ws://localhost:8000/ws/research/sessions/{session_id}/
```

---

# Production URLs

```txt
Base URL:
https://research.srikanto.dev

Admin:
https://research.srikanto.dev/admin/

API Root:
https://research.srikanto.dev/api/

Repositories:
https://research.srikanto.dev/api/repositories/

Research Sessions:
https://research.srikanto.dev/api/research/sessions/

WebSocket:
wss://research.srikanto.dev/ws/research/sessions/{session_id}/
```

---

# How To Test Locally

## 1. Start Redis

```bash
redis-cli ping
```

Expected:

```txt
PONG
```

If Redis is not running, start it first.

---

## 2. Start Django

```bash
python manage.py runserver
```

---

## 3. Open Admin

```txt
http://localhost:8000/admin/
```

---

## 4. Create A Research Session

Use this request:

```bash
curl -X POST http://localhost:8000/api/research/sessions/ \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/pallets/itsdangerous",
    "question": "How does URL-safe timed token signing work internally?",
    "options": {
      "run_agent": true,
      "sync_repository": true,
      "async": false,
      "stream_events": true,
      "llm_provider": "openai",
      "model_name": "gpt-5-mini",
      "max_steps": 8,
      "max_files_to_read": 8,
      "max_file_chars": 14000,
      "reuse_previous_findings": true,
      "include_tool_logs": true
    }
  }'
```

---

## 5. Re-run Faster With Existing Repo

After the repository has already been cloned, use:

```json
"sync_repository": false
```

Example:

```bash
curl -X POST http://localhost:8000/api/research/sessions/ \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/pallets/itsdangerous",
    "question": "Find the source code functions and classes that implement URL-safe timed token signing and verification. Focus on internal implementation, not documentation.",
    "options": {
      "run_agent": true,
      "sync_repository": false,
      "async": false,
      "stream_events": true,
      "llm_provider": "openai",
      "model_name": "gpt-5-mini",
      "max_steps": 8,
      "max_files_to_read": 8,
      "max_file_chars": 14000,
      "reuse_previous_findings": true,
      "include_tool_logs": true
    }
  }'
```

---

# Local Development Notes

The project can run locally without starting Celery workers.

Recommended local setup:

```txt
SQLite
Redis running locally
async=false
stream_events=true
```

Use Celery only when testing background jobs.

Recommended local request option:

```json
{
  "options": {
    "run_agent": true,
    "async": false
  }
}
```

Recommended production-style request option:

```json
{
  "options": {
    "run_agent": true,
    "async": true
  }
}
```

---

# API Usage

## Create Research Session

```http
POST /api/research/sessions/
```

Local:

```bash
curl -X POST http://localhost:8000/api/research/sessions/ \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/tiangolo/fastapi",
    "question": "How does FastAPI handle dependency injection internally?",
    "options": {
      "run_agent": true,
      "sync_repository": true,
      "async": false,
      "llm_provider": "openai",
      "model_name": "gpt-5-mini",
      "max_steps": 8,
      "max_files_to_read": 8,
      "max_file_chars": 14000,
      "reuse_previous_findings": true,
      "include_tool_logs": true,
      "stream_events": true
    }
  }'
```

Production:

```bash
curl -X POST https://research.srikanto.dev/api/research/sessions/ \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/tiangolo/fastapi",
    "question": "How does FastAPI handle dependency injection internally?",
    "options": {
      "run_agent": true,
      "sync_repository": true,
      "async": false,
      "llm_provider": "openai",
      "model_name": "gpt-5-mini",
      "max_steps": 8,
      "max_files_to_read": 8,
      "max_file_chars": 14000,
      "reuse_previous_findings": true,
      "include_tool_logs": true,
      "stream_events": true
    }
  }'
```

---

# Request Body Formats

## Minimal Request

```json
{
  "repo_url": "https://github.com/tiangolo/fastapi",
  "question": "How does FastAPI handle dependency injection internally?"
}
```

---

## Full Request

```json
{
  "repo_url": "https://github.com/tiangolo/fastapi",
  "repository_id": null,
  "local_path": null,
  "question": "How does FastAPI handle dependency injection internally?",
  "options": {
    "run_agent": true,
    "sync_repository": true,
    "async": false,
    "llm_provider": "openai",
    "model_name": "gpt-5-mini",
    "max_steps": 8,
    "max_files_to_read": 8,
    "max_file_chars": 14000,
    "reuse_previous_findings": true,
    "include_tool_logs": true,
    "stream_events": true
  }
}
```

---

# Request Field Explanation

## `repo_url`

GitHub repository URL.

Example:

```json
"repo_url": "https://github.com/tiangolo/fastapi"
```

Use this when starting research on a new repository or when the client does not know the internal repository ID.

---

## `repository_id`

Existing repository ID from the database.

Example:

```json
"repository_id": 5
```

Use this when the repository already exists and you want faster repeated research.

---

## `local_path`

Optional local repository path.

Example:

```json
"local_path": "/home/ubuntu/codebase_research_agent/storage/repos/fastapi"
```

Use this when analyzing a repository already available on the server.

---

## `question`

The technical question the user wants answered.

Example:

```json
"question": "Where is task retry logic implemented?"
```

---

# Options Explanation

## `run_agent`

```json
"run_agent": true
```

When `true`, the agent starts researching immediately.

When `false`, the system only creates the session but does not run the full agent.

Use `false` when:

- You want to create a session first
- You want to run the agent later
- You are testing session creation only

---

## `sync_repository`

```json
"sync_repository": true
```

Controls whether the repository should be cloned or updated.

### `sync_repository=true`

Behavior:

- Clone repository if missing
- Pull latest changes if already cloned
- Use latest available code

Recommended for:

- Fresh analysis
- Production demo
- Latest code research

### `sync_repository=false`

Behavior:

- Do not pull latest changes
- Use existing local files
- Faster repeated tests

Recommended for:

- Local development
- Repeating the same test
- Avoiding unnecessary GitHub calls

---

## `async`

```json
"async": false
```

Controls whether the research agent runs synchronously or through Celery.

### `async=false`

Behavior:

- Runs the research agent directly in the Django request
- Does not require Celery worker
- Easier to test locally
- Good for demos and debugging

Recommended for:

- Local development
- Simple demo
- Debugging agent behavior

### `async=true`

Behavior:

- Sends the research job to Celery
- Requires Redis and Celery worker
- Better for long-running production jobs

Recommended for:

- Production background processing
- Long-running research sessions
- Non-blocking API behavior

---

## `llm_provider`

```json
"llm_provider": "openai"
```

Supported examples:

```txt
openai
anthropic
```

This controls which provider is used for final reasoning.

---

## `model_name`

```json
"model_name": "gpt-5-mini"
```

Controls which model is used.

Recommended examples:

```txt
gpt-5-mini
claude-3-5-sonnet-latest
```

---

## `max_steps`

```json
"max_steps": 8
```

Maximum number of agent reasoning/tool-use steps.

Higher value:

- Better research depth
- More tool calls
- More tokens
- Slower response

Lower value:

- Faster response
- Lower cost
- May miss details

---

## `max_files_to_read`

```json
"max_files_to_read": 8
```

Maximum number of files the agent can read.

This prevents the agent from reading too many files and wasting tokens.

---

## `max_file_chars`

```json
"max_file_chars": 14000
```

Maximum characters to read from each file.

This helps control LLM context size.

---

## `reuse_previous_findings`

```json
"reuse_previous_findings": true
```

When enabled, the agent may use previously saved findings from the same repository.

Good for:

- Repeated research
- Faster answers
- Lower token usage

---

## `include_tool_logs`

```json
"include_tool_logs": true
```

When enabled, the API response may include tool-call logs.

Useful for:

- Debugging
- Demo video
- Showing agent workflow
- Evaluation transparency

---

## `stream_events`

```json
"stream_events": true
```

When enabled, the system publishes realtime progress events over WebSocket.

Useful for:

- Frontend progress UI
- Live agent activity
- Debugging long-running tasks

---

# Example Response

```json
{
  "id": "f9e0358e-5eca-4b3c-be15-6f4cd6532d11",
  "repository": {
    "id": "a449ed12-59ed-4dd3-b920-42d5ffaaf85b",
    "source_type": "github",
    "url": "https://github.com/pallets/itsdangerous.git",
    "canonical_url": "https://github.com/pallets/itsdangerous",
    "owner": "pallets",
    "name": "itsdangerous",
    "display_name": "pallets/itsdangerous",
    "default_branch": "main",
    "current_branch": "main",
    "local_path": "storage/repos/pallets__itsdangerous",
    "sync_status": "synced",
    "is_synced": true
  },
  "question": "How does URL-safe timed token signing work internally?",
  "status": "completed",
  "final_answer": "URL-safe timed token signing is implemented through URLSafeTimedSerializer, TimestampSigner, Serializer, and encoding helpers...",
  "answer_references": [
    {
      "file_path": "src/itsdangerous/url_safe.py",
      "function_name": "URLSafeTimedSerializer",
      "line_start": 1,
      "line_end": 80
    },
    {
      "file_path": "src/itsdangerous/timed.py",
      "function_name": "TimestampSigner",
      "line_start": 20,
      "line_end": 150
    }
  ],
  "summary": {
    "total_tool_calls": 18,
    "total_findings": 6,
    "input_tokens": 13264,
    "output_tokens": 1057
  },
  "websocket_url": "ws://localhost:8000/ws/research/sessions/f9e0358e-5eca-4b3c-be15-6f4cd6532d11/"
}
```

---

# WebSocket Usage

## Endpoint

Local:

```txt
ws://localhost:8000/ws/research/sessions/{session_id}/
```

Production:

```txt
wss://research.srikanto.dev/ws/research/sessions/{session_id}/
```

Replace `{session_id}` with the actual research session ID.

Example:

```txt
ws://localhost:8000/ws/research/sessions/f9e0358e-5eca-4b3c-be15-6f4cd6532d11/
```

---

# WebSocket Event Examples

## Session Started

```json
{
  "type": "SESSION_STARTED",
  "session_id": "f9e0358e-5eca-4b3c-be15-6f4cd6532d11",
  "message": "Research session started"
}
```

---

## Repository Sync Started

```json
{
  "type": "REPOSITORY_SYNC_STARTED",
  "session_id": "f9e0358e-5eca-4b3c-be15-6f4cd6532d11",
  "repo_url": "https://github.com/pallets/itsdangerous"
}
```

---

## Tool Started

```json
{
  "type": "TOOL_STARTED",
  "session_id": "f9e0358e-5eca-4b3c-be15-6f4cd6532d11",
  "tool_name": "search_code",
  "input": {
    "query": "TimestampSigner"
  }
}
```

---

## Tool Completed

```json
{
  "type": "TOOL_COMPLETED",
  "session_id": "f9e0358e-5eca-4b3c-be15-6f4cd6532d11",
  "tool_name": "search_code",
  "output": {
    "matches": 12
  }
}
```

---

## Finding Saved

```json
{
  "type": "FINDING_SAVED",
  "session_id": "f9e0358e-5eca-4b3c-be15-6f4cd6532d11",
  "file_path": "src/itsdangerous/timed.py",
  "note": "Timed signing logic found in TimestampSigner."
}
```

---

## Session Completed

```json
{
  "type": "SESSION_COMPLETED",
  "session_id": "f9e0358e-5eca-4b3c-be15-6f4cd6532d11",
  "status": "completed"
}
```

---

## Session Failed

```json
{
  "type": "SESSION_FAILED",
  "session_id": "f9e0358e-5eca-4b3c-be15-6f4cd6532d11",
  "error": "Repository clone failed"
}
```

---

# Project Structure

```txt
codebase_research_agent/
├── apps/
│   ├── agent/
│   │   ├── nodes/
│   │   ├── tools/
│   │   ├── llm.py
│   │   └── prompts.py
│   │
│   ├── common/
│   │
│   ├── realtime/
│   │   ├── consumers.py
│   │   ├── routing.py
│   │   └── publisher.py
│   │
│   ├── repositories/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── services.py
│   │   ├── urls.py
│   │   └── views.py
│   │
│   └── research/
│       ├── models.py
│       ├── serializers.py
│       ├── services.py
│       ├── urls.py
│       └── views.py
│
├── config/
│   ├── settings/
│   ├── asgi.py
│   ├── celery.py
│   ├── urls.py
│   ├── wsgi.py
│   └── __init__.py
│
├── deployment/
│   ├── gunicorn/
│   ├── nginx/
│   └── systemd/
│
├── storage/
│   └── repos/
│
├── manage.py
├── requirements.txt
├── .env.example
└── README.md
```

---

# App Responsibilities

## `apps.repositories`

This app manages source-code repositories.

Main responsibilities:

- Store repository metadata
- Store repository URL
- Track local repository path
- Clone GitHub repositories
- Sync existing repositories
- Reuse already cloned repositories
- Track repository sync status
- Track current branch and commit hash
- Count source files

Example responsibility:

```txt
GitHub URL → local repository folder inside storage/repos/
```

Typical model responsibilities:

```txt
Repository
- id
- source_type
- url
- canonical_url
- owner
- name
- display_name
- default_branch
- current_branch
- current_commit_hash
- local_path
- source_file_count
- sync_status
- sync_error
- is_synced
- last_synced_at
- last_analyzed_at
- created_at
- updated_at
```

This app answers:

```txt
Where is the repo stored?
Has it already been cloned?
Should we sync it again?
What commit or branch are we analyzing?
How many source files were found?
Did repository sync fail?
```

---

## `apps.research`

This app manages research sessions and research outputs.

Main responsibilities:

- Create research sessions
- Store user questions
- Track research status
- Store final answers
- Store findings
- Store tool-call logs
- Store token usage and execution metadata
- Store agent options
- Track started/completed timestamps

Typical model responsibilities:

```txt
ResearchSession
- id
- repository
- question
- status
- final_answer
- error_message
- options
- llm_provider
- model_name
- max_steps
- current_step
- input_tokens
- output_tokens
- started_at
- completed_at
- created_at
- updated_at
```

```txt
Finding
- id
- session
- source
- file_path
- symbol_name
- symbol_type
- line_start
- line_end
- note
- evidence_snippet
- confidence
- metadata
- created_at
- updated_at
```

```txt
ToolCallLog
- id
- session
- tool_name
- tool_type
- status
- step_number
- input_payload
- output_payload
- error_message
- duration_ms
- created_at
- updated_at
```

This app answers:

```txt
What did the user ask?
What did the agent find?
What tools were used?
What was the final answer?
How many tokens were used?
Where is the source evidence?
```

---

## `apps.agent`

This is the core AI agent app.

Main responsibilities:

- Plan search terms
- Search repository source code
- Read relevant files
- Save findings
- Reuse previous findings
- Call the LLM
- Generate the final answer
- Control max steps and token usage
- Avoid reading the whole repository blindly
- Produce evidence-based answers

Important areas usually include:

```txt
apps/agent/llm.py
```

Handles OpenAI or Anthropic client calls.

```txt
apps/agent/prompts.py
```

Stores planner and answer-generation prompts.

```txt
apps/agent/tools/code_tools.py
```

Contains tools for searching and reading repository files.

Common tool ideas:

```txt
search_code(query)
read_file(path)
read_around_match(path, line)
list_files(path)
```

```txt
apps/agent/tools/database_tools.py
```

Contains tools for saving and retrieving findings or previous sessions.

Common database tool ideas:

```txt
save_finding(...)
get_previous_findings(...)
list_past_sessions(...)
```

```txt
apps/agent/nodes/planner.py
```

Creates the research plan and search terms.

```txt
apps/agent/nodes/researcher.py
```

Runs code search, reads files, and collects evidence.

```txt
apps/agent/nodes/answer_writer.py
```

Creates the final answer from gathered evidence.

This app answers:

```txt
What should the agent search?
Which files should it read?
What evidence is useful?
How should the final answer be written?
How can the answer stay grounded in source code?
```

---

## `apps.realtime`

This app handles live progress updates using Django Channels WebSocket.

Main responsibilities:

- Define WebSocket routes
- Accept WebSocket connections
- Stream research progress events
- Send session-specific updates
- Publish tool progress
- Publish session completion/failure events

Typical files:

```txt
apps/realtime/routing.py
apps/realtime/consumers.py
apps/realtime/publisher.py
```

This app answers:

```txt
How can the frontend see live agent progress?
How can a user know which tool is running now?
How can session updates be streamed in real time?
How can long-running research feel interactive?
```

---

## `apps.common`

This app contains shared helpers, base models, utilities, or common logic used by multiple apps.

Typical responsibilities:

- Shared timestamp model
- Common utility functions
- Shared constants
- Reusable exceptions
- Shared response helpers

---

## `config`

This folder contains Django project-level configuration.

Important files:

```txt
config/settings/
```

Contains Django settings such as installed apps, database, static files, REST framework, Channels, Celery, and LLM-related settings.

```txt
config/urls.py
```

Main URL routing file for admin and API routes.

```txt
config/asgi.py
```

ASGI entrypoint for HTTP and WebSocket support.

```txt
config/wsgi.py
```

WSGI entrypoint for normal HTTP requests.

```txt
config/celery.py
```

Celery application configuration for optional background jobs.

```txt
config/__init__.py
```

Loads the Celery app when Celery is installed and configured.

---

# How The System Works

## Step 1: User submits research request

The user sends a POST request to:

```http
POST /api/research/sessions/
```

with a repository URL and a question.

Example:

```json
{
  "repo_url": "https://github.com/tiangolo/fastapi",
  "question": "How does FastAPI handle dependency injection internally?"
}
```

---

## Step 2: Repository is created or reused

The backend checks whether this repository already exists in the system.

If it does not exist:

```txt
Create Repository record
Clone repository into storage/repos/
Save repository metadata
Track branch and commit
```

If it already exists:

```txt
Reuse existing Repository record
Optionally sync latest changes
Use existing local_path
```

---

## Step 3: Research session is created

A new `ResearchSession` record is created.

It stores:

```txt
- repository
- question
- status
- options
- model settings
- timestamps
- token usage
```

Possible statuses may include:

```txt
pending
running
completed
failed
```

---

## Step 4: Agent creates a plan

The planner decides what to search.

For example, for this question:

```txt
How does FastAPI handle dependency injection internally?
```

The planner may produce search terms like:

```txt
Depends
Dependency
solve_dependencies
Dependant
dependency injection
```

For this question:

```txt
How does URL-safe timed token signing work internally?
```

The planner may produce search terms like:

```txt
URLSafeTimedSerializer
URLSafeSerializerMixin
TimestampSigner
TimedSerializer
Signer
sign
unsign
max_age
SignatureExpired
base64_encode
base64_decode
```

The goal is to avoid sending the full codebase to the LLM.

Instead, the system searches first, reads only relevant files, and then asks the LLM to reason over selected evidence.

---

## Step 5: Agent searches code

The agent uses source-code tools such as:

```txt
search_code(query)
read_file(path)
read_around_match(path, line)
save_finding(...)
get_previous_findings(...)
```

Example search:

```txt
search_code("solve_dependencies")
```

Example result:

```json
{
  "file_path": "fastapi/dependencies/utils.py",
  "line": 572,
  "function_name": "solve_dependencies",
  "snippet": "async def solve_dependencies(...):"
}
```

---

## Step 6: Agent reads relevant files

After search results are found, the agent reads selected files or snippets.

Example:

```txt
read_file("fastapi/dependencies/utils.py")
```

or:

```txt
read_around_match("fastapi/dependencies/utils.py", 572)
```

This keeps token usage controlled because the agent does not read the whole repository.

---

## Step 7: Findings are saved

Important evidence is saved as findings.

Example finding:

```json
{
  "file_path": "fastapi/dependencies/utils.py",
  "line_start": 560,
  "line_end": 650,
  "function_name": "solve_dependencies",
  "note": "Main dependency resolution logic is implemented here."
}
```

Findings help with:

- Final answer generation
- Auditability
- Future session reuse
- Debugging
- Demo explanation
- Showing source-grounded research behavior

---

## Step 8: Tool calls are logged

Every tool call can be stored.

Example:

```json
{
  "tool_name": "search_code",
  "input_payload": {
    "query": "solve_dependencies"
  },
  "status": "success",
  "output_payload": {
    "matches": 12
  }
}
```

This shows how the agent researched the codebase step by step.

---

## Step 9: LLM writes final answer

After the agent collects enough evidence, it sends the evidence to the selected LLM.

The answer should include:

- Direct explanation
- Important files
- Important functions/classes
- Code references
- Clear reasoning based on source evidence
- Limitations if evidence is incomplete

Example final answer shape:

```json
{
  "answer": "FastAPI handles dependency injection mainly through Dependant models and the solve_dependencies function...",
  "references": [
    {
      "file": "fastapi/dependencies/utils.py",
      "function": "solve_dependencies",
      "lines": "560-650"
    }
  ]
}
```

---

## Step 10: WebSocket streams progress

If WebSocket streaming is enabled, the frontend can receive live updates while the research is running.

Example events:

```txt
SESSION_STARTED
REPOSITORY_SYNC_STARTED
TOOL_STARTED
TOOL_COMPLETED
FINDING_SAVED
SESSION_COMPLETED
SESSION_FAILED
```

---

# Agent Workflow Summary

```txt
User Request
   ↓
Create / reuse Repository
   ↓
Create ResearchSession
   ↓
Clone or sync repository
   ↓
Plan search terms
   ↓
Search codebase
   ↓
Read relevant files
   ↓
Save findings
   ↓
Log tool calls
   ↓
Call LLM
   ↓
Write final answer
   ↓
Save final answer
   ↓
Return API response
   ↓
Stream WebSocket updates
```

---

# Why This Design Is Useful

This design avoids sending the entire repository to the LLM.

Instead, the agent first searches the codebase, reads only relevant files, and gives the LLM a smaller evidence package.

Benefits:

- Lower token usage
- Lower cost
- Faster responses
- Better traceability
- Better source-code grounding
- Easier debugging
- More realistic backend architecture
- Better support for repeated research
- Clearer evaluation story for a take-home project

---

# Good Demo Repositories

Small repositories are better for demo and testing.

Examples:

```txt
https://github.com/pallets/itsdangerous
https://github.com/encode/httpx
https://github.com/psf/requests
https://github.com/pallets/click
```

Large repositories like FastAPI can work, but they may use more tokens and take more time.

---

# Good Demo Questions

## itsdangerous

```txt
How does URL-safe timed token signing work internally?
```

Expected important files:

```txt
src/itsdangerous/url_safe.py
src/itsdangerous/timed.py
src/itsdangerous/signer.py
src/itsdangerous/serializer.py
src/itsdangerous/encoding.py
```

---

## FastAPI

```txt
How does FastAPI handle dependency injection internally?
```

Expected important files:

```txt
fastapi/dependencies/utils.py
fastapi/dependencies/models.py
fastapi/params.py
```

---

## Requests

```txt
How does Requests prepare and send HTTP requests internally?
```

Expected important files:

```txt
requests/sessions.py
requests/models.py
requests/adapters.py
```

---

## HTTPX

```txt
How does HTTPX send requests through transports internally?
```

Expected important files:

```txt
httpx/_client.py
httpx/_transports/
httpx/_models.py
```

---

# Notes For Evaluators

This project is designed to show:

- Django backend structure
- API design
- Database modeling
- AI agent orchestration
- Tool-calling architecture
- Source-grounded answer generation
- WebSocket streaming
- Production-aware engineering decisions
- Context management for large codebases
- Cost-aware LLM usage
- Clean app separation

The key idea is not only to call an LLM, but to build a backend system where the agent can explore code, save evidence, and explain the final answer using real source references.

The project intentionally focuses on backend architecture, code research workflow, and explainable AI-agent behavior rather than frontend polish.

---

# Summary

Codebase Research Agent is a Django-based backend system for AI-assisted codebase research.

It accepts a repository and a question, explores the source code using tools, saves findings and tool calls, streams progress through WebSocket, and returns a final answer grounded in real source-code evidence.