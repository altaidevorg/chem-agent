# src/agent/core.py
import json
import re
import os
from datetime import datetime
from src.vllm_client import get_vllm_client, MODEL_NAME
from src.agent.prompts import SYSTEM_PROMPT, AVAILABLE_TOOLS
from src.skills.rdkit_skills import calculate_molecular_properties, search_substructure, calculate_molecular_similarity, resolve_name_to_smiles
from src.skills.file_skills import read_file, write_file

client = get_vllm_client()

LOG_FILE_PATH = "agent_execution_logs.jsonl"

def write_jsonl_log(event_type: str, data: dict):
    """Helper function to write structured logs into a JSONL file."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        **data
    }
    try:
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[Logger Error] Failed to write log to JSONL: {e}")


def run_chemistry_agent(user_query: str):
    write_jsonl_log("session_start", {"user_query": user_query})
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query}
    ]
    
    # Oturum bazlı akıllı araç zincirleme hafızası (Stateful Pipeline Memory)
    session_memory = {
        "last_resolved_smiles": None,
        "last_resolved_name": None
    }
    
    max_iterations = 10
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        print(f"[Agent] (Turn {iteration}) Initiating model completion request...")
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=AVAILABLE_TOOLS,
            tool_choice="auto",
            temperature=0.1
        )
        
        response_message = response.choices[0].message
        messages.append(response_message)
        
        write_jsonl_log("model_response", {
            "iteration": iteration,
            "raw_content": response_message.content,
            "has_native_tool_calls": bool(response_message.tool_calls)
        })
        
        tool_calls_to_process = []
        is_xml_fallback = False
        
        # 1. Standard Native Tool Call Parser
        if response_message.tool_calls:
            for tc in response_message.tool_calls:
                tool_calls_to_process.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments)
                })
                
        # 2. XML Tag Fallback Parser with Advanced Regex Auto-Repair
        elif response_message.content and "<tool_call>" in response_message.content:
            print(f"[Agent] Detected raw XML tool call in text content at turn {iteration}. Processing...")
            is_xml_fallback = True
            
            xml_matches = re.findall(r'<tool_call>(.*?)</tool_call>', response_message.content, re.DOTALL)
            for match in xml_matches:
                cleaned_match = match.strip()
                try:
                    parsed_call = json.loads(cleaned_match)
                    tool_calls_to_process.append({
                        "id": "xml_fallback_id",
                        "name": parsed_call.get("name"),
                        "arguments": parsed_call.get("arguments")
                    })
                except json.JSONDecodeError as json_error:
                    print(f"[Warning] Standard JSON parsing failed due to string escaping. Activating Regex Recovery...")
                    
                    name_match = re.search(r'"name"\s*:\s*"([^"]+)"', cleaned_match)
                    if name_match:
                        func_name = name_match.group(1)
                        args_dict = {}
                        
                        if func_name == "write_file":
                            path_match = re.search(r'"(?:file_path|path|file|filename)"\s*:\s*"([^"]+)"', cleaned_match)
                            content_match = re.search(r'"(?:content|text|data)"\s*:\s*"(.*)"', cleaned_match, re.DOTALL)
                            
                            if path_match and content_match:
                                target_path = path_match.group(1)
                                raw_content = content_match.group(1)
                                raw_content = re.sub(r'"\s*\}\s*\}?\s*$', '', raw_content)
                                raw_content = raw_content.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"')
                                
                                args_dict["file_path"] = target_path
                                args_dict["content"] = raw_content
                                
                                tool_calls_to_process.append({
                                    "id": "xml_fallback_id",
                                    "name": func_name,
                                    "arguments": args_dict
                                })
                                print(f"[Success] Regex Recovery successfully bypassed JSON deformation for 'write_file'!")
                                continue
                    print(f"[Error] Critical: Advanced Regex recovery pipeline also aborted: {json_error}")

        # Final loop termination clause
        if not tool_calls_to_process:
            print(f"[Agent] Execution finished successfully at turn {iteration}.")
            
            final_output = response_message.content if response_message.content else ""
            if "</think>" in final_output:
                final_output = final_output.split("</think>")[-1].strip()
            
            write_jsonl_log("session_end", {"final_response": final_output})
            return final_output

        # 3. Dynamic Execution Routing Execution Blocks
        print(f"[Agent] Processing {len(tool_calls_to_process)} tool execution task(s)...")
        for tool_call in tool_calls_to_process:
            function_name = tool_call["name"]
            function_args = tool_call["arguments"]
            tool_result = {"error": "Unknown function"}
            
            # --- ARCHITECTURAL PROXY: AKILLI DURUM VE ZİNCİRLEME İYİLEŞTİRME SİSTEMİ ---
            # Eğer model bir kimyasal özellik hesaplama çağrısı yapıyorsa ve hafızamızda doğrulanmış bir SMILES varsa:
            if "smiles" in function_args and session_memory["last_resolved_smiles"]:
                model_smiles = function_args["smiles"]
                exact_smiles = session_memory["last_resolved_smiles"]
                
                # Model kopyalama esnasında Attention Glitch yaşayıp string'i eksik veya kırık yazdıysa (yarı yarıya uyuşma kontrolü)
                if model_smiles != exact_smiles and (exact_smiles[:15] == model_smiles[:15] or len(model_smiles) > len(exact_smiles) * 0.7):
                    print(f"[Core Architecture Proxy] Attention Glitch detected! Auto-healing and injecting the exact verified SMILES from session memory.")
                    function_args["smiles"] = exact_smiles
            
            # Benzer düzeltmeyi smiles1 ve smiles2 parametreleri gerektiren similarity fonksiyonu için de yapıyoruz
            if "smiles1" in function_args and session_memory["last_resolved_smiles"]:
                if function_args["smiles1"] != session_memory["last_resolved_smiles"] and session_memory["last_resolved_smiles"][:15] == function_args["smiles1"][:15]:
                    function_args["smiles1"] = session_memory["last_resolved_smiles"]

            # --- DYNAMIC ROUTING ---
            if function_name == "resolve_name_to_smiles":
                molecule_name = function_args.get("molecule_name")
                print(f"[PubChem Tool] Resolving molecule name to SMILES for: '{molecule_name}'")
                tool_result = resolve_name_to_smiles(molecule_name)
                print(f"[PubChem Tool] Execution Result -> {json.dumps(tool_result)}")
                
                # Başarılı aramayı hemen hafızaya kaydet (Bir sonraki adıma paslamak için)
                if "smiles" in tool_result:
                    session_memory["last_resolved_smiles"] = tool_result["smiles"]
                    session_memory["last_resolved_name"] = molecule_name

            elif function_name == "calculate_molecular_properties":
                target_smiles = function_args.get("smiles")
                print(f"[RDKit Tool] Executing property calculation for SMILES: '{target_smiles}'")
                tool_result = calculate_molecular_properties(target_smiles)
                print(f"[RDKit Tool] Execution Result -> {json.dumps(tool_result)}")
                
            elif function_name == "search_substructure":
                target_smiles = function_args.get("smiles")
                target_pattern = function_args.get("pattern")
                print(f"[RDKit Tool] Searching substructure pattern '{target_pattern}' in SMILES '{target_smiles}'")
                tool_result = search_substructure(target_smiles, target_pattern)
                print(f"[RDKit Tool] Execution Result -> {json.dumps(tool_result)}")
                
            elif function_name == "calculate_molecular_similarity":
                s1, s2 = function_args.get("smiles1"), function_args.get("smiles2")
                print(f"[RDKit Tool] Calculating Tanimoto similarity between '{s1}' and '{s2}'")
                tool_result = calculate_molecular_similarity(s1, s2)
                print(f"[RDKit Tool] Execution Result -> {json.dumps(tool_result)}")
                
            elif function_name == "read_file":
                target_path = function_args.get("file_path") or function_args.get("path") or function_args.get("file") or function_args.get("filename")
                print(f"[File Tool] Reading target file content from path: {target_path}")
                tool_result = read_file(target_path)
                
            elif function_name == "write_file":
                target_path = function_args.get("file_path") or function_args.get("path") or function_args.get("file") or function_args.get("filename")
                file_content = function_args.get("content") or function_args.get("text") or function_args.get("data")
                print(f"[File Tool] Writing output report file to path: {target_path}")
                tool_result = write_file(target_path, file_content)
            
            write_jsonl_log("tool_execution", {
                "iteration": iteration,
                "tool_name": function_name,
                "arguments": function_args,
                "result": tool_result
            })
            
            if is_xml_fallback:
                messages.append({
                    "role": "user",
                    "content": f"[SYSTEM TOOL RESPONSE]\n<tool_response>\n{json.dumps(tool_result)}\n</tool_response>"
                })
            else:
                messages.append({
                    "tool_call_id": tool_call["id"],
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps(tool_result)
                })
                
    write_jsonl_log("session_abort", {"reason": "Reached maximum allowed reasoning/execution turns (10)."})
    return "Agent aborted: Reached maximum allowed reasoning/execution turns (10)."