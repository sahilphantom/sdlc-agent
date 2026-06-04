"""
core/schemas/artifacts.py
==========================
All 8 typed artifact schemas for the SDLC Agent pipeline.

These are the contracts between every agent. No agent ever passes raw text
to another agent — all inter-agent communication is validated against one
of these schemas. If an LLM output fails Pydantic validation, the agent
retries (max 3 times) before escalating to human review.

Schema hierarchy (data flows top → bottom through the pipeline):
  PRD text
    └─► SpecJSON          (Phase 1 — PRD Ingestion)
          └─► DesignDoc   (Phase 2 — Architecture Design)
                └─► CodeArtifact  (Phase 3 — Code Generation)
                      └─► ReviewReport  (Phase 4 — Code Review)
                            └─► TestReport  (Phase 5 — Test Execution)
                                  └─► BuildReport  (Phase 6 — CI/CD)
                                        └─► DeploymentReport  (Phase 7 — Deploy)
                                              └─► OpsReport  (Phase 8 — Ops)

Usage:
    from core.schemas.artifacts import (
        SpecJSON, DesignDoc, CodeArtifact, ReviewReport,
        TestReport, BuildReport, DeploymentReport, OpsReport,
        AgentPhase, Severity, DeploymentStrategy,
    )
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


# ─────────────────────────────────────────────────────────────────────────────
# Shared enums — used across multiple schemas
# ─────────────────────────────────────────────────────────────────────────────

class AgentPhase(int, Enum):
    """Maps each schema to its agent phase number."""
    PRD_INGESTION       = 1
    ARCHITECTURE_DESIGN = 2
    CODE_GENERATION     = 3
    CODE_REVIEW         = 4
    TEST_EXECUTION      = 5
    CICD_ORCHESTRATION  = 6
    DEPLOYMENT          = 7
    OPS_MAINTENANCE     = 8


class Severity(str, Enum):
    """Issue severity levels used by review and ops agents."""
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


class Priority(str, Enum):
    """Requirement and task priority levels."""
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"
    MUST   = "must"  # non-negotiable / MVP requirement


class Status(str, Enum):
    """General pipeline status values."""
    PENDING    = "pending"
    IN_PROGRESS = "in_progress"
    PASSED     = "passed"
    FAILED     = "failed"
    SKIPPED    = "skipped"
    ESCALATED  = "escalated"  # routed to human gate


class DeploymentStrategy(str, Enum):
    BLUE_GREEN = "blue_green"
    CANARY     = "canary"
    ROLLING    = "rolling"
    RECREATE   = "recreate"


class TechStackLayer(str, Enum):
    FRONTEND   = "frontend"
    BACKEND    = "backend"
    DATABASE   = "database"
    INFRA      = "infra"
    AUTH       = "auth"
    MESSAGING  = "messaging"
    MONITORING = "monitoring"
    TESTING    = "testing"


# ─────────────────────────────────────────────────────────────────────────────
# Base class — every artifact inherits this
# ─────────────────────────────────────────────────────────────────────────────

class BaseArtifact(BaseModel):
    """
    Common metadata carried by every artifact through the pipeline.
    Agents must not modify fields from previous phases — only append.
    """
    artifact_id:  UUID     = Field(default_factory=uuid4, description="Unique artifact identifier")
    run_id:       UUID     = Field(description="Pipeline run this artifact belongs to")
    project_id:   str      = Field(description="Project identifier (slug or UUID)")
    phase:        AgentPhase = Field(description="Which agent produced this artifact")
    produced_at:  datetime = Field(default_factory=datetime.utcnow)
    confidence:   float    = Field(
        ge=0.0, le=1.0,
        description="Agent confidence in this output (0.0–1.0). "
                    "Below settings.sdlc_confidence_threshold triggers human gate."
    )
    retry_count:  int      = Field(default=0, ge=0, le=3, description="Number of retries before this output")
    agent_model:  str      = Field(description="Ollama model tag that produced this artifact")
    notes:        str      = Field(default="", description="Free-text agent notes or warnings")

    model_config = {"frozen": False, "populate_by_name": True}

    # 🔧 ADD THIS VALIDATOR TO FIX LLM CONFIDENCE SCALE ISSUES
    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, v: Any) -> float:
        """Auto-fix LLM returning 90 instead of 0.9"""
        if isinstance(v, (int, float)):
            if v > 1.0:
                return float(v) / 100.0
            return float(v)
        return 0.8  # Safe default

# ─────────────────────────────────────────────────────────────────────────────
# Shared sub-models
# ─────────────────────────────────────────────────────────────────────────────

class Requirement(BaseModel):
    """A single extracted requirement from the PRD."""
    id:          str      = Field(description="Stable requirement ID, e.g. REQ-001")
    title:       str      = Field(min_length=3, max_length=200)
    description: str      = Field(min_length=10)
    priority:    Priority = Field(default=Priority.MEDIUM)
    category:    str      = Field(description="functional | non_functional | constraint | edge_case")
    acceptance_criteria: list[str] = Field(default_factory=list, min_length=1)
    open_questions:      list[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def id_format(cls, v: str) -> str:
        if not v.startswith("REQ-"):
            raise ValueError("Requirement ID must start with 'REQ-'")
        return v


class DataModel(BaseModel):
    """A single entity in the data model / ERD."""
    entity_name: str       = Field(description="Table / collection name, PascalCase")
    fields:      list[str] = Field(description="Field definitions, e.g. ['id UUID PK', 'email TEXT UNIQUE']")
    relations:   list[str] = Field(default_factory=list, description="e.g. ['User has_many Post']")


class APIEndpoint(BaseModel):
    """A single API endpoint in the OpenAPI contract."""
    method:      str  = Field(description="HTTP method: GET | POST | PUT | PATCH | DELETE")
    path:        str  = Field(description="URL path, e.g. /api/v1/users/{id}")
    summary:     str
    request_body:  dict[str, Any] | None = Field(default=None, description="JSON Schema for request body")
    response_200:  dict[str, Any]        = Field(description="JSON Schema for success response")
    auth_required: bool = Field(default=True)

    @field_validator("method")
    @classmethod
    def valid_method(cls, v: str) -> str:
        allowed = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
        if v.upper() not in allowed:
            raise ValueError(f"HTTP method must be one of {allowed}")
        return v.upper()


class TechChoice(BaseModel):
    """A single technology selection with justification."""
    layer:       TechStackLayer
    technology:  str  = Field(description="e.g. 'FastAPI', 'PostgreSQL', 'Next.js 15'")
    version:     str  = Field(default="latest", description="Pinned version or 'latest'")
    rationale:   str  = Field(description="Why this was chosen for this project")


class SecurityFinding(BaseModel):
    """A single security or quality issue found during code review."""
    finding_id:  str      = Field(description="e.g. SEC-001, QUAL-005")
    severity:    Severity
    category:    str      = Field(description="e.g. sqli, xss, hardcoded_secret, complexity, style")
    file_path:   str      = Field(description="Relative path to affected file")
    line_start:  int | None = None
    line_end:    int | None = None
    description: str
    remediation: str      = Field(description="Specific fix recommendation")
    auto_fixed:  bool     = Field(default=False, description="True if the agent auto-applied a fix")
    cwe_id:      str | None = Field(default=None, description="CWE identifier if applicable, e.g. CWE-89")

    @field_validator("finding_id")
    @classmethod
    def id_format(cls, v: str) -> str:
        if not any(v.startswith(p) for p in ("SEC-", "QUAL-", "VULN-", "DEP-")):
            raise ValueError("finding_id must start with SEC-, QUAL-, VULN-, or DEP-")
        return v


class TestCase(BaseModel):
    """A single test case result."""
    test_id:    str
    name:       str
    file_path:  str
    status:     Status
    duration_ms: float = Field(ge=0.0)
    error_message: str | None = None
    is_flaky:   bool = Field(default=False)


class HealthCheck(BaseModel):
    """A single post-deployment health check result."""
    name:       str
    endpoint:   str
    status_code: int
    passed:     bool
    response_ms: float
    checked_at: datetime = Field(default_factory=datetime.utcnow)


class ProductionAlert(BaseModel):
    """A single production alert triaged by the Ops agent."""
    alert_id:    str
    source:      str  = Field(description="e.g. 'prometheus', 'grafana', 'pagerduty'")
    severity:    Severity
    title:       str
    description: str
    fired_at:    datetime
    resolved:    bool = False
    root_cause:  str | None = None
    github_issue_url: str | None = None


class ProposedPatch(BaseModel):
    """A code patch proposed by the Ops agent for a production bug."""
    patch_id:    str
    file_path:   str
    description: str
    diff:        str  = Field(description="Unified diff format patch")
    confidence:  float = Field(ge=0.0, le=1.0)
    risk_level:  Severity
    rollback_plan: str


# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA 1 — SpecJSON  (Phase 1: PRD Ingestion Agent)
# ─────────────────────────────────────────────────────────────────────────────

class SpecJSON(BaseArtifact):
    """
    Output of the PRD Ingestion Agent.
    Structured, validated requirements extracted from raw PRD input.
    Input to: Architecture Design Agent (Phase 2).
    """
    phase: AgentPhase = AgentPhase.PRD_INGESTION

    # Core requirements
    project_name:        str  = Field(min_length=1, max_length=100)
    project_description: str  = Field(min_length=20)
    requirements:        list[Requirement] = Field(min_length=1)

    # Derived analysis
    tech_constraints:    list[str] = Field(
        default_factory=list,
        description="Explicit tech constraints from PRD, e.g. 'must use PostgreSQL', 'Python 3.11+'"
    )
    out_of_scope:        list[str] = Field(
        default_factory=list,
        description="Explicitly out-of-scope items identified from PRD"
    )
    open_questions:      list[str] = Field(
        default_factory=list,
        description="Ambiguities that need clarification before architecture design"
    )
    estimated_complexity: str = Field(
        description="low | medium | high | very_high — agent's estimate of implementation complexity"
    )

    # Counts for quick inspection
    @property
    def must_have_count(self) -> int:
        return sum(1 for r in self.requirements if r.priority == Priority.MUST)

    @property
    def functional_count(self) -> int:
        return sum(1 for r in self.requirements if r.category == "functional")

    # 🔧 ADD THESE TWO VALIDATORS TO FIX LLM HALLUCINATIONS

    @field_validator("estimated_complexity", mode="before")
    @classmethod
    def fix_complexity(cls, v: Any) -> str:
        """Auto-fix LLM returning invalid enum values like ':'"""
        valid = {"low", "medium", "high", "very_high"}
        if not isinstance(v, str) or v.lower() not in valid:
            return "medium"  # Safe default fallback
        return v.lower()

    @field_validator("requirements", mode="before")
    @classmethod
    def fix_requirement_ids(cls, v: Any) -> list[Any]:
        """Auto-fix LLM putting descriptions in the 'id' field instead of REQ-001"""
        if isinstance(v, list):
            for i, req in enumerate(v):
                if isinstance(req, dict):
                    req_id = req.get("id", "")
                    # If it doesn't start with REQ-, auto-generate a valid ID
                    if not isinstance(req_id, str) or not req_id.startswith("REQ-"):
                        req["id"] = f"REQ-{i+1:03d}"
        return v

    @field_validator("estimated_complexity")
    @classmethod
    def valid_complexity(cls, v: str) -> str:
        if v not in ("low", "medium", "high", "very_high"):
            raise ValueError("estimated_complexity must be low | medium | high | very_high")
        return v

# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA 2 — DesignDoc  (Phase 2: Architecture Design Agent)
# ─────────────────────────────────────────────────────────────────────────────

class DesignDoc(BaseArtifact):
    """
    Output of the Architecture Design Agent.
    Complete system design derived from SpecJSON.
    Input to: Code Generation Agent (Phase 3).
    Human gate: mandatory approval before code generation begins.
    """
    phase: AgentPhase = AgentPhase.ARCHITECTURE_DESIGN

    # Lineage
    spec_artifact_id: UUID = Field(description="artifact_id of the SpecJSON that produced this")

    # Architecture decisions
    architecture_style: str = Field(
        description="e.g. 'monolith', 'microservices', 'modular_monolith', 'serverless', 'event_driven'"
    )
    architecture_rationale: str = Field(description="Why this style was chosen for the project")

    # Tech stack
    tech_stack: list[TechChoice] = Field(min_length=1)

    # Data model
    data_model: list[DataModel] = Field(
        min_length=1,
        description="All entities / tables with fields and relations (ERD in structured form)"
    )

    # API contract
    api_endpoints: list[APIEndpoint] = Field(
        default_factory=list,
        description="OpenAPI-style endpoint definitions. Empty for non-API projects."
    )

    # Implementation guidance
    folder_structure: dict[str, Any] = Field(
        description="Nested dict representing the recommended project folder layout"
    )
    implementation_order: list[str] = Field(
        description="Ordered list of modules to implement, e.g. ['db_models', 'auth', 'api_layer', 'ui']"
    )
    infra_blueprint: str = Field(
        description="Plain-text infrastructure description: services, ports, dependencies"
    )

    # Security & non-functional
    security_considerations: list[str] = Field(default_factory=list)
    performance_targets:     dict[str, str] = Field(
        default_factory=dict,
        description="e.g. {'api_p99_latency': '<200ms', 'db_query_max': '<50ms'}"
    )

    @model_validator(mode="after")
    def validate_tech_stack_coverage(self) -> "DesignDoc":
        """Ensure at minimum backend and database layers are specified."""
        layers = {tc.layer for tc in self.tech_stack}
        required = {TechStackLayer.BACKEND, TechStackLayer.DATABASE}
        missing = required - layers
        if missing:
            raise ValueError(f"tech_stack must include layers: {[l.value for l in missing]}")
        return self


# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA 3 — CodeArtifact  (Phase 3: Code Generation Agent)
# ─────────────────────────────────────────────────────────────────────────────

class GeneratedFile(BaseModel):
    """A single generated or modified source file."""
    path:        str  = Field(description="Relative path from project root, e.g. 'src/api/routes/users.py'")
    language:    str  = Field(description="Programming language, e.g. 'python', 'typescript', 'sql'")
    content_hash: str = Field(description="SHA-256 hash of file content for integrity verification")
    lines_of_code: int = Field(ge=0)
    is_new_file:  bool = Field(default=True, description="False if this modifies an existing file")
    module:       str  = Field(description="Which module this belongs to, e.g. 'auth', 'api', 'db', 'ui'")


class CodeArtifact(BaseArtifact):
    """
    Output of the Code Generation Agent.
    Full implementation committed to a feature branch.
    Input to: Code Review Agent (Phase 4).
    """
    phase: AgentPhase = AgentPhase.CODE_GENERATION

    # Lineage
    design_artifact_id: UUID = Field(description="artifact_id of the DesignDoc that produced this")

    # Git reference
    git_branch:   str = Field(description="Feature branch name, e.g. 'feature/sdlc-run-abc123'")
    git_commit:   str = Field(description="Full commit SHA of the generated code")
    repository:   str = Field(description="Repository URL or local path")

    # What was generated
    generated_files: list[GeneratedFile] = Field(min_length=1)
    modules_completed: list[str] = Field(
        description="Modules fully implemented in this run, e.g. ['db_models', 'auth_api']"
    )
    modules_skipped: list[str] = Field(
        default_factory=list,
        description="Modules deferred due to complexity or dependency — each must have a note"
    )
    skip_reasons: dict[str, str] = Field(
        default_factory=dict,
        description="module_name → reason for skipping"
    )

    # Quality signals
    has_tests:        bool = Field(description="True if test files were generated alongside implementation")
    has_migrations:   bool = Field(description="True if DB migration files were generated")
    has_dockerfile:   bool = Field(default=False)
    dependency_changes: list[str] = Field(
        default_factory=list,
        description="New packages added, e.g. ['fastapi==0.115.0', 'sqlalchemy==2.0.0']"
    )

    @property
    def total_lines(self) -> int:
        return sum(f.lines_of_code for f in self.generated_files)

    @property
    def file_count(self) -> int:
        return len(self.generated_files)

    @model_validator(mode="after")
    def validate_skip_reasons(self) -> "CodeArtifact":
        for module in self.modules_skipped:
            if module not in self.skip_reasons:
                raise ValueError(f"Module '{module}' is in modules_skipped but has no entry in skip_reasons")
        return self


# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA 4 — ReviewReport  (Phase 4: Code Review Agent)
# ─────────────────────────────────────────────────────────────────────────────

class ReviewReport(BaseArtifact):
    """
    Output of the Code Review Agent.
    Comprehensive static analysis, security scan, and quality assessment.
    Input to: Test Execution Agent (Phase 5).
    Human gate: triggered if any HIGH or CRITICAL severity finding exists.
    """
    phase: AgentPhase = AgentPhase.CODE_REVIEW

    # Lineage
    code_artifact_id: UUID = Field(description="artifact_id of the CodeArtifact that was reviewed")

    # Tool results
    semgrep_ran:  bool = Field(description="True if Semgrep SAST scan was executed")
    trivy_ran:    bool = Field(description="True if Trivy dependency/container scan was executed")
    linter_ran:   bool = Field(description="True if language-specific linter (ruff/eslint) ran")

    # Findings
    findings: list[SecurityFinding] = Field(default_factory=list)

    # Architecture compliance
    architecture_compliant: bool = Field(
        description="True if generated code matches the DesignDoc architecture"
    )
    architecture_deviations: list[str] = Field(
        default_factory=list,
        description="List of deviations from DesignDoc if not compliant"
    )

    # Scores (0–10)
    security_score:   float = Field(ge=0.0, le=10.0, description="0 = critical vulnerabilities, 10 = clean")
    quality_score:    float = Field(ge=0.0, le=10.0, description="Code quality: complexity, style, coverage readiness")
    compliance_score: float = Field(ge=0.0, le=10.0, description="Architecture compliance score")

    # Auto-fix patches applied during review
    auto_fix_patches: list[str] = Field(
        default_factory=list,
        description="Unified diff patches already applied by the agent for LOW severity issues"
    )

    # Gate decision
    requires_human_gate: bool = Field(
        description="True if any HIGH/CRITICAL finding exists — triggers Gate 2"
    )
    gate_reason: str = Field(
        default="",
        description="Human-readable reason for triggering the gate"
    )

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.HIGH)

    @model_validator(mode="after")
    def sync_gate_flag(self) -> "ReviewReport":
        """Auto-set requires_human_gate based on findings severity."""
        has_blocker = any(
            f.severity in (Severity.HIGH, Severity.CRITICAL)
            for f in self.findings
            if not f.auto_fixed
        )
        if has_blocker and not self.requires_human_gate:
            self.requires_human_gate = True
            self.gate_reason = (
                f"HIGH/CRITICAL findings require human approval: "
                f"{self.critical_count} critical, {self.high_count} high"
            )
        return self


# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA 5 — TestReport  (Phase 5: Test Execution Agent)
# ─────────────────────────────────────────────────────────────────────────────

class TestReport(BaseArtifact):
    """
    Output of the Test Execution Agent.
    Full test suite results from isolated Docker sandbox.
    Input to: CI/CD Orchestration Agent (Phase 6).
    Self-correction: if tests fail, routes back to Code Generation (Phase 3) with retry context.
    """
    phase: AgentPhase = AgentPhase.TEST_EXECUTION

    # Lineage
    code_artifact_id:   UUID = Field(description="CodeArtifact that was tested")
    review_artifact_id: UUID = Field(description="ReviewReport that preceded this test run")

    # Execution environment
    sandbox_image:  str  = Field(description="Docker image used for sandbox execution")
    sandbox_isolated: bool = Field(description="True if --network none was enforced")

    # Test results
    test_cases:    list[TestCase] = Field(default_factory=list)
    total_tests:   int  = Field(ge=0)
    passed_tests:  int  = Field(ge=0)
    failed_tests:  int  = Field(ge=0)
    skipped_tests: int  = Field(ge=0)
    flaky_tests:   int  = Field(ge=0, description="Tests that failed on first run but passed on retry")

    # Coverage
    coverage_percent:    float = Field(ge=0.0, le=100.0)
    coverage_target:     float = Field(default=80.0, description="Minimum required coverage %")
    coverage_met:        bool  = Field(description="True if coverage_percent >= coverage_target")
    uncovered_modules:   list[str] = Field(default_factory=list)

    # Retry context (populated if routing back to Phase 3)
    needs_code_retry:    bool  = Field(default=False)
    retry_instructions:  str   = Field(
        default="",
        description="Structured failure context fed back to Code Generation agent on retry"
    )
    failure_summary:     str   = Field(default="", description="Human-readable test failure summary")

    # Timing
    total_duration_ms: float = Field(ge=0.0)

    @property
    def pass_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return round(self.passed_tests / self.total_tests * 100, 2)

    @model_validator(mode="after")
    def validate_counts(self) -> "TestReport":
        derived = self.passed_tests + self.failed_tests + self.skipped_tests
        if self.total_tests != derived:
            raise ValueError(
                f"total_tests ({self.total_tests}) must equal "
                f"passed + failed + skipped ({derived})"
            )
        return self


# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA 6 — BuildReport  (Phase 6: CI/CD Orchestration Agent)
# ─────────────────────────────────────────────────────────────────────────────

class BuildReport(BaseArtifact):
    """
    Output of the CI/CD Orchestration Agent.
    GitHub Actions build result and environment promotion decision.
    Input to: Deployment Agent (Phase 7).
    Human gate: required before production promotion.
    """
    phase: AgentPhase = AgentPhase.CICD_ORCHESTRATION

    # Lineage
    test_artifact_id: UUID = Field(description="TestReport that triggered this build")

    # GitHub Actions
    workflow_run_id:  str  = Field(description="GitHub Actions workflow run ID")
    workflow_url:     str  = Field(description="URL to the workflow run in GitHub")
    branch:           str
    commit_sha:       str

    # Build result
    build_status:     Status
    build_duration_ms: float = Field(ge=0.0)
    build_logs_summary: str  = Field(description="Key lines from build log (errors, warnings)")

    # Docker image
    docker_image_tag: str | None = Field(default=None, description="Built image tag if applicable")
    docker_image_size_mb: float | None = None

    # Environment promotion
    target_environment:  str  = Field(description="'staging' or 'production'")
    promotion_approved:  bool = Field(
        description="True if this build can proceed to deployment. "
                    "Always False for production until Gate 3 is passed."
    )
    promotion_blocked_reason: str = Field(
        default="",
        description="Why promotion was blocked, if applicable"
    )

    # Dependency audit
    new_vulnerabilities_found: bool = Field(default=False)
    vulnerability_summary:     str  = Field(default="")

    @model_validator(mode="after")
    def production_requires_gate(self) -> "BuildReport":
        """Production promotions must not be auto-approved — Gate 3 handles that."""
        if self.target_environment == "production" and self.promotion_approved:
            raise ValueError(
                "BuildReport cannot set promotion_approved=True for production. "
                "Gate 3 (human approval) must set this via the gate decision record."
            )
        return self


# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA 7 — DeploymentReport  (Phase 7: Deployment Agent)
# ─────────────────────────────────────────────────────────────────────────────

class DeploymentReport(BaseArtifact):
    """
    Output of the Deployment Agent.
    Infrastructure provisioning result, deployment outcome, and health status.
    Input to: Ops & Maintenance Agent (Phase 8).
    Human gate: Gate 3 (production) must be passed before this agent runs.
    """
    phase: AgentPhase = AgentPhase.DEPLOYMENT

    # Lineage
    build_artifact_id: UUID = Field(description="BuildReport that triggered this deployment")

    # Deployment config
    environment:          str                = Field(description="'staging' or 'production'")
    deployment_strategy:  DeploymentStrategy
    docker_image:         str                = Field(description="Full image reference that was deployed")
    pulumi_stack:         str                = Field(description="Pulumi stack name, e.g. 'sdlc-agent/staging'")

    # Outcome
    deployment_status:    Status
    deployed_at:          datetime = Field(default_factory=datetime.utcnow)
    deployment_url:       str | None = Field(default=None, description="Live URL if deployment succeeded")

    # Health checks (run for 5 min post-deploy)
    health_checks:        list[HealthCheck] = Field(default_factory=list)
    health_check_passed:  bool
    monitoring_window_minutes: int = Field(default=5, description="How long post-deploy monitoring ran")

    # Rollback
    rollback_triggered:   bool = Field(default=False)
    rollback_reason:      str  = Field(default="")
    previous_version:     str | None = Field(default=None, description="Version rolled back to if triggered")

    # IaC
    pulumi_preview:       str = Field(description="pulumi preview output — what infrastructure changed")
    resources_created:    list[str] = Field(default_factory=list)
    resources_updated:    list[str] = Field(default_factory=list)
    resources_destroyed:  list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def rollback_requires_reason(self) -> "DeploymentReport":
        if self.rollback_triggered and not self.rollback_reason:
            raise ValueError("rollback_reason must be set when rollback_triggered is True")
        return self


# ─────────────────────────────────────────────────────────────────────────────
# SCHEMA 8 — OpsReport  (Phase 8: Ops & Maintenance Agent)
# ─────────────────────────────────────────────────────────────────────────────

class OpsReport(BaseArtifact):
    """
    Output of the Ops & Maintenance Agent.
    Continuous monitoring report: alert triage, issue creation, patch proposals.
    This agent runs continuously post-deployment — each report covers one monitoring cycle.
    Human gate: Gate 4 required before any proposed patch is applied to production.
    """
    phase: AgentPhase = AgentPhase.OPS_MAINTENANCE

    # Lineage
    deployment_artifact_id: UUID = Field(description="DeploymentReport this ops cycle monitors")

    # Monitoring window
    monitoring_start: datetime
    monitoring_end:   datetime
    environment:      str = Field(description="'staging' or 'production'")

    # Prometheus metrics snapshot
    error_rate_percent:  float = Field(ge=0.0, description="HTTP error rate during monitoring window")
    p99_latency_ms:      float = Field(ge=0.0)
    cpu_utilization:     float = Field(ge=0.0, le=100.0)
    memory_utilization:  float = Field(ge=0.0, le=100.0)
    metrics_healthy:     bool  = Field(description="True if all metrics within defined thresholds")

    # Alerts
    alerts_fired:     list[ProductionAlert] = Field(default_factory=list)
    alerts_resolved:  int = Field(ge=0)
    alerts_pending:   int = Field(ge=0)

    # GitHub issues
    issues_created:   list[str] = Field(
        default_factory=list,
        description="GitHub issue URLs created by the agent for production bugs"
    )

    # Patch proposals
    proposed_patches: list[ProposedPatch] = Field(
        default_factory=list,
        description="Code patches proposed for production bugs. Require Gate 4 human approval."
    )
    patches_pending_approval: int = Field(ge=0)

    # Memory write-back
    memory_updates_written: int = Field(
        ge=0,
        description="Number of learnings written back to Qdrant for future pipeline runs"
    )
    memory_update_summary: str = Field(
        default="",
        description="What patterns/lessons were stored in agent memory"
    )

    @model_validator(mode="after")
    def sync_patch_count(self) -> "OpsReport":
        self.patches_pending_approval = len(self.proposed_patches)
        return self

    @model_validator(mode="after")
    def sync_alert_counts(self) -> "OpsReport":
        self.alerts_pending = sum(1 for a in self.alerts_fired if not a.resolved)
        self.alerts_resolved = sum(1 for a in self.alerts_fired if a.resolved)
        return self


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline state type — used by LangGraph state machine (Step 7)
# ─────────────────────────────────────────────────────────────────────────────

class PipelineState(BaseModel):
    """
    The full state object carried through the LangGraph graph.
    Each node reads what it needs and writes its output artifact.
    Checkpointed to PostgreSQL at every node transition.
    """
    run_id:      UUID
    project_id:  str
    mode:        str = Field(description="Execution mode, e.g. 'full_pipeline', 'code_review_only'")
    prd_input:   str = Field(default="", description="Raw PRD text or file content")

    # Artifacts — populated as pipeline progresses
    spec:        SpecJSON | None        = None
    design:      DesignDoc | None       = None
    code:        CodeArtifact | None    = None
    review:      ReviewReport | None    = None
    test:        TestReport | None      = None
    build:       BuildReport | None     = None
    deployment:  DeploymentReport | None = None
    ops:         OpsReport | None       = None

    # Control flow
    current_phase:    AgentPhase | None = None
    retry_count:      int = Field(default=0, ge=0)
    error_message:    str = Field(default="")
    awaiting_human:   bool = Field(default=False)
    human_gate_name:  str  = Field(default="")
    gate_approved:    bool | None = None  # None = not yet decided
    is_complete:      bool = Field(default=False)

    model_config = {"frozen": False}


# ─────────────────────────────────────────────────────────────────────────────
# Exports
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    # Enums
    "AgentPhase", "Severity", "Priority", "Status",
    "DeploymentStrategy", "TechStackLayer",
    # Sub-models
    "BaseArtifact", "Requirement", "DataModel", "APIEndpoint",
    "TechChoice", "SecurityFinding", "TestCase", "HealthCheck",
    "ProductionAlert", "ProposedPatch", "GeneratedFile",
    # Artifact schemas (the 8)
    "SpecJSON", "DesignDoc", "CodeArtifact", "ReviewReport",
    "TestReport", "BuildReport", "DeploymentReport", "OpsReport",
    # Pipeline state
    "PipelineState",
]