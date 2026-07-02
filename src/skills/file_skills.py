# src/skills/file_skills.py
import json
import os
from pypdf import PdfReader

def read_file(file_path: str) -> dict:
    """Reads the content of a local file. Supports .txt, .md, .json, and .pdf formats."""
    if not os.path.exists(file_path):
        return {"error": f"File not found at local path: {file_path}"}
    
    _, ext = os.path.splitext(file_path.lower())
    
    try:
        if ext in ['.txt', '.md']:
            with open(file_path, 'r', encoding='utf-8') as f:
                return {"file_path": file_path, "format": ext, "content": f.read()}
        
        elif ext == '.json':
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {"file_path": file_path, "format": ".json", "content": data}
        
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


def write_file(file_path: str, content: str) -> dict:
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