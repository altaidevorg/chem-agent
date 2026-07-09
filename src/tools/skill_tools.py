# src/tools/skill_tools.py
import json
from typing import Any, Dict, Optional
from src.tools.base import BaseTool, ToolRegistry
from src.skills.registry import SkillRegistry

class LoadSkillTool(BaseTool):
    def __init__(self, skill_registry: SkillRegistry):
        self.registry = skill_registry

    @property
    def name(self) -> str:
        return "load_skill_instructions"

    @property
    def description(self) -> str:
        return "Loads the full markdown instructions for a specific Agent Skill. Use this when you need to execute a skill."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["load", "list"],
                    "description": "Use 'list' to enumerate discovered skills. Use 'load' (default) to fetch one skill by name."
                },
                "skill_name": {
                    "type": "string",
                    "description": "Exact skill name when action is load (e.g. 'molecule_analysis')."
                },
                "detail": {
                    "type": "string",
                    "enum": ["full", "metadata"],
                    "description": "When action is load: 'full' returns instruction body (default). 'metadata' returns name, availability, description, and body length without the full body."
                }
            }
        }

    def execute(self, action: str = "load", skill_name: Optional[str] = None, detail: str = "full") -> Dict[str, Any]:
        if action == "list":
            return {"content": self.registry.format_skill_directory()}

        if not skill_name:
            return {"error": "Missing 'skill_name' when action is load (default)."}

        if detail == "metadata":
            meta = self.registry.get_skill_metadata(skill_name)
            if not meta:
                return {"error": f"Skill '{skill_name}' not found."}
            return meta

        instructions = self.registry.get_skill_instructions(skill_name)
        if not instructions:
            return {"error": f"Skill '{skill_name}' not found or unavailable."}
        
        return {"skill_name": skill_name, "instructions": instructions}

# Note: This tool needs a SkillRegistry instance to be initialized.
# We will register it in the agent initialization or a central place.
