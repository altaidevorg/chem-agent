# src/agent/core.py
import json
import re
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

from src.vllm_client import get_vllm_client
from src.config import MODEL_NAME, MAX_ITERATIONS, TEMPERATURE, TELEMETRY_LOG_FILE, THOUGHT_LOGS_DIR
from src.agent.prompts import SYSTEM_PROMPT
from src.agent.memory import AgentMemory
from src.skills.base import SkillRegistry
# Import skills to ensure they are registered
import src.skills.rdkit_skills
import src.skills.file_skills

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
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[Logger Error] Failed to write telemetry: {e}")

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
        """Retrieves tool definitions from the SkillRegistry."""
        return SkillRegistry.get_tool_definitions()

    def _execute_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a tool by name using the SkillRegistry and updates memory."""
        skill = SkillRegistry.get_skill(name)
        if not skill:
            return {"error": f"Tool '{name}' not found in registry."}
        
        try:
            result = skill.execute(**arguments)
            
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
        
        # Inject current chemical context into the system prompt
        context_summary = self.memory.get_context_summary()
        current_system_prompt = f"{SYSTEM_PROMPT}\n\n{context_summary}"
        
        # Initialize messages for this specific run with full conversation history
        run_messages = [{"role": "system", "content": current_system_prompt}]
        for msg in self.memory.messages:
            run_messages.append(msg)
        run_messages.append({"role": "user", "content": user_query})
        
        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1
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
            thought = ""
            if "<think>" in content and "</think>" in content:
                thought = content.split("<think>")[1].split("</think>")[0].strip()
            elif "</think>" in content:
                thought = content.split("</think>")[0].strip()
            
            if thought:
                self._log_thought(iteration, thought)

            self._write_telemetry("model_response", {
                "iteration": iteration,
                "has_thought": bool(thought),
                "tool_calls": bool(response_message.tool_calls)
            })

            # 1. Handle Native Tool Calls
            if response_message.tool_calls:
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
                    
                    run_messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": json.dumps(result)
                    })
                continue

            # 2. Handle XML Fallback
            if "<tool_call>" in content:
                print(f"[Agent] Detected XML tool call fallback. Parsing...")
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
                                
                                run_messages.append({
                                    "role": "user",
                                    "content": f"[SYSTEM TOOL RESPONSE]\n<tool_response>\n{json.dumps(result)}\n</tool_response>"
                                })
                        except Exception as parse_err:
                            print(f"[Agent] XML Parse Error: {parse_err}")
                    continue

            # 3. Final Response
            final_output = content
            if "</think>" in final_output:
                final_output = final_output.split("</think>")[-1].strip()
            
            # Save interaction to memory
            self.memory.add_message("user", user_query)
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
