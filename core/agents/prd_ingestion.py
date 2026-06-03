"""
Phase 1: PRD Ingestion Agent

Parses raw PRD text and extracts structured requirements, acceptance criteria,
and constraints into a SpecJSON artifact.
"""

import logging
from typing import Dict, Any

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from core.agents.base import BaseAgent
from core.llm.client import get_reasoning_model
from core.schemas.artifacts import SpecJSON
from config.settings import settings

logger = logging.getLogger(__name__)

# Define an input schema to satisfy BaseAgent's input_schema requirement
class PRDInput(BaseModel):
    input_text: str = Field(description="The raw PRD text to process.")


class PRDIngestionAgent(BaseAgent):
    """
    Agent responsible for Phase 1: Ingesting PRD and producing SpecJSON.
    """

    def __init__(self):
        system_prompt = """You are an expert Technical Product Manager. 
Your task is to analyze the provided Product Requirements Document (PRD) or feature description.

You must extract and structure the following:
1. Functional Requirements: What the system must do.
2. Non-Functional Requirements: Performance, security, scalability.
3. Acceptance Criteria: Specific conditions to verify the feature works.
4. Constraints: Technical or business limitations.
5. Edge Cases: Potential failure points or unusual scenarios.

Be precise, concise, and technical. If information is missing, make reasonable assumptions based on standard industry practices but flag them in 'open_questions'."""

        # 🔧 FIX: Pass string literals directly to avoid AttributeError before super().__init__()
        super().__init__(
            name="prd_ingestion_agent",
            input_schema=PRDInput,
            output_schema=SpecJSON,
            model_name=settings.sdlc_reason_model,
            system_prompt=system_prompt
        )
        
        # 1. Initialize LLM with structured output enforcement
        base_llm = get_reasoning_model(temperature=0.1)
        self.llm = base_llm.with_structured_output(SpecJSON)
        
        # 2. Define the System Prompt
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input_text}"),
        ])
        
        # 3. Create the Chain
        self.chain = self.prompt | self.llm

    async def _arun(self, input_data: PRDInput) -> SpecJSON:
        """
        Execute the agent logic.
        """
        input_text = input_data.input_text
        logger.info(f"Running PRD Ingestion on text of length: {len(input_text)}")
        
        # Invoke the chain
        result = await self.chain.ainvoke({"input_text": input_text})
        
        if not hasattr(result, 'confidence'):
             result.confidence = 0.85 
             
        return result