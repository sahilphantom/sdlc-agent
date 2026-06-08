"""
Routing Schemas for Intent Classification and Input Adaptation.
Defines the 8 execution modes and the typed routing JSON.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class ExecutionMode(str, Enum):
    """The 8 named execution modes defined in Section 11.2."""
    FULL_PIPELINE = "full_pipeline"
    FRONTEND_ONLY = "frontend_only"
    REFACTOR = "refactor"
    DEPLOY_ONLY = "deploy_only"
    TEST_ONLY = "test_only"
    CODE_REVIEW_ONLY = "code_review_only"
    ARCHITECTURE_ONLY = "architecture_only"
    FIX_AND_PATCH = "fix_and_patch"


class InputType(str, Enum):
    """Supported input formats defined in Section 11.3."""
    TEXT = "text"
    MARKDOWN = "markdown"
    DOCX = "docx"
    ZIP = "zip"
    GIT_URL = "git_url"
    PASTED_CODE = "pasted_code"
    ERROR_LOG = "error_log"


class IntentRouting(BaseModel):
    """
    Output of the Intent Classifier.
    Maps user request to a specific execution mode and active agents.
    """
    mode: ExecutionMode = Field(description="The determined execution mode")
    active_agents: List[int] = Field(
        description="List of active agent phase numbers (1-8). E.g., [1,2] for architecture_only, [3,4,5] for refactor."
    )
    input_type: InputType = Field(description="The type of input provided by the user")
    project_id: str = Field(default="default-project", description="Project identifier")
    clarification_needed: bool = Field(
        default=False, 
        description="True if the request is ambiguous and needs a clarifying question"
    )
    clarification_question: Optional[str] = Field(
        default=None, 
        description="The question to ask the user if clarification_needed is True"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, 
        description="Classifier confidence in this routing decision"
    )