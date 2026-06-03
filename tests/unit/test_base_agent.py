"""
tests/unit/test_base_agent.py
=============================
Unit tests for the BaseAgent abstract base class.
Uses mock LLM responses to test retries, formatting, and exception throwing.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pytest
import asyncio
from uuid import uuid4
from unittest.mock import MagicMock, AsyncMock, patch
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage

from core.schemas.artifacts import BaseArtifact, AgentPhase
from core.agents.base import BaseAgent
from core.agents.exceptions import AgentValidationError


# Define Pydantic schemas for testing
class MockInput(BaseModel):
    query: str


class MockOutput(BaseArtifact):
    phase: AgentPhase = AgentPhase.PRD_INGESTION
    result: str


# Concrete subclass implementation for testing
class TestConcreteAgent(BaseAgent[MockInput, MockOutput]):
    pass


@pytest.fixture
def agent():
    return TestConcreteAgent(
        name="test_concrete_agent",
        input_schema=MockInput,
        output_schema=MockOutput,
        model_name="llama3.2:3b",
        system_prompt="You are a helper agent."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Synchronous Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_base_agent_format_messages(agent):
    input_data = MockInput(query="hello")
    messages = agent._format_messages(input_data)
    assert len(messages) == 2
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert "You are a helper agent." in messages[0].content
    assert "hello" in messages[1].content
    # JSON schema should be injected in the system prompt
    assert "result" in messages[0].content


@patch("core.agents.base.ChatOllama")
def test_base_agent_invoke_success(mock_chat_ollama_class, agent):
    # Setup mock
    mock_llm = MagicMock()
    mock_chat_ollama_class.return_value = mock_llm
    
    run_id = uuid4()
    mock_response = MagicMock()
    mock_response.content = (
        f'{{"run_id": "{run_id}", "project_id": "test", "phase": 1, '
        f'"confidence": 0.95, "agent_model": "llama3.2:3b", "result": "success"}}'
    )
    mock_llm.invoke.return_value = mock_response

    input_data = MockInput(query="test query")
    output = agent.invoke(input_data)

    assert isinstance(output, MockOutput)
    assert output.result == "success"
    assert output.retry_count == 0
    assert output.agent_model == "llama3.2:3b"
    assert output.run_id == run_id


@patch("core.agents.base.ChatOllama")
def test_base_agent_invoke_retry_and_success(mock_chat_ollama_class, agent):
    # Setup mock to return invalid JSON first, then valid JSON
    mock_llm = MagicMock()
    mock_chat_ollama_class.return_value = mock_llm
    
    run_id = uuid4()
    invalid_response = MagicMock()
    invalid_response.content = "invalid-json"
    
    valid_response = MagicMock()
    valid_response.content = (
        f'{{"run_id": "{run_id}", "project_id": "test", "phase": 1, '
        f'"confidence": 0.95, "agent_model": "llama3.2:3b", "result": "success after retry"}}'
    )
    
    mock_llm.invoke.side_effect = [invalid_response, valid_response]

    input_data = MockInput(query="test query")
    output = agent.invoke(input_data)

    assert isinstance(output, MockOutput)
    assert output.result == "success after retry"
    assert output.retry_count == 1
    assert mock_llm.invoke.call_count == 2


@patch("core.agents.base.ChatOllama")
def test_base_agent_invoke_max_retries_fail(mock_chat_ollama_class, agent):
    # Setup mock to always return invalid output (missing fields required by BaseArtifact)
    mock_llm = MagicMock()
    mock_chat_ollama_class.return_value = mock_llm
    
    invalid_response = MagicMock()
    invalid_response.content = '{"result": "missing key fields"}'
    mock_llm.invoke.return_value = invalid_response

    input_data = MockInput(query="test query")
    
    with pytest.raises(AgentValidationError) as excinfo:
        agent.invoke(input_data)
        
    assert "Failed to produce a valid schema after" in str(excinfo.value)
    # 1 initial attempt + 3 retries = 4 total calls
    assert mock_llm.invoke.call_count == 4


# ─────────────────────────────────────────────────────────────────────────────
# Asynchronous Tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("core.agents.base.ChatOllama")
async def test_base_agent_ainvoke_success(mock_chat_ollama_class, agent):
    mock_llm = MagicMock()
    mock_chat_ollama_class.return_value = mock_llm
    
    run_id = uuid4()
    mock_response = MagicMock()
    mock_response.content = (
        f'{{"run_id": "{run_id}", "project_id": "test", "phase": 1, '
        f'"confidence": 0.95, "agent_model": "llama3.2:3b", "result": "async success"}}'
    )
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    input_data = MockInput(query="test query")
    output = await agent.ainvoke(input_data)

    assert isinstance(output, MockOutput)
    assert output.result == "async success"
    assert output.retry_count == 0
    mock_llm.ainvoke.assert_called_once()


@pytest.mark.asyncio
@patch("core.agents.base.ChatOllama")
async def test_base_agent_ainvoke_retry_and_success(mock_chat_ollama_class, agent):
    mock_llm = MagicMock()
    mock_chat_ollama_class.return_value = mock_llm
    
    run_id = uuid4()
    invalid_response = MagicMock()
    invalid_response.content = "invalid-json"
    
    valid_response = MagicMock()
    valid_response.content = (
        f'{{"run_id": "{run_id}", "project_id": "test", "phase": 1, '
        f'"confidence": 0.95, "agent_model": "llama3.2:3b", "result": "async success after retry"}}'
    )
    mock_llm.ainvoke = AsyncMock()
    mock_llm.ainvoke.side_effect = [invalid_response, valid_response]

    input_data = MockInput(query="test query")
    output = await agent.ainvoke(input_data)

    assert isinstance(output, MockOutput)
    assert output.result == "async success after retry"
    assert output.retry_count == 1
    assert mock_llm.ainvoke.call_count == 2


@pytest.mark.asyncio
@patch("core.agents.base.ChatOllama")
async def test_base_agent_ainvoke_max_retries_fail(mock_chat_ollama_class, agent):
    mock_llm = MagicMock()
    mock_chat_ollama_class.return_value = mock_llm
    
    invalid_response = MagicMock()
    invalid_response.content = '{"result": "missing key fields"}'
    mock_llm.ainvoke = AsyncMock(return_value=invalid_response)

    input_data = MockInput(query="test query")
    
    with pytest.raises(AgentValidationError) as excinfo:
        await agent.ainvoke(input_data)
        
    assert "Failed to produce a valid schema after" in str(excinfo.value)
    assert mock_llm.ainvoke.call_count == 4
