# src/skills/registry.py
import os
import yaml
from typing import Dict, List, Optional, Any

class SkillDefinition:
    def __init__(self, name: str, description: str, instructions: str, path: str, required_tools: List[str] = None, available: bool = True):
        self.name = name
        self.description = description
        self.instructions = instructions
        self.path = path
        self.required_tools = required_tools or []
        self.available = available

class SkillRegistry:
    def __init__(self, skills_dir: str):
        self.skills_dir = skills_dir
        self.skills: Dict[str, SkillDefinition] = {}
        self.scan_for_skills()

    def scan_for_skills(self):
        """Scans the skills directory for folders containing a SKILL.md file."""
        if not os.path.exists(self.skills_dir):
            return

        for entry in os.listdir(self.skills_dir):
            entry_path = os.path.join(self.skills_dir, entry)
            if os.path.isdir(entry_path):
                skill_md_path = os.path.join(entry_path, "SKILL.md")
                if os.path.exists(skill_md_path):
                    skill_def = self._parse_skill_md(skill_md_path)
                    if skill_def:
                        self.skills[skill_def.name] = skill_def
                        print(f"[SkillRegistry] Loaded skill: {skill_def.name}")

    def _parse_skill_md(self, path: str) -> Optional[SkillDefinition]:
        """Parses a SKILL.md file extracting YAML frontmatter and the Markdown body."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content.startswith("---"):
                print(f"[SkillRegistry] Warning: No YAML frontmatter found in {path}")
                return None

            parts = content.split("---", 2)
            if len(parts) < 3:
                print(f"[SkillRegistry] Warning: Unclosed YAML frontmatter in {path}")
                return None

            frontmatter_str = parts[1]
            body_str = parts[2].strip()
            metadata = yaml.safe_load(frontmatter_str)

            if not isinstance(metadata, dict) or 'name' not in metadata or 'description' not in metadata:
                print(f"[SkillRegistry] Warning: Missing required fields in frontmatter of {path}")
                return None

            return SkillDefinition(
                name=metadata['name'],
                description=metadata['description'],
                instructions=body_str,
                path=path,
                required_tools=metadata.get('required_tools', [])
            )
        except Exception as e:
            print(f"[SkillRegistry] Error parsing {path}: {e}")
            return None

    def get_skill_index(self) -> Dict[str, str]:
        """Returns a mapping of skill name to its short description for routing."""
        return {skill.name: skill.description for skill in self.skills.values() if skill.available}

    def get_capabilities_summary(self, skill_names: Optional[List[str]] = None) -> str:
        """Returns the metadata for progressive disclosure. If skill_names is provided, only those are included."""
        if not self.skills:
            return ""

        summary = "\n\nAvailable Agent Skills:\n"
        
        skills_to_include = []
        if skill_names:
            skills_to_include = [self.skills[name] for name in skill_names if name in self.skills and self.skills[name].available]
        else:
            skills_to_include = [skill for skill in self.skills.values() if skill.available]

        if not skills_to_include:
            return ""

        for skill in skills_to_include:
            summary += f"- **{skill.name}**: {skill.description}\n"
        
        summary += "\nTo execute a skill, use the 'load_skill_instructions' tool with the skill's name to learn how to use it contextually.\n"
        return summary

    def get_skill_instructions(self, name: str) -> Optional[str]:
        """Returns the full instructions for a skill."""
        skill = self.skills.get(name)
        if skill and skill.available:
            return skill.instructions
        return None

    def format_skill_directory(self) -> str:
        """One line per skill for quick discovery."""
        if not self.skills:
            return "No skills discovered."
        
        out = "Available skills:\n\n"
        for name in sorted(self.skills.keys()):
            skill = self.skills[name]
            out += f"- **{name}**: {skill.description}\n"
        return out

    def get_skill_metadata(self, name: str) -> Optional[Dict[str, Any]]:
        """Short metadata for a skill."""
        skill = self.skills.get(name)
        if not skill:
            return None
        
        return {
            "name": skill.name,
            "available": skill.available,
            "description": skill.description,
            "instruction_length": len(skill.instructions),
            "path": skill.path,
            "required_tools": skill.required_tools
        }

    def get_required_tools_for_skills(self, skill_names: List[str]) -> List[str]:
        """Returns a deduplicated list of required tools for the given skill names."""
        tools = set()
        for name in skill_names:
            skill = self.skills.get(name)
            if skill:
                tools.update(skill.required_tools)
        return list(tools)
