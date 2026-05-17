from __future__ import annotations

from apps.agent.runner import AgentRunner


class AgentExecutionBridge:
    """Small integration layer so research.services does not depend on LangGraph internals."""

    @staticmethod
    def run_session(session_id):
        return AgentRunner().run(str(session_id))
