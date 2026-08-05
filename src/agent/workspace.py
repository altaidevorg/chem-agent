import os
from pathlib import Path
from typing import List, Optional

class WorkspaceManager:
    def __init__(self, default_workspace: str = "data"):
        # Resolve to handle relative paths like 'data' or './data'
        self.root_path = Path(default_workspace).resolve()
        self._ensure_workspace_exists()

    def set_workspace(self, new_path: str) -> str:
        """Dynamically changes the working directory."""
        target = Path(new_path).resolve()
        if not target.exists():
            target.mkdir(parents=True, exist_ok=True)
        self.root_path = target
        return str(self.root_path)

    def resolve(self, relative_or_absolute_path: str) -> Path:
        """
        Securely maps any path into the active Workspace.
        Prevents Path Traversal (climbing to parent directories) attacks.
        Supports paths that already include the workspace folder name.
        """
        clean_path = str(relative_or_absolute_path).strip()
        
        # 🛡️ Remove common redundant prefixes (e.g., "data/", "./data/")
        # This handles cases where the model writes "data/file.csv" even if workspace is already "data/"
        prefixes_to_strip = [
            str(self.root_path.name) + "/", 
            "./" + str(self.root_path.name) + "/",
            "chem-agent/" + str(self.root_path.name) + "/",
            "./",
        ]
        
        for prefix in prefixes_to_strip:
            if clean_path.startswith(prefix):
                clean_path = clean_path[len(prefix):]
                break # Only strip one level

        # Join and resolve to absolute path
        resolved = (self.root_path / clean_path).resolve()

        # Sandboxing Security Check: Is the resolved path within the Workspace?
        # This prevents "../../etc/passwd" style attacks
        if not str(resolved).startswith(str(self.root_path)):
            raise PermissionError(
                f"Access Denied: Path '{relative_or_absolute_path}' resolves to '{resolved}', "
                f"which is outside the allowed workspace '{self.root_path}'."
            )

        return resolved

    def list_files(self, sub_dir: str = ".") -> List[str]:
        """Lists files under the workspace."""
        try:
            target_dir = self.resolve(sub_dir)
        except (PermissionError, ValueError):
            return []
            
        if not target_dir.is_dir():
            return []
        
        rel_files = []
        for root, _, files in os.walk(target_dir):
            for file in files:
                full_p = Path(root) / file
                try:
                    rel_p = full_p.relative_to(self.root_path)
                    rel_files.append(str(rel_p))
                except ValueError:
                    continue
        return sorted(rel_files)

    def _ensure_workspace_exists(self):
        if not self.root_path.exists():
            self.root_path.mkdir(parents=True, exist_ok=True)
