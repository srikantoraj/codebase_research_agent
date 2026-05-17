from django.db import models


class ResearchSessionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class ToolCallStatus(models.TextChoices):
    STARTED = "started", "Started"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"


class ToolCallType(models.TextChoices):
    CODE = "code", "Code Exploration"
    DATABASE = "database", "Database"
    LLM = "llm", "LLM"
    SYSTEM = "system", "System"


class AgentEventType(models.TextChoices):
    SESSION_CREATED = "session_created", "Session Created"
    SESSION_STARTED = "session_started", "Session Started"
    REPOSITORY_SYNCED = "repository_synced", "Repository Synced"
    PREVIOUS_FINDINGS_CHECKED = "previous_findings_checked", "Previous Findings Checked"
    TOOL_STARTED = "tool_started", "Tool Started"
    TOOL_COMPLETED = "tool_completed", "Tool Completed"
    TOOL_FAILED = "tool_failed", "Tool Failed"
    FINDING_SAVED = "finding_saved", "Finding Saved"
    ANSWER_STARTED = "answer_started", "Answer Started"
    ANSWER_COMPLETED = "answer_completed", "Answer Completed"
    SESSION_COMPLETED = "session_completed", "Session Completed"
    SESSION_FAILED = "session_failed", "Session Failed"
    SESSION_CANCELLED = "session_cancelled", "Session Cancelled"


class FindingSource(models.TextChoices):
    AGENT = "agent", "Agent"
    DATABASE_REUSE = "database_reuse", "Database Reuse"
    SYSTEM = "system", "System"
