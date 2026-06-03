"""
orchestrator/graph/nodes.py
============================
Stub node functions for all 8 agent phases + 4 human gate nodes.

Each node:
  - Receives the full GraphState
  - Returns a partial dict update (LangGraph merges it into state)
  - Stubs return synthetic artifacts — real LLM calls come in Phase 2

Human gate nodes use LangGraph's interrupt() to pause the pipeline
until the dashboard/CLI sends an approval.
"""

from __future__ import annotations

import logging
from uuid import uuid4
from datetime import datetime, timezone

from langgraph.types import interrupt

from orchestrator.graph.state import GraphState

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _base_artifact(state: GraphState, phase: str, model: str) -> dict:
    """Common artifact metadata every stub produces."""
    return {
        "artifact_id": str(uuid4()),
        "run_id": state.get("run_id", str(uuid4())),
        "project_id": state.get("project_id", "unknown"),
        "phase": phase,
        "produced_at": _now_iso(),
        "confidence": 0.95,
        "retry_count": state.get("retry_count", 0),
        "agent_model": model,
        "notes": "stub — no real LLM call",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 — PRD Ingestion
# ─────────────────────────────────────────────────────────────────────────────

def prd_ingestion_node(state: GraphState) -> dict:
    """Parses raw PRD input → SpecJSON artifact."""
    logger.info("▶ Phase 1: PRD Ingestion (stub)")
    artifact = {
        **_base_artifact(state, "PRD_INGESTION", "llama3.2:3b"),
        "project_name": "Stub Project",
        "project_description": state.get("prd_input", "No PRD provided") or "No PRD provided",
        "requirements": [
            {
                "id": "REQ-001",
                "title": "Stub Requirement",
                "description": "Auto-generated stub requirement for pipeline testing",
                "priority": "must",
                "category": "functional",
                "acceptance_criteria": ["Pipeline runs end-to-end"],
                "open_questions": [],
            }
        ],
        "tech_constraints": [],
        "out_of_scope": [],
        "open_questions": [],
        "estimated_complexity": "medium",
    }
    return {
        "spec": artifact,
        "current_phase": "PRD_INGESTION",
        "error_message": "",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 — Architecture Design
# ─────────────────────────────────────────────────────────────────────────────

def architecture_design_node(state: GraphState) -> dict:
    """Reads SpecJSON → produces DesignDoc artifact."""
    logger.info("▶ Phase 2: Architecture Design (stub)")
    spec = state.get("spec", {})
    artifact = {
        **_base_artifact(state, "ARCHITECTURE_DESIGN", "llama3.2:3b"),
        "spec_artifact_id": spec.get("artifact_id", str(uuid4())),
        "architecture_style": "monolith",
        "architecture_rationale": "Stub — monolith selected for simplicity",
        "tech_stack": [
            {"layer": "backend", "technology": "FastAPI", "version": "0.115.0",
             "rationale": "Async Python, OpenAPI built-in"},
            {"layer": "database", "technology": "PostgreSQL", "version": "16",
             "rationale": "ACID, pgvector extension"},
        ],
        "data_model": [
            {"entity_name": "User",
             "fields": ["id UUID PK", "email TEXT UNIQUE NOT NULL"],
             "relations": []},
        ],
        "api_endpoints": [],
        "folder_structure": {"src": {"api": {}, "models": {}}},
        "implementation_order": ["db_models", "api_routes"],
        "infra_blueprint": "FastAPI on 8000, PostgreSQL on 5432",
        "security_considerations": [],
        "performance_targets": {},
    }
    return {
        "design": artifact,
        "current_phase": "ARCHITECTURE_DESIGN",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3 — Code Generation
# ─────────────────────────────────────────────────────────────────────────────

def code_generation_node(state: GraphState) -> dict:
    """Reads DesignDoc → produces CodeArtifact."""
    logger.info("▶ Phase 3: Code Generation (stub)")
    design = state.get("design", {})
    artifact = {
        **_base_artifact(state, "CODE_GENERATION", "qwen2.5-coder:3b"),
        "design_artifact_id": design.get("artifact_id", str(uuid4())),
        "git_branch": f"feature/sdlc-run-{state.get('run_id', 'stub')[:8]}",
        "git_commit": "a" * 40,
        "repository": "local",
        "generated_files": [
            {"path": "src/main.py", "language": "python",
             "content_hash": "b" * 64, "lines_of_code": 50,
             "is_new_file": True, "module": "core"},
        ],
        "modules_completed": ["core"],
        "modules_skipped": [],
        "skip_reasons": {},
        "has_tests": True,
        "has_migrations": True,
        "has_dockerfile": False,
        "dependency_changes": [],
    }
    return {
        "code": artifact,
        "current_phase": "CODE_GENERATION",
        "retry_count": 0,  # reset retry count after successful generation
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 — Code Review
# ─────────────────────────────────────────────────────────────────────────────

def code_review_node(state: GraphState) -> dict:
    """Reviews CodeArtifact → produces ReviewReport."""
    logger.info("▶ Phase 4: Code Review (stub)")
    code = state.get("code", {})
    artifact = {
        **_base_artifact(state, "CODE_REVIEW", "qwen2.5-coder:3b"),
        "code_artifact_id": code.get("artifact_id", str(uuid4())),
        "semgrep_ran": True,
        "trivy_ran": True,
        "linter_ran": True,
        "findings": [],  # clean review — no HIGH findings
        "architecture_compliant": True,
        "architecture_deviations": [],
        "security_score": 9.0,
        "quality_score": 8.5,
        "compliance_score": 9.5,
        "auto_fix_patches": [],
        "requires_human_gate": False,
        "gate_reason": "",
    }
    return {
        "review": artifact,
        "current_phase": "CODE_REVIEW",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5 — Test Execution
# ─────────────────────────────────────────────────────────────────────────────

def test_execution_node(state: GraphState) -> dict:
    """Runs tests in Docker sandbox → produces TestReport."""
    logger.info("▶ Phase 5: Test Execution (stub)")
    code = state.get("code", {})
    review = state.get("review", {})
    artifact = {
        **_base_artifact(state, "TEST_EXECUTION", "qwen2.5-coder:3b"),
        "code_artifact_id": code.get("artifact_id", str(uuid4())),
        "review_artifact_id": review.get("artifact_id", str(uuid4())),
        "sandbox_image": "python:3.11-slim",
        "sandbox_isolated": True,
        "test_cases": [],
        "total_tests": 10,
        "passed_tests": 10,
        "failed_tests": 0,
        "skipped_tests": 0,
        "flaky_tests": 0,
        "coverage_percent": 85.0,
        "coverage_target": 80.0,
        "coverage_met": True,
        "uncovered_modules": [],
        "needs_code_retry": False,
        "retry_instructions": "",
        "failure_summary": "",
        "total_duration_ms": 3500.0,
    }
    return {
        "test": artifact,
        "current_phase": "TEST_EXECUTION",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6 — CI/CD Orchestration
# ─────────────────────────────────────────────────────────────────────────────

def cicd_orchestration_node(state: GraphState) -> dict:
    """Triggers build pipeline → produces BuildReport."""
    logger.info("▶ Phase 6: CI/CD Orchestration (stub)")
    test = state.get("test", {})
    artifact = {
        **_base_artifact(state, "CICD_ORCHESTRATION", "llama3.2:3b"),
        "test_artifact_id": test.get("artifact_id", str(uuid4())),
        "workflow_run_id": "stub-12345",
        "workflow_url": "https://github.com/stub/repo/actions/runs/12345",
        "branch": "feature/sdlc-stub",
        "commit_sha": "e" * 40,
        "build_status": "passed",
        "build_duration_ms": 45000.0,
        "build_logs_summary": "Build succeeded. 0 warnings.",
        "docker_image_tag": None,
        "docker_image_size_mb": None,
        "target_environment": "staging",
        "promotion_approved": True,
        "promotion_blocked_reason": "",
        "new_vulnerabilities_found": False,
        "vulnerability_summary": "",
    }
    return {
        "build": artifact,
        "current_phase": "CICD_ORCHESTRATION",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7 — Deployment
# ─────────────────────────────────────────────────────────────────────────────

def deployment_node(state: GraphState) -> dict:
    """Provisions infra & deploys → produces DeploymentReport."""
    logger.info("▶ Phase 7: Deployment (stub)")
    build = state.get("build", {})
    artifact = {
        **_base_artifact(state, "DEPLOYMENT", "llama3.2:3b"),
        "build_artifact_id": build.get("artifact_id", str(uuid4())),
        "environment": "staging",
        "deployment_strategy": "blue_green",
        "docker_image": "ghcr.io/stub/app:latest",
        "pulumi_stack": "sdlc-agent/staging",
        "deployment_status": "passed",
        "deployed_at": _now_iso(),
        "deployment_url": "https://staging.stub.example.com",
        "health_checks": [
            {"name": "API health", "endpoint": "/health",
             "status_code": 200, "passed": True, "response_ms": 42.0,
             "checked_at": _now_iso()},
        ],
        "health_check_passed": True,
        "monitoring_window_minutes": 5,
        "rollback_triggered": False,
        "rollback_reason": "",
        "previous_version": None,
        "pulumi_preview": "+ 3 resources created",
        "resources_created": ["k8s:Deployment", "k8s:Service", "k8s:Ingress"],
        "resources_updated": [],
        "resources_destroyed": [],
    }
    return {
        "deployment": artifact,
        "current_phase": "DEPLOYMENT",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Phase 8 — Ops & Maintenance
# ─────────────────────────────────────────────────────────────────────────────

def ops_maintenance_node(state: GraphState) -> dict:
    """Post-deploy monitoring cycle → produces OpsReport."""
    logger.info("▶ Phase 8: Ops & Maintenance (stub)")
    dep = state.get("deployment", {})
    now = _now_iso()
    artifact = {
        **_base_artifact(state, "OPS_MAINTENANCE", "llama3.2:3b"),
        "deployment_artifact_id": dep.get("artifact_id", str(uuid4())),
        "monitoring_start": now,
        "monitoring_end": now,
        "environment": "staging",
        "error_rate_percent": 0.1,
        "p99_latency_ms": 120.0,
        "cpu_utilization": 35.0,
        "memory_utilization": 52.0,
        "metrics_healthy": True,
        "alerts_fired": [],
        "alerts_resolved": 0,
        "alerts_pending": 0,
        "issues_created": [],
        "proposed_patches": [],
        "patches_pending_approval": 0,
        "memory_updates_written": 1,
        "memory_update_summary": "Stub ops cycle — no real learnings",
    }
    return {
        "ops": artifact,
        "current_phase": "OPS_MAINTENANCE",
        "is_complete": True,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Human Gate Nodes — use LangGraph interrupt() to pause the pipeline
# ─────────────────────────────────────────────────────────────────────────────

def gate_1_architecture(state: GraphState) -> dict:
    """Gate 1: Mandatory architecture approval before code generation."""
    logger.info("⏸ Gate 1: Architecture Approval — awaiting human decision")
    decision = interrupt({
        "gate": "gate_1_architecture",
        "message": "Please review the architecture design and approve or reject.",
        "artifact_key": "design",
    })
    approved = decision if isinstance(decision, bool) else str(decision).lower() in ("true", "approve", "yes")
    logger.info(f"  Gate 1 decision: {'APPROVED' if approved else 'REJECTED'}")
    return {
        "awaiting_human": False,
        "human_gate_name": "gate_1_architecture",
        "gate_approved": approved,
    }


def gate_2_security(state: GraphState) -> dict:
    """Gate 2: Security escalation — only reached when HIGH/CRITICAL findings exist."""
    logger.info("⏸ Gate 2: Security Escalation — awaiting human decision")
    decision = interrupt({
        "gate": "gate_2_security",
        "message": "HIGH/CRITICAL security findings found. Review and approve or reject.",
        "artifact_key": "review",
    })
    approved = decision if isinstance(decision, bool) else str(decision).lower() in ("true", "approve", "yes")
    logger.info(f"  Gate 2 decision: {'APPROVED' if approved else 'REJECTED'}")
    return {
        "awaiting_human": False,
        "human_gate_name": "gate_2_security",
        "gate_approved": approved,
    }


def gate_3_production(state: GraphState) -> dict:
    """Gate 3: Production deployment approval."""
    logger.info("⏸ Gate 3: Production Deployment — awaiting human decision")
    decision = interrupt({
        "gate": "gate_3_production",
        "message": "Approve production deployment?",
        "artifact_key": "build",
    })
    approved = decision if isinstance(decision, bool) else str(decision).lower() in ("true", "approve", "yes")
    logger.info(f"  Gate 3 decision: {'APPROVED' if approved else 'REJECTED'}")
    return {
        "awaiting_human": False,
        "human_gate_name": "gate_3_production",
        "gate_approved": approved,
    }


def gate_4_ops_patch(state: GraphState) -> dict:
    """Gate 4: Production patch approval."""
    logger.info("⏸ Gate 4: Ops Patch Approval — awaiting human decision")
    decision = interrupt({
        "gate": "gate_4_ops_patch",
        "message": "Approve auto-patch for production?",
        "artifact_key": "ops",
    })
    approved = decision if isinstance(decision, bool) else str(decision).lower() in ("true", "approve", "yes")
    logger.info(f"  Gate 4 decision: {'APPROVED' if approved else 'REJECTED'}")
    return {
        "awaiting_human": False,
        "human_gate_name": "gate_4_ops_patch",
        "gate_approved": approved,
    }
