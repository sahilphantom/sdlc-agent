"""
LangGraph Pipeline Nodes

This module defines all 12 nodes (8 agents + 4 human gates) for the SDLC pipeline.
Currently, these are stub implementations that return mock artifacts to allow
end-to-end pipeline testing without real LLM calls.
"""

import logging
from typing import Dict, Any
import concurrent
import concurrent
from langgraph.types import interrupt
from uuid_utils import uuid4

from orchestrator.graph.state import GraphState
from core.agents.prd_ingestion import PRDIngestionAgent
from core.agents.architecture_design import ArchitectureDesignAgent
from core.agents.code_generation import CodeGenerationAgent
from core.agents.code_review import CodeReviewAgent
import asyncio


logger = logging.getLogger(__name__)



_persistent_loop = None

def run_async_safely(coro):
    """
    Bulletproof async runner for Python 3.10+.
    Reuses a persistent event loop to prevent 'Event loop is closed' errors 
    when libraries cache loop-dependent clients (like httpx/Ollama).
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
        
    if loop is not None:
        # Already in an async context (e.g., FastAPI), run in a thread
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        # Sync context: reuse a single persistent event loop
        global _persistent_loop
        if _persistent_loop is None or _persistent_loop.is_closed():
            _persistent_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(_persistent_loop)
        return _persistent_loop.run_until_complete(coro)

# ============================================================================
# AGENT NODES (Stubs for Phase 1)
# ============================================================================

_prd_agent = PRDIngestionAgent()

def prd_ingestion_node(state: GraphState) -> Dict[str, Any]:
    print("🟢 [NODE EXECUTING] prd_ingestion_node (REAL LLM CALL)")
    input_data = state.get("input_data", {})
    raw_text = input_data.get("content", "")
    
    if not raw_text:
        return {"spec_json": None, "errors": [{"node": "prd_ingestion", "msg": "Empty input"}]}

    try:
        result = run_async_safely(_prd_agent.arun({"input_text": raw_text}))
        print(f"✅ PRD Agent Success: Generated SpecJSON with {len(result.requirements)} requirements.")
        return {"spec_json": result.model_dump(), "errors": []}
    except Exception as e:
        print(f"🔴 PRD Agent Failed: {e}")
        return {"spec_json": None, "errors": [{"node": "prd_ingestion", "msg": str(e)}]}


_arch_agent = ArchitectureDesignAgent()

def architecture_design_node(state: GraphState) -> Dict[str, Any]:
    print("🟢 [NODE EXECUTING] architecture_design_node (REAL LLM CALL)")
    spec_json = state.get("spec_json")
    run_id = state.get("run_id", "")
    project_id = state.get("project_id", "")
    
    if not spec_json:
        return {"design_doc": None, "errors": [{"node": "architecture_design", "msg": "Missing spec_json"}]}

    spec_artifact_id = spec_json.get("artifact_id", str(uuid4()))
    input_data = {
        "spec_json": spec_json, "run_id": str(run_id), 
        "project_id": str(project_id), "spec_artifact_id": str(spec_artifact_id)
    }

    try:
        result = run_async_safely(_arch_agent.arun(input_data))
        print(f"✅ Architecture Agent Success: Generated design document.")
        return {"design_doc": result.model_dump(), "errors": []}
    except Exception as e:
        print(f"🔴 Architecture Agent Failed: {e}")
        return {"design_doc": None, "errors": [{"node": "architecture_design", "msg": str(e)}]}

_code_agent = CodeGenerationAgent()

def code_generation_node(state: GraphState) -> Dict[str, Any]:
    print("🟢 [NODE EXECUTING] code_generation_node (REAL LLM CALL)")
    design_doc = state.get("design_doc")
    run_id = state.get("run_id", "")
    project_id = state.get("project_id", "")
    
    if not design_doc:
        return {"code_artifact": None, "errors": [{"node": "code_generation", "msg": "Missing design_doc"}]}

    design_artifact_id = design_doc.get("artifact_id", str(uuid4()))
    input_data = {
        "design_doc": design_doc, "run_id": str(run_id), 
        "project_id": str(project_id), "design_artifact_id": str(design_artifact_id)
    }

    try:
        result = run_async_safely(_code_agent.arun(input_data))
        print(f"✅ Code Generation Agent Success: Generated {len(result.generated_files)} files across {len(result.modules_completed)} modules.")
        return {"code_artifact": result.model_dump(), "errors": []}
    except Exception as e:
        print(f"🔴 Code Generation Agent Failed: {e}")
        return {"code_artifact": None, "errors": [{"node": "code_generation", "msg": str(e)}]}

_review_agent = CodeReviewAgent()

def code_review_node(state: GraphState) -> Dict[str, Any]:
    print("🟢 [NODE EXECUTING] code_review_node (REAL LLM CALL)")
    code_artifact = state.get("code_artifact")
    run_id = state.get("run_id", "")
    project_id = state.get("project_id", "")
    
    if not code_artifact:
        return {"review_report": None, "errors": [{"node": "code_review", "msg": "Missing code_artifact"}]}

    code_artifact_id = code_artifact.get("artifact_id", str(uuid4()))
    input_data = {
        "code_artifact": code_artifact, "run_id": str(run_id), 
        "project_id": str(project_id), "code_artifact_id": str(code_artifact_id)
    }

    try:
        result = run_async_safely(_review_agent.arun(input_data))
        gate_status = "TRIGGERED 🚨" if result.requires_human_gate else "CLEARED ✅"
        print(f"✅ Code Review Agent Success: Score {result.security_score}/10. Human Gate: {gate_status}")
        return {"review_report": result.model_dump(), "errors": []}
    except Exception as e:
        print(f"🔴 Code Review Agent Failed: {e}")
        return {"review_report": None, "errors": [{"node": "code_review", "msg": str(e)}]}

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