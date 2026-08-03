import json
import re
from typing import List, Dict, Any, Optional
from src.vllm_client import get_vllm_client
from src.config import MODEL_NAME

class SkillRouter:
    """
    Decides which skills are relevant to a user query to minimize prompt noise.
    """
    
    def __init__(self, skill_index: Dict[str, str]):
        self.skill_index = skill_index
        self.client = get_vllm_client()

    def route(self, user_query: str) -> List[str]:
        """
        Analyzes the query and returns a list of relevant skill names.
        """
        if not self.skill_index:
            return []

        # Prepare a very compact index
        index_items = [f"- {name}: {desc}" for name, desc in self.skill_index.items()]
        index_str = "\n".join(index_items)
        
        system_prompt = (
            "You are a routing specialist for a chemistry AI agent.\n"
            "Analyze the user's query and select at most 3 relevant skills from the index.\n"
            "If no specific skills are needed, select an empty list [].\n\n"
            "Index:\n"
            f"{index_str}\n\n"
            "Instruction:\n"
            "Briefly state your reasoning in 1 sentence, then output the final selection as a valid JSON list at the end.\n"
            "Example: Reason: Query involves molecular calculation. Selection: [\"chemical_math\"]"
        )

        try:
            response = self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Query: {user_query}\nSelection:"}
                ],
                temperature=0.0, 
                max_tokens=768
            )
            
            content = response.choices[0].message.content.strip()
            
            # 1. Regex allowing empty lists [] or populated lists ["skill_a", "skill_b"]
            # Look for the last occurrence of a JSON list format
            list_pattern = r'\[\s*(?:(?:"[^"]*")\s*(?:,\s*(?:"[^"]*")\s*)*)?\]'
            json_matches = list(re.finditer(list_pattern, content, re.DOTALL))
            
            if json_matches:
                try:
                    selected_skills = json.loads(json_matches[-1].group(0))
                    if isinstance(selected_skills, list):
                        # Filter only valid skill names present in our index
                        return [s for s in selected_skills if s in self.skill_index][:3]
                except Exception:
                    pass
            
            # 2. Emergency Fallback: Strip reasoning tags and search for skill keywords
            clean_content = content
            for marker in ["</think>", "Thinking Process:", "Reasoning:", "Selection:"]:
                if marker in clean_content:
                    clean_content = clean_content.split(marker)[-1]
            
            found_skills = []
            for name in self.skill_index.keys():
                if re.search(rf'\b{re.escape(name)}\b', clean_content):
                    found_skills.append(name)
            
            if found_skills:
                # Deduplicate preserving order
                seen = set()
                unique_skills = [x for x in found_skills if not (x in seen or seen.add(x))]
                return unique_skills[:3]
                
            return []
            
        except Exception as e:
            print(f"[SkillRouter Error] Routing failed: {e}")
            return []