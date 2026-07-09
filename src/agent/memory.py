# src/agent/memory.py
import json
import os
import tiktoken
from datetime import datetime
from typing import List, Dict, Any, Optional

from src.config import SESSIONS_DIR, MAX_CONTEXT_TOKENS, COMPACTION_THRESHOLD

class AgentMemory:
    """
    Manages the agent's short-term and contextual memory.
    Stores conversation history and chemical entity tracking.
    """
    
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.messages: List[Dict[str, str]] = []
        self.entities: Dict[str, Dict[str, Any]] = {}  # Track molecules by name/smiles
        self.summary: Optional[str] = None # Stores the condensed conversation summary
        self.metadata: Dict[str, Any] = {
            "start_time": datetime.now().isoformat(),
            "last_interaction": None
        }
        self._tokenizer = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Counts the number of tokens in a string."""
        return len(self._tokenizer.encode(text))

    def get_total_tokens(self, system_prompt: str) -> int:
        """Calculates the total tokens that would be sent to the LLM, including metadata and tool calls."""
        total = self.count_tokens(system_prompt)
        for msg in self.messages:
            # Count content
            content = msg.get("content") or ""
            total += self.count_tokens(content)
            
            # Count tool calls if present (assistant role)
            if "tool_calls" in msg and msg["tool_calls"]:
                for tc in msg["tool_calls"]:
                    # Handle both dict and object types for tool calls
                    if isinstance(tc, dict):
                        total += self.count_tokens(json.dumps(tc))
                    else:
                        # Fallback for objects (like from OpenAI SDK)
                        try:
                            total += self.count_tokens(str(tc))
                        except:
                            pass
            
            # Count tool metadata (tool role)
            if msg.get("role") == "tool":
                total += self.count_tokens(msg.get("tool_call_id", ""))
                total += self.count_tokens(msg.get("name", ""))
                
        return total

    def compact_tool_results(self):
        """Prunes large tool results to save space, keeping only a summary placeholder."""
        for msg in self.messages:
            if msg.get("role") == "tool" and isinstance(msg.get("content"), str) and len(msg["content"]) > 500:
                original_len = len(msg["content"])
                # Keep a small snippet or just a placeholder
                msg["content"] = f"[Tool result pruned. Original size: {original_len} chars. Data already processed by assistant.]"

    def check_and_compact(self, agent, system_prompt: str):
        """Checks if the token limit is reached and triggers compaction if necessary."""
        total_tokens = self.get_total_tokens(system_prompt)
        threshold = MAX_CONTEXT_TOKENS * COMPACTION_THRESHOLD

        if total_tokens > threshold:
            print(f"[Memory] ⚠️ Token count ({total_tokens}) exceeded threshold ({threshold}). Compacting...")
            
            # 1. First attempt: Prune tool results
            self.compact_tool_results()
            
            # Re-check tokens
            total_tokens = self.get_total_tokens(system_prompt)
            if total_tokens <= threshold:
                print(f"[Memory] ✅ Compaction successful via tool pruning. New count: {total_tokens}")
                return

            # 2. Second attempt: Summarize old history
            # We need to find a safe split point to avoid orphaning tool messages
            if len(self.messages) > 6:
                # Start by trying to keep the last 4 messages
                split_idx = len(self.messages) - 4
                
                # Dynamically adjust split_idx to ensure no orphaned tool messages
                while split_idx > 0:
                    orphaned = False
                    for i in range(split_idx, len(self.messages)):
                        msg = self.messages[i]
                        if msg.get('role') == 'tool':
                            tool_call_id = msg.get('tool_call_id')
                            has_parent = False
                            # Look for the parent assistant message within the 'keep_verbatim' part
                            for j in range(split_idx, i):
                                parent = self.messages[j]
                                if parent.get('role') == 'assistant' and parent.get('tool_calls'):
                                    for tc in parent['tool_calls']:
                                        tc_id = tc.get('id') if isinstance(tc, dict) else getattr(tc, 'id', None)
                                        if tc_id == tool_call_id:
                                            has_parent = True
                                            break
                                    if has_parent:
                                        break
                            if not has_parent:
                                orphaned = True
                                break
                    
                    if orphaned:
                        split_idx -= 1 # Move back to include the parent assistant message
                    else:
                        break
                
                if split_idx <= 0:
                    print("[Memory] ⚠️ Could not find a safe split point for compaction. Skipping summarization.")
                    return

                to_summarize = self.messages[:split_idx]
                keep_verbatim = self.messages[split_idx:]
                
                summary_prompt = "Please provide a concise summary of the following conversation history, focusing on key findings, data points, and decisions made. This summary will be used as context for future turns."
                history_text = "\n".join([f"{m['role']}: {m.get('content', '')}" for m in to_summarize])
                
                try:
                    # We call the agent's client directly to avoid recursion
                    response = agent.client.chat.completions.create(
                        model=agent.model_name,
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant that summarizes conversation history."},
                            {"role": "user", "content": f"{summary_prompt}\n\nHistory:\n{history_text}"}
                        ],
                        temperature=0.1
                    )
                    new_summary = response.choices[0].message.content
                    
                    # Update the summary
                    if self.summary:
                        self.summary = f"{self.summary}\n\nAdditionally: {new_summary}"
                    else:
                        self.summary = new_summary
                        
                    # Replace summarized messages with the summary marker
                    self.messages = [
                        {"role": "system", "content": f"[CONVERSATION SUMMARY]: {self.summary}"}
                    ] + keep_verbatim
                    
                    print(f"[Memory] ✅ Compaction successful via summarization. New count: {self.get_total_tokens(system_prompt)}")
                except Exception as e:
                    print(f"[Memory Error] Failed to summarize: {e}")
                    # Fallback: Drop the oldest message and try to find a safe state
                    # Instead of just dropping 2, we drop 1 and let the next turn try again
                    # or we could find the first safe split point from the beginning.
                    if len(self.messages) > 2:
                        self.messages = self.messages[1:]
                        # Ensure we don't start with a tool message
                        while self.messages and self.messages[0].get('role') == 'tool':
                            self.messages = self.messages[1:]

    def add_message(self, role: str, content: str, tool_calls: Optional[List[Any]] = None):
        """Adds a message to the conversation history."""
        message = {"role": role, "content": content}
        if tool_calls:
            message["tool_calls"] = tool_calls
        self.messages.append(message)
        self.metadata["last_interaction"] = datetime.now().isoformat()

    def add_tool_response(self, tool_call_id: str, name: str, content: str):
        """Adds a tool response to the conversation history."""
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": content
        })

    def update_entity(self, name: Optional[str], smiles: Optional[str], properties: Optional[Dict[str, Any]] = None):
        """Tracks or updates a chemical entity in memory."""
        key = name or smiles
        if not key:
            return
            
        if key not in self.entities:
            self.entities[key] = {}
            
        if name: self.entities[key]["name"] = name
        if smiles: self.entities[key]["smiles"] = smiles
        if properties:
            if "properties" not in self.entities[key]:
                self.entities[key]["properties"] = {}
            self.entities[key]["properties"].update(properties)

    def get_context_summary(self) -> str:
        """Generates a text summary of the current chemical context for the LLM."""
        if not self.entities:
            return "No chemical entities resolved in this session yet."
            
        summary = "Current Chemical Context:\n"
        for key, data in self.entities.items():
            name = data.get("name", "Unknown")
            smiles = data.get("smiles", "N/A")
            summary += f"- {name}: SMILES={smiles}\n"
            if "properties" in data:
                summary += f"  Properties: {list(data['properties'].keys())}\n"
        return summary

    def clear(self):
        """Resets the memory."""
        self.messages = []
        self.entities = {}
        self.metadata["last_interaction"] = datetime.now().isoformat()

    def save_to_file(self, folder: str = SESSIONS_DIR):
        """Persists the current session memory to a JSON file."""
        os.makedirs(folder, exist_ok=True)
        filepath = os.path.join(folder, f"session_{self.session_id}.json")
        data = {
            "metadata": self.metadata,
            "entities": self.entities,
            "messages": self.messages
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return filepath
