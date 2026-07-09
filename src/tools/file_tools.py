# src/tools/file_tools.py
import json
import os
from typing import Any, Dict
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

    def execute(self, file_path: str) -> Dict[str, Any]:
        """Reads the content of a local file. Supports .txt, .md, .json, .csv, .jsonl, and .pdf formats."""
        if not os.path.exists(file_path):
            return {"error": f"File not found at local path: {file_path}"}
        
        _, ext = os.path.splitext(file_path.lower())
        
        try:
            if ext in ['.txt', '.md', '.csv']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return {"file_path": file_path, "format": ext, "content": f.read()}
            
            elif ext == '.json':
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return {"file_path": file_path, "format": ".json", "content": data}

            elif ext == '.jsonl':
                data = []
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            data.append(json.loads(line))
                return {"file_path": file_path, "format": ".jsonl", "content": data}
            
            elif ext == '.pdf':
                reader = PdfReader(file_path)
                text = ""
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
                return {"file_path": file_path, "format": ".pdf", "content": text.strip()}
            
            else:
                return {"error": f"Unsupported file extension: {ext}. Only .txt, .md, .json, and .pdf are allowed."}
                
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

    def execute(self, file_path: str, content: str) -> Dict[str, Any]:
        """Writes or overwrites text content to a specified file path. Automatically creates parent directories."""
        try:
            parent_dir = os.path.dirname(file_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
                
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            return {
                "file_path": file_path,
                "status": "success",
                "message": "File successfully written to disk."
            }
        except Exception as e:
            return {"error": str(e)}

# Register file tools
ToolRegistry.register(ReadFileTool())
ToolRegistry.register(WriteFileTool())

# Legacy functions for backward compatibility
def read_file(file_path: str) -> dict:
    return ReadFileTool().execute(file_path)

def write_file(file_path: str, content: str) -> dict:
    return WriteFileTool().execute(file_path, content)
