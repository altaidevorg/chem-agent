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
        """Calculates the total tokens that would be sent to the LLM."""
        total = self.count_tokens(system_prompt)
        for msg in self.messages:
            total += self.count_tokens(msg.get("content", ""))
        return total

    def compact_tool_results(self):
        """Prunes large tool results to save space, keeping only a summary placeholder."""
        for msg in self.messages:
            if msg.get("role") == "tool" and len(msg.get("content", "")) > 500:
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
            # Keep the last 4 messages verbatim, summarize everything before that
            if len(self.messages) > 6:
                to_summarize = self.messages[:-4]
                keep_verbatim = self.messages[-4:]
                
                summary_prompt = "Please provide a concise summary of the following conversation history, focusing on key findings, data points, and decisions made. This summary will be used as context for future turns."
                history_text = "\n".join([f"{m['role']}: {m['content']}" for m in to_summarize])
                
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
                    # Fallback: Just drop the oldest 2 messages if summarization fails
                    self.messages = self.messages[2:]

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
