# src/tools/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class BaseTool(ABC):
    """
    Abstract Base Class for all agent tools.
    Defines the interface for tool definition and execution.
    """
    
    # Global map to dynamically resolve common parameter naming errors
    GLOBAL_ALIASES = {
        "name": "molecule_name",
        "moleculename": "molecule_name",
        "outputpath": "file_path",
        "targetpath": "file_path",
        "targetsmiles": "smiles",
        "patternsmarts": "pattern",
        "smilespattern": "pattern",
        "usechirality": "chirality_enforced",
        "smiles1": "smiles1",
        "smiles2": "smiles2",
        "moleculename1": "molecule_name1",
        "moleculename2": "molecule_name2",
        "ingredients": "queries",
        "compounds": "queries",
        "criteria": "regulatory_category",
        "regulatorycategory": "regulatory_category"
    }

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

    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        The actual implementation of the tool. 
        Must be overridden by subclasses.
        """
        raise NotImplementedError(f"Tool {self.name} must implement execute() method.")

    def run(self, **kwargs) -> Dict[str, Any]:
        """
        Entry point for tool execution. Handles sanitization, 
        alias resolution, and validation before calling execute().
        """
        # 1. Normalize and resolve aliases
        sanitized_kwargs = {}
        for k, v in kwargs.items():
            # Basic cleaning: lower, strip, remove underscores
            clean_k = k.lower().replace("_", "").strip()
            
            # Use global alias map to find the canonical key
            canonical_key = self.GLOBAL_ALIASES.get(clean_k, clean_k)
            
            # If the canonical key doesn't exist in our map but the tool expects 
            # something similar (e.g. without underscores), we check tool's expected params
            expected_params = [p.lower() for p in self.parameters.get("properties", {}).keys()]
            if canonical_key not in expected_params:
                # Try finding a match in expected params by removing underscores
                for ep in expected_params:
                    if ep.replace("_", "") == clean_k:
                        canonical_key = ep
                        break

            sanitized_kwargs[canonical_key] = v

        # 2. Validation with Tutorial Error Messages
        required = self.parameters.get("required", [])
        missing = [r for r in required if r not in sanitized_kwargs]
        
        if missing:
            expected = list(self.parameters.get("properties", {}).keys())
            error_msg = (
                f"Missing required parameter(s): {', '.join(missing)}. "
                f"Received: {list(kwargs.keys())}. "
                f"Expected Parameters for '{self.name}': {expected}. "
                "Please correct your parameters and retry WITHOUT calling 'inspect_tool'."
            )
            return {
                "status": "error",
                "error": error_msg,
                "hint": "Check the parameter names carefully. Common errors include using 'name' instead of 'molecule_name'."
            }

        # 3. Call actual implementation
        try:
            return self.execute(**sanitized_kwargs)
        except Exception as e:
            return {
                "status": "error", 
                "error": f"Internal execution error in {self.name}: {str(e)}",
                "tool": self.name
            }

    def _sanitize_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Deprecated: Logic moved to run() for more robust handling."""
        return kwargs

    def _get_required_params(self) -> List[str]:
        """Deprecated: Logic moved to run()."""
        return self.parameters.get("required", [])

    def _validate_inputs(self, sanitized_kwargs: Dict[str, Any]) -> Optional[str]:
        """Deprecated: Logic moved to run()."""
        return None

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
