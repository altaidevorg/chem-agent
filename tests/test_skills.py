import pytest
from src.skills.base import SkillRegistry, BaseSkill

class MockSkill(BaseSkill):
    @property
    def name(self): return "mock_tool"
    @property
    def description(self): return "A mock tool"
    @property
    def parameters(self): return {"type": "object", "properties": {}}
    def execute(self, **kwargs): return {"status": "success"}

def test_skill_registration():
    skill = MockSkill()
    SkillRegistry.register(skill)
    
    registered_skill = SkillRegistry.get_skill("mock_tool")
    assert registered_skill is not None
    assert registered_skill.name == "mock_tool"
    
    definitions = SkillRegistry.get_tool_definitions()
    assert any(d["function"]["name"] == "mock_tool" for d in definitions)

def test_get_all_skills():
    skills = SkillRegistry.get_all_skills()
    assert len(skills) > 0
