"""
LangGraph Pipeline Nodes

This module defines all 12 nodes (8 agents + 4 human gates) for the SDLC pipeline.
Currently, these are stub implementations that return mock artifacts to allow
end-to-end pipeline testing without real LLM calls.
"""

import logging
from typing import Dict, Any
from langgraph.types import interrupt
from uuid_utils import uuid4

from orchestrator.graph.state import GraphState
from core.agents.prd_ingestion import PRDIngestionAgent
from core.agents.architecture_design import ArchitectureDesignAgent, ArchitectureDesignInput
import asyncio


logger = logging.getLogger(__name__)

# ============================================================================
# AGENT NODES (Stubs for Phase 1)
# ============================================================================

_prd_agent = PRDIngestionAgent()

def prd_ingestion_node(state: GraphState) -> Dict[str, Any]:
    """Phase 1: PRD Ingestion Agent (REAL IMPLEMENTATION)"""
    print("🟢 [NODE EXECUTING] prd_ingestion_node (REAL LLM CALL)")
    
    # 1. Extract input text from state
    input_data = state.get("input_data", {})
    raw_text = input_data.get("content", "")
    
    if not raw_text:
        print("⚠️ Warning: No input text found in state.")
        return {"spec_json": None, "errors": [{"node": "prd_ingestion", "msg": "Empty input"}]}

    # 2. Run the agent
    try:
        # Pass a dictionary matching the PRDInput schema
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(asyncio.run, _prd_agent.arun({"input_text": raw_text})).result()
        else:
            result = asyncio.run(_prd_agent.arun({"input_text": raw_text}))
            
        print(f"✅ PRD Agent Success: Generated SpecJSON with {len(result.requirements)} requirements.")
        
        # 3. Return the artifact
        return {
            "spec_json": result.model_dump(),
            "errors": [] # Clear errors on success
        }
        
    except Exception as e:
        print(f"🔴 PRD Agent Failed: {e}")
        return {
            "spec_json": None,
            "errors": [{"node": "prd_ingestion", "msg": str(e)}]
        }


_arch_agent = ArchitectureDesignAgent()

def architecture_design_node(state: GraphState) -> Dict[str, Any]:
    """Phase 2: Architecture Design Agent (REAL IMPLEMENTATION)"""
    print("🟢 [NODE EXECUTING] architecture_design_node (REAL LLM CALL)")
    
    # 1. Extract required data from state
    spec_json = state.get("spec_json")
    run_id = state.get("run_id", "")
    project_id = state.get("project_id", "")
    
    if not spec_json:
        print("⚠️ Warning: No spec_json found in state. Cannot design architecture.")
        return {"design_doc": None, "errors": [{"node": "architecture_design", "msg": "Missing spec_json"}]}

    # Extract the artifact_id from the spec_json dict
    spec_artifact_id = spec_json.get("artifact_id", str(uuid4()))

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    try:
        # 🔧 FIX: Added spec_artifact_id to satisfy the ArchitectureDesignInput schema
        input_data = {
            "spec_json": spec_json, 
            "run_id": str(run_id), 
            "project_id": str(project_id),
            "spec_artifact_id": str(spec_artifact_id) 
        }

        if loop is not None:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                result = pool.submit(asyncio.run, _arch_agent.arun(input_data)).result()
        else:
            result = asyncio.run(_arch_agent.arun(input_data))
            
        print(f"✅ Architecture Agent Success: Generated design document.")
        
        return {
            "design_doc": result.model_dump(),
            "errors": []
        }
    
    except Exception as e:
        print(f"🔴 Architecture Agent Failed: {e}")
        return {
            "design_doc": None,
            "errors": [{"node": "architecture_design", "msg": str(e)}]
        }

def code_generation_node(state: GraphState) -> Dict[str, Any]:
    """Phase 3: Code Generation Agent stub."""
    logger.info("Executing Code Generation Agent (stub)")
    return {
        "code_artifact": {
            "files": ["main.py", "models.py", "routes.py"],
            "commit_hash": "abc123def456",
            "branch": "feature/auto-generated-001"
        }
    }

def code_review_node(state: GraphState) -> Dict[str, Any]:
    """Phase 4: Code Review Agent stub."""
    logger.info("Executing Code Review Agent (stub)")
    # Simulate a mix of severities to test routing
    # Change high_severity_count to >0 to test the security escalation gate
    return {
        "review_report": {
            "high_severity_count": 0,  
            "medium_severity_count": 1,
            "low_severity_count": 2,
            "issues": ["Missing docstring in main.py"],
            "confidence": 0.85
        }
    }

def test_execution_node(state: GraphState) -> Dict[str, Any]:
    """Phase 5: Test Execution Agent stub."""
    logger.info("Executing Test Execution Agent (stub)")
    return {
        "test_report": {
            "passed": True,
            "coverage": 0.85,
            "failed_tests": [],
            "flaky_tests": []
        }
    }

def cicd_orchestration_node(state: GraphState) -> Dict[str, Any]:
    """Phase 6: CI/CD Orchestration Agent stub."""
    logger.info("Executing CI/CD Orchestration Agent (stub)")
    return {
        "build_report": {
            "status": "success",
            "target_environment": "staging",  # Change to "production" to test prod gate
            "build_id": "build-9876"
        }
    }

def deployment_node(state: GraphState) -> Dict[str, Any]:
    """Phase 7: Deployment Agent stub."""
    logger.info("Executing Deployment Agent (stub)")
    return {
        "deployment_report": {
            "status": "deployed",
            "url": "https://staging.example.com",
            "health_check": "passing"
        }
    }

def ops_maintenance_node(state: GraphState) -> Dict[str, Any]:
    """Phase 8: Operations & Maintenance Agent stub."""
    logger.info("Executing Ops & Maintenance Agent (stub)")
    return {
        "ops_report": {
            "status": "monitoring",
            "alerts_triaged": 0,
            "metrics": {"error_rate": 0.01, "latency_p95": 120}
        }
    }


# ============================================================================
# HUMAN GATE NODES
# ============================================================================

def architecture_approval_gate(state: GraphState) -> Dict[str, Any]:
    """
    Human Gate 1: Architecture Approval
    Pauses the pipeline and waits for human approval via interrupt().
    """
    logger.info("HITTING GATE 1: Architecture Approval")
    
    approval = interrupt({
        "gate": "architecture_approval",
        "message": "Please review the DesignDoc and approve or request changes.",
        "design_doc": state.get("design_doc")
    })
    
    logger.info(f"Gate 1 resumed with: {approval}")
    return {"human_approval_status": "approved", "current_gate": None}


def security_escalation_gate(state: GraphState) -> Dict[str, Any]:
    """
    Human Gate 2: Security Escalation
    Triggered if code review finds HIGH severity issues.
    """
    logger.info("HITTING GATE 2: Security Escalation")
    
    approval = interrupt({
        "gate": "security_escalation",
        "message": "HIGH severity issues found. Please review and decide.",
        "review_report": state.get("review_report")
    })
    
    logger.info(f"Gate 2 resumed with: {approval}")
    return {"human_approval_status": "approved", "current_gate": None}


def production_deployment_gate(state: GraphState) -> Dict[str, Any]:
    """
    Human Gate 3: Production Deployment Approval
    Triggered before deploying to production environment.
    """
    logger.info("HITTING GATE 3: Production Deployment")
    
    approval = interrupt({
        "gate": "production_deployment",
        "message": "Ready to deploy to PRODUCTION. Please approve.",
        "build_report": state.get("build_report")
    })
    
    logger.info(f"Gate 3 resumed with: {approval}")
    return {"human_approval_status": "approved", "current_gate": None}


def production_patch_gate(state: GraphState) -> Dict[str, Any]:
    """
    Human Gate 4: Production Patch Approval
    Triggered when Ops agent proposes an auto-patch for a production bug.
    """
    logger.info("HITTING GATE 4: Production Patch")
    
    approval = interrupt({
        "gate": "production_patch",
        "message": "Auto-patch proposed for production bug. Please approve.",
        "ops_report": state.get("ops_report")
    })
    
    logger.info(f"Gate 4 resumed with: {approval}")
    return {"human_approval_status": "approved", "current_gate": None}