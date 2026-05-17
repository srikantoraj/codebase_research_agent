from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel
from apps.research.enums import (
    AgentEventType,
    FindingSource,
    ResearchSessionStatus,
    ToolCallStatus,
    ToolCallType,
)


class ResearchSession(TimeStampedModel):
    """
    One technical question asked against one repository.

    This model is intentionally richer than a simple prompt/answer table because
    the assignment evaluates whether the agent workflow is persisted and
    reviewable after execution.
    """

    repository = models.ForeignKey(
        "repositories.Repository",
        on_delete=models.CASCADE,
        related_name="research_sessions",
    )
    question = models.TextField()

    status = models.CharField(
        max_length=30,
        choices=ResearchSessionStatus.choices,
        default=ResearchSessionStatus.PENDING,
    )
    final_answer = models.TextField(blank=True)
    error_message = models.TextField(blank=True)

    options = models.JSONField(default=dict, blank=True)
    answer_references = models.JSONField(default=list, blank=True)

    llm_provider = models.CharField(max_length=100, blank=True)
    model_name = models.CharField(max_length=150, blank=True)

    max_steps = models.PositiveIntegerField(default=8)
    current_step = models.PositiveIntegerField(default=0)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    total_tool_calls = models.PositiveIntegerField(default=0)
    total_findings = models.PositiveIntegerField(default=0)

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["repository", "-created_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return "%s - %s" % (self.repository, self.question[:80])

    @property
    def is_finished(self):
        return self.status in {
            ResearchSessionStatus.COMPLETED,
            ResearchSessionStatus.FAILED,
            ResearchSessionStatus.CANCELLED,
        }

    @property
    def websocket_group_name(self):
        return "research_session_%s" % self.id

    def mark_running(self):
        self.status = ResearchSessionStatus.RUNNING
        self.error_message = ""
        self.started_at = self.started_at or timezone.now()
        self.save(update_fields=["status", "error_message", "started_at", "updated_at"])

    def mark_completed(self, final_answer, answer_references=None):
        self.status = ResearchSessionStatus.COMPLETED
        self.final_answer = final_answer or ""
        self.answer_references = answer_references or []
        self.completed_at = timezone.now()
        self.total_tool_calls = self.tool_calls.count()
        self.total_findings = self.findings.count()
        self.save(
            update_fields=[
                "status",
                "final_answer",
                "answer_references",
                "completed_at",
                "total_tool_calls",
                "total_findings",
                "updated_at",
            ]
        )

    def mark_failed(self, message):
        self.status = ResearchSessionStatus.FAILED
        self.error_message = message or "Research failed."
        self.completed_at = timezone.now()
        self.total_tool_calls = self.tool_calls.count()
        self.total_findings = self.findings.count()
        self.save(
            update_fields=[
                "status",
                "error_message",
                "completed_at",
                "total_tool_calls",
                "total_findings",
                "updated_at",
            ]
        )

    def mark_cancelled(self, message="Research session cancelled."):
        self.status = ResearchSessionStatus.CANCELLED
        self.error_message = message
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "error_message", "completed_at", "updated_at"])


class ToolCallLog(TimeStampedModel):
    """Audit trail of every tool call made during a research session."""

    session = models.ForeignKey(
        ResearchSession,
        on_delete=models.CASCADE,
        related_name="tool_calls",
    )
    repository = models.ForeignKey(
        "repositories.Repository",
        on_delete=models.CASCADE,
        related_name="tool_calls",
    )

    tool_name = models.CharField(max_length=150)
    tool_type = models.CharField(
        max_length=30,
        choices=ToolCallType.choices,
        default=ToolCallType.SYSTEM,
    )
    status = models.CharField(
        max_length=30,
        choices=ToolCallStatus.choices,
        default=ToolCallStatus.STARTED,
    )

    step_number = models.PositiveIntegerField(default=0)
    input_payload = models.JSONField(default=dict, blank=True)
    output_payload = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    duration_ms = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["session", "step_number"]),
            models.Index(fields=["repository", "tool_name"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return "%s #%s" % (self.tool_name, self.step_number)


class Finding(TimeStampedModel):
    """A code evidence note produced or reused by the agent."""

    session = models.ForeignKey(
        ResearchSession,
        on_delete=models.CASCADE,
        related_name="findings",
    )
    repository = models.ForeignKey(
        "repositories.Repository",
        on_delete=models.CASCADE,
        related_name="findings",
    )

    source = models.CharField(
        max_length=30,
        choices=FindingSource.choices,
        default=FindingSource.AGENT,
    )
    file_path = models.TextField()
    symbol_name = models.CharField(max_length=255, blank=True)
    symbol_type = models.CharField(max_length=80, blank=True)
    line_start = models.PositiveIntegerField(null=True, blank=True)
    line_end = models.PositiveIntegerField(null=True, blank=True)

    note = models.TextField()
    evidence_snippet = models.TextField(blank=True)
    confidence = models.FloatField(default=0.0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["session", "created_at"]),
            models.Index(fields=["repository", "file_path"]),
            models.Index(fields=["source"]),
        ]

    def __str__(self):
        location = self.file_path
        if self.line_start:
            location = "%s:%s" % (location, self.line_start)
        return location

    @property
    def reference(self):
        data = {"file_path": self.file_path}
        if self.symbol_name:
            data["symbol_name"] = self.symbol_name
        if self.symbol_type:
            data["symbol_type"] = self.symbol_type
        if self.line_start:
            data["line_start"] = self.line_start
        if self.line_end:
            data["line_end"] = self.line_end
        return data


class AgentEvent(TimeStampedModel):
    """
    Persisted timeline event for WebSocket and post-run review.

    Even if the frontend disconnects, these events allow the session timeline to
    be reconstructed later.
    """

    session = models.ForeignKey(
        ResearchSession,
        on_delete=models.CASCADE,
        related_name="events",
    )

    event_type = models.CharField(
        max_length=100,
        choices=AgentEventType.choices,
        default=AgentEventType.SESSION_CREATED,
    )
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    step_number = models.PositiveIntegerField(default=0)
    is_public = models.BooleanField(default=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["session", "created_at"]),
            models.Index(fields=["event_type"]),
            models.Index(fields=["is_public"]),
        ]

    def __str__(self):
        return "%s - %s" % (self.event_type, self.title)
