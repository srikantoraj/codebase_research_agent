# import os
# import re
# import time
# from pathlib import Path

# from django.db import transaction
# from django.utils import timezone

# from apps.repositories.models import Repository
# from apps.repositories.services import RepositoryService
# from apps.research.enums import (
#     AgentEventType,
#     FindingSource,
#     ResearchSessionStatus,
#     ToolCallStatus,
#     ToolCallType,
# )
# from apps.research.models import AgentEvent, Finding, ResearchSession, ToolCallLog
# from apps.research.selectors import FindingSelector, ResearchSessionSelector

# try:
#     from apps.realtime.services import RealtimeEventPublisher
# except Exception:  # pragma: no cover - realtime app is optional during early milestones
#     RealtimeEventPublisher = None


# class ResearchServiceError(Exception):
#     pass


# class ResearchEventService:
#     @staticmethod
#     def emit(session, event_type, title, message="", payload=None, step_number=0, is_public=True):
#         payload = payload or {}
#         event = AgentEvent.objects.create(
#             session=session,
#             event_type=event_type,
#             title=title,
#             message=message,
#             payload=payload,
#             step_number=step_number,
#             is_public=is_public,
#         )

#         event_data = {
#             "id": str(event.id),
#             "session_id": str(session.id),
#             "event_type": event.event_type,
#             "title": event.title,
#             "message": event.message,
#             "payload": event.payload,
#             "step_number": event.step_number,
#             "created_at": event.created_at.isoformat(),
#         }

#         if RealtimeEventPublisher is not None:
#             try:
#                 RealtimeEventPublisher.publish(session.id, event_data)
#             except Exception:
#                 # Realtime should never break persistence/API execution.
#                 pass

#         return event


# class ToolCallService:
#     @staticmethod
#     def run(session, tool_name, tool_type, input_payload, callback, step_number=0):
#         input_payload = input_payload or {}
#         ResearchEventService.emit(
#             session=session,
#             event_type=AgentEventType.TOOL_STARTED,
#             title="Running %s" % tool_name,
#             message="Tool execution started.",
#             payload={"tool_name": tool_name, "tool_type": tool_type, "input": input_payload},
#             step_number=step_number,
#         )

#         tool_call = ToolCallLog.objects.create(
#             session=session,
#             repository=session.repository,
#             tool_name=tool_name,
#             tool_type=tool_type,
#             status=ToolCallStatus.STARTED,
#             step_number=step_number,
#             input_payload=input_payload,
#         )

#         started = time.perf_counter()
#         try:
#             output = callback()
#             duration_ms = int((time.perf_counter() - started) * 1000)
#             tool_call.status = ToolCallStatus.SUCCEEDED
#             tool_call.output_payload = output or {}
#             tool_call.duration_ms = duration_ms
#             tool_call.save(update_fields=["status", "output_payload", "duration_ms", "updated_at"])

#             ResearchEventService.emit(
#                 session=session,
#                 event_type=AgentEventType.TOOL_COMPLETED,
#                 title="Completed %s" % tool_name,
#                 message="Tool execution completed successfully.",
#                 payload={"tool_name": tool_name, "output_preview": ToolCallService.preview(output)},
#                 step_number=step_number,
#             )
#             return output

#         except Exception as exc:
#             duration_ms = int((time.perf_counter() - started) * 1000)
#             tool_call.status = ToolCallStatus.FAILED
#             tool_call.error_message = str(exc)
#             tool_call.duration_ms = duration_ms
#             tool_call.save(update_fields=["status", "error_message", "duration_ms", "updated_at"])

#             ResearchEventService.emit(
#                 session=session,
#                 event_type=AgentEventType.TOOL_FAILED,
#                 title="Failed %s" % tool_name,
#                 message=str(exc),
#                 payload={"tool_name": tool_name},
#                 step_number=step_number,
#             )
#             raise

#     @staticmethod
#     def preview(value, max_length=600):
#         text = str(value)
#         if len(text) > max_length:
#             return text[:max_length] + "..."
#         return text


# class FindingService:
#     @staticmethod
#     def create(session, file_path, note, evidence_snippet="", line_start=None, line_end=None,
#                symbol_name="", symbol_type="", confidence=0.7, source=FindingSource.AGENT,
#                metadata=None, step_number=0):
#         finding = Finding.objects.create(
#             session=session,
#             repository=session.repository,
#             source=source,
#             file_path=file_path,
#             symbol_name=symbol_name or "",
#             symbol_type=symbol_type or "",
#             line_start=line_start,
#             line_end=line_end,
#             note=note,
#             evidence_snippet=evidence_snippet or "",
#             confidence=confidence,
#             metadata=metadata or {},
#         )

#         ResearchEventService.emit(
#             session=session,
#             event_type=AgentEventType.FINDING_SAVED,
#             title="Finding saved",
#             message=note[:300],
#             payload=finding.reference,
#             step_number=step_number,
#         )
#         return finding


# class ResearchService:
#     @classmethod
#     @transaction.atomic
#     def create_session(cls, repository, question, options=None):
#         options = options or {}
#         session = ResearchSession.objects.create(
#             repository=repository,
#             question=question,
#             options=options,
#             max_steps=int(options.get("max_steps", 8) or 8),
#             llm_provider=options.get("llm_provider", ""),
#             model_name=options.get("model_name", ""),
#         )
#         ResearchEventService.emit(
#             session=session,
#             event_type=AgentEventType.SESSION_CREATED,
#             title="Research session created",
#             message="The question has been stored and linked to the repository.",
#             payload={"repository_id": str(repository.id), "question": question},
#         )
#         return session

#     @classmethod
#     def start_session(cls, repository_id=None, repo_url=None, local_path=None, question=None,
#                       options=None, sync_repository=True, run_agent=True):
#         repository = cls.resolve_repository(
#             repository_id=repository_id,
#             repo_url=repo_url,
#             local_path=local_path,
#             sync_repository=sync_repository,
#         )
#         session = cls.create_session(repository=repository, question=question, options=options or {})

#         if run_agent:
#             StarterResearchExecutionService.run(session)
#             return ResearchSessionSelector.get_session(session.id)

#         return session

#     @classmethod
#     def resolve_repository(cls, repository_id=None, repo_url=None, local_path=None, sync_repository=True):
#         if repository_id:
#             try:
#                 repository = Repository.objects.get(id=repository_id)
#             except Repository.DoesNotExist:
#                 raise ResearchServiceError("Repository not found.")
#             if sync_repository:
#                 repository = RepositoryService.sync(repository)
#             return repository

#         repository = RepositoryService.get_or_create_from_input(
#             repo_url=repo_url,
#             local_path=local_path,
#             sync=sync_repository,
#         )
#         return repository

#     @classmethod
#     def run_existing_session(cls, session, force=False, options=None):
#         if session.is_finished and not force:
#             raise ResearchServiceError("This session is already finished. Pass force=true to rerun.")

#         if options:
#             merged = session.options or {}
#             merged.update(options)
#             session.options = merged
#             session.max_steps = int(merged.get("max_steps", session.max_steps) or session.max_steps)
#             session.save(update_fields=["options", "max_steps", "updated_at"])

#         StarterResearchExecutionService.run(session)
#         return ResearchSessionSelector.get_session(session.id)

#     @classmethod
#     def cancel_session(cls, session):
#         if session.is_finished:
#             return session
#         session.mark_cancelled()
#         ResearchEventService.emit(
#             session=session,
#             event_type=AgentEventType.SESSION_CANCELLED,
#             title="Research cancelled",
#             message="The session was manually cancelled.",
#         )
#         return session


# class StarterResearchExecutionService:
#     """
#     Lightweight execution used until the real LangGraph agent is added.

#     This keeps the research app fully testable: sessions run, tool logs are
#     persisted, findings are saved, and a final answer is generated from code
#     evidence. The agent milestone can replace this service without changing the
#     research database/API layer.
#     """

#     IGNORED_DIRS = {
#         ".git",
#         "node_modules",
#         "venv",
#         ".venv",
#         "env",
#         "__pycache__",
#         ".pytest_cache",
#         ".mypy_cache",
#         ".ruff_cache",
#         "dist",
#         "build",
#         "coverage",
#         ".next",
#         ".turbo",
#     }
#     SOURCE_EXTENSIONS = {
#         ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs", ".php",
#         ".rb", ".cs", ".c", ".cpp", ".h", ".hpp", ".swift", ".kt", ".sql",
#         ".md", ".json", ".yaml", ".yml", ".toml",
#     }
#     STOP_WORDS = {
#         "how", "does", "where", "what", "which", "when", "why", "the", "and",
#         "or", "for", "with", "from", "this", "that", "internally", "implemented",
#         "handle", "handles", "supported", "support", "codebase", "logic", "about",
#     }

#     @classmethod
#     def run(cls, session):
#         session.mark_running()
#         ResearchEventService.emit(
#             session=session,
#             event_type=AgentEventType.SESSION_STARTED,
#             title="Research started",
#             message="The starter research engine is inspecting repository metadata and code evidence.",
#         )

#         try:
#             previous = cls.load_previous_findings(session)
#             matches = cls.search_code(session)
#             findings = cls.save_findings_from_matches(session, matches)
#             final_answer, references = cls.build_final_answer(session, previous, findings)

#             session.mark_completed(final_answer=final_answer, answer_references=references)
#             session.repository.last_analyzed_at = timezone.now()
#             session.repository.save(update_fields=["last_analyzed_at", "updated_at"])

#             ResearchEventService.emit(
#                 session=session,
#                 event_type=AgentEventType.SESSION_COMPLETED,
#                 title="Research completed",
#                 message="The session has been completed and the final answer has been saved.",
#                 payload={"finding_count": len(findings), "reference_count": len(references)},
#                 step_number=session.current_step,
#             )

#         except Exception as exc:
#             session.mark_failed(str(exc))
#             ResearchEventService.emit(
#                 session=session,
#                 event_type=AgentEventType.SESSION_FAILED,
#                 title="Research failed",
#                 message=str(exc),
#                 step_number=session.current_step,
#             )

#     @classmethod
#     def next_step(cls, session):
#         session.current_step += 1
#         session.save(update_fields=["current_step", "updated_at"])
#         return session.current_step

#     @classmethod
#     def load_previous_findings(cls, session):
#         step = cls.next_step(session)

#         def callback():
#             findings = list(FindingSelector.previous_for_repository(session.repository, limit=10))
#             return {
#                 "count": len(findings),
#                 "items": [
#                     {
#                         "file_path": item.file_path,
#                         "line_start": item.line_start,
#                         "line_end": item.line_end,
#                         "note": item.note,
#                     }
#                     for item in findings
#                     if item.session_id != session.id
#                 ],
#             }

#         output = ToolCallService.run(
#             session=session,
#             tool_name="get_previous_findings",
#             tool_type=ToolCallType.DATABASE,
#             input_payload={"repository_id": str(session.repository_id), "limit": 10},
#             callback=callback,
#             step_number=step,
#         )

#         ResearchEventService.emit(
#             session=session,
#             event_type=AgentEventType.PREVIOUS_FINDINGS_CHECKED,
#             title="Checked previous findings",
#             message="Found %s previous finding(s) for this repository." % output.get("count", 0),
#             payload=output,
#             step_number=step,
#         )
#         return output.get("items", [])

#     @classmethod
#     def search_code(cls, session):
#         step = cls.next_step(session)
#         keywords = cls.extract_keywords(session.question)

#         def callback():
#             return {
#                 "keywords": keywords,
#                 "matches": cls.search_repository(session.repository.local_path, keywords),
#             }

#         output = ToolCallService.run(
#             session=session,
#             tool_name="search_code",
#             tool_type=ToolCallType.CODE,
#             input_payload={"repo_path": session.repository.local_path, "keywords": keywords},
#             callback=callback,
#             step_number=step,
#         )
#         return output.get("matches", [])

#     @classmethod
#     def save_findings_from_matches(cls, session, matches, limit=8):
#         saved = []
#         for match in matches[:limit]:
#             step = cls.next_step(session)
#             note = "Potentially relevant code match for the question: '%s'." % session.question
#             finding = FindingService.create(
#                 session=session,
#                 file_path=match.get("file_path", ""),
#                 line_start=match.get("line_number"),
#                 line_end=match.get("line_number"),
#                 note=note,
#                 evidence_snippet=match.get("line", ""),
#                 confidence=match.get("score", 0.65),
#                 metadata={"matched_keywords": match.get("matched_keywords", [])},
#                 step_number=step,
#             )
#             saved.append(finding)
#         return saved

#     @classmethod
#     def build_final_answer(cls, session, previous_findings, findings):
#         step = cls.next_step(session)
#         ResearchEventService.emit(
#             session=session,
#             event_type=AgentEventType.ANSWER_STARTED,
#             title="Writing starter answer",
#             message="Composing a first answer from persisted code findings.",
#             step_number=step,
#         )

#         if findings:
#             lines = [
#                 "Starter research completed. I searched the repository and found likely relevant code locations for this question.",
#                 "",
#                 "Question: %s" % session.question,
#                 "",
#                 "Evidence found:",
#             ]
#             for index, finding in enumerate(findings, start=1):
#                 location = finding.file_path
#                 if finding.line_start:
#                     location = "%s:%s" % (location, finding.line_start)
#                 lines.append("%s. %s — %s" % (index, location, finding.evidence_snippet[:220]))

#             lines.extend([
#                 "",
#                 "Note: this is the database-backed starter execution. The next agent milestone should replace this with the LangGraph/LLM reasoning loop, using these same persisted findings, tool logs, and events.",
#             ])
#         else:
#             lines = [
#                 "Starter research completed, but no strong code matches were found using the lightweight keyword search.",
#                 "Question: %s" % session.question,
#                 "Next step: the LangGraph/LLM agent should plan broader searches, read files, and save deeper findings.",
#             ]

#         if previous_findings:
#             lines.append("")
#             lines.append("Previous repository findings were available and checked before searching again.")

#         references = [finding.reference for finding in findings]

#         ResearchEventService.emit(
#             session=session,
#             event_type=AgentEventType.ANSWER_COMPLETED,
#             title="Starter answer saved",
#             message="Final answer text has been prepared from available findings.",
#             payload={"reference_count": len(references)},
#             step_number=step,
#         )
#         return "\n".join(lines), references

#     @classmethod
#     def extract_keywords(cls, question):
#         words = re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", question or "")
#         keywords = []
#         seen = set()
#         for word in words:
#             lowered = word.lower()
#             if lowered in cls.STOP_WORDS:
#                 continue
#             if lowered not in seen:
#                 seen.add(lowered)
#                 keywords.append(word)
#         return keywords[:10] or words[:5] or [question[:40]]

#     @classmethod
#     def search_repository(cls, local_path, keywords, max_results=20, max_file_bytes=600000):
#         if not local_path:
#             raise ResearchServiceError("Repository has no local_path. Sync the repository first.")

#         root = Path(local_path)
#         if not root.exists() or not root.is_dir():
#             raise ResearchServiceError("Repository local_path does not exist: %s" % local_path)

#         lowered_keywords = [keyword.lower() for keyword in keywords if keyword]
#         results = []

#         for current_root, dirs, files in os.walk(str(root)):
#             dirs[:] = [item for item in dirs if item not in cls.IGNORED_DIRS]
#             for filename in files:
#                 path = Path(current_root) / filename
#                 if not cls.is_supported_source_file(path):
#                     continue
#                 try:
#                     if path.stat().st_size > max_file_bytes:
#                         continue
#                     rel_path = str(path.relative_to(root))
#                     with path.open("r", encoding="utf-8", errors="ignore") as handle:
#                         for line_number, line in enumerate(handle, start=1):
#                             lowered_line = line.lower()
#                             matched = [kw for kw in lowered_keywords if kw and kw in lowered_line]
#                             if not matched:
#                                 continue
#                             results.append(
#                                 {
#                                     "file_path": rel_path,
#                                     "line_number": line_number,
#                                     "line": line.strip(),
#                                     "matched_keywords": matched,
#                                     "score": min(0.95, 0.55 + 0.1 * len(matched)),
#                                 }
#                             )
#                             if len(results) >= max_results:
#                                 return results
#                 except OSError:
#                     continue
#         return results

#     @classmethod
#     def is_supported_source_file(cls, path):
#         if path.suffix in cls.SOURCE_EXTENSIONS:
#             return True
#         if path.name in {"Dockerfile", "Makefile", "README", "LICENSE"}:
#             return True
#         return False


import time

from django.db import transaction
from django.utils import timezone

from apps.repositories.models import Repository
from apps.repositories.services import RepositoryService
from apps.research.enums import (
    AgentEventType,
    FindingSource,
    ResearchSessionStatus,
    ToolCallStatus,
)
from apps.research.models import AgentEvent, Finding, ResearchSession, ToolCallLog
from apps.research.selectors import ResearchSessionSelector

try:
    from apps.realtime.services import RealtimeEventPublisher
except Exception:  # pragma: no cover - realtime app is optional during early milestones
    RealtimeEventPublisher = None


class ResearchServiceError(Exception):
    pass


class ResearchEventService:
    @staticmethod
    def emit(
        session,
        event_type,
        title,
        message="",
        payload=None,
        step_number=0,
        is_public=True,
    ):
        payload = payload or {}

        event = AgentEvent.objects.create(
            session=session,
            event_type=event_type,
            title=title,
            message=message,
            payload=payload,
            step_number=step_number,
            is_public=is_public,
        )

        event_data = {
            "id": str(event.id),
            "session_id": str(session.id),
            "event_type": event.event_type,
            "title": event.title,
            "message": event.message,
            "payload": event.payload,
            "step_number": event.step_number,
            "created_at": event.created_at.isoformat(),
        }

        if RealtimeEventPublisher is not None:
            try:
                RealtimeEventPublisher.publish(session.id, event_data)
            except Exception:
                # Realtime should never break persistence/API execution.
                pass

        return event


class ToolCallService:
    @staticmethod
    def run(session, tool_name, tool_type, input_payload, callback, step_number=0):
        input_payload = input_payload or {}

        ResearchEventService.emit(
            session=session,
            event_type=AgentEventType.TOOL_STARTED,
            title="Running %s" % tool_name,
            message="Tool execution started.",
            payload={
                "tool_name": tool_name,
                "tool_type": tool_type,
                "input": input_payload,
            },
            step_number=step_number,
        )

        tool_call = ToolCallLog.objects.create(
            session=session,
            repository=session.repository,
            tool_name=tool_name,
            tool_type=tool_type,
            status=ToolCallStatus.STARTED,
            step_number=step_number,
            input_payload=input_payload,
        )

        started = time.perf_counter()

        try:
            output = callback()
            duration_ms = int((time.perf_counter() - started) * 1000)

            tool_call.status = ToolCallStatus.SUCCEEDED
            tool_call.output_payload = output or {}
            tool_call.duration_ms = duration_ms
            tool_call.save(
                update_fields=[
                    "status",
                    "output_payload",
                    "duration_ms",
                    "updated_at",
                ]
            )

            ResearchEventService.emit(
                session=session,
                event_type=AgentEventType.TOOL_COMPLETED,
                title="Completed %s" % tool_name,
                message="Tool execution completed successfully.",
                payload={
                    "tool_name": tool_name,
                    "output_preview": ToolCallService.preview(output),
                },
                step_number=step_number,
            )

            return output

        except Exception as exc:
            duration_ms = int((time.perf_counter() - started) * 1000)

            tool_call.status = ToolCallStatus.FAILED
            tool_call.error_message = str(exc)
            tool_call.duration_ms = duration_ms
            tool_call.save(
                update_fields=[
                    "status",
                    "error_message",
                    "duration_ms",
                    "updated_at",
                ]
            )

            ResearchEventService.emit(
                session=session,
                event_type=AgentEventType.TOOL_FAILED,
                title="Failed %s" % tool_name,
                message=str(exc),
                payload={"tool_name": tool_name},
                step_number=step_number,
            )

            raise

    @staticmethod
    def preview(value, max_length=600):
        text = str(value)
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text


class FindingService:
    @staticmethod
    def create(
        session,
        file_path,
        note,
        evidence_snippet="",
        line_start=None,
        line_end=None,
        symbol_name="",
        symbol_type="",
        confidence=0.7,
        source=FindingSource.AGENT,
        metadata=None,
        step_number=0,
    ):
        finding = Finding.objects.create(
            session=session,
            repository=session.repository,
            source=source,
            file_path=file_path,
            symbol_name=symbol_name or "",
            symbol_type=symbol_type or "",
            line_start=line_start,
            line_end=line_end,
            note=note,
            evidence_snippet=evidence_snippet or "",
            confidence=confidence,
            metadata=metadata or {},
        )

        ResearchEventService.emit(
            session=session,
            event_type=AgentEventType.FINDING_SAVED,
            title="Finding saved",
            message=note[:300],
            payload=finding.reference,
            step_number=step_number,
        )

        return finding


class ResearchService:
    @classmethod
    @transaction.atomic
    def create_session(cls, repository, question, options=None):
        options = options or {}

        session = ResearchSession.objects.create(
            repository=repository,
            question=question,
            options=options,
            status=ResearchSessionStatus.PENDING,
            max_steps=int(options.get("max_steps", 8) or 8),
            llm_provider=options.get("llm_provider", "openai"),
            model_name=options.get("model_name", "gpt-4o-mini"),
        )

        ResearchEventService.emit(
            session=session,
            event_type=AgentEventType.SESSION_CREATED,
            title="Research session created",
            message="The question has been stored and linked to the repository.",
            payload={
                "repository_id": str(repository.id),
                "question": question,
            },
            step_number=0,
        )

        return session

    @classmethod
    def start_session(
        cls,
        repository_id=None,
        repo_url=None,
        local_path=None,
        question=None,
        options=None,
        sync_repository=True,
        run_agent=True,
    ):
        if not question:
            raise ResearchServiceError("Question is required.")

        repository = cls.resolve_repository(
            repository_id=repository_id,
            repo_url=repo_url,
            local_path=local_path,
            sync_repository=sync_repository,
        )

        session = cls.create_session(
            repository=repository,
            question=question,
            options=options or {},
        )

        if run_agent:
            return cls.run_agent_for_session(session)

        return session

    @classmethod
    def resolve_repository(
        cls,
        repository_id=None,
        repo_url=None,
        local_path=None,
        sync_repository=True,
    ):
        if repository_id:
            try:
                repository = Repository.objects.get(id=repository_id)
            except Repository.DoesNotExist:
                raise ResearchServiceError("Repository not found.")

            if sync_repository:
                repository = RepositoryService.sync(repository)

            return repository

        repository = RepositoryService.get_or_create_from_input(
            repo_url=repo_url,
            local_path=local_path,
            sync=sync_repository,
        )

        return repository

    @classmethod
    def run_existing_session(cls, session, force=False, options=None):
        if session.is_finished and not force:
            raise ResearchServiceError(
                "This session is already finished. Pass force=true to rerun."
            )

        if options:
            merged = session.options or {}
            merged.update(options)

            session.options = merged
            session.max_steps = int(
                merged.get("max_steps", session.max_steps) or session.max_steps
            )
            session.llm_provider = merged.get("llm_provider", session.llm_provider)
            session.model_name = merged.get("model_name", session.model_name)

            session.save(
                update_fields=[
                    "options",
                    "max_steps",
                    "llm_provider",
                    "model_name",
                    "updated_at",
                ]
            )

        return cls.run_agent_for_session(session)

    @classmethod
    def run_agent_for_session(cls, session):
        """
        This is the important integration point.

        The old service called StarterResearchExecutionService.run(session).
        This version calls the real LangGraph/LangChain agent bridge.
        """

        try:
            ResearchEventService.emit(
                session=session,
                event_type=AgentEventType.SESSION_STARTED,
                title="AI research started",
                message="The LangGraph agent is starting the repository research workflow.",
                payload={
                    "llm_provider": session.llm_provider or "openai",
                    "model_name": session.model_name or "gpt-4o-mini",
                    "max_steps": session.max_steps,
                },
                step_number=session.current_step,
            )

            # Local import avoids circular imports:
            # agent -> tools -> research services -> agent bridge
            from apps.research.agent_bridge import AgentExecutionBridge

            AgentExecutionBridge.run_session(session.id)

            session.refresh_from_db()

            if session.status == ResearchSessionStatus.COMPLETED:
                session.repository.last_analyzed_at = timezone.now()
                session.repository.save(
                    update_fields=[
                        "last_analyzed_at",
                        "updated_at",
                    ]
                )

            return ResearchSessionSelector.get_session(session.id)

        except Exception as exc:
            session.refresh_from_db()

            if not session.is_finished:
                session.mark_failed(str(exc))

            ResearchEventService.emit(
                session=session,
                event_type=AgentEventType.SESSION_FAILED,
                title="AI research failed",
                message=str(exc),
                payload={
                    "error": str(exc),
                    "integration": "AgentExecutionBridge",
                },
                step_number=session.current_step,
            )

            return ResearchSessionSelector.get_session(session.id)

    @classmethod
    def cancel_session(cls, session):
        if session.is_finished:
            return session

        session.mark_cancelled()

        ResearchEventService.emit(
            session=session,
            event_type=AgentEventType.SESSION_CANCELLED,
            title="Research cancelled",
            message="The session was manually cancelled.",
            step_number=session.current_step,
        )

        return session