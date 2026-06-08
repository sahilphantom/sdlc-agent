"""
LangGraph StateGraph Builder - Compiles the complete SDLC pipeline

This module builds the directed acyclic graph (with cycles for retries) that
orchestrates all 8 agents and 4 human gates in the SDLC pipeline.
"""

from typing import Literal, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres import PostgresSaver

from orchestrator.graph.state import GraphState
from orchestrator.graph.nodes import (
    prd_ingestion_node,
    architecture_design_node,
    code_generation_node,
    code_review_node,
    test_execution_node,
    cicd_orchestration_node,
    deployment_node,
    ops_maintenance_node,
    architecture_approval_gate,
    security_escalation_gate,
    production_deployment_gate,
    production_patch_gate,
)
from config.settings import settings


def should_retry_code_generation(state: GraphState) -> Literal["code_generation", "cicd_orchestration"]:
    """
    Conditional edge: Route back to code generation if tests fail or coverage is low.
    Max 3 retries before proceeding to CI/CD anyway.
    """
    test_report = state.get("test_report")
    retry_count = state.get("retry_count", 0)
    
    if test_report:
        needs_retry = test_report.get("needs_code_retry", False)
        if needs_retry and retry_count < settings.sdlc_max_retries:
            print(f"🔄 Retry {retry_count + 1}/{settings.sdlc_max_retries}: Routing back to code generation")
            return "code_generation"
    
    return "cicd_orchestration"


def should_escalate_security(state: GraphState) -> Literal["security_escalation_gate", "test_execution"]:
    """
    Conditional edge: Route to security gate if HIGH severity findings.
    """
    review_report = state.get("review_report")
    
    if review_report:
        high_severity_count = review_report.get("high_severity_count", 0)
        if high_severity_count > 0:
            return "security_escalation_gate"
    
    return "test_execution"


def should_gate_production_deployment(state: GraphState) -> Literal["production_deployment_gate", "deployment"]:
    """
    Conditional edge: Route to production gate before deploying to prod.
    """
    build_report = state.get("build_report")
    
    if build_report:
        environment = build_report.get("target_environment", "staging")
        if environment == "production":
            return "production_deployment_gate"
    
    return "deployment"


def build_pipeline(use_postgres: bool = False):
    """
    Build and compile the complete SDLC LangGraph pipeline.
    
    Args:
        use_postgres: If True, use PostgresSaver for production. 
                     If False, use MemorySaver for development.
    
    Returns:
        Compiled LangGraph StateGraph
    """
    # Initialize the graph
    workflow = StateGraph(GraphState)
    
    # Add all 8 agent nodes
    workflow.add_node("prd_ingestion", prd_ingestion_node)
    workflow.add_node("architecture_design", architecture_design_node)
    workflow.add_node("code_generation", code_generation_node)
    workflow.add_node("code_review", code_review_node)
    workflow.add_node("test_execution", test_execution_node)
    workflow.add_node("cicd_orchestration", cicd_orchestration_node)
    workflow.add_node("deployment", deployment_node)
    workflow.add_node("ops_maintenance", ops_maintenance_node)
    
    # Add all 4 human gate nodes
    workflow.add_node("architecture_approval_gate", architecture_approval_gate)
    workflow.add_node("security_escalation_gate", security_escalation_gate)
    workflow.add_node("production_deployment_gate", production_deployment_gate)
    workflow.add_node("production_patch_gate", production_patch_gate)
    
    # Define edges - the flow of the pipeline
    
    # Entry point
    workflow.set_entry_point("prd_ingestion")
    
    # Linear flow: PRD → Architecture
    workflow.add_edge("prd_ingestion", "architecture_design")
    
    # Architecture → Human Gate (mandatory)
    workflow.add_edge("architecture_design", "architecture_approval_gate")
    
    # After approval → Code Generation
    workflow.add_edge("architecture_approval_gate", "code_generation")
    
    # Code Generation → Code Review
    workflow.add_edge("code_generation", "code_review")
    
    # Code Review → Conditional (Security Gate or Test Execution)
    workflow.add_conditional_edges(
        "code_review",
        should_escalate_security,
        {
            "security_escalation_gate": "security_escalation_gate",
            "test_execution": "test_execution",
        }
    )
    
    # Security Gate → Test Execution (after human review)
    workflow.add_edge("security_escalation_gate", "test_execution")
    
    # Test Execution → Conditional (Retry to Code Gen or proceed to CI/CD)
    workflow.add_conditional_edges(
        "test_execution",
        should_retry_code_generation,
        {
            "code_generation": "code_generation",
            "cicd_orchestration": "cicd_orchestration",
        }
    )
    
    # CI/CD → Conditional (Production Gate or Deployment)
    workflow.add_conditional_edges(
        "cicd_orchestration",
        should_gate_production_deployment,
        {
            "production_deployment_gate": "production_deployment_gate",
            "deployment": "deployment",
        }
    )
    
    # Production Gate → Deployment (after human approval)
    workflow.add_edge("production_deployment_gate", "deployment")
    
    # Deployment → Ops & Maintenance
    workflow.add_edge("deployment", "ops_maintenance")
    
    # Ops → End
    workflow.add_edge("ops_maintenance", END)
    
    # Configure checkpointer
    if use_postgres:
        # Production: Use PostgreSQL for persistent checkpointing
        checkpointer = PostgresSaver.from_conn_string(settings.database_url)
    else:
        # Development: Use in-memory checkpointer
        checkpointer = MemorySaver()
    
    # Compile the graph
    app = workflow.compile(checkpointer=checkpointer)
    
    return app


# Singleton pattern for pipeline instance
_pipeline_instance = None


def get_pipeline(use_postgres: Optional[bool] = None):
    """
    Get or create the pipeline singleton.
    
    Args:
        use_postgres: Override the default setting. If None, uses settings.use_postgres_checkpointer
    
    Returns:
        Compiled LangGraph StateGraph
    """
    global _pipeline_instance
    
    if _pipeline_instance is None:
        if use_postgres is None:
            use_postgres = getattr(settings, 'use_postgres_checkpointer', False)
        _pipeline_instance = build_pipeline(use_postgres=use_postgres)
    
    return _pipeline_instance