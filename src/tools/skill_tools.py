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

    def execute(self, action: str = "load", skill_name: Optional[str] = None, detail: str = "full", **kwargs) -> Dict[str, Any]:
        if action == "list":
            return {"content": self.registry.format_skill_directory()}

        if not skill_name:
            return {"error": "Missing 'skill_name' when action is load (default)."}

        if detail == "metadata":
            meta = self.registry.get_skill_metadata(skill_name)
            if not meta:
                return {"error": f"Skill '{skill_name}' not found."}
            return {
                "skill_name": skill_name,
                "description": meta.get("description", ""),
                "required_tools": meta.get("required_tools", [])
            }

        instructions = self.registry.get_skill_instructions(skill_name)
        if not instructions:
            return {"error": f"Skill '{skill_name}' not found or unavailable."}
        
        # 🚀 PROGRESSIVE FIX: Batch tool activation removed!
        # The model will now read the instructions and call 'inspect_tool' for specific tools it needs.
        return {
            "skill_name": skill_name, 
            "instructions": instructions
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

    def execute(self, action: str = "inspect", tool_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        if action == "list_all":
            all_tools = ToolRegistry.get_all_tools()
            return {
                "total_tools_registered": len(all_tools),
                "available_tools": [
                    {"name": t.name, "description": t.description[:120]} for t in all_tools
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

class SetWorkspaceTool(BaseTool):
    """
    Allows the agent to dynamically change its active working directory.
    """
    @property
    def name(self) -> str:
        return "set_workspace"

    @property
    def description(self) -> str:
        return "Switches the agent's active working directory to a new folder. All subsequent file operations will be relative to this new root."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "workspace_path": {
                    "type": "string",
                    "description": "The absolute or relative local path to the new workspace directory."
                }
            },
            "required": ["workspace_path"]
        }

    def execute(self, workspace_path: str, workspace: Optional[Any] = None, **kwargs) -> Dict[str, Any]:
        if not workspace:
            return {"error": "WorkspaceManager not available.", "status": "fail"}
        
        try:
            new_root = workspace.set_workspace(workspace_path)
            return {
                "status": "success",
                "message": f"Workspace successfully changed to: {new_root}",
                "new_root": new_root
            }
        except Exception as e:
            return {"error": f"Failed to set workspace: {str(e)}", "status": "fail"}

# Note: This tool needs a SkillRegistry instance to be initialized.
# We will register it in the agent initialization or a central place.
