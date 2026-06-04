"""
Phase 3: Code Generation Agent

Reads the DesignDoc and generates the actual code implementation.
Outputs a structured CodeArtifact with file paths, content hashes, and Git metadata.
"""

import logging
from typing import Dict, Any, Union

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, ConfigDict

from core.agents.base import BaseAgent
from core.llm.client import get_code_model
from core.schemas.artifacts import CodeArtifact
from config.settings import settings

logger = logging.getLogger(__name__)


class CodeGenerationInput(BaseModel):
    """Input schema for the Code Generation Agent."""
    design_doc: Dict[str, Any] = Field(description="The structured DesignDoc from Phase 2")
    run_id: str = Field(description="The current pipeline run ID (UUID string)")
    project_id: str = Field(description="The project identifier")
    design_artifact_id: str = Field(description="The artifact_id of the DesignDoc (UUID string)")


class CodeGenerationAgent(BaseAgent):
    """
    Agent responsible for Phase 3: Code Generation.
    """
    
    model_config = ConfigDict(extra="allow")

    def __init__(self):
        system_prompt = """You are an expert Senior Software Engineer and Code Generation Specialist.
Your task is to implement the system described in the provided DesignDoc.

You must output a complete CodeArtifact. CRITICAL FORMATTING RULES:
1. You MUST copy `run_id`, `project_id`, and `design_artifact_id` exactly as provided.
2. You MUST set `phase` to 3 (or "CODE_GENERATION").
3. You MUST set `agent_model` to "qwen2.5-coder:3b".
4. For `git_branch`, generate a valid branch name like "feature/sdlc-{{run_id[:8]}}".
5. For `git_commit`, generate a realistic 40-character hex SHA (e.g., "a1b2c3d4e5f6...").
6. For `generated_files`, provide 3 to 5 CORE files that represent the implementation. 
   - `path`: Relative path (e.g., "src/main.py", "src/models/user.py").
   - `language`: Lowercase (e.g., "python", "typescript", "sql").
   - `content_hash`: A realistic 64-character hexadecimal SHA-256 string.
   - `lines_of_code`: A realistic integer (e.g., 50-200).
   - `is_new_file`: true.
   - `module`: The logical module (e.g., "api", "db", "auth").
7. For `modules_completed`, list the modules you generated (e.g., ["db", "api"]).
8. Leave `modules_skipped` and `skip_reasons` EMPTY for this initial generation.
9. Set `has_tests` to true, `has_migrations` to true, `has_dockerfile` to true.

Be precise and strictly adhere to the JSON schema. Do not output markdown code blocks outside the JSON structure."""

        super().__init__(
            name="code_generation_agent",
            input_schema=CodeGenerationInput,
            output_schema=CodeArtifact,
            model_name=settings.sdlc_code_model,
            system_prompt=system_prompt
        )
        
        # Use the code-specific model (Qwen2.5-Coder)
        base_llm = get_code_model(temperature=0.2)
        self.llm = base_llm.with_structured_output(CodeArtifact)
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "Here is the DesignDoc from Phase 2:\n{design_doc}\n\nMetadata to copy:\n- run_id: {run_id}\n- project_id: {project_id}\n- design_artifact_id: {design_artifact_id}"),
        ])
        
        self.chain = self.prompt | self.llm

    async def arun(self, input_data: Union[Dict[str, Any], CodeGenerationInput]) -> CodeArtifact:
        # Normalize input to CodeGenerationInput instance if a dict was passed
        if isinstance(input_data, dict):
            input_data = CodeGenerationInput(**input_data)
            
        logger.info("Running Code Generation Agent...")
        
        result = await self.chain.ainvoke({
            "design_doc": input_data.design_doc,
            "run_id": input_data.run_id,
            "project_id": input_data.project_id,
            "design_artifact_id": input_data.design_artifact_id,
        })
        
        if not hasattr(result, 'confidence'):
            result.confidence = 0.75
            
        return result