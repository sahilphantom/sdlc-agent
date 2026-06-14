"""
Phase 6: CI/CD Orchestration Agent

Takes the TestReport, simulates a GitHub Actions build, parses logs,
and produces a structured BuildReport with environment promotion decisions.
"""

import logging
from typing import Dict, Any, Union

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, ConfigDict

from core.agents.base import BaseAgent
from core.llm.client import get_code_model
from core.schemas.artifacts import BuildReport, Status
from config.settings import settings

logger = logging.getLogger(__name__)

class CICDOrchestrationInput(BaseModel):
    """Input schema for the CI/CD Orchestration Agent."""
    test_report: Dict[str, Any] = Field(description="The structured TestReport from Phase 5")
    run_id: str = Field(description="The current pipeline run ID (UUID string)")
    project_id: str = Field(description="The project identifier")
    test_artifact_id: str = Field(description="The artifact_id of the TestReport (UUID string)")


class CICDOrchestrationAgent(BaseAgent):
    """
    Agent responsible for Phase 6: CI/CD Orchestration.
    """
    
    model_config = ConfigDict(extra="allow")

    def __init__(self):
        system_prompt = """You are an expert DevOps and CI/CD Engineer.
Your task is to analyze the TestReport and simulate a GitHub Actions build pipeline.

You must output a complete BuildReport. CRITICAL FORMATTING RULES:
1. You MUST copy `run_id`, `project_id`, and `test_artifact_id` exactly as provided.
2. You MUST set `phase` to 6 (or "CICD_ORCHESTRATION").
3. You MUST set `agent_model` to "qwen2.5-coder:3b".
4. Generate a realistic `workflow_run_id` (e.g., "1234567890") and `workflow_url`.
5. Set `branch` to "main" or "feature/..." and `commit_sha` to a 40-char hex string.
6. Set `build_status` to "PASSED" if tests passed, or "FAILED" if tests failed. (Valid: PASSED, FAILED, SKIPPED).
7. Set `build_duration_ms` to a realistic value (e.g., 45000.0 for 45 seconds).
8. Write a concise `build_logs_summary` (e.g., "Build successful. 0 warnings, 0 errors.").
9. Set `docker_image_tag` to "ghcr.io/org/project:latest" and `docker_image_size_mb` to ~150.0.
10. Set `target_environment` to "staging" (for this demo run).
11. CRITICAL: Set `promotion_approved` to FALSE if `target_environment` is "production". For "staging", set it to TRUE.
12. Set `new_vulnerabilities_found` to false and `vulnerability_summary` to "No new vulnerabilities detected by Trivy."

Be precise, technical, and strictly adhere to the JSON schema."""

        super().__init__(
            name="cicd_orchestration_agent",
            input_schema=CICDOrchestrationInput,
            output_schema=BuildReport,
            model_name=settings.sdlc_code_model,
            system_prompt=system_prompt
        )
        
        base_llm = get_code_model(temperature=0.1) # Low temp for deterministic CI/CD logic
        self.llm = base_llm.with_structured_output(BuildReport)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Here is the TestReport from Phase 5:\n{test_report}\n\nMetadata to copy:\n- run_id: {run_id}\n- project_id: {project_id}\n- test_artifact_id: {test_artifact_id}"),
        ])
        
        self.chain = self.prompt | self.llm

    async def arun(self, input_data: Union[Dict[str, Any], CICDOrchestrationInput]) -> BuildReport:
        if isinstance(input_data, dict):
            input_data = CICDOrchestrationInput(**input_data)
            
        logger.info("Running CI/CD Orchestration Agent...")
        
        result = await self.chain.ainvoke({
            "test_report": input_data.test_report,
            "run_id": input_data.run_id,
            "project_id": input_data.project_id,
            "test_artifact_id": input_data.test_artifact_id,
        })
        
        if not hasattr(result, 'confidence'):
            result.confidence = 0.90
            
        return result