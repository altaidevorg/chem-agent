# src/agent/memory.py
import json
import os
import threading
import tiktoken
from datetime import datetime
from typing import List, Dict, Any, Optional

from src.config import SESSIONS_DIR, MAX_CONTEXT_TOKENS, COMPACTION_THRESHOLD


def _serialize_tool_calls(tool_calls: List[Any]) -> List[Dict[str, Any]]:
    """Converts SDK tool call objects into JSON-serializable dicts."""
    serialized: List[Dict[str, Any]] = []
    for tc in tool_calls:
        if isinstance(tc, dict):
            serialized.append(tc)
            continue
        if hasattr(tc, "model_dump"):
            serialized.append(tc.model_dump())
            continue
        fn = getattr(tc, "function", None)
        serialized.append({
            "id": getattr(tc, "id", None),
            "type": getattr(tc, "type", "function"),
            "function": {
                "name": getattr(fn, "name", None) if fn else None,
                "arguments": getattr(fn, "arguments", None) if fn else None,
            },
        })
    return serialized


class AgentMemory:
    """
    Manages the agent's short-term and contextual memory.
    Supports thread-safe operations and asynchronous background compaction using Reentrant Lock.
    """
    
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.messages: List[Dict[str, str]] = []
        self.entities: Dict[str, Dict[str, Any]] = {}  # Track molecules by name/smiles
        self.active_tools: List[str] = [] # Track discovered tool names for this session
        self.summary: Optional[str] = None # Stores the condensed conversation summary
        self.metadata: Dict[str, Any] = {
            "start_time": datetime.now().isoformat(),
            "last_interaction": None
        }
        self._tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # --- Thread Safety & Async Control ---
        # CRITICAL FIX: Use RLock (Reentrant Lock) to prevent self-deadlock when methods call each other
        self._lock = threading.RLock()
        self._compaction_thread: Optional[threading.Thread] = None

    def count_tokens(self, text: str) -> int:
        """Counts the number of tokens in a string."""
        return len(self._tokenizer.encode(text))

    def get_total_tokens(self, system_prompt: str) -> int:
        """Calculates the total tokens, including messages and dynamic tool overhead."""
        with self._lock:
            # Dynamic tool overhead: Active scoped tools + mandatory tools
            num_active_tools = len(self.active_tools) + 2
            tool_overhead = num_active_tools * 120
            
            total = self.count_tokens(system_prompt) + tool_overhead
            for msg in self.messages:
                content = msg.get("content") or ""
                total += self.count_tokens(content)
                
                if "tool_calls" in msg and msg["tool_calls"]:
                    for tc in msg["tool_calls"]:
                        if isinstance(tc, dict):
                            total += self.count_tokens(json.dumps(tc))
                        else:
                            try:
                                total += self.count_tokens(str(tc))
                            except Exception:
                                pass
                
                if msg.get("role") == "tool":
                    total += self.count_tokens(msg.get("tool_call_id", ""))
                    total += self.count_tokens(msg.get("name", ""))
                    
            return total

    def ensure_compaction_finished(self, timeout: float = 2.5):
        """Waits briefly for background compaction if it's currently running."""
        if self._compaction_thread and self._compaction_thread.is_alive():
            print("[Memory] Waiting for background compaction worker to finish...")
            self._compaction_thread.join(timeout=timeout)

    def compact_tool_results_fast(self, force_last: bool = False):
        """Fast synchronous tool result pruning (sub-millisecond operation)."""
        with self._lock:
            if not self.messages:
                return

            metadata_tools = ["inspect_dataset", "list_files", "search_columns"]

            for i in range(len(self.messages)):
                msg = self.messages[i]
                if msg.get("role") == "tool" and isinstance(msg.get("content"), str) and len(msg["content"]) > 500:
                    tool_name = msg.get("name")
                    if tool_name in metadata_tools and not force_last:
                        continue

                    has_subsequent_assistant = any(
                        self.messages[j].get("role") == "assistant"
                        for j in range(i + 1, len(self.messages))
                    )
                    
                    if has_subsequent_assistant:
                        original_len = len(msg["content"])
                        msg["content"] = f"[Tool result pruned. Original size: {original_len} chars. Data already processed by assistant in previous turns.]"
                    elif force_last and i == len(self.messages) - 1:
                        original_len = len(msg["content"])
                        msg["content"] = msg["content"][:1000] + f"\n... [TRUNCATED DUE TO SIZE: {original_len} chars total] ..."

    def check_and_compact(self, agent, system_prompt: str, force: bool = False):
        """Synchronous version of compaction for immediate relief before API calls."""
        # 1. Fast tool pruning first
        self.compact_tool_results_fast(force_last=force)

        with self._lock:
            total_tokens = self.get_total_tokens(system_prompt)
            # Use lower threshold for sync check to ensure space
            threshold = MAX_CONTEXT_TOKENS * 0.85 

            # If not forced, check if we actually need compaction
            if not force and (total_tokens <= threshold or len(self.messages) <= 6):
                return

            # Determine split index ensuring no orphaned tool messages
            messages_snapshot = list(self.messages)
            split_idx = len(messages_snapshot) - 4
            while split_idx > 0:
                orphaned = False
                for i in range(split_idx, len(messages_snapshot)):
                    msg = messages_snapshot[i]
                    if msg.get('role') == 'tool':
                        tool_call_id = msg.get('tool_call_id')
                        has_parent = False
                        for j in range(split_idx, i):
                            parent = messages_snapshot[j]
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
                    split_idx -= 1
                else:
                    break

            if split_idx <= 0:
                return

            to_summarize = messages_snapshot[:split_idx]
            keep_verbatim = messages_snapshot[split_idx:]
            
            summary_prompt = "Please provide a concise summary of the following conversation history, focusing on key findings, data points, and decisions made. This summary will be used as context for future turns."
            history_text = "\n".join([f"{m['role']}: {m.get('content', '')}" for m in to_summarize])

            try:
                response = agent.client.chat.completions.create(
                    model=agent.model_name,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant that summarizes conversation history."},
                        {"role": "user", "content": f"{summary_prompt}\n\nHistory:\n{history_text}"}
                    ],
                    temperature=0.1
                )
                new_summary = response.choices[0].message.content

                if self.summary:
                    self.summary = f"{self.summary}\n\nAdditionally: {new_summary}"
                else:
                    self.summary = new_summary

                summary_guard = (
                    "[SYSTEM_SUMMARY_NOTE: The following is an internal archived memory. "
                    "DO NOT quote, repeat, or format this summary in your visible response to the user.]"
                )
                
                self.messages = [
                    {"role": "user", "content": f"{summary_guard}\n\n[CONVERSATION SUMMARY]:\n{self.summary}"},
                    {"role": "assistant", "content": "Understood. I have absorbed the archived summary and will rely on it for context without repeating it."}
                ] + keep_verbatim

            except Exception as e:
                print(f"[Memory Error] Sync compaction failed: {e}")

    def trigger_async_compaction(self, agent, system_prompt: str):
        """Launches background compaction thread if tokens exceed the threshold."""
        # Prevent starting multiple compaction worker threads simultaneously
        if self._compaction_thread and self._compaction_thread.is_alive():
            return

        total_tokens = self.get_total_tokens(system_prompt)
        threshold = MAX_CONTEXT_TOKENS * COMPACTION_THRESHOLD

        if total_tokens > threshold:
            self._compaction_thread = threading.Thread(
                target=self._run_async_compaction_worker,
                args=(agent, system_prompt),
                daemon=True
            )
            self._compaction_thread.start()
            print("[Memory] Background compaction thread launched.")

    def _run_async_compaction_worker(self, agent, system_prompt: str):
        """Background worker executing LLM summarization without blocking the main turn."""
        try:
            # 1. Fast tool pruning first
            self.compact_tool_results_fast()

            with self._lock:
                current_tokens = self.get_total_tokens(system_prompt)
                threshold = MAX_CONTEXT_TOKENS * COMPACTION_THRESHOLD
                messages_snapshot = list(self.messages)

            if current_tokens <= threshold or len(messages_snapshot) <= 6:
                return

            # Determine split index ensuring no orphaned tool messages
            split_idx = len(messages_snapshot) - 4
            while split_idx > 0:
                orphaned = False
                for i in range(split_idx, len(messages_snapshot)):
                    msg = messages_snapshot[i]
                    if msg.get('role') == 'tool':
                        tool_call_id = msg.get('tool_call_id')
                        has_parent = False
                        for j in range(split_idx, i):
                            parent = messages_snapshot[j]
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
                    split_idx -= 1
                else:
                    break

            if split_idx <= 0:
                return

            to_summarize = messages_snapshot[:split_idx]
            summary_prompt = "Please provide a concise summary of the following conversation history, focusing on key findings, data points, and decisions made. This summary will be used as context for future turns."
            history_text = "\n".join([f"{m['role']}: {m.get('content', '')}" for m in to_summarize])

            # LLM API Call (Executed asynchronously in background thread - NO LOCK HELD HERE)
            response = agent.client.chat.completions.create(
                model=agent.model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes conversation history."},
                    {"role": "user", "content": f"{summary_prompt}\n\nHistory:\n{history_text}"}
                ],
                temperature=0.1
            )
            new_summary = response.choices[0].message.content

            # Thread-safe atomic update of the message stack
            with self._lock:
                if self.summary:
                    self.summary = f"{self.summary}\n\nAdditionally: {new_summary}"
                else:
                    self.summary = new_summary

                # Replace summarized messages with the summary marker using user role for API safety
                summary_guard = (
                    "[SYSTEM_SUMMARY_NOTE: The following is an internal archived memory. "
                    "DO NOT quote, repeat, or format this summary in your visible response to the user.]"
                )
                
                # Identify any new messages added while summarization was running
                new_messages_during_async = self.messages[len(messages_snapshot):]
                keep_verbatim = messages_snapshot[split_idx:] + new_messages_during_async

                self.messages = [
                    {"role": "user", "content": f"{summary_guard}\n\n[CONVERSATION SUMMARY]:\n{self.summary}"},
                    {"role": "assistant", "content": "Understood. I have absorbed the archived summary and will rely on it for context without repeating it."}
                ] + keep_verbatim

            agent._write_telemetry("async_memory_compaction_success", {
                "new_token_count": self.get_total_tokens(system_prompt)
            })

        except Exception as e:
            agent._write_telemetry("async_memory_compaction_error", {"error": str(e)})

    def add_message(self, role: str, content: str, tool_calls: Optional[List[Any]] = None):
        """Adds a message to the conversation history."""
        with self._lock:
            message = {"role": role, "content": content}
            if tool_calls:
                message["tool_calls"] = _serialize_tool_calls(tool_calls)
            self.messages.append(message)
            self.metadata["last_interaction"] = datetime.now().isoformat()

    def add_tool_response(self, tool_call_id: str, name: str, content: str):
        """Adds a tool response to the conversation history."""
        with self._lock:
            self.messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": name,
                "content": content
            })

    def update_entity(self, name: Optional[str], smiles: Optional[str], properties: Optional[Dict[str, Any]] = None):
        """Tracks or updates a chemical entity in memory."""
        with self._lock:
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
        with self._lock:
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
        with self._lock:
            self.messages = []
            self.entities = {}
            self.active_tools = []
            self.summary = None
            self.metadata["last_interaction"] = datetime.now().isoformat()

    def save_to_file(self, folder: str = SESSIONS_DIR):
        """Persists the current session memory to a JSON file."""
        with self._lock:
            os.makedirs(folder, exist_ok=True)
            filepath = os.path.join(folder, f"session_{self.session_id}.json")
            data = {
                "metadata": self.metadata,
                "entities": self.entities,
                "active_tools": self.active_tools,
                "messages": self.messages
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return filepath
