"""
LangGraph State Definition

Defines the GraphState TypedDict that carries data through the entire pipeline.
All artifacts are optional since they're generated progressively by each agent.
"""

from typing import TypedDict, Optional, Dict, Any, List


class GraphState(TypedDict, total=False):
    """
    State that flows through the LangGraph pipeline.
    
    All artifact fields are optional (total=False) because they're populated
    progressively as each agent node executes.
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
    input_data: Dict[str, Any]  # {"type": "prd_text", "content": "..."}
    
    # =========================================================================
    # Agent Artifacts (generated progressively)
    # =========================================================================
    spec_json: Optional[Dict[str, Any]]  # Phase 1: PRD Ingestion
    design_doc: Optional[Dict[str, Any]]  # Phase 2: Architecture Design
    code_artifact: Optional[Dict[str, Any]]  # Phase 3: Code Generation
    review_report: Optional[Dict[str, Any]]  # Phase 4: Code Review
    test_report: Optional[Dict[str, Any]]  # Phase 5: Test Execution
    build_report: Optional[Dict[str, Any]]  # Phase 6: CI/CD
    deployment_report: Optional[Dict[str, Any]]  # Phase 7: Deployment
    ops_report: Optional[Dict[str, Any]]  # Phase 8: Operations
    
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