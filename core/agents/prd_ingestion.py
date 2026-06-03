"""
Phase 1: PRD Ingestion Agent

Parses raw PRD text and extracts structured requirements, acceptance criteria,
and constraints into a SpecJSON artifact.
"""

import logging
from typing import Dict, Any, Union

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, ConfigDict

from core.agents.base import BaseAgent
from core.llm.client import get_reasoning_model
from core.schemas.artifacts import SpecJSON
from config.settings import settings

logger = logging.getLogger(__name__)

class PRDInput(BaseModel):
    input_text: str = Field(description="The raw PRD text to process.")


class PRDIngestionAgent(BaseAgent):
    """
    Agent responsible for Phase 1: Ingesting PRD and producing SpecJSON.
    """
    
    model_config = ConfigDict(extra="allow")

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

        super().__init__(
            name="prd_ingestion_agent",
            input_schema=PRDInput,
            output_schema=SpecJSON,
            model_name=settings.sdlc_reason_model,
            system_prompt=system_prompt
        )
        
        base_llm = get_reasoning_model(temperature=0.1)
        self.llm = base_llm.with_structured_output(SpecJSON)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input_text}"),
        ])
        
        self.chain = self.prompt | self.llm

    # 🔧 FIX: Accept Union[dict, PRDInput] and normalize to PRDInput
    async def arun(self, input_data: Union[Dict[str, Any], PRDInput]) -> SpecJSON:
        # Normalize input to PRDInput instance
        if isinstance(input_data, dict):
            input_data = PRDInput(**input_data)
        
        input_text = input_data.input_text
        logger.info(f"Running PRD Ingestion on text of length: {len(input_text)}")
        
        result = await self.chain.ainvoke({"input_text": input_text})
        
        if not hasattr(result, 'confidence'):
             result.confidence = 0.85 
             
        return result