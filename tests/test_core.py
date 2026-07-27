import pytest
from unittest.mock import MagicMock, patch
from src.agent.core import ChemistryAgent

@pytest.fixture
def mock_agent():
    with patch('src.agent.core.get_vllm_client') as mock_client:
        agent = ChemistryAgent()
        yield agent, mock_client

def test_agent_initialization(mock_agent):
    agent, _ = mock_agent
    assert agent.model_name is not None
    assert agent.memory is not None

def test_agent_run_loop(mock_agent):
    agent, mock_client_factory = mock_agent
    
    # Mock LLM response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content="Hello! I am your chemistry assistant.", tool_calls=None))
    ]
    mock_client_factory.return_value.chat.completions.create.return_value = mock_response
    
    response = agent.run("Hi")
    assert "assistant" in response.lower() or "hello" in response.lower()
    assert len(agent.memory.messages) >= 2 # User + Assistant


def test_extract_thought_from_response(mock_agent):
    agent, _ = mock_agent
    content = (
        "<think>I should inspect the dataset first.</think>\n"
        "Let me analyze the file."
    )

    thought = agent._extract_thought(content)
    visible = agent._strip_thought(content)

    assert thought == "I should inspect the dataset first."
    assert visible == "Let me analyze the file."


def test_extract_reasoning_from_vllm_message_field(mock_agent):
    agent, _ = mock_agent
    message = MagicMock(content=None, reasoning="Step 1: inspect dataset.", reasoning_content=None)

    assert agent._extract_reasoning_from_message(message) == "Step 1: inspect dataset."


def test_extract_reasoning_prefers_reasoning_content(mock_agent):
    agent, _ = mock_agent
    message = MagicMock(
        content=None,
        reasoning="fallback",
        reasoning_content="primary reasoning",
    )

    assert agent._extract_reasoning_from_message(message) == "primary reasoning"
