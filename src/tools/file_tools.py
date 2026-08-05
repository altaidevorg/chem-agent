# src/tools/file_tools.py
import json
import os
from typing import Any, Dict, Optional
from pypdf import PdfReader
from src.tools.base import BaseTool, ToolRegistry

class ReadFileTool(BaseTool):
    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Reads and returns the complete text or data content from a local file (.txt, .md, .json, .csv, .jsonl, or .pdf). Use this to inspect datasets, input sheets, or documents provided by the user."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute or relative local path to the target file."
                }
            },
            "required": ["file_path"]
        }

    def execute(self, file_path: Optional[str] = None, path: Optional[str] = None, workspace: Optional[Any] = None, **kwargs) -> Dict[str, Any]:
        """Reads the content of a local file. Supports .txt, .md, .json, .csv, .jsonl, and .pdf formats."""
        # 🛡️ Flexible parameter handling: support 'file_path', 'path', or 'filepath'
        target_path = file_path or path or kwargs.get("filepath")
        if not target_path:
            return {"error": "Missing required argument: 'file_path' or 'path'"}

        if workspace:
            try:
                real_path = workspace.resolve(target_path)
                target_path = str(real_path)
            except PermissionError as e:
                return {"error": str(e)}

        if not os.path.exists(target_path):
            return {"error": f"File not found: {target_path}"}
        
        _, ext = os.path.splitext(target_path.lower())
        
        try:
            if ext in ['.txt', '.md', '.csv']:
                with open(target_path, 'r', encoding='utf-8') as f:
                    return {"file_path": target_path, "format": ext, "content": f.read()}
            
            elif ext == '.json':
                with open(target_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {"file_path": target_path, "format": ".json", "content": data}

            elif ext == '.jsonl':
                data = []
                with open(target_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            data.append(json.loads(line))
                return {"file_path": target_path, "format": ".jsonl", "content": data}
            
            elif ext == '.pdf':
                reader = PdfReader(target_path)
                text = ""
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
                return {"file_path": target_path, "format": ".pdf", "content": text.strip()}
            
            else:
                return {"error": f"Unsupported file extension: {ext}. Only .txt, .md, .json, and .pdf are allowed."}
                
        except Exception as e:
            return {"error": str(e)}

class ListFilesTool(BaseTool):
    @property
    def name(self) -> str:
        return "list_files"

    @property
    def description(self) -> str:
        return "Lists all files and subdirectories in a specified local directory. Use this to discover datasets or documents when you are unsure of the exact file path."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "directory_path": {
                    "type": "string",
                    "description": "The local directory path to list (e.g., 'data/' or '.'). Defaults to the current directory.",
                    "default": "."
                }
            }
        }

    def execute(self, directory_path: Optional[str] = None, path: Optional[str] = None, workspace: Optional[Any] = None, **kwargs) -> Dict[str, Any]:
        """Lists contents of a directory."""
        # 🛡️ Flexible parameter handling
        target_dir = directory_path or path or kwargs.get("dirpath") or "."
        
        try:
            if workspace:
                try:
                    real_path = workspace.resolve(target_dir)
                    target_dir = str(real_path)
                except PermissionError as e:
                    return {"error": str(e)}

            if not os.path.exists(target_dir):
                return {"error": f"Directory not found: {target_dir}"}
            
            if not os.path.isdir(target_dir):
                return {"error": f"Path is not a directory: {target_dir}"}

            items = os.listdir(target_dir)
            files = []
            directories = []

            for item in items:
                full_path = os.path.join(target_dir, item)
                if os.path.isdir(full_path):
                    directories.append(item)
                else:
                    files.append(item)

            return {
                "directory": target_dir,
                "files": sorted(files),
                "directories": sorted(directories),
                "status": "success",
                "count": len(items)
            }
        except Exception as e:
            return {"error": str(e)}

class WriteFileTool(BaseTool):
    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Writes text or structured markdown content into a file on disk. Use this when the user asks you to save an analytical report, results list, or chemical analysis to a file."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The target path where the file should be created or overwritten."
                },
                "content": {
                    "type": "string",
                    "description": "The full text or markdown compilation content to be saved."
                }
            },
            "required": ["file_path", "content"]
        }

    def execute(self, file_path: Optional[str] = None, path: Optional[str] = None, content: str = "", workspace: Optional[Any] = None, **kwargs) -> Dict[str, Any]:
        """Writes or overwrites text content to a specified file path. Automatically creates parent directories."""
        # 🛡️ Flexible parameter handling
        target_path = file_path or path or kwargs.get("filepath")
        if not target_path:
            return {"error": "Missing required argument: 'file_path' or 'path'"}

        try:
            if workspace:
                try:
                    real_path = workspace.resolve(target_path)
                    target_path = str(real_path)
                except PermissionError as e:
                    return {"error": str(e)}

            parent_dir = os.path.dirname(target_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
                
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            return {
                "file_path": target_path,
                "status": "success",
                "message": "File successfully written to disk."
            }
        except Exception as e:
            return {"error": str(e)}

# Register file tools
ToolRegistry.register(ReadFileTool())
ToolRegistry.register(ListFilesTool())
ToolRegistry.register(WriteFileTool())

# Legacy functions for backward compatibility
def read_file(file_path: str) -> dict:
    return ReadFileTool().execute(file_path)

def write_file(file_path: str, content: str, **kwargs) -> dict:
    return WriteFileTool().execute(file_path, content, **kwargs)
