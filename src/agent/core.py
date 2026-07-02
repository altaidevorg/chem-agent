# src/agent/core.py
import json
import re
from src.vllm_client import get_vllm_client, MODEL_NAME
from src.agent.prompts import SYSTEM_PROMPT, AVAILABLE_TOOLS
from src.skills.rdkit_skills import calculate_molecular_properties, search_substructure, calculate_molecular_similarity
from src.skills.file_skills import read_file, write_file

client = get_vllm_client()

def run_chemistry_agent(user_query: str):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query}
    ]
    
    max_iterations = 5
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
                    # Attempt standard JSON loading first
                    parsed_call = json.loads(cleaned_match)
                    tool_calls_to_process.append({
                        "id": "xml_fallback_id",
                        "name": parsed_call.get("name"),
                        "arguments": parsed_call.get("arguments")
                    })
                except json.JSONDecodeError as json_error:
                    print(f"[Warning] Standard JSON parsing failed due to string escaping. Activating Regex Recovery...")
                    
                    # Extraction Fallback Step A: Catch the function name
                    name_match = re.search(r'"name"\s*:\s*"([^"]+)"', cleaned_match)
                    if name_match:
                        func_name = name_match.group(1)
                        args_dict = {}
                        
                        if func_name == "write_file":
                            # Extraction Fallback Step B: Pull out path and text contents via granular regex rules
                            path_match = re.search(r'"(?:file_path|path|file|filename)"\s*:\s*"([^"]+)"', cleaned_match)
                            content_match = re.search(r'"(?:content|text|data)"\s*:\s*"(.*)"', cleaned_match, re.DOTALL)
                            
                            if path_match and content_match:
                                target_path = path_match.group(1)
                                raw_content = content_match.group(1)
                                
                                # Clean trailing structural JSON syntax artifacts safely
                                raw_content = re.sub(r'"\s*\}\s*\}?\s*$', '', raw_content)
                                
                                # Re-hydrate escaped sequence format strings back to native plaintext
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
            return response_message.content

        # 3. Dynamic Execution Routing Execution Blocks
        print(f"[Agent] Processing {len(tool_calls_to_process)} tool execution task(s)...")
        for tool_call in tool_calls_to_process:
            function_name = tool_call["name"]
            function_args = tool_call["arguments"]
            tool_result = {"error": "Unknown function"}
            
            if function_name == "calculate_molecular_properties":
                print(f"[RDKit Tool] Executing property calculation...")
                tool_result = calculate_molecular_properties(function_args.get("smiles"))
                
            elif function_name == "search_substructure":
                tool_result = search_substructure(function_args.get("smiles"), function_args.get("pattern"))
                
            elif function_name == "calculate_molecular_similarity":
                tool_result = calculate_molecular_similarity(function_args.get("smiles1"), function_args.get("smiles2"))
                
            elif function_name == "read_file":
                target_path = function_args.get("file_path") or function_args.get("path") or function_args.get("file") or function_args.get("filename")
                print(f"[File Tool] Reading target file content: {target_path}")
                tool_result = read_file(target_path)
                
            elif function_name == "write_file":
                target_path = function_args.get("file_path") or function_args.get("path") or function_args.get("file") or function_args.get("filename")
                file_content = function_args.get("content") or function_args.get("text") or function_args.get("data")
                print(f"[File Tool] Writing output report file to path: {target_path}")
                tool_result = write_file(target_path, file_content)
            
            # Send results log back into context queue
            if is_xml_fallback:
                messages.append({
                    "role": "user",
                    "content": f"<tool_response>\n{json.dumps(tool_result)}\n</tool_response>"
                })
            else:
                messages.append({
                    "tool_call_id": tool_call["id"],
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps(tool_result)
                })
                
    return "Agent aborted: Reached maximum allowed reasoning/execution turns (5)."