"""
LangGraph State Definition

Defines the GraphState TypedDict that carries data through the entire pipeline.
"""

from typing import TypedDict, Optional, Dict, Any, List


class GraphState(TypedDict, total=False):
    """
    State that flows through the LangGraph pipeline.
    """
    
    # =========================================================================
    # Pipeline Metadata
    # =========================================================================
    project_id: str
    run_id: str
    mode: str  # "full_pipeline", "refactor", "deploy_only", etc.
    retry_count: int
    
    # =========================================================================
    # Input Data
    # =========================================================================
    input_data: Dict[str, Any]
    
    # =========================================================================
    # Intent Routing State (Section 11)
    # =========================================================================
    execution_mode: Optional[str]      # e.g., "full_pipeline", "refactor"
    active_agents: Optional[List[int]] # e.g., [3, 4, 5]
    
    # =========================================================================
    # Agent Artifacts (generated progressively)
    # =========================================================================
    spec_json: Optional[Dict[str, Any]]
    design_doc: Optional[Dict[str, Any]]
    code_artifact: Optional[Dict[str, Any]]
    review_report: Optional[Dict[str, Any]]
    test_report: Optional[Dict[str, Any]]
    build_report: Optional[Dict[str, Any]]
    deployment_report: Optional[Dict[str, Any]]
    ops_report: Optional[Dict[str, Any]]
    
    # =========================================================================
    # Human Gate State
    # =========================================================================
    requires_human_approval: bool
    current_gate: Optional[str]
    human_approval_status: Optional[str]
    
    # =========================================================================
    # Error Tracking
    # =========================================================================
    errors: List[Dict[str, Any]]