# DECISIONS.md

# Codebase Research Agent — Design Decisions

## Architecture Overview

This project is a Django + Django REST Framework backend for an AI-powered codebase research agent. The agent accepts a public GitHub repository URL or local path and a natural language question, then explores the codebase using tools before producing a source-grounded answer.

The project is split into focused Django apps:

- `apps.repositories` handles repository metadata, cloning/syncing, local storage paths, branches, commits, and repository reuse.
- `apps.research` handles research sessions, findings, tool-call logs, final answers, statuses, timestamps, and token metadata.
- `apps.agent` contains the agent workflow, tool definitions, prompts, and LLM integration.
- `apps.realtime` handles WebSocket progress events using Django Channels.
- `apps.common` contains shared utilities.

The main API creates a research session, prepares the repository, runs the agent, stores findings/tool calls, and returns the final answer. WebSocket events are used to show progress during long-running research.

## Agent Design

The agent uses a tool-calling approach instead of sending the full repository to the LLM. This is important because large repositories can easily exceed context limits.

The agent has two main tool groups.

Code exploration tools include:

- `list_files(path)`
- `search_code(query)`
- `read_file(path)`
- `read_around_match(path, line)`
- `get_file_summary(path)`

Database tools include:

- `save_finding(session_id, file_path, note)`
- `get_previous_findings(repo_url)`
- `list_past_sessions(repo_url)`
- `log_tool_call(...)`

The workflow is:

1. Create or reuse a repository record.
2. Clone or sync the repository into local storage.
3. Create a research session.
4. Generate search terms from the question.
5. Search relevant source files.
6. Read selected files or snippets.
7. Save findings.
8. Log tool calls.
9. Generate a final answer.
10. Persist the final answer and status.

The agent stops using configured limits such as `max_steps`, `max_files_to_read`, and `max_file_chars`. These limits prevent infinite loops, reduce token usage, and keep execution predictable.

## Database Schema Rationale

The schema is centered around repository research.

`Repository` stores the repo URL, canonical URL, owner, name, branch, commit, local path, sync status, last analyzed timestamp, and file count. This avoids cloning the same repository repeatedly and allows future sessions to reuse existing data.

`ResearchSession` stores one question against one repository. It keeps the question, final answer, status, options, model name, token usage, timestamps, and error message.

`Finding` stores useful evidence discovered by the agent, including file path, symbol/function name, line range, note, evidence snippet, confidence, and metadata.

`ToolCallLog` records each tool call, input/output payload, status, error, step number, and duration. This makes the agent workflow reviewable and helps debugging.

The schema is normalized where relationships matter: one repository has many sessions, and one session has many findings and tool logs. JSON fields are used for flexible tool metadata because different tools return different structures.

At scale, I would add stronger indexing, semantic search, file chunk tables, and possibly embeddings for faster repeated research.

## Context, Cost, and Latency

The agent uses a search-first strategy to control context size. It searches the repository first, reads only relevant files/snippets, saves concise findings, and sends selected evidence to the LLM.

This reduces cost, latency, and irrelevant context. It also improves explainability because the final answer is based on saved findings and file references.

The project supports synchronous execution for simple local demos:

```json
{
  "async": false
}