"""
core/agents/base.py
===================
Base agent class implementing the LangChain Runnable interface.
All 8 agents in the pipeline inherit from this class.
"""

import time
import json
import logging
from typing import Type, TypeVar, Any, List
from pydantic import BaseModel, Field, ConfigDict
from langchain_core.runnables import RunnableSerializable, RunnableConfig
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain_ollama import ChatOllama
from prometheus_client import REGISTRY, Counter, Histogram

from config.settings import settings
from core.schemas.artifacts import BaseArtifact
from core.agents.exceptions import AgentValidationError

logger = logging.getLogger(__name__)

InputType = TypeVar("InputType", bound=BaseModel)
OutputType = TypeVar("OutputType", bound=BaseArtifact)


# ─────────────────────────────────────────────────────────────────────────────
# Metrics (Safe from duplicate registration)
# ─────────────────────────────────────────────────────────────────────────────

def _get_metric(metric_class, name, documentation, labelnames):
    if name in REGISTRY._names_to_collectors:
        return REGISTRY._names_to_collectors[name]
    return metric_class(name, documentation, labelnames)


AGENT_EXECUTION_TIME = _get_metric(
    Histogram,
    "sdlc_agent_execution_seconds",
    "Time spent executing an agent phase in seconds",
    ["agent_name", "model_name"]
)

AGENT_EXECUTION_RETRIES = _get_metric(
    Counter,
    "sdlc_agent_execution_retries_total",
    "Total retries performed by an agent",
    ["agent_name", "model_name"]
)

AGENT_EXECUTION_FAILURES = _get_metric(
    Counter,
    "sdlc_agent_execution_failures_total",
    "Total failures after all retries",
    ["agent_name", "model_name", "failure_type"]
)


# ─────────────────────────────────────────────────────────────────────────────
# BaseAgent Class
# ─────────────────────────────────────────────────────────────────────────────

class BaseAgent(RunnableSerializable[InputType, OutputType]):
    """
    Abstract base class representing an agent in the SDLC pipeline.
    Handles JSON output enforcement, validation, auto-retries, and metrics tracking.
    """
    name: str = Field(description="Name of the agent")
    input_schema_class: Any = Field(description="Expected input schema class")
    output_schema_class: Any = Field(description="Expected output schema class")
    model_name: str = Field(description="Ollama model tag to use")
    system_prompt: str = Field(description="System prompt template")

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(
        self,
        name: str,
        input_schema: Type[InputType],
        output_schema: Type[OutputType],
        model_name: str,
        system_prompt: str,
        **kwargs: Any
    ):
        super().__init__(
            name=name,
            input_schema_class=input_schema,
            output_schema_class=output_schema,
            model_name=model_name,
            system_prompt=system_prompt,
            **kwargs
        )

    def _get_llm(self, config: RunnableConfig = None) -> ChatOllama:
        """Instantiates the ChatOllama model with JSON format forced."""
        return ChatOllama(
            base_url=settings.ollama_host,
            model=self.model_name,
            temperature=0.0,  # deterministic output for structural validation
            format="json",    # force JSON grammar format
        )

    def _format_messages(self, input_data: InputType) -> List[BaseMessage]:
        """Formats the initial message list including the system prompt and schema injection."""
        schema_json = json.dumps(self.output_schema_class.model_json_schema(), indent=2)
        
        system_content = (
            f"{self.system_prompt}\n\n"
            f"CRITICAL: You MUST respond with a JSON object conforming exactly to this JSON Schema:\n"
            f"{schema_json}\n"
            f"Do not include any extra text, code blocks, or preamble outside the JSON object itself."
        )
        
        user_content = (
            f"Here is the structured input data for your processing:\n"
            f"{input_data.model_dump_json(indent=2)}"
        )
        
        return [
            SystemMessage(content=system_content),
            HumanMessage(content=user_content)
        ]

    def invoke(self, input: InputType | dict, config: RunnableConfig = None) -> OutputType:
        """Executes the agent synchronously with retries and validation."""
        start_time = time.time()
        
        # 1. Parse/Validate input
        if isinstance(input, dict):
            parsed_input = self.input_schema_class.model_validate(input)
        else:
            parsed_input = input
            
        messages = self._format_messages(parsed_input)
        retry_count = 0
        max_retries = settings.sdlc_max_retries
        last_error = None
        
        while retry_count <= max_retries:
            raw_content = ""
            try:
                llm = self._get_llm(config)
                
                # Traced LLM call
                response = llm.invoke(messages, config=config)
                raw_content = response.content
                
                # Parse JSON
                try:
                    data = json.loads(raw_content)
                except json.JSONDecodeError as je:
                    raise ValueError(f"Invalid JSON string returned. Error: {str(je)}")
                
                # Validate against output schema
                output = self.output_schema_class.model_validate(data)
                
                # Set metadata fields on the output artifact
                if hasattr(output, "retry_count"):
                    output.retry_count = retry_count
                if hasattr(output, "agent_model"):
                    output.agent_model = self.model_name
                
                # Record success metrics
                duration = time.time() - start_time
                AGENT_EXECUTION_TIME.labels(agent_name=self.name, model_name=self.model_name).observe(duration)
                if retry_count > 0:
                    AGENT_EXECUTION_RETRIES.labels(agent_name=self.name, model_name=self.model_name).inc(retry_count)
                    
                return output
                
            except Exception as e:
                last_error = e
                retry_count += 1
                logger.warning(
                    f"Agent {self.name} failed attempt {retry_count}/{max_retries + 1}. Error: {str(e)}"
                )
                
                if retry_count > max_retries:
                    break
                
                # Append error message back to conversation history to let LLM self-correct
                messages.append(AIMessage(content=raw_content if raw_content else "[Failed to generate valid response]"))
                error_feedback = (
                    f"Validation failed with error: {str(e)}.\n"
                    f"Please correct your response to match the JSON Schema exactly."
                )
                messages.append(HumanMessage(content=error_feedback))
                
        # If we reach here, we exceeded max retries
        AGENT_EXECUTION_FAILURES.labels(
            agent_name=self.name, 
            model_name=self.model_name, 
            failure_type=type(last_error).__name__
        ).inc()
        
        raise AgentValidationError(
            agent_name=self.name,
            message=f"Failed to produce a valid schema after {max_retries} retries.",
            last_error=last_error
        )

    async def ainvoke(self, input: InputType | dict, config: RunnableConfig = None) -> OutputType:
        """Executes the agent asynchronously with retries and validation."""
        start_time = time.time()
        
        # 1. Parse/Validate input
        if isinstance(input, dict):
            parsed_input = self.input_schema_class.model_validate(input)
        else:
            parsed_input = input
            
        messages = self._format_messages(parsed_input)
        retry_count = 0
        max_retries = settings.sdlc_max_retries
        last_error = None
        
        while retry_count <= max_retries:
            raw_content = ""
            try:
                llm = self._get_llm(config)
                
                # Traced LLM call (async)
                response = await llm.ainvoke(messages, config=config)
                raw_content = response.content
                
                # Parse JSON
                try:
                    data = json.loads(raw_content)
                except json.JSONDecodeError as je:
                    raise ValueError(f"Invalid JSON string returned. Error: {str(je)}")
                
                # Validate against output schema
                output = self.output_schema_class.model_validate(data)
                
                # Set metadata fields on the output artifact
                if hasattr(output, "retry_count"):
                    output.retry_count = retry_count
                if hasattr(output, "agent_model"):
                    output.agent_model = self.model_name
                
                # Record success metrics
                duration = time.time() - start_time
                AGENT_EXECUTION_TIME.labels(agent_name=self.name, model_name=self.model_name).observe(duration)
                if retry_count > 0:
                    AGENT_EXECUTION_RETRIES.labels(agent_name=self.name, model_name=self.model_name).inc(retry_count)
                    
                return output
                
            except Exception as e:
                last_error = e
                retry_count += 1
                logger.warning(
                    f"Agent {self.name} failed async attempt {retry_count}/{max_retries + 1}. Error: {str(e)}"
                )
                
                if retry_count > max_retries:
                    break
                
                # Append error message back to conversation history to let LLM self-correct
                messages.append(AIMessage(content=raw_content if raw_content else "[Failed to generate valid response]"))
                error_feedback = (
                    f"Validation failed with error: {str(e)}.\n"
                    f"Please correct your response to match the JSON Schema exactly."
                )
                messages.append(HumanMessage(content=error_feedback))
                
        # If we reach here, we exceeded max retries
        AGENT_EXECUTION_FAILURES.labels(
            agent_name=self.name, 
            model_name=self.model_name, 
            failure_type=type(last_error).__name__
        ).inc()
        
        raise AgentValidationError(
            agent_name=self.name,
            message=f"Failed to produce a valid schema after {max_retries} retries.",
            last_error=last_error
        )
