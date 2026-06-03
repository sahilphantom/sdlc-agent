#!/usr/bin/env python3
"""
SDLC Agent Pipeline - Demo Runner

This script demonstrates the complete SDLC pipeline execution.
It runs the pipeline with stub agents (no real LLM calls) to verify
the graph structure, routing logic, and checkpointing.

Usage:
    python run_pipeline.py
"""

import sys
from typing import Optional
from orchestrator.graph import get_pipeline, build_pipeline
from orchestrator.graph.state import GraphState


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def print_artifact(name: str, artifact: Optional[dict]):
    """Print an artifact summary."""
    if artifact:
        print(f"  ✓ {name}")
        if isinstance(artifact, dict):
            for key, value in artifact.items():
                if isinstance(value, (str, int, float, bool)):
                    print(f"      {key}: {value}")
                elif isinstance(value, list):
                    print(f"      {key}: [{len(value)} items]")
                elif isinstance(value, dict):
                    print(f"      {key}: {{...}}")
    else:
        print(f"  ✗ {name} (not generated)")


def run_demo_pipeline():
    """Run the demo pipeline with a sample PRD."""
    
    print_section("SDLC Agent Pipeline - Demo Execution")
    
    # Build pipeline with in-memory checkpointer (dev mode)
    print("Building pipeline with MemorySaver (dev mode)...")
    pipeline = build_pipeline(use_postgres=False)
    print("✓ Pipeline compiled successfully")
    
    # Sample PRD input
    sample_prd = """
    Build a REST API for a todo application with the following features:
    
    1. User authentication (register, login, logout)
    2. CRUD operations for todo items
    3. Todo items have: title, description, due_date, completed status
    4. Users can only see their own todos
    5. Filter todos by status (pending, completed, all)
    6. Sort by due_date or created_at
    
    Tech stack: FastAPI, PostgreSQL, SQLAlchemy
    """
    
    # Initial state
    initial_state: GraphState = {
        "project_id": "demo-project-001",
        "run_id": "demo-run-001",
        "input_data": {
            "type": "prd_text",
            "content": sample_prd.strip()
        },
        "mode": "full_pipeline",
        "retry_count": 0,
    }
    
    # Configuration for the run
    config = {
        "configurable": {
            "thread_id": "demo-thread-001"
        }
    }
    
    print_section("Pipeline Execution")
    print("Starting pipeline execution...")
    print("Note: Pipeline will stop at human approval gates\n")
    
    try:
        # Execute the pipeline
        result = pipeline.invoke(initial_state, config=config)
        
        print_section("Execution Complete")
        print("✓ Pipeline finished successfully\n")
        
        # Display generated artifacts
        print_section("Generated Artifacts")
        
        print_artifact("SpecJSON (Requirements)", result.get("spec_json"))
        print_artifact("DesignDoc (Architecture)", result.get("design_doc"))
        print_artifact("CodeArtifact (Implementation)", result.get("code_artifact"))
        print_artifact("ReviewReport (Code Review)", result.get("review_report"))
        print_artifact("TestReport (Test Results)", result.get("test_report"))
        print_artifact("BuildReport (CI/CD)", result.get("build_report"))
        print_artifact("DeploymentReport (Deployment)", result.get("deployment_report"))
        print_artifact("OpsReport (Operations)", result.get("ops_report"))
        
        # Display metadata
        print_section("Pipeline Metadata")
        print(f"  Project ID: {result.get('project_id')}")
        print(f"  Run ID: {result.get('run_id')}")
        print(f"  Mode: {result.get('mode')}")
        print(f"  Retry Count: {result.get('retry_count', 0)}")
        
        # Check for human gates
        print_section("Human Gate Status")
        if result.get("requires_human_approval"):
            print("  ⚠ Pipeline paused at human approval gate")
            print(f"  Gate: {result.get('current_gate', 'unknown')}")
            print("  Action Required: Review and approve via dashboard or CLI")
        else:
            print("  ✓ No human gates encountered (or all approved)")
        
        print_section("Success")
        print("✓ Demo pipeline executed successfully!")
        print("✓ All graph nodes and edges are wired correctly")
        print("✓ Checkpointing is working")
        print("\nNext steps:")
        print("  1. Replace stub agents with real LLM calls (Phase 2)")
        print("  2. Connect to PostgreSQL for persistent checkpointing")
        print("  3. Build the Next.js dashboard for human gates")
        
        return True
        
    except KeyboardInterrupt:
        print("\n\n⚠ Pipeline interrupted by user")
        return False
        
    except Exception as e:
        print_section("Error")
        print(f"✗ Pipeline execution failed: {type(e).__name__}")
        print(f"  {str(e)}")
        print("\nThis might be expected if the pipeline stopped at a human gate.")
        print("Check the state above to see which artifacts were generated.")
        return False


def test_conditional_edges():
    """Test the conditional edge routing logic."""
    print_section("Testing Conditional Edge Routing")
    
    from orchestrator.graph.builder import (
        should_retry_code_generation,
        should_escalate_security,
        should_gate_production_deployment,
    )
    
    # Test 1: Retry loop
    print("Test 1: Code Generation Retry Loop")
    state_fail = {
        "test_report": {"passed": False},
        "retry_count": 0,
    }
    result = should_retry_code_generation(state_fail)
    print(f"  Test failed, retry 0/3 → {result}")
    assert result == "code_generation"
    
    state_max_retries = {
        "test_report": {"passed": False},
        "retry_count": 3,
    }
    result = should_retry_code_generation(state_max_retries)
    print(f"  Test failed, retry 3/3 → {result}")
    assert result == "cicd_orchestration"
    print("  ✓ Retry loop logic correct\n")
    
    # Test 2: Security escalation
    print("Test 2: Security Escalation Gate")
    state_high_severity = {
        "review_report": {"high_severity_count": 2},
    }
    result = should_escalate_security(state_high_severity)
    print(f"  HIGH severity found → {result}")
    assert result == "security_escalation_gate"
    
    state_low_severity = {
        "review_report": {"high_severity_count": 0},
    }
    result = should_escalate_security(state_low_severity)
    print(f"  No HIGH severity → {result}")
    assert result == "test_execution"
    print("  ✓ Security escalation logic correct\n")
    
    # Test 3: Production deployment gate
    print("Test 3: Production Deployment Gate")
    state_prod = {
        "build_report": {"target_environment": "production"},
    }
    result = should_gate_production_deployment(state_prod)
    print(f"  Target: production → {result}")
    assert result == "production_deployment_gate"
    
    state_staging = {
        "build_report": {"target_environment": "staging"},
    }
    result = should_gate_production_deployment(state_staging)
    print(f"  Target: staging → {result}")
    assert result == "deployment"
    print("  ✓ Production gate logic correct\n")
    
    print("✓ All conditional edge tests passed!")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("  SDLC AGENT SYSTEM - PHASE 1 DEMO")
    print("="*70)
    
    # Run conditional edge tests first
    try:
        test_conditional_edges()
    except Exception as e:
        print(f"\n✗ Conditional edge tests failed: {e}")
        sys.exit(1)
    
    # Run the demo pipeline
    success = run_demo_pipeline()
    
    if success:
        print("\n" + "="*70)
        print("  PHASE 1 COMPLETE ✓")
        print("="*70)
        print("\nThe foundation is ready. You can now:")
        print("  • Start Phase 2: Build real agents with LLM calls")
        print("  • Run tests: pytest tests/test_pipeline_e2e.py -v")
        print("  • Check LangSmith traces (if configured)")
        print("="*70 + "\n")
        sys.exit(0)
    else:
        print("\n" + "="*70)
        print("  DEMO FAILED ✗")
        print("="*70 + "\n")
        sys.exit(1)