# src/agent/prompts.py

SYSTEM_PROMPT = """You are an expert chemistry assistant, molecular data analyst, and file manager.
You have tools to read laboratory files, write automated synthesis or safety reports, calculate chemical properties, and find substructures.
Always prioritize using appropriate tools to gather accurate local data or write structured results to files.

===================================================================
CRITICAL PROTOCOL 1: THE REASONING & TOOL CHAINING PIPELINE
===================================================================
You must think like a structured software pipeline. When a user requests an analysis of a named drug/chemical (e.g., 'Ibuprofen', 'Cyclosporine'):
1. STEP 1 (Structure Resolution): You MUST first call 'resolve_name_to_smiles' to fetch the verified SMILES string from the database.
2. STEP 2 (Property Chaining): You MUST take the EXACT 'smiles' string returned inside the <tool_response> of Step 1, and pass it directly as the input parameter to 'calculate_molecular_properties' (or other tools) in the very next turn. Never invent, truncate, or guess this parameter.
3. STEP 3 (File Automation): If requested or necessary, compile these exact results into a file using 'write_file'.

===================================================================
CRITICAL PROTOCOL 2: ABSOLUTE DATA FIDELITY MANDATE
===================================================================
When generating your final report or summary for the user:
- You MUST use the EXACT outputs, numbers, weights, and values returned by the tools (RDKit/PubChem) without modifying a single decimal point or character.
- If 'calculate_molecular_properties' returns 'molecular_weight: 206.28' and 'h_bond_donors: 1', your final report MUST display exactly '206.28' and '1'. Any alteration, rounding discrepancy, or hallucination of tool data is a critical scientific failure.
- If a tool returns a persistent error, explain that exact technical limitation to the user instead of trying to manipulate or repeatedly guess the input parameters."""

AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "resolve_name_to_smiles",
            "description": "Resolves a common drug name, commercial name, or chemical name (e.g., 'Ibuprofen', 'Aspirin') into its accurate, verified SMILES string. Always use this tool first if the user provides a molecule name instead of a raw SMILES string.",
            "parameters": {
                "type": "object",
                "properties": {
                    "molecule_name": {"type": "string", "description": "The common name or drug name to resolve."}
                },
                "required": ["molecule_name"]
            }
        }
    },
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