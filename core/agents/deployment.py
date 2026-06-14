"""
Phase 7: Deployment Agent

Takes the BuildReport, simulates an IaC deployment (Pulumi/Helm),
runs post-deployment health checks, and produces a structured DeploymentReport.
"""

import logging
from typing import Dict, Any, Union

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, ConfigDict

from core.agents.base import BaseAgent
from core.llm.client import get_code_model
from core.schemas.artifacts import DeploymentReport, Status, DeploymentStrategy
from config.settings import settings

logger = logging.getLogger(__name__)

class DeploymentInput(BaseModel):
    """Input schema for the Deployment Agent."""
    build_report: Dict[str, Any] = Field(description="The structured BuildReport from Phase 6")
    run_id: str = Field(description="The current pipeline run ID (UUID string)")
    project_id: str = Field(description="The project identifier")
    build_artifact_id: str = Field(description="The artifact_id of the BuildReport (UUID string)")


class DeploymentAgent(BaseAgent):
    """
    Agent responsible for Phase 7: Deployment.
    """
    
    model_config = ConfigDict(extra="allow")

    def __init__(self):
        system_prompt = """You are an expert Site Reliability Engineer (SRE) and DevOps Specialist.
Your task is to simulate the deployment of the built artifact to the target environment.

You must output a complete DeploymentReport. CRITICAL FORMATTING RULES:
1. You MUST copy `run_id`, `project_id`, and `build_artifact_id` exactly as provided.
2. You MUST set `phase` to 7 (or "DEPLOYMENT").
3. You MUST set `agent_model` to "qwen2.5-coder:3b".
4. Copy `environment` from the BuildReport's `target_environment` (e.g., "staging" or "production").
5. Set `deployment_strategy` to one of: "blue_green", "canary", "rolling", or "recreate".
6. Set `docker_image` to the `docker_image_tag` from the BuildReport.
7. Set `pulumi_stack` to "sdlc-agent/{{environment}}".
8. Set `deployment_status` to "PASSED" (or "FAILED" if simulating a rollback).
9. Generate a realistic `pulumi_preview` string (e.g., "Resources: +3 to create, ~0 to update, 0 to delete").
10. List 2-3 items in `resources_created` (e.g., ["aws_ecs_service:main", "aws_alb:frontend"]).
11. Generate 2 realistic `HealthCheck` items:
    - `name`: e.g., "API Health"
    - `endpoint`: e.g., "/health"
    - `status_code`: 200
    - `passed`: true
    - `response_ms`: realistic float (e.g., 45.5)
12. Set `health_check_passed` to true if all health checks passed.
13. Set `rollback_triggered` to false (unless simulating a failure).

Be precise, technical, and strictly adhere to the JSON schema."""

        super().__init__(
            name="deployment_agent",
            input_schema=DeploymentInput,
            output_schema=DeploymentReport,
            model_name=settings.sdlc_code_model,
            system_prompt=system_prompt
        )
        
        base_llm = get_code_model(temperature=0.1) # Low temp for deterministic IaC logic
        self.llm = base_llm.with_structured_output(DeploymentReport)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Here is the BuildReport from Phase 6:\n{build_report}\n\nMetadata to copy:\n- run_id: {run_id}\n- project_id: {project_id}\n- build_artifact_id: {build_artifact_id}"),
        ])
        
        self.chain = self.prompt | self.llm

    async def arun(self, input_data: Union[Dict[str, Any], DeploymentInput]) -> DeploymentReport:
        if isinstance(input_data, dict):
            input_data = DeploymentInput(**input_data)
            
        logger.info("Running Deployment Agent...")
        
        result = await self.chain.ainvoke({
            "build_report": input_data.build_report,
            "run_id": input_data.run_id,
            "project_id": input_data.project_id,
            "build_artifact_id": input_data.build_artifact_id,
        })
        
        if not hasattr(result, 'confidence'):
            result.confidence = 0.90
            
        return result