"""
Phase 5: Test Execution Agent

Analyzes the CodeArtifact and ReviewReport, then simulates test execution.
Generates a TestReport with coverage metrics, pass/fail status,
and retry instructions if tests fail.
"""

import logging
from typing import Dict, Any, Union

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, ConfigDict

from core.agents.base import BaseAgent
from core.llm.client import get_code_model
from core.schemas.artifacts import TestReport
from config.settings import settings

logger = logging.getLogger(__name__)

class TestExecutionInput(BaseModel):
    """Input schema for the Test Execution Agent."""
    code_artifact: Dict[str, Any] = Field(description="The structured CodeArtifact from Phase 3")
    review_report: Dict[str, Any] = Field(description="The ReviewReport from Phase 4")
    run_id: str = Field(description="The current pipeline run ID (UUID string)")
    project_id: str = Field(description="The project identifier")
    code_artifact_id: str = Field(description="The artifact_id of the CodeArtifact (UUID string)")
    review_artifact_id: str = Field(description="The artifact_id of the ReviewReport (UUID string)")


class TestExecutionAgent(BaseAgent):
    """
    Agent responsible for Phase 5: Test Execution.
    """
    
    model_config = ConfigDict(extra="allow")

    def __init__(self):
        system_prompt = """You are an expert QA Engineer and Test Automation Specialist.
Your task is to analyze the generated CodeArtifact and ReviewReport, then simulate test execution.

You must output a complete TestReport. CRITICAL FORMATTING RULES:
1. You MUST copy `run_id`, `project_id`, `code_artifact_id`, and `review_artifact_id` exactly as provided.
2. You MUST set `phase` to 5 (or "TEST_EXECUTION").
3. You MUST set `agent_model` to "qwen2.5-coder:3b".
4. Set `sandbox_image` to "python:3.11-slim" (or appropriate for the tech stack).
5. Set `sandbox_isolated` to true (network isolation).
6. Generate 5 to 10 realistic `TestCase` items based on the generated files.
   - `test_id`: e.g., "TC-001"
   - `name`: Descriptive test name
   - `file_path`: Path to the test file
   - `status`: "passed", "failed", or "skipped"
   - `duration_ms`: Realistic duration (10-500ms)
   - `error_message`: If failed, provide a realistic error message
   - `is_flaky`: false (unless simulating flaky behavior)
7. Calculate `total_tests`, `passed_tests`, `failed_tests`, `skipped_tests`, `flaky_tests` correctly.
8. Set `coverage_percent` between 60.0 and 95.0 (realistic range).
9. Set `coverage_target` to 80.0.
10. Set `coverage_met` to true if `coverage_percent` >= `coverage_target`.
11. If `failed_tests` > 0 OR `coverage_met` is false:
    - Set `needs_code_retry` to true
    - Set `retry_instructions` to a detailed explanation of what needs to be fixed
    - Set `failure_summary` to a concise summary
12. If all tests pass and coverage is met:
    - Set `needs_code_retry` to false
    - Leave `retry_instructions` and `failure_summary` empty
13. Set `total_duration_ms` to a realistic value (sum of test durations + overhead).

DECISION LOGIC:
- If the ReviewReport found HIGH severity issues, increase the likelihood of test failures.
- If the CodeArtifact has many files, generate more test cases.
- Randomly decide if tests should fail (30% chance) to test the retry loop.
- If tests fail, make `retry_instructions` very specific so the Code Generation agent can fix it.

Be precise, technical, and strictly adhere to the JSON schema."""

        super().__init__(
            name="test_execution_agent",
            input_schema=TestExecutionInput,
            output_schema=TestReport,
            model_name=settings.sdlc_code_model,
            system_prompt=system_prompt
        )
        
        base_llm = get_code_model(temperature=0.3)
        self.llm = base_llm.with_structured_output(TestReport)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Here is the CodeArtifact from Phase 3:\n{code_artifact}\n\nHere is the ReviewReport from Phase 4:\n{review_report}\n\nMetadata to copy:\n- run_id: {run_id}\n- project_id: {project_id}\n- code_artifact_id: {code_artifact_id}\n- review_artifact_id: {review_artifact_id}"),
        ])
        
        self.chain = self.prompt | self.llm

    async def arun(self, input_data: Union[Dict[str, Any], TestExecutionInput]) -> TestReport:
        if isinstance(input_data, dict):
            input_data = TestExecutionInput(**input_data)
            
        logger.info("Running Test Execution Agent...")
        
        result = await self.chain.ainvoke({
            "code_artifact": input_data.code_artifact,
            "review_report": input_data.review_report,
            "run_id": input_data.run_id,
            "project_id": input_data.project_id,
            "code_artifact_id": input_data.code_artifact_id,
            "review_artifact_id": input_data.review_artifact_id,
        })
        
        if not hasattr(result, 'confidence'):
            result.confidence = 0.80
            
        return result