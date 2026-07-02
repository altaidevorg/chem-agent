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
