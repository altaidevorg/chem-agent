# tests/test_tools.py
import pytest
from src.tools.base import ToolRegistry, BaseTool

class MockTool(BaseTool):
    @property
    def name(self): return "mock_tool"
    @property
    def description(self): return "A mock tool"
    @property
    def parameters(self): return {"type": "object", "properties": {}}
    def execute(self, **kwargs): return {"status": "success"}

def test_tool_registration():
    tool = MockTool()
    ToolRegistry.register(tool)
    
    registered_tool = ToolRegistry.get_tool("mock_tool")
    assert registered_tool is not None
    assert registered_tool.name == "mock_tool"
    
    definitions = ToolRegistry.get_tool_definitions()
    assert any(d["function"]["name"] == "mock_tool" for d in definitions)

def test_get_all_tools():
    tools = ToolRegistry.get_all_tools()
    assert len(tools) > 0
