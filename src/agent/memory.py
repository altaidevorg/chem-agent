# src/agent/memory.py
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from src.config import SESSIONS_DIR

class AgentMemory:
    """
    Manages the agent's short-term and contextual memory.
    Stores conversation history and chemical entity tracking.
    """
    
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.messages: List[Dict[str, str]] = []
        self.entities: Dict[str, Dict[str, Any]] = {}  # Track molecules by name/smiles
        self.metadata: Dict[str, Any] = {
            "start_time": datetime.now().isoformat(),
            "last_interaction": None
        }

    def add_message(self, role: str, content: str, tool_calls: Optional[List[Any]] = None):
        """Adds a message to the conversation history."""
        message = {"role": role, "content": content}
        if tool_calls:
            message["tool_calls"] = tool_calls
        self.messages.append(message)
        self.metadata["last_interaction"] = datetime.now().isoformat()

    def add_tool_response(self, tool_call_id: str, name: str, content: str):
        """Adds a tool response to the conversation history."""
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": content
        })

    def update_entity(self, name: Optional[str], smiles: Optional[str], properties: Optional[Dict[str, Any]] = None):
        """Tracks or updates a chemical entity in memory."""
        key = name or smiles
        if not key:
            return
            
        if key not in self.entities:
            self.entities[key] = {}
            
        if name: self.entities[key]["name"] = name
        if smiles: self.entities[key]["smiles"] = smiles
        if properties:
            if "properties" not in self.entities[key]:
                self.entities[key]["properties"] = {}
            self.entities[key]["properties"].update(properties)

    def get_context_summary(self) -> str:
        """Generates a text summary of the current chemical context for the LLM."""
        if not self.entities:
            return "No chemical entities resolved in this session yet."
            
        summary = "Current Chemical Context:\n"
        for key, data in self.entities.items():
            name = data.get("name", "Unknown")
            smiles = data.get("smiles", "N/A")
            summary += f"- {name}: SMILES={smiles}\n"
            if "properties" in data:
                summary += f"  Properties: {list(data['properties'].keys())}\n"
        return summary

    def clear(self):
        """Resets the memory."""
        self.messages = []
        self.entities = {}
        self.metadata["last_interaction"] = datetime.now().isoformat()

    def save_to_file(self, folder: str = SESSIONS_DIR):
        """Persists the current session memory to a JSON file."""
        os.makedirs(folder, exist_ok=True)
        filepath = os.path.join(folder, f"session_{self.session_id}.json")
        data = {
            "metadata": self.metadata,
            "entities": self.entities,
            "messages": self.messages
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return filepath
