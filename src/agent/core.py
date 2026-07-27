# src/agent/core.py
import json
import re
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        # Handle numpy types without explicitly importing numpy
        if hasattr(obj, "item") and callable(getattr(obj, "item")):
            return obj.item()
        return super().default(obj)

def safe_json_dumps(obj, **kwargs):
    return json.dumps(obj, cls=CustomEncoder, ensure_ascii=False, **kwargs)

from src.vllm_client import get_vllm_client
from src.config import MODEL_NAME, MAX_ITERATIONS, TEMPERATURE, TELEMETRY_LOG_FILE, THOUGHT_LOGS_DIR, SKILLS_DIR
from src.agent.prompts import SYSTEM_PROMPT
from src.agent.memory import AgentMemory
from src.tools.base import ToolRegistry
from src.skills.registry import SkillRegistry
from src.tools.skill_tools import LoadSkillTool
# Import tools to ensure they are registered
import src.tools.rdkit_tools
import src.tools.file_tools
import src.tools.data_tools
import src.tools.stats_tools

class ChemistryAgent:
    """
    A stateful agent responsible for orchestrating chemical analysis tasks.
    Uses structured memory to maintain context across turns and provides rich logging.
    """
    
    def __init__(self, model_name: str = MODEL_NAME, max_iterations: int = MAX_ITERATIONS):
        self.client = get_vllm_client()
        self.model_name = model_name
        self.max_iterations = max_iterations
        self.memory = AgentMemory()
        self.session_thought_log = []
        
        # Initialize Skill Registry
        self.skill_registry = SkillRegistry(SKILLS_DIR)
        
        # Initialize instance-specific tools from global registry
        # This avoids shared-state anti-pattern where agents overwrite each other's tools
        self.tools = {name: tool for name, tool in ToolRegistry._tools.items()}
        
        # Register instance-specific LoadSkillTool
        load_skill_tool = LoadSkillTool(self.skill_registry)
        self.tools[load_skill_tool.name] = load_skill_tool
        
    def _write_telemetry(self, event_type: str, data: dict):
        """Writes structured telemetry logs to a JSONL file."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            **data
        }
        try:
            os.makedirs(os.path.dirname(TELEMETRY_LOG_FILE), exist_ok=True)
            with open(TELEMETRY_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(safe_json_dumps(log_entry) + "\n")
        except Exception as e:
            print(f"[Logger Error] Failed to write telemetry: {e}")

    def _extract_reasoning_from_message(self, message) -> str:
        """Reads reasoning from provider-specific message fields (vLLM, etc.)."""
        for field in ("reasoning_content", "reasoning"):
            value = getattr(message, field, None)
            if value and str(value).strip():
                return str(value).strip()
        return ""

    def _extract_thought(self, content: str) -> str:
        """Extracts the model's chain-of-thought block from a response."""
        if not content:
            return ""

        if "<think>" in content:
            parts = content.split("<think>", 1)
            if len(parts) > 1:
                thought_part = parts[1]
                if "</think>" in thought_part:
                    return thought_part.split("</think>", 1)[0].strip()
                return thought_part.strip()
        if "</think>" in content:
            return content.split("</think>", 1)[0].strip()
        return ""

    def _strip_thought(self, content: str) -> str:
        """Returns response content with the thinking block removed."""
        if not content:
            return ""

        if "<think>" in content:
            parts = content.split("<think>", 1)
            before_think = parts[0].strip()
            if "</think>" in parts[1]:
                after_think = parts[1].split("</think>", 1)[1].strip()
                content = f"{before_think}\n{after_think}".strip() if before_think else after_think
            else:
                content = before_think
        elif "</think>" in content:
            content = content.split("</think>", 1)[-1].strip()
        else:
            content = content.strip()

        # --- SAFETY VALVE: HALLUCINATION/LOOP DETECTION ---
        # Detect and truncate abnormally long, repetitive strings (common in SMILES hallucinations)
        words = content.split()
        safe_content = []
        for word in words:
            # If a single word is suspicious (>200 chars and high repetitive pattern)
            if len(word) > 200:
                # Simple heuristic for SMILES loops: many numbers and capital letters in a tight loop
                digit_count = sum(c.isdigit() for c in word)
                if digit_count > len(word) * 0.3: # If >30% are digits, it's likely a ring-closure loop
                    word = word[:100] + "... [TRUNCATED POTENTIAL HALLUCINATION LOOP] ..."
            safe_content.append(word)
        
        return " ".join(safe_content)

    def _log_thought(self, iteration: int, thought: str):
        """Logs the agent's reasoning process (Chain of Thought) for observability."""
        timestamp = datetime.now().isoformat()
        entry = {
            "timestamp": timestamp,
            "iteration": iteration,
            "thought": thought
        }
        self.session_thought_log.append(entry)
        
        # Also write to a dedicated session thought file
        thought_file = os.path.join(THOUGHT_LOGS_DIR, f"thoughts_{self.memory.session_id}.md")
        try:
            os.makedirs(os.path.dirname(thought_file), exist_ok=True)
            with open(thought_file, "a", encoding="utf-8") as f:
                if iteration == 1 and f.tell() == 0:
                    f.write(f"# Chain of Thought Log - Session {self.memory.session_id}\n\n")
                f.write(f"### Iteration {iteration} ({timestamp})\n")
                f.write(f"{thought}\n\n---\n\n")
        except Exception as e:
            print(f"[Logger Error] Failed to write thought log: {e}")

    def _get_available_tools(self) -> List[Dict[str, Any]]:
        """Retrieves tool definitions from the instance-specific tools."""
        return [tool.get_tool_definition() for tool in self.tools.values()]

    def _execute_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a tool by name using instance-specific tools and updates memory."""
        tool = self.tools.get(name)
        if not tool:
            return {"error": f"Tool '{name}' not found in agent's toolset."}
        
        try:
            result = tool.execute(**arguments)
            
            # Update structured memory based on tool results
            if name == "resolve_name_to_smiles" and "smiles" in result:
                self.memory.update_entity(name=arguments.get("molecule_name"), smiles=result["smiles"])
            elif name == "calculate_molecular_properties" and "smiles" in result:
                self.memory.update_entity(name=None, smiles=result["smiles"], properties=result)
                
            return result
        except Exception as e:
            return {"error": f"Execution error in tool '{name}': {str(e)}"}

    def run(self, user_query: str) -> str:
        """Main execution loop for the agent."""
        self._write_telemetry("session_start", {"user_query": user_query})
        
        # Inject current chemical context and available skills into the system prompt
        context_summary = self.memory.get_context_summary()
        skills_summary = self.skill_registry.get_capabilities_summary()
        current_system_prompt = f"{SYSTEM_PROMPT}\n\n{context_summary}\n\n{skills_summary}"

        # Add current user query to memory
        self.memory.add_message("user", user_query)
        
        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1
            
            # --- AUTO-COMPACTION CHECK ---
            # We check before every API call to ensure tool results or long history 
            # don't exceed the model's context window.
            self.memory.check_and_compact(self, current_system_prompt)
            # -----------------------------

            # Refresh run_messages after potential compaction
            run_messages = [{"role": "system", "content": current_system_prompt}]
            for msg in self.memory.messages:
                run_messages.append(msg)

            print(f"[Agent] (Turn {iteration}) Requesting completion...")
            
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=run_messages,
                    tools=self._get_available_tools(),
                    tool_choice="auto",
                    temperature=TEMPERATURE
                )
            except Exception as e:
                error_msg = f"LLM API Error: {str(e)}"
                self._write_telemetry("error", {"message": error_msg})
                return error_msg

            response_message = response.choices[0].message
            run_messages.append(response_message)
            
            # Extract and log the thought process (Chain of Thought)
            content = response_message.content or ""
            # First try provider-specific reasoning fields (vLLM: reasoning or reasoning_content)
            thought = self._extract_reasoning_from_message(response_message)

            # If not found, fall back to tag extraction from content (legacy chem-coder)
            if not thought:
                thought = self._extract_thought(content)
            
            visible_content = self._strip_thought(content)

            if thought:
                self._log_thought(iteration, thought)

            model_response_log = {
                "iteration": iteration,
                "has_thought": bool(thought),
                "thought": thought or None,
                "visible_content": visible_content or None,
                "tool_calls": bool(response_message.tool_calls),
            }

            if response_message.tool_calls:
                model_response_log["tool_call_names"] = [
                    tool_call.function.name for tool_call in response_message.tool_calls
                ]

            self._write_telemetry("model_response", model_response_log)

            # 1. Handle Native Tool Calls
            if response_message.tool_calls:
                # Save the assistant message with tool calls to memory
                self.memory.add_message("assistant", response_message.content or "", tool_calls=response_message.tool_calls)
                
                print(f"[Agent] Executing {len(response_message.tool_calls)} native tool(s)...")
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    result = self._execute_tool(function_name, function_args)
                    
                    self._write_telemetry("tool_execution", {
                        "iteration": iteration,
                        "tool": function_name,
                        "args": function_args,
                        "result": result
                    })
                    
                    # Save the tool response to memory
                    self.memory.add_tool_response(tool_call.id, function_name, safe_json_dumps(result))
                    
                    run_messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": safe_json_dumps(result)
                    })
                continue

            # 2. Handle XML Fallback
            if "<tool_call>" in content:
                print(f"[Agent] Detected XML tool call fallback. Parsing...")
                
                # Save the assistant's XML tool call to memory
                self.memory.add_message("assistant", content)
                
                xml_matches = re.findall(r'<tool_call>(.*?)</tool_call>', content, re.DOTALL)
                
                if xml_matches:
                    for match in xml_matches:
                        try:
                            parsed_call = json.loads(match.strip())
                            tool_name = parsed_call.get("name")
                            tool_args = parsed_call.get("arguments")
                            
                            if tool_name:
                                result = self._execute_tool(tool_name, tool_args)
                                self._write_telemetry("tool_execution", {
                                    "iteration": iteration,
                                    "tool": tool_name,
                                    "args": tool_args,
                                    "result": result,
                                    "fallback": "xml"
                                })
                                
                                response_content = f"[SYSTEM TOOL RESPONSE]\n<tool_response>\n{safe_json_dumps(result)}\n</tool_response>"
                                
                                # Save the XML tool response to memory as a user message (fallback pattern)
                                self.memory.add_message("user", response_content)
                                
                                run_messages.append({
                                    "role": "user",
                                    "content": response_content
                                })
                        except Exception as parse_err:
                            print(f"[Agent] XML Parse Error: {parse_err}")
                    continue

            # 3. Final Response
            final_output = self._strip_thought(content)

            # Save final assistant response to memory
            self.memory.add_message("assistant", final_output)
            self.memory.save_to_file()
            
            self._write_telemetry("session_end", {"final_response": final_output})
            return final_output

        abort_msg = "Agent reached maximum iterations without finishing."
        self._write_telemetry("session_abort", {"reason": abort_msg})
        return abort_msg

_global_agent = None

def run_chemistry_agent(user_query: str) -> str:
    """Wrapper for the ChemistryAgent class. Maintains a global instance for memory persistence."""
    global _global_agent
    if _global_agent is None:
        _global_agent = ChemistryAgent()
    return _global_agent.run(user_query)
