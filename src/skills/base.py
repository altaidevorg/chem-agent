# src/skills/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class BaseSkill(ABC):
    """
    Abstract Base Class for all agent skills.
    Defines the interface for tool definition and execution.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of the skill/tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A clear description of what the skill does for the LLM."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """JSON Schema representation of the tool's parameters."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """The actual implementation of the skill."""
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

class SkillRegistry:
    """
    Registry to manage and retrieve agent skills dynamically.
    """
    _skills: Dict[str, BaseSkill] = {}

    @classmethod
    def register(cls, skill_instance: BaseSkill):
        """Registers a skill instance."""
        cls._skills[skill_instance.name] = skill_instance
        print(f"[Registry] Registered skill: {skill_instance.name}")

    @classmethod
    def get_skill(cls, name: str) -> Optional[BaseSkill]:
        """Retrieves a skill by name."""
        return cls._skills.get(name)

    @classmethod
    def get_all_skills(cls) -> List[BaseSkill]:
        """Returns all registered skill instances."""
        return list(cls._skills.values())

    @classmethod
    def get_tool_definitions(cls) -> List[Dict[str, Any]]:
        """Returns OpenAI-compatible tool definitions for all registered skills."""
        return [skill.get_tool_definition() for skill in cls._skills.values()]
