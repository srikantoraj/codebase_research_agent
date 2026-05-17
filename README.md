# Codebase Research Agent

A Django + DRF backend application that researches GitHub repositories and answers technical questions using source-code evidence.

The system combines:

* Django REST Framework API
* AI agent workflows
* GitHub repository analysis
* Tool-calling architecture
* PostgreSQL persistence
* Redis + Celery background processing
* WebSocket live updates
* Production deployment using Gunicorn, Daphne, Nginx, and systemd

---

# Features

* GitHub repository cloning and syncing
* AI-powered codebase research
* File/function/class evidence extraction
* Tool call logging
* Findings persistence
* Realtime progress events via WebSocket
* Multi-step agent workflows
* OpenAI and Anthropic support
* PostgreSQL database
* Production-ready Ubuntu deployment

---

# Project Goal

The user provides:

1. A GitHub repository URL
2. A technical question about the repository

Example:

```txt
Repository:
https://github.com/tiangolo/fastapi

Question:
How does FastAPI handle dependency injection internally?
```

The system:

1. Creates or reuses a repository
2. Clones or syncs repository
3. Creates research session
4. Searches source code
5. Reads relevant files
6. Uses LLM reasoning
7. Saves findings and tool logs
8. Streams live progress events
9. Returns structured final answer

---

# Local URLs

```txt
Base URL:
http://localhost:8000

Admin:
http://localhost:8000/admin/

API:
http://localhost:8000/api/

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

API:
https://research.srikanto.dev/api/

WebSocket:
wss://research.srikanto.dev/ws/research/sessions/{session_id}/
```

Fallback server IP:

```txt
http://54.238.221.134
```

---

# Tech Stack

```txt
Backend:
- Django
- Django REST Framework

Database:
- PostgreSQL

Async Tasks:
- Celery

Broker / Cache:
- Redis

Realtime:
- Django Channels
- Daphne

Production:
- Gunicorn
- Nginx
- systemd

LLM:
- OpenAI
- Anthropic
```

---

# Local Setup

## 1. Clone repository

```bash
git clone YOUR_REPOSITORY_URL
cd codebase_research_agent
```

---

## 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

Important packages:

```bash
pip install django djangorestframework django-environ
pip install gunicorn daphne channels channels-redis
pip install celery redis psycopg2-binary
pip install openai anthropic
```

---

## 4. Install PostgreSQL

Ubuntu:

```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib
```

Create database:

```bash
sudo -u postgres psql
```

```sql
CREATE DATABASE codebase_research_agent_db;

CREATE USER codebase_agent_user
WITH PASSWORD '@StrongPassword_2026';

ALTER ROLE codebase_agent_user
SET client_encoding TO 'utf8';

ALTER ROLE codebase_agent_user
SET default_transaction_isolation TO 'read committed';

ALTER ROLE codebase_agent_user
SET timezone TO 'UTC';

GRANT ALL PRIVILEGES
ON DATABASE codebase_research_agent_db
TO codebase_agent_user;

\c codebase_research_agent_db

GRANT ALL ON SCHEMA public
TO codebase_agent_user;

ALTER SCHEMA public
OWNER TO codebase_agent_user;

\q
```

---

# Environment Variables

Create `.env`

```bash
nano .env
```

Example:

```env
SECRET_KEY=change-this-secret-key
DEBUG=True

ALLOWED_HOSTS=localhost,127.0.0.1,research.srikanto.dev

CSRF_TRUSTED_ORIGINS=http://localhost:8000,https://research.srikanto.dev

DB_NAME=codebase_research_agent_db
DB_USER=codebase_agent_user
DB_PASSWORD=@StrongPassword_2026
DB_HOST=127.0.0.1
DB_PORT=5432

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

# Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

---

# Create Superuser

```bash
python manage.py createsuperuser
```

---

# Collect Static Files

```bash
python manage.py collectstatic --noinput
```

---

# Run Local Development Server

```bash
python manage.py runserver 0.0.0.0:8000
```

---

# Run ASGI Server With Daphne

```bash
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

---

# API Endpoints

## Create Research Session

```http
POST /api/research/sessions/
```

Example request:

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

---

## Request Body Options

| Field                   | Type    | Description                          |
| ----------------------- | ------- | ------------------------------------ |
| run_agent               | boolean | Run agent automatically              |
| sync_repository         | boolean | Pull latest repository changes       |
| llm_provider            | string  | openai or anthropic                  |
| model_name              | string  | LLM model name                       |
| max_steps               | integer | Maximum reasoning steps              |
| max_files_to_read       | integer | Maximum files agent can read         |
| max_file_chars          | integer | Maximum characters per file          |
| reuse_previous_findings | boolean | Reuse previous saved findings        |
| include_tool_logs       | boolean | Include tool logs in response        |
| stream_events           | boolean | Stream realtime events via websocket |

---

# Example API Response

```json
{
  "session_id": 12,
  "status": "completed",
  "question": "How does FastAPI handle dependency injection internally?",
  "final_answer": "FastAPI handles dependency injection using Depends...",
  "references": [
    {
      "file": "fastapi/dependencies/utils.py",
      "function": "solve_dependencies",
      "lines": "100-220"
    }
  ],
  "token_usage": {
    "input_tokens": 13264,
    "output_tokens": 1057
  }
}
```

---

# Repository Sync Behavior

## sync_repository=true

```json
{
  "sync_repository": true
}
```

Behavior:

* Clones repository if missing
* Pulls latest changes if repository already exists
* Updates local working copy

Recommended for:

* Fresh research
* Latest code analysis
* Production runs

---

## sync_repository=false

```json
{
  "sync_repository": false
}
```

Behavior:

* Uses existing local repository
* Skips git pull
* Faster execution

Recommended for:

* Repeated testing
* Faster local development
* Cached repositories

---

# Realtime WebSocket Events

## WebSocket Endpoint

```txt
ws://localhost:8000/ws/research/sessions/{session_id}/
```

Production:

```txt
wss://research.srikanto.dev/ws/research/sessions/{session_id}/
```

---

# Example WebSocket Events

## Session Started

```json
{
  "type": "SESSION_STARTED",
  "session_id": 12,
  "message": "Research session started"
}
```

---

## Tool Started

```json
{
  "type": "TOOL_STARTED",
  "tool_name": "search_code",
  "query": "dependency injection"
}
```

---

## Tool Completed

```json
{
  "type": "TOOL_COMPLETED",
  "tool_name": "read_file",
  "file": "fastapi/dependencies/utils.py"
}
```

---

## Finding Saved

```json
{
  "type": "FINDING_SAVED",
  "file": "fastapi/dependencies/utils.py",
  "note": "Dependency solving logic found"
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

# Production Deployment

## Install Ubuntu packages

```bash
sudo apt update

sudo apt install -y \
nginx \
redis-server \
postgresql \
postgresql-contrib \
python3-pip \
python3-venv \
python3-dev \
build-essential \
libpq-dev
```

---

# Gunicorn Service

File:

```txt
/etc/systemd/system/gunicorn.service
```

---

# Daphne Service

File:

```txt
/etc/systemd/system/daphne.service
```

---

# Celery Service

File:

```txt
/etc/systemd/system/celery.service
```

---

# Nginx Site

File:

```txt
/etc/nginx/sites-available/codebase_research_agent
```

Enable:

```bash
sudo ln -sf /etc/nginx/sites-available/codebase_research_agent /etc/nginx/sites-enabled/codebase_research_agent
sudo rm -f /etc/nginx/sites-enabled/default
```

---

# SSL Setup

Install certbot:

```bash
sudo apt install -y certbot python3-certbot-nginx
```

Generate SSL:

```bash
sudo certbot --nginx -d research.srikanto.dev
```

---

# Service Commands

## Start Services

```bash
sudo systemctl start gunicorn
sudo systemctl start daphne
sudo systemctl start celery
sudo systemctl start nginx
sudo systemctl start redis-server
```

---

## Restart Services

```bash
sudo systemctl restart gunicorn
sudo systemctl restart daphne
sudo systemctl restart celery
sudo systemctl restart nginx
```

---

## Enable Services

```bash
sudo systemctl enable gunicorn
sudo systemctl enable daphne
sudo systemctl enable celery
sudo systemctl enable nginx
sudo systemctl enable redis-server
```

---

## Check Service Status

```bash
sudo systemctl status gunicorn
sudo systemctl status daphne
sudo systemctl status celery
sudo systemctl status nginx
sudo systemctl status redis-server
```

---

# Useful Debug Commands

## Gunicorn logs

```bash
sudo journalctl -u gunicorn -n 100 --no-pager
```

---

## Daphne logs

```bash
sudo journalctl -u daphne -n 100 --no-pager
```

---

## Celery logs

```bash
sudo journalctl -u celery -n 100 --no-pager
```

---

## Nginx logs

```bash
sudo tail -n 100 /var/log/nginx/error.log
```

---

# Suggested Development Order

1. Setup PostgreSQL
2. Setup Redis
3. Run migrations
4. Confirm admin panel works
5. Implement repository cloning
6. Implement code search tools
7. Implement database tools
8. Implement LLM layer
9. Implement LangGraph workflow
10. Add WebSocket event streaming
11. Deploy with Gunicorn + Daphne + Nginx
12. Add SSL
13. Record demo video

---

# Important Notes

* Gunicorn handles normal Django HTTP requests
* Daphne handles WebSocket ASGI requests
* Redis is required for Channels and Celery
* Celery handles long-running research tasks
* Nginx serves static files and reverse proxies requests
* PostgreSQL is recommended for production
* SSL should always be enabled in production

---

# Project Structure

```txt
apps/
├── agent/
├── common/
├── realtime/
├── repositories/
└── research/

config/
├── settings/
├── asgi.py
├── urls.py
└── wsgi.py
```

---

# Final Production URL

```txt
https://research.srikanto.dev
```
