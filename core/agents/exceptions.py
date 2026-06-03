"""
core/agents/exceptions.py
=========================
Custom exceptions for the SDLC Agent system.
"""

class AgentError(Exception):
    """Base exception for all agent execution errors."""
    pass


class AgentValidationError(AgentError):
    """Raised when an agent's output fails to parse or validate against its output schema."""
    def __init__(self, agent_name: str, message: str, last_error: Exception | None = None):
        super().__init__(f"Agent '{agent_name}' validation failed: {message}")
        self.agent_name = agent_name
        self.last_error = last_error


class AgentEscalationError(AgentError):
    """Raised when an agent triggers human review or manual escalation."""
    def __init__(self, agent_name: str, message: str):
        super().__init__(f"Agent '{agent_name}' escalated to human review: {message}")
        self.agent_name = agent_name
