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
        return "Reads and returns the complete text or data content from a local file (.txt, .md, .json, .csv, .jsonl, or .pdf)."

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

    def execute(self, **kwargs) -> Dict[str, Any]:
        target_path = kwargs.get("file_path")
        workspace = kwargs.get("workspace")
        
        if not target_path or not isinstance(target_path, str):
            return {"status": "error", "error": "Missing required string argument: 'file_path'"}

        if workspace:
            try:
                real_path = workspace.resolve(target_path)
                target_path = str(real_path)
            except PermissionError as e:
                return {"status": "error", "error": str(e)}

        if not os.path.exists(target_path):
            return {"status": "error", "error": f"File not found: {target_path}"}
        
        _, ext = os.path.splitext(target_path.lower())
        
        try:
            if ext in ['.txt', '.md', '.csv']:
                with open(target_path, 'r', encoding='utf-8') as f:
                    return {"status": "success", "file_path": target_path, "format": ext, "content": f.read()}
            
            elif ext == '.json':
                with open(target_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {"status": "success", "file_path": target_path, "format": ".json", "content": data}

            elif ext == '.jsonl':
                data = []
                with open(target_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            data.append(json.loads(line))
                return {"status": "success", "file_path": target_path, "format": ".jsonl", "content": data}
            
            elif ext == '.pdf':
                reader = PdfReader(target_path)
                text = ""
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
                return {"status": "success", "file_path": target_path, "format": ".pdf", "content": text.strip()}
            
            else:
                return {"status": "error", "error": f"Unsupported file extension: {ext}. Only .txt, .md, .json, .csv, .jsonl, and .pdf are allowed."}
                
        except Exception as e:
            return {"status": "error", "error": str(e)}


class ListFilesTool(BaseTool):
    @property
    def name(self) -> str:
        return "list_files"

    @property
    def description(self) -> str:
        return "Lists all files and subdirectories in a specified local directory."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "directory_path": {
                    "type": "string",
                    "description": "The local directory path to list (e.g., 'data/' or '.'). Defaults to '.'.",
                    "default": "."
                }
            }
        }

    def execute(self, **kwargs) -> Dict[str, Any]:
        target_dir = kwargs.get("directory_path", ".")
        workspace = kwargs.get("workspace")
        
        try:
            if workspace:
                try:
                    real_path = workspace.resolve(target_dir)
                    target_dir = str(real_path)
                except PermissionError as e:
                    return {"status": "error", "error": str(e)}

            if not os.path.exists(target_dir):
                return {"status": "error", "error": f"Directory not found: {target_dir}"}
            
            if not os.path.isdir(target_dir):
                return {"status": "error", "error": f"Path is not a directory: {target_dir}"}

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
                "status": "success",
                "directory": target_dir,
                "files": sorted(files),
                "directories": sorted(directories),
                "count": len(items)
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


class WriteFileTool(BaseTool):
    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Writes text or structured markdown content into a file on disk."

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

    def execute(self, **kwargs) -> Dict[str, Any]:
        target_path = kwargs.get("file_path")
        content = kwargs.get("content")
        workspace = kwargs.get("workspace")
        
        if not target_path or content is None:
            return {"status": "error", "error": "Missing required arguments: 'file_path' and 'content' must be provided."}

        try:
            if workspace:
                try:
                    real_path = workspace.resolve(target_path)
                    target_path = str(real_path)
                except PermissionError as e:
                    return {"status": "error", "error": str(e)}

            parent_dir = os.path.dirname(target_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
                
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            return {
                "status": "success",
                "file_path": target_path,
                "message": "File successfully written to disk."
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# Register file tools
ToolRegistry.register(ReadFileTool())
ToolRegistry.register(ListFilesTool())
ToolRegistry.register(WriteFileTool())