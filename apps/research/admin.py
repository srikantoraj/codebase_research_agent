from django.contrib import admin

from apps.research.models import AgentEvent, Finding, ResearchSession, ToolCallLog


class FindingInline(admin.TabularInline):
    model = Finding
    extra = 0
    fields = ("file_path", "symbol_name", "line_start", "line_end", "confidence", "source")
    readonly_fields = fields
    can_delete = False
    show_change_link = True


class ToolCallLogInline(admin.TabularInline):
    model = ToolCallLog
    extra = 0
    fields = ("step_number", "tool_name", "tool_type", "status", "duration_ms")
    readonly_fields = fields
    can_delete = False
    show_change_link = True


class AgentEventInline(admin.TabularInline):
    model = AgentEvent
    extra = 0
    fields = ("step_number", "event_type", "title", "created_at")
    readonly_fields = fields
    can_delete = False
    show_change_link = True


@admin.register(ResearchSession)
class ResearchSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "repository",
        "short_question",
        "status",
        "total_tool_calls",
        "total_findings",
        "started_at",
        "completed_at",
        "created_at",
    )
    list_filter = ("status", "llm_provider", "model_name", "created_at")
    search_fields = (
        "question",
        "final_answer",
        "repository__name",
        "repository__owner",
        "repository__canonical_url",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "started_at",
        "completed_at",
        "total_tool_calls",
        "total_findings",
        "websocket_group_name",
    )
    fieldsets = (
        ("Session", {"fields": ("id", "repository", "question", "status", "error_message")}),
        ("Answer", {"fields": ("final_answer", "answer_references")}),
        ("Agent Options", {"fields": ("options", "max_steps", "current_step")}),
        ("LLM", {"fields": ("llm_provider", "model_name", "input_tokens", "output_tokens")}),
        ("Metrics", {"fields": ("total_tool_calls", "total_findings")}),
        ("Timing", {"fields": ("started_at", "completed_at", "created_at", "updated_at")}),
        ("Realtime", {"fields": ("websocket_group_name",)}),
    )
    inlines = [FindingInline, ToolCallLogInline, AgentEventInline]

    def short_question(self, obj):
        return obj.question[:90]


@admin.register(Finding)
class FindingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "repository",
        "session",
        "file_path",
        "symbol_name",
        "line_start",
        "line_end",
        "confidence",
        "source",
        "created_at",
    )
    list_filter = ("source", "confidence", "created_at")
    search_fields = ("file_path", "symbol_name", "note", "evidence_snippet", "repository__name")
    readonly_fields = ("id", "created_at", "updated_at", "reference")


@admin.register(ToolCallLog)
class ToolCallLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "session",
        "repository",
        "step_number",
        "tool_name",
        "tool_type",
        "status",
        "duration_ms",
        "created_at",
    )
    list_filter = ("tool_type", "status", "tool_name", "created_at")
    search_fields = ("tool_name", "error_message", "repository__name", "session__question")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(AgentEvent)
class AgentEventAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "session",
        "event_type",
        "title",
        "step_number",
        "is_public",
        "created_at",
    )
    list_filter = ("event_type", "is_public", "created_at")
    search_fields = ("title", "message", "session__question", "session__repository__name")
    readonly_fields = ("id", "created_at", "updated_at")
