# Codebase Research Agent

A Django + Django REST Framework backend application that researches GitHub repositories and answers technical questions using real source-code evidence.

This project is designed as a backend-focused AI agent system. A user submits a repository URL and a technical question. The system clones or reuses the repository, searches the codebase, reads relevant source files, records tool calls and findings, and produces a structured answer with code references.

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

* Repository-based research sessions
* GitHub repository cloning and syncing
* Source-code search tools
* File reading tools
* AI-assisted answer generation
* Evidence-based final answers
* Tool-call logging
* Findings storage
* Previous finding reuse
* WebSocket progress events
* OpenAI and Anthropic model support
* Clean Django app-based architecture

---

# Local URLs

```txt
Base URL:
http://localhost:8000

Admin:
http://localhost:8000/admin/

API Root:
http://localhost:8000/api/

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

Research Sessions:
https://research.srikanto.dev/api/research/sessions/

WebSocket:
wss://research.srikanto.dev/ws/research/sessions/{session_id}/
```

---

# Project Structure

```txt
codebase_research_agent/
├── apps/
│   ├── agent/
│   ├── common/
│   ├── realtime/
│   ├── repositories/
│   └── research/
│
├── config/
│   ├── settings/
│   ├── asgi.py
│   ├── urls.py
│   └── wsgi.py
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

* Store repository metadata
* Store repository URL
* Track local repository path
* Clone GitHub repositories
* Sync existing repositories
* Reuse already cloned repositories

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
- name
- owner
- default_branch
- current_commit
- local_path
- last_synced_at
- created_at
- updated_at
```

This app answers:

```txt
Where is the repo stored?
Has it already been cloned?
Should we sync it again?
What commit or branch are we analyzing?
```

---

## `apps.research`

This app manages research sessions and research outputs.

Main responsibilities:

* Create research sessions
* Store user questions
* Track research status
* Store final answers
* Store findings
* Store tool-call logs
* Store token usage and execution metadata

Typical model responsibilities:

```txt
ResearchSession
- repository
- question
- status
- final_answer
- error_message
- started_at
- completed_at
- token usage
- options
```

```txt
Finding
- session
- file_path
- line_start
- line_end
- function_name
- note
- evidence
```

```txt
ToolCallLog
- session
- tool_name
- input_payload
- output_payload
- status
- duration
- error_message
```

This app answers:

```txt
What did the user ask?
What did the agent find?
What tools were used?
What was the final answer?
```

---

## `apps.agent`

This is the core AI agent app.

Main responsibilities:

* Plan search terms
* Search repository source code
* Read relevant files
* Save findings
* Call the LLM
* Generate the final answer
* Control max steps and token usage
* Avoid reading the whole repository blindly

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

```txt
apps/agent/tools/database_tools.py
```

Contains tools for saving and retrieving findings or previous sessions.

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
```

---

## `apps.realtime`

This app handles live progress updates using Django Channels WebSocket.

Main responsibilities:

* Define WebSocket routes
* Accept WebSocket connections
* Stream research progress events
* Send session-specific updates

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
```

---

## `apps.common`

This app contains shared helpers, base models, utilities, or common logic used by multiple apps.

Typical responsibilities:

* Shared timestamp model
* Common utility functions
* Shared constants
* Reusable exceptions

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
```

If it already exists:

```txt
Reuse existing Repository record
Optionally sync latest changes
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
- timestamps
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

* Final answer generation
* Auditability
* Future session reuse
* Debugging
* Demo explanation

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

* Direct explanation
* Important files
* Important functions/classes
* Code references
* Clear reasoning based on source evidence

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
TOOL_STARTED
TOOL_COMPLETED
FINDING_SAVED
SESSION_COMPLETED
SESSION_FAILED
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

## Minimal request

```json
{
  "repo_url": "https://github.com/tiangolo/fastapi",
  "question": "How does FastAPI handle dependency injection internally?"
}
```

---

## Full request

```json
{
  "repo_url": "https://github.com/tiangolo/fastapi",
  "repository_id": null,
  "local_path": null,
  "question": "How does FastAPI handle dependency injection internally?",
  "options": {
    "run_agent": true,
    "sync_repository": true,
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

* You want to create a session first
* You want to run the agent later
* You are testing session creation only

---

## `sync_repository`

```json
"sync_repository": true
```

Controls whether the repository should be cloned or updated.

### `sync_repository=true`

Behavior:

* Clone repository if missing
* Pull latest changes if already cloned
* Use latest available code

Recommended for:

* Fresh analysis
* Production demo
* Latest code research

### `sync_repository=false`

Behavior:

* Do not pull latest changes
* Use existing local files
* Faster repeated tests

Recommended for:

* Local development
* Repeating the same test
* Avoiding unnecessary GitHub calls

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

* Better research depth
* More tool calls
* More tokens
* Slower response

Lower value:

* Faster response
* Lower cost
* May miss details

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

* Repeated research
* Faster answers
* Lower token usage

---

## `include_tool_logs`

```json
"include_tool_logs": true
```

When enabled, the API response may include tool-call logs.

Useful for:

* Debugging
* Demo video
* Showing agent workflow
* Evaluation transparency

---

## `stream_events`

```json
"stream_events": true
```

When enabled, the system publishes realtime progress events over WebSocket.

Useful for:

* Frontend progress UI
* Live agent activity
* Debugging long-running tasks

---

# Example Response

```json
{
  "id": 12,
  "repository": {
    "id": 3,
    "url": "https://github.com/tiangolo/fastapi",
    "local_path": "storage/repos/tiangolo_fastapi"
  },
  "question": "How does FastAPI handle dependency injection internally?",
  "status": "completed",
  "final_answer": "FastAPI handles dependency injection through the Dependant model and solve_dependencies function...",
  "references": [
    {
      "file": "fastapi/dependencies/utils.py",
      "function": "solve_dependencies",
      "lines": "560-650"
    }
  ],
  "summary": {
    "total_tool_calls": 18,
    "total_findings": 6,
    "input_tokens": 13264,
    "output_tokens": 1057
  }
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
wss://research.srikanto.dev/ws/research/sessions/12/
```

---

# WebSocket Event Examples

## Session Started

```json
{
  "type": "SESSION_STARTED",
  "session_id": 12,
  "message": "Research session started"
}
```

---

## Repository Sync Started

```json
{
  "type": "REPOSITORY_SYNC_STARTED",
  "session_id": 12,
  "repo_url": "https://github.com/tiangolo/fastapi"
}
```

---

## Tool Started

```json
{
  "type": "TOOL_STARTED",
  "session_id": 12,
  "tool_name": "search_code",
  "input": {
    "query": "solve_dependencies"
  }
}
```

---

## Tool Completed

```json
{
  "type": "TOOL_COMPLETED",
  "session_id": 12,
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
  "session_id": 12,
  "file_path": "fastapi/dependencies/utils.py",
  "note": "Main dependency solving logic found."
}
```

---

## Session Completed

```json
{
  "type": "SESSION_COMPLETED",
  "session_id": 12,
  "status": "completed"
}
```

---

## Session Failed

```json
{
  "type": "SESSION_FAILED",
  "session_id": 12,
  "error": "Repository clone failed"
}
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

* Lower token usage
* Lower cost
* Faster responses
* Better traceability
* Better source-code grounding
* Easier debugging
* More realistic backend architecture

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

# Notes For Evaluators

This project is designed to show:

* Django backend structure
* API design
* Database modeling
* AI agent orchestration
* Tool-calling architecture
* Source-grounded answer generation
* WebSocket streaming
* Production-aware engineering decisions

The key idea is not only to call an LLM, but to build a backend system where the agent can explore code, save evidence, and explain the final answer using real source references.
