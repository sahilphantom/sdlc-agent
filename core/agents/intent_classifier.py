"""
Intent Classifier Agent

The very first node in the LangGraph orchestrator. 
Reads the user's message and file context, then outputs a typed routing JSON.
"""

import logging
from typing import Dict, Any, Union

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, ConfigDict

from core.agents.base import BaseAgent
from core.llm.client import get_reasoning_model
from core.schemas.routing import IntentRouting, ExecutionMode, InputType
from config.settings import settings

logger = logging.getLogger(__name__)

class IntentClassifierInput(BaseModel):
    user_message: str = Field(description="The user's plain language request")
    has_file: bool = Field(description="True if the user attached a file (ZIP, Git URL, etc.)")
    file_type: str = Field(default="none", description="Type of file attached, e.g., 'zip', 'git_url', 'none'")


class IntentClassifierAgent(BaseAgent):
    """Agent responsible for classifying user intent and routing to the correct subgraph."""
    
    model_config = ConfigDict(extra="allow")

    def __init__(self):
        system_prompt = """You are the Intent Classifier for an Autonomous SDLC Agent System.
Your job is to read the user's request and route it to the correct execution mode.

RULES FOR ROUTING:
1. NO file + "build/create/make" keywords -> FULL_PIPELINE (Agents: 1,2,3,4,5,6,7,8)
2. NO file + "design/frontend/UI" keywords -> FRONTEND_ONLY (Agents: 2,3,4)
3. NO file + "architecture/system design" keywords -> ARCHITECTURE_ONLY (Agents: 1,2)
4. ZIP/Git URL + "refactor/clean/restructure" -> REFACTOR (Agents: 3,4,5)
5. ZIP/Git URL + "deploy/release/push" -> DEPLOY_ONLY (Agents: 6,7,8)
6. ZIP/Git URL + "test/coverage/spec" -> TEST_ONLY (Agent: 5)
7. ZIP/Git URL + "review/audit/security" -> CODE_REVIEW_ONLY (Agent: 4)
8. ZIP/Git URL + "fix/bug/error/crash" + error description -> FIX_AND_PATCH (Agents: 3,4,5,6)

If the request is highly ambiguous and matches none of these, set clarification_needed=True and write a clarifying_question.
Otherwise, set clarification_needed=False.

Map file_type to input_type: 'zip' -> 'zip', 'git' -> 'git_url', 'none' -> 'text'.
Set confidence between 0.0 and 1.0 based on how clear the intent is."""

        super().__init__(
            name="intent_classifier_agent",
            input_schema=IntentClassifierInput,
            output_schema=IntentRouting,
            model_name=settings.sdlc_reason_model,
            system_prompt=system_prompt

        )
        
        base_llm = get_reasoning_model(temperature=0.0) # Deterministic classification
        self.llm = base_llm.with_structured_output(IntentRouting)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "User Message: {user_message}\nHas File: {has_file}\nFile Type: {file_type}"),
        ])
        
        self.chain = self.prompt | self.llm

    async def arun(self, input_data: Union[Dict[str, Any], IntentClassifierInput]) -> IntentRouting:
        if isinstance(input_data, dict):
            input_data = IntentClassifierInput(**input_data)
            
        logger.info(f"Classifying intent for: {input_data.user_message[:50]}...")
        
        result = await self.chain.ainvoke({
            "user_message": input_data.user_message,
            "has_file": input_data.has_file,
            "file_type": input_data.file_type
        })
        
        return result