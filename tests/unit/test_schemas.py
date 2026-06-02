"""
tests/unit/test_schemas.py
===========================
Validates all 8 Pydantic schemas work correctly.
Run with:  (.venv) PS> pytest tests/unit/test_schemas.py -v
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest
from uuid import uuid4
from datetime import datetime

from core.schemas.artifacts import (
    AgentPhase, Severity, Priority, Status, DeploymentStrategy, TechStackLayer,
    SpecJSON, DesignDoc, CodeArtifact, ReviewReport,
    TestReport, BuildReport, DeploymentReport, OpsReport,
    PipelineState,
    Requirement, DataModel, APIEndpoint, TechChoice,
    SecurityFinding, TestCase, HealthCheck, GeneratedFile,
)

RUN_ID = uuid4()
PROJECT_ID = "test-project"


# ── helpers ──────────────────────────────────────────────────────────────────

def base_fields(phase: AgentPhase, model: str = "llama3.2:3b") -> dict:
    return dict(run_id=RUN_ID, project_id=PROJECT_ID, phase=phase,
                confidence=0.95, agent_model=model)


# ── Schema 1: SpecJSON ────────────────────────────────────────────────────────

def test_spec_json_valid():
    spec = SpecJSON(
        **base_fields(AgentPhase.PRD_INGESTION),
        project_name="Auth Service",
        project_description="A JWT-based authentication microservice with OAuth2 support.",
        requirements=[
            Requirement(
                id="REQ-001", title="User Registration",
                description="Users can register with email and password",
                priority=Priority.MUST, category="functional",
                acceptance_criteria=["POST /auth/register returns 201", "Password hashed with bcrypt"],
            )
        ],
        estimated_complexity="medium",
    )
    assert spec.phase == AgentPhase.PRD_INGESTION
    assert spec.must_have_count == 1
    assert spec.functional_count == 1


def test_spec_json_invalid_complexity():
    with pytest.raises(Exception):
        SpecJSON(
            **base_fields(AgentPhase.PRD_INGESTION),
            project_name="Test", project_description="A" * 20,
            requirements=[Requirement(
                id="REQ-001", title="Test req",
                description="Some requirement here",
                category="functional",
                acceptance_criteria=["criterion one"],
            )],
            estimated_complexity="extreme",  # invalid
        )


def test_requirement_id_must_start_with_REQ():
    with pytest.raises(Exception):
        Requirement(
            id="FUNC-001",  # invalid prefix
            title="Test", description="Some description here",
            category="functional", acceptance_criteria=["one"],
        )


# ── Schema 2: DesignDoc ───────────────────────────────────────────────────────

def _make_spec() -> SpecJSON:
    return SpecJSON(
        **base_fields(AgentPhase.PRD_INGESTION),
        project_name="Auth Service",
        project_description="JWT auth microservice with OAuth2.",
        requirements=[Requirement(
            id="REQ-001", title="User Registration",
            description="Users register with email/password",
            priority=Priority.MUST, category="functional",
            acceptance_criteria=["Returns 201"],
        )],
        estimated_complexity="medium",
    )


def test_design_doc_valid():
    spec = _make_spec()
    doc = DesignDoc(
        **base_fields(AgentPhase.ARCHITECTURE_DESIGN),
        spec_artifact_id=spec.artifact_id,
        architecture_style="monolith",
        architecture_rationale="Small team, simple domain, monolith is appropriate.",
        tech_stack=[
            TechChoice(layer=TechStackLayer.BACKEND, technology="FastAPI", version="0.115.0",
                       rationale="Async Python, OpenAPI built-in"),
            TechChoice(layer=TechStackLayer.DATABASE, technology="PostgreSQL", version="16",
                       rationale="ACID, pgvector extension available"),
        ],
        data_model=[DataModel(
            entity_name="User",
            fields=["id UUID PK", "email TEXT UNIQUE NOT NULL", "password_hash TEXT NOT NULL"],
            relations=[],
        )],
        folder_structure={"src": {"api": {}, "models": {}, "auth": {}}},
        implementation_order=["db_models", "auth_core", "api_routes"],
        infra_blueprint="FastAPI on port 8000, PostgreSQL on 5432",
    )
    assert doc.phase == AgentPhase.ARCHITECTURE_DESIGN
    assert len(doc.tech_stack) == 2


def test_design_doc_missing_backend_layer_fails():
    spec = _make_spec()
    with pytest.raises(Exception):
        DesignDoc(
            **base_fields(AgentPhase.ARCHITECTURE_DESIGN),
            spec_artifact_id=spec.artifact_id,
            architecture_style="monolith",
            architecture_rationale="Test",
            tech_stack=[
                TechChoice(layer=TechStackLayer.FRONTEND, technology="Next.js",
                           version="15", rationale="UI layer"),
            ],  # missing BACKEND and DATABASE
            data_model=[DataModel(entity_name="User", fields=["id UUID PK"])],
            folder_structure={},
            implementation_order=["ui"],
            infra_blueprint="Next.js app",
        )


# ── Schema 3: CodeArtifact ────────────────────────────────────────────────────

def test_code_artifact_valid():
    artifact = CodeArtifact(
        **base_fields(AgentPhase.CODE_GENERATION, model="qwen2.5-coder:3b"),
        design_artifact_id=uuid4(),
        git_branch="feature/sdlc-run-test-001",
        git_commit="a" * 40,
        repository="https://github.com/test/auth-service",
        generated_files=[GeneratedFile(
            path="src/api/routes/auth.py",
            language="python",
            content_hash="b" * 64,
            lines_of_code=120,
            module="auth",
        )],
        modules_completed=["auth"],
        has_tests=True,
        has_migrations=True,
    )
    assert artifact.total_lines == 120
    assert artifact.file_count == 1


def test_code_artifact_skip_without_reason_fails():
    with pytest.raises(Exception):
        CodeArtifact(
            **base_fields(AgentPhase.CODE_GENERATION, model="qwen2.5-coder:3b"),
            design_artifact_id=uuid4(),
            git_branch="feature/test",
            git_commit="c" * 40,
            repository="local",
            generated_files=[GeneratedFile(
                path="src/main.py", language="python",
                content_hash="d" * 64, lines_of_code=10, module="core",
            )],
            modules_completed=["core"],
            modules_skipped=["ui"],  # skipped but no reason provided
            skip_reasons={},
            has_tests=False,
            has_migrations=False,
        )


# ── Schema 4: ReviewReport ────────────────────────────────────────────────────

def test_review_report_auto_sets_gate_flag():
    report = ReviewReport(
        **base_fields(AgentPhase.CODE_REVIEW, model="qwen2.5-coder:3b"),
        code_artifact_id=uuid4(),
        semgrep_ran=True, trivy_ran=True, linter_ran=True,
        findings=[SecurityFinding(
            finding_id="SEC-001", severity=Severity.HIGH,
            category="sqli", file_path="src/db/queries.py",
            description="SQL injection via string concatenation",
            remediation="Use parameterised queries",
        )],
        architecture_compliant=True,
        security_score=3.0, quality_score=7.0, compliance_score=9.0,
        requires_human_gate=False,  # starts False — validator should flip it
    )
    # model_validator should have auto-set this to True
    assert report.requires_human_gate is True
    assert "HIGH" in report.gate_reason or "high" in report.gate_reason.lower()


def test_review_report_clean_no_gate():
    report = ReviewReport(
        **base_fields(AgentPhase.CODE_REVIEW, model="qwen2.5-coder:3b"),
        code_artifact_id=uuid4(),
        semgrep_ran=True, trivy_ran=True, linter_ran=True,
        findings=[],
        architecture_compliant=True,
        security_score=9.5, quality_score=8.5, compliance_score=10.0,
        requires_human_gate=False,
    )
    assert report.requires_human_gate is False
    assert report.critical_count == 0
    assert report.high_count == 0


# ── Schema 5: TestReport ──────────────────────────────────────────────────────

def test_test_report_valid():
    report = TestReport(
        **base_fields(AgentPhase.TEST_EXECUTION),
        code_artifact_id=uuid4(),
        review_artifact_id=uuid4(),
        sandbox_image="python:3.11-slim",
        sandbox_isolated=True,
        total_tests=50, passed_tests=48, failed_tests=1, skipped_tests=1, flaky_tests=0,
        coverage_percent=84.5, coverage_met=True,
        total_duration_ms=12500.0,
    )
    assert report.pass_rate == 96.0


def test_test_report_count_mismatch_fails():
    with pytest.raises(Exception):
        TestReport(
            **base_fields(AgentPhase.TEST_EXECUTION),
            code_artifact_id=uuid4(), review_artifact_id=uuid4(),
            sandbox_image="python:3.11-slim", sandbox_isolated=True,
            total_tests=50,
            passed_tests=40, failed_tests=5, skipped_tests=3,  # sums to 48 ≠ 50
            flaky_tests=0, coverage_percent=80.0, coverage_met=True,
            total_duration_ms=5000.0,
        )


# ── Schema 6: BuildReport ─────────────────────────────────────────────────────

def test_build_report_staging_ok():
    report = BuildReport(
        **base_fields(AgentPhase.CICD_ORCHESTRATION),
        test_artifact_id=uuid4(),
        workflow_run_id="12345678",
        workflow_url="https://github.com/test/repo/actions/runs/12345678",
        branch="feature/sdlc-test", commit_sha="e" * 40,
        build_status=Status.PASSED, build_duration_ms=95000.0,
        build_logs_summary="Build succeeded. 0 warnings.",
        target_environment="staging",
        promotion_approved=True,
    )
    assert report.build_status == Status.PASSED


def test_build_report_production_cannot_auto_approve():
    with pytest.raises(Exception):
        BuildReport(
            **base_fields(AgentPhase.CICD_ORCHESTRATION),
            test_artifact_id=uuid4(),
            workflow_run_id="99999",
            workflow_url="https://github.com/test/repo/actions/runs/99999",
            branch="main", commit_sha="f" * 40,
            build_status=Status.PASSED, build_duration_ms=90000.0,
            build_logs_summary="All good.",
            target_environment="production",
            promotion_approved=True,  # must fail — Gate 3 required
        )


# ── Schema 7: DeploymentReport ────────────────────────────────────────────────

def test_deployment_report_valid():
    report = DeploymentReport(
        **base_fields(AgentPhase.DEPLOYMENT),
        build_artifact_id=uuid4(),
        environment="staging",
        deployment_strategy=DeploymentStrategy.BLUE_GREEN,
        docker_image="ghcr.io/test/auth-service:abc123",
        pulumi_stack="sdlc-agent/staging",
        deployment_status=Status.PASSED,
        deployment_url="https://staging.auth.example.com",
        health_checks=[HealthCheck(
            name="API health", endpoint="/health",
            status_code=200, passed=True, response_ms=45.0,
        )],
        health_check_passed=True,
        pulumi_preview="+ 3 resources created",
        resources_created=["k8s:Deployment", "k8s:Service", "k8s:Ingress"],
    )
    assert report.health_check_passed is True


def test_deployment_rollback_requires_reason():
    with pytest.raises(Exception):
        DeploymentReport(
            **base_fields(AgentPhase.DEPLOYMENT),
            build_artifact_id=uuid4(),
            environment="production",
            deployment_strategy=DeploymentStrategy.CANARY,
            docker_image="ghcr.io/test/auth:bad",
            pulumi_stack="sdlc-agent/prod",
            deployment_status=Status.FAILED,
            health_check_passed=False,
            rollback_triggered=True,
            rollback_reason="",  # must fail — reason required
            pulumi_preview="rollback",
        )


# ── Schema 8: OpsReport ───────────────────────────────────────────────────────

def test_ops_report_valid():
    now = datetime.utcnow()
    report = OpsReport(
        **base_fields(AgentPhase.OPS_MAINTENANCE),
        deployment_artifact_id=uuid4(),
        monitoring_start=now,
        monitoring_end=now,
        environment="production",
        error_rate_percent=0.2,
        p99_latency_ms=185.0,
        cpu_utilization=42.0,
        memory_utilization=61.0,
        metrics_healthy=True,
        alerts_fired=[],
        alerts_resolved=0, alerts_pending=0,
        patches_pending_approval=0,
        memory_updates_written=3,
    )
    assert report.metrics_healthy is True
    assert report.patches_pending_approval == 0


# ── PipelineState ─────────────────────────────────────────────────────────────

def test_pipeline_state_initially_empty():
    state = PipelineState(run_id=uuid4(), project_id="test", mode="full_pipeline")
    assert state.spec is None
    assert state.is_complete is False
    assert state.retry_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])