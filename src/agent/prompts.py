# src/agent/prompts.py

SYSTEM_PROMPT = """You are an expert chemistry assistant, molecular data analyst, and file manager.
You have tools to read laboratory files, write automated synthesis or safety reports, calculate chemical properties, and find substructures.
Always prioritize using appropriate tools to gather accurate local data or write structured results to files."""

AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculate_molecular_properties",
            "description": "Calculates physicochemical properties of a chemical compound given its SMILES string.",
            "parameters": {
                "type": "object",
                "properties": {
                    "smiles": {"type": "string", "description": "The SMILES representation of the molecule."}
                },
                "required": ["smiles"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_substructure",
            "description": "Searches for a basic substructure or SMARTS pattern within a target molecule.",
            "parameters": {
                "type": "object",
                "properties": {
                    "smiles": {"type": "string", "description": "The SMILES representation of the molecule."},
                    "pattern": {"type": "string", "description": "The SMARTS or SMILES pattern to find."}
                },
                "required": ["smiles", "pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_molecular_similarity",
            "description": "Calculates the structural Tanimoto similarity score between two molecules.",
            "parameters": {
                "type": "object",
                "properties": {
                    "smiles1": {"type": "string", "description": "SMILES of the first molecule."},
                    "smiles2": {"type": "string", "description": "SMILES of the second molecule."}
                },
                "required": ["smiles1", "smiles2"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Reads and returns the complete text or data content from a local file (.txt, .md, .json, or .pdf). Use this to inspect datasets, input sheets, or documents provided by the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The absolute or relative local path to the target file."
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Writes text or structured markdown content into a file on disk. Use this when the user asks you to save an analytical report, results list, or chemical analysis to a file.",
            "parameters": {
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
        }
    }
]