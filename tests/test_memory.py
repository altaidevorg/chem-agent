import pytest
import os
import json
from src.agent.memory import AgentMemory

def test_memory_initialization():
    memory = AgentMemory(session_id="test_session")
    assert memory.session_id == "test_session"
    assert len(memory.messages) == 0
    assert len(memory.entities) == 0

def test_add_message():
    memory = AgentMemory()
    memory.add_message("user", "Hello")
    assert len(memory.messages) == 1
    assert memory.messages[0]["role"] == "user"
    assert memory.messages[0]["content"] == "Hello"

def test_update_entity():
    memory = AgentMemory()
    memory.update_entity(name="Aspirin", smiles="CC(=O)OC1=CC=CC=C1C(=O)O")
    assert "Aspirin" in memory.entities
    assert memory.entities["Aspirin"]["smiles"] == "CC(=O)OC1=CC=CC=C1C(=O)O"

def test_get_context_summary():
    memory = AgentMemory()
    memory.update_entity(name="Water", smiles="O")
    summary = memory.get_context_summary()
    assert "Water" in summary
    assert "SMILES=O" in summary

def test_save_to_file(tmp_path):
    memory = AgentMemory(session_id="save_test")
    memory.add_message("user", "Test message")
    
    # Use a temporary directory for testing
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    
    filepath = memory.save_to_file(folder=str(session_dir))
    assert os.path.exists(filepath)
    
    with open(filepath, "r") as f:
        data = json.load(f)
        assert data["messages"][0]["content"] == "Test message"


class _MockFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class _MockToolCall:
    def __init__(self, call_id, name, arguments):
        self.id = call_id
        self.type = "function"
        self.function = _MockFunction(name, arguments)


def test_save_to_file_with_native_tool_calls(tmp_path):
    memory = AgentMemory(session_id="tool_call_save_test")
    memory.add_message(
        "assistant",
        "",
        tool_calls=[_MockToolCall("call_1", "inspect_dataset", '{"file_path": "data.csv"}')],
    )
    memory.add_tool_response("call_1", "inspect_dataset", '{"status": "success"}')

    session_dir = tmp_path / "sessions"
    session_dir.mkdir()

    filepath = memory.save_to_file(folder=str(session_dir))
    with open(filepath, "r") as f:
        data = json.load(f)

    tool_calls = data["messages"][0]["tool_calls"]
    assert tool_calls[0]["id"] == "call_1"
    assert tool_calls[0]["function"]["name"] == "inspect_dataset"
