# src/tools/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class BaseTool(ABC):
    """
    Abstract Base Class for all agent tools.
    Defines the interface for tool definition and execution.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A clear description of what the tool does for the LLM."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """JSON Schema representation of the tool's parameters."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """The actual implementation of the tool."""
        pass

    def get_tool_definition(self) -> Dict[str, Any]:
        """Returns the OpenAI-compatible tool definition."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }

class ToolRegistry:
    """
    Registry to manage and retrieve agent tools dynamically.
    """
    _tools: Dict[str, BaseTool] = {}

    @classmethod
    def register(cls, tool_instance: BaseTool):
        """Registers a tool instance."""
        cls._tools[tool_instance.name] = tool_instance
        print(f"[Registry] Registered tool: {tool_instance.name}")

    @classmethod
    def get_tool(cls, name: str) -> Optional[BaseTool]:
        """Retrieves a tool by name."""
        return cls._tools.get(name)

    @classmethod
    def get_all_tools(cls) -> List[BaseTool]:
        """Returns all registered tool instances."""
        return list(cls._tools.values())

    @classmethod
    def get_tool_definitions(cls) -> List[Dict[str, Any]]:
        """Returns OpenAI-compatible tool definitions for all registered tools."""
        return [tool.get_tool_definition() for tool in cls._tools.values()]
