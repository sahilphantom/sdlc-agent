"""
orchestrator/graph/state.py
===========================
LangGraph state definition for the SDLC pipeline.

Uses TypedDict for clean LangGraph partial-update semantics.
Each node returns only the keys it modifies; LangGraph merges them into state.
The Pydantic PipelineState in core/schemas/artifacts.py is the *validated* form
used at API boundaries — this TypedDict is the *graph-internal* representation.
"""

from __future__ import annotations

from typing import Any, Optional, TypedDict


class GraphState(TypedDict, total=False):
    """
    Full pipeline state carried through the LangGraph graph.
    Checkpointed to PostgreSQL (prod) or MemorySaver (dev) at every node.
    """

    # ── Identity ──
    run_id: str                # UUID as string for JSON serialisability
    project_id: str
    mode: str                  # execution mode: full_pipeline, refactor, etc.
    prd_input: str             # raw PRD text / markdown

    # ── Artifacts (stored as validated dicts for graph portability) ──
    spec: Optional[dict[str, Any]]
    design: Optional[dict[str, Any]]
    code: Optional[dict[str, Any]]
    review: Optional[dict[str, Any]]
    test: Optional[dict[str, Any]]
    build: Optional[dict[str, Any]]
    deployment: Optional[dict[str, Any]]
    ops: Optional[dict[str, Any]]

    # ── Control flow ──
    current_phase: Optional[str]        # AgentPhase name
    retry_count: int
    error_message: str
    awaiting_human: bool
    human_gate_name: str
    gate_approved: Optional[bool]       # None = not yet decided
    is_complete: bool
