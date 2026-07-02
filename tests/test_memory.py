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
