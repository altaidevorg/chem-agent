import json
import os
import pandas as pd
from datetime import datetime

LOG_FILE = "logs/agent_execution_logs.jsonl"

def analyze_metrics():
    if not os.path.exists(LOG_FILE):
        print(f"Log file {LOG_FILE} not found.")
        return

    sessions = []
    current_session = None

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                event = json.loads(line)
                event_type = event.get("event_type")

                if event_type == "session_start":
                    current_session = {
                        "start_time": event["timestamp"],
                        "query": event["user_query"],
                        "turns": 0,
                        "total_tokens": 0,
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_latency_ms": 0,
                        "tool_calls": [],
                        "status": "in_progress"
                    }
                elif event_type == "model_response" and current_session:
                    current_session["turns"] += 1
                    usage = event.get("usage", {})
                    current_session["prompt_tokens"] += usage.get("prompt_tokens", 0)
                    current_session["completion_tokens"] += usage.get("completion_tokens", 0)
                    current_session["total_tokens"] += usage.get("total_tokens", 0)
                    current_session["total_latency_ms"] += event.get("latency_ms", 0)
                elif event_type == "tool_execution" and current_session:
                    tool_name = event.get("tool")
                    result = event.get("result", {})
                    exec_time = result.get("_execution_time_ms", 0)
                    
                    # Estimate token usage by tool result size (roughly 4 chars per token)
                    result_str = json.dumps(result)
                    result_size_chars = len(result_str)
                    
                    current_session["tool_calls"].append({
                        "tool": tool_name,
                        "time_ms": exec_time,
                        "result_size_chars": result_size_chars
                    })
                elif event_type == "session_end" and current_session:
                    current_session["end_time"] = event["timestamp"]
                    current_session["status"] = "completed"
                    sessions.append(current_session)
                    current_session = None
                elif event_type == "session_abort" and current_session:
                    current_session["end_time"] = event["timestamp"]
                    current_session["status"] = "aborted"
                    sessions.append(current_session)
                    current_session = None
            except Exception as e:
                continue

    if not sessions:
        print("No completed sessions found in logs.")
        return

    df = pd.DataFrame(sessions)
    
    print("\n" + "="*50)
    print("      🧪 AGENT PERFORMANCE METRICS REPORT")
    print("="*50)
    
    print(f"Total Sessions Analyzed: {len(df)}")
    print(f"Success Rate: {(df['status'] == 'completed').mean()*100:.1f}%")
    
    print("\n--- Efficiency Metrics (Averages) ---")
    print(f"Turns per Session:    {df['turns'].mean():.2f}")
    
    # Filter out sessions with zero tokens (old logs)
    token_df = df[df['total_tokens'] > 0]
    if not token_df.empty:
        print(f"Total Tokens/Session: {token_df['total_tokens'].mean():.0f}")
        print(f"Prompt Tokens:        {token_df['prompt_tokens'].mean():.0f}")
        print(f"Completion Tokens:    {token_df['completion_tokens'].mean():.0f}")
        print(f"Latency/Turn (ms):    {token_df['total_latency_ms'].sum() / token_df['turns'].sum():.0f}")
    else:
        print("Token/Latency data not available for old logs.")

    print("\n--- Tool Usage Analytics ---")
    all_tools = []
    for tc in df['tool_calls']:
        all_tools.extend(tc)
    
    if all_tools:
        tool_df = pd.DataFrame(all_tools)
        tool_stats = tool_df.groupby('tool').agg(
            count=('tool', 'count'),
            avg_time_ms=('time_ms', 'mean'),
            avg_size_chars=('result_size_chars', 'mean')
        ).sort_values('count', ascending=False)
        
        # Add an estimated token column (4 chars per token)
        tool_stats['est_result_tokens'] = (tool_stats['avg_size_chars'] / 4).round(0).astype(int)
        
        print(tool_stats.to_string())
    else:
        print("No tool execution data recorded yet.")

    print("="*50 + "\n")

if __name__ == "__main__":
    analyze_metrics()
