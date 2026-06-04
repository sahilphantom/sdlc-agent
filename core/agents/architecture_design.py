"""
Phase 2: Architecture Design Agent

Reads the SpecJSON and produces a complete system design (DesignDoc).
Decides architecture style, selects tech stack, designs data model (ERD),
defines API contracts, and produces an infrastructure blueprint.
"""

import logging
from typing import Dict, Any

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, ConfigDict

from core.agents.base import BaseAgent
from core.llm.client import get_reasoning_model
from core.schemas.artifacts import DesignDoc, AgentPhase
from config.settings import settings

logger = logging.getLogger(__name__)

class ArchitectureDesignInput(BaseModel):
    """Input schema for the Architecture Design Agent."""
    spec_json: Dict[str, Any] = Field(description="The structured SpecJSON from Phase 1")
    run_id: str = Field(description="The current pipeline run ID (UUID string)")
    project_id: str = Field(description="The project identifier")
    spec_artifact_id: str = Field(description="The artifact_id of the SpecJSON (UUID string)")


class ArchitectureDesignAgent(BaseAgent):
    """
    Agent responsible for Phase 2: Architecture Design.
    """
    
    model_config = ConfigDict(extra="allow")

    def __init__(self):
        system_prompt = """You are an expert Software Architect and Staff Engineer.
Your task is to design a robust, scalable system based on the provided SpecJSON.

You must output a complete DesignDoc artifact. CRITICAL FORMATTING RULES:
1. You MUST copy the `run_id`, `project_id`, and `spec_artifact_id` exactly as provided in the input.
2. You MUST set `phase` to 2 (or "ARCHITECTURE_DESIGN").
3. You MUST set `agent_model` to "llama3.2:3b".
4. For `tech_stack`, you MUST provide at least a BACKEND and DATABASE layer. Use valid TechStackLayer enums: 'frontend', 'backend', 'database', 'infra', 'auth', 'messaging', 'monitoring', 'testing'.
5. For `data_model`, provide entity names in PascalCase and clear field definitions.
6. For `api_endpoints`, use valid HTTP methods (GET, POST, PUT, PATCH, DELETE) and clear paths.
7. Keep `folder_structure` as a nested dictionary representing the project layout.

Be precise, technical, and aligned with modern best practices. If the SpecJSON is lightweight, make reasonable, industry-standard assumptions."""

        super().__init__(
            name="architecture_design_agent",
            input_schema=ArchitectureDesignInput,
            output_schema=DesignDoc,
            model_name=settings.sdlc_reason_model,
            system_prompt=system_prompt
        )
        
        base_llm = get_reasoning_model(temperature=0.2) # Slightly higher temp for creative design
        self.llm = base_llm.with_structured_output(DesignDoc)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Here is the SpecJSON from Phase 1:\n{spec_json}\n\nMetadata to copy:\n- run_id: {run_id}\n- project_id: {project_id}\n- spec_artifact_id: {spec_artifact_id}"),
        ])
        
        self.chain = self.prompt | self.llm

    async def arun(self, input_data: ArchitectureDesignInput) -> DesignDoc:
        logger.info("Running Architecture Design Agent...")
        
        result = await self.chain.ainvoke({
            "spec_json": input_data.spec_json,
            "run_id": input_data.run_id,
            "project_id": input_data.project_id,
            "spec_artifact_id": input_data.spec_artifact_id,
        })
        
        if not hasattr(result, 'confidence'):
            result.confidence = 0.80
            
        return result