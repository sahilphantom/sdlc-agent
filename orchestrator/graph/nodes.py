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

from core.agents.cicd_orchestration import CICDOrchestrationAgent
from core.agents.intent_classifier import IntentClassifierAgent
from core.agents.test_execution import TestExecutionAgent
from orchestrator.graph.state import GraphState
from core.agents.prd_ingestion import PRDIngestionAgent
from core.agents.architecture_design import ArchitectureDesignAgent
from core.agents.code_generation import CodeGenerationAgent
from core.agents.code_review import CodeReviewAgent
import asyncio


logger = logging.getLogger(__name__)



_persistent_loop = None

_intent_agent = IntentClassifierAgent()

def intent_classifier_node(state: GraphState) -> Dict[str, Any]:
    """Step 1: Classify user intent and determine execution mode."""
    print("🟢 [NODE EXECUTING] intent_classifier_node")
    
    input_data = state.get("input_data", {})
    user_message = input_data.get("content", "")
    has_file = input_data.get("has_file", False)
    file_type = input_data.get("file_type", "none")
    
    try:
        result = run_async_safely(_intent_agent.arun({
            "user_message": user_message,
            "has_file": has_file,
            "file_type": file_type
        }))
        
        print(f"✅ Intent Classified: Mode={result.mode.value}, Agents={result.active_agents}")
        
        if result.clarification_needed:
            return {
                "errors": [{"node": "intent_classifier", "msg": result.clarification_question}],
                "is_complete": True
            }
            
        return {
            "execution_mode": result.mode.value,       # <-- Must match GraphState key
            "active_agents": result.active_agents,     # <-- Must match GraphState key
            "project_id": result.project_id,
            "errors": []
        }
    except Exception as e:
        print(f"🔴 Intent Classifier Failed: {e}")
        return {"errors": [{"node": "intent_classifier", "msg": str(e)}]}


def input_adapter_node(state: GraphState) -> Dict[str, Any]:
    """Step 2: Normalize input based on the determined execution mode."""
    print(f"🟢 [NODE EXECUTING] input_adapter_node for mode: {state.get('execution_mode')}")
    
    mode = state.get("execution_mode", "full_pipeline")
    input_data = state.get("input_data", {})
    project_id = state.get("project_id", "default-project")
    run_id = state.get("run_id", "run-001")
    
    # For this demo, we simulate the Input Adapter preparing the state
    # In production, this is where ZIP extraction and Tree-sitter parsing happens
    adapted_state = {
        "project_id": project_id,
        "run_id": run_id,
        "mode": mode,
        "input_data": input_data,
        "errors": []
    }
    
    # If it's a refactor/test/review mode, we might inject mock existing code state 
    # so the downstream agents don't fail looking for a design_doc
    if mode in ["refactor", "test_only", "code_review_only", "fix_and_patch"]:
        print("  ↳ Adapting input for existing codebase mode (injecting mock design_doc)")
        adapted_state["design_doc"] = {
            "artifact_id": "mock-design-123",
            "architecture_style": "monolith",
            "tech_stack": [{"layer": "backend", "technology": "Python", "rationale": "Existing"}],
            "data_model": [],
            "api_endpoints": []
        }
        
    print("✅ Input Adapted successfully")
    return adapted_state

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

_test_agent = TestExecutionAgent()

def test_execution_node(state: GraphState) -> Dict[str, Any]:
    """Phase 5: Test Execution Agent (REAL IMPLEMENTATION)"""
    print("🟢 [NODE EXECUTING] test_execution_node (REAL LLM CALL)")
    
    code_artifact = state.get("code_artifact")
    review_report = state.get("review_report")
    run_id = state.get("run_id", "")
    project_id = state.get("project_id", "")
    retry_count = state.get("retry_count", 0)
    
    if not code_artifact:
        print("⚠️ Warning: No code_artifact found in state. Cannot run tests.")
        return {"test_report": None, "errors": [{"node": "test_execution", "msg": "Missing code_artifact"}]}
    
    if not review_report:
        print("⚠️ Warning: No review_report found in state. Using empty review report.")
        review_report = {}

    code_artifact_id = code_artifact.get("artifact_id", str(uuid4()))
    review_artifact_id = review_report.get("artifact_id", str(uuid4()))
    
    input_data = {
        "code_artifact": code_artifact,
        "review_report": review_report,
        "run_id": str(run_id),
        "project_id": str(project_id),
        "code_artifact_id": str(code_artifact_id),
        "review_artifact_id": str(review_artifact_id)
    }

    try:
        result = run_async_safely(_test_agent.arun(input_data))
        
        retry_status = "RETRY NEEDED 🔄" if result.needs_code_retry else "ALL TESTS PASSED ✅"
        print(f"✅ Test Execution Agent Success: {result.passed_tests}/{result.total_tests} tests passed. Coverage: {result.coverage_percent}%. Status: {retry_status}")
        
        new_retry_count = retry_count + 1 if result.needs_code_retry else retry_count
        
        return {
            "test_report": result.model_dump(),
            "retry_count": new_retry_count,
            "errors": []
        }
        
    except Exception as e:
        print(f"🔴 Test Execution Agent Failed: {e}")
        return {
            "test_report": None,
            "errors": [{"node": "test_execution", "msg": str(e)}]
        }

_cicd_agent = CICDOrchestrationAgent()

def cicd_orchestration_node(state: GraphState) -> Dict[str, Any]:
    """Phase 6: CI/CD Orchestration Agent (REAL IMPLEMENTATION)"""
    print("🟢 [NODE EXECUTING] cicd_orchestration_node (REAL LLM CALL)")
    
    test_report = state.get("test_report")
    run_id = state.get("run_id", "")
    project_id = state.get("project_id", "")
    
    if not test_report:
        print("⚠️ Warning: No test_report found in state. Cannot orchestrate CI/CD.")
        return {"build_report": None, "errors": [{"node": "cicd_orchestration", "msg": "Missing test_report"}]}

    test_artifact_id = test_report.get("artifact_id", str(uuid4()))
    
    input_data = {
        "test_report": test_report,
        "run_id": str(run_id),
        "project_id": str(project_id),
        "test_artifact_id": str(test_artifact_id)
    }

    try:
        result = run_async_safely(_cicd_agent.arun(input_data))
        
        env = result.target_environment
        approved = "APPROVED ✅" if result.promotion_approved else "PENDING GATE 🚧"
        print(f"✅ CI/CD Agent Success: Build {result.build_status.value}. Target: {env}. Promotion: {approved}")
        
        return {
            "build_report": result.model_dump(),
            "errors": []
        }
        
    except Exception as e:
        print(f"🔴 CI/CD Orchestration Agent Failed: {e}")
        return {
            "build_report": None,
            "errors": [{"node": "cicd_orchestration", "msg": str(e)}]
        }

_deploy_agent = DeploymentAgent()

def deployment_node(state: GraphState) -> Dict[str, Any]:
    """Phase 7: Deployment Agent (REAL IMPLEMENTATION)"""
    print("🟢 [NODE EXECUTING] deployment_node (REAL LLM CALL)")
    
    build_report = state.get("build_report")
    run_id = state.get("run_id", "")
    project_id = state.get("project_id", "")
    
    if not build_report:
        print("⚠️ Warning: No build_report found in state. Cannot deploy.")
        return {"deployment_report": None, "errors": [{"node": "deployment", "msg": "Missing build_report"}]}

    build_artifact_id = build_report.get("artifact_id", str(uuid4()))
    
    input_data = {
        "build_report": build_report,
        "run_id": str(run_id),
        "project_id": str(project_id),
        "build_artifact_id": str(build_artifact_id)
    }

    try:
        result = run_async_safely(_deploy_agent.arun(input_data))
        
        env = result.environment
        status = "SUCCESS ✅" if result.deployment_status == "PASSED" else "FAILED/ROLLED BACK 🚨"
        print(f"✅ Deployment Agent Success: Deployed to {env} via {result.deployment_strategy.value}. Health Checks: {status}")
        
        return {
            "deployment_report": result.model_dump(),
            "errors": []
        }
        
    except Exception as e:
        print(f"🔴 Deployment Agent Failed: {e}")
        return {
            "deployment_report": None,
            "errors": [{"node": "deployment", "msg": str(e)}]
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