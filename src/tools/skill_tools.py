# src/tools/skill_tools.py
import json
from typing import Any, Dict, Optional
from src.tools.base import BaseTool, ToolRegistry
from src.skills.registry import SkillRegistry
from src.agent.memory import AgentMemory

class LoadSkillTool(BaseTool):
    def __init__(self, skill_registry: SkillRegistry, agent_memory: Optional[AgentMemory] = None):
        self.registry = skill_registry
        self.memory = agent_memory

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
        
        # AUTOMATIC TOOL ACTIVATION: Add tools required by the loaded skill to session memory
        added_tools = []
        if self.memory:
            req_tools = self.registry.get_required_tools_for_skills([skill_name])
            for t in req_tools:
                if t not in self.memory.active_tools:
                    self.memory.active_tools.append(t)
                    added_tools.append(t)
            
            if added_tools:
                print(f"[LoadSkill] Automatically enabled tools for '{skill_name}': {', '.join(added_tools)}")
        
        return {
            "skill_name": skill_name, 
            "instructions": instructions,
            "automatically_enabled_tools": added_tools
        }

class InspectTool(BaseTool):
    """
    Allows the agent to discover and 'enable' new tools from the global registry.
    This supports dynamic tool caching.
    """
    def __init__(self, agent_memory: AgentMemory):
        self.memory = agent_memory

    @property
    def name(self) -> str:
        return "inspect_tool"

    @property
    def description(self) -> str:
        return (
            "Retrieves the JSON schema for a specific tool from the global registry. "
            "Using this tool 'enables' the target tool for the rest of the session, "
            "allowing you to call it directly in subsequent turns."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["inspect", "list_all"],
                    "description": "Use 'list_all' to see all available tools in the registry. Use 'inspect' (default) to get the schema for a specific tool and enable it."
                },
                "tool_name": {
                    "type": "string",
                    "description": "The name of the tool to inspect and enable (required when action is 'inspect')."
                }
            },
            "required": []
        }

    def execute(self, action: str = "inspect", tool_name: Optional[str] = None) -> Dict[str, Any]:
        if action == "list_all":
            all_tools = ToolRegistry.get_all_tools()
            return {
                "available_tools": [
                    {"name": t.name, "description": t.description} for t in all_tools
                ]
            }

        if not tool_name:
            return {"error": "Missing 'tool_name' when action is 'inspect'."}

        tool = ToolRegistry.get_tool(tool_name)
        if not tool:
            return {"error": f"Tool '{tool_name}' not found in global registry."}
        
        # Add to session cache
        if tool_name not in self.memory.active_tools:
            self.memory.active_tools.append(tool_name)
            print(f"[InspectTool] Enabled tool for session: {tool_name}")
            
        return {
            "tool_name": tool_name,
            "status": "enabled",
            "schema": tool.get_tool_definition()
        }

# Note: This tool needs a SkillRegistry instance to be initialized.
# We will register it in the agent initialization or a central place.
