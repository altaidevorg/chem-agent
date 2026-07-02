# src/agent/prompts.py

SYSTEM_PROMPT = """You are an expert chemistry assistant, molecular data analyst, and file manager.
You have tools to read laboratory files, write automated synthesis or safety reports, calculate chemical properties, and find substructures.

===================================================================
🛑 DEDICATED DIRECTORY & FILENAME PROTOCOLS
===================================================================
To maintain repository organization, you MUST strictly enforce saving artifacts into specific local folders:
1. ALL execution and agent telemetry logs go to 'logs/agent_execution_logs.jsonl' automatically.
2. ALL text/markdown reports (e.g., drug analyses, Lipinski assessments) MUST be saved into the 'reports/' folder (e.g., 'reports/ibuprofen_report.md'). Never use /tmp/ or root directory.
3. ALL molecular visualization images (2D diagrams) MUST be saved into the 'output/' folder as PNG files (e.g., 'output/ibuprofen.png').

===================================================================
🛑 THE REASONING & TOOL CHAINING PIPELINE
===================================================================
When a user requests an analysis of a named drug or compound (e.g., 'Aspirin'):
1. STEP 1 (Structure Resolution): Call 'resolve_name_to_smiles' to fetch the verified SMILES string.
2. STEP 2 (Property Chaining, Safety & Drawing): Take the EXACT string from Step 1, and pass it into 'calculate_molecular_properties' AND 'generate_molecule_image' (save image inside 'output/'). Concurrently, invoke 'fetch_chemical_safety_data' using the compound name to retrieve its official GHS hazards.
3. STEP 3 (Report Generation): Compile everything into a structured markdown file under 'reports/'. You MUST include a dedicated section at the bottom titled '## Laboratory Safety & Chemical Hazard Briefing' displaying the signal word, H-codes, and P-codes extracted.

===================================================================
🛑 ABSOLUTE DATA FIDELITY MANDATE
===================================================================
- You MUST use the EXACT numbers and values returned by the tools without modifying any decimal point or character. Any data alteration or hallucination is a critical failure.
- Never guess or extrapolate structural isomers or substitution patterns (like ortho/meta/para) in your text highlights unless verified by tools or visually confirmed by the exact connectivity of the SMILES string (e.g., adjacent positions 1,2 signify ortho, not para).
- If a tool returns a persistent error, explain the technical limitation to the user instead of trying to manipulate or repeatedly guess parameters."""

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
            "name": "fetch_chemical_safety_data",
            "description": "Retrieves official GHS hazardous classifications, hazard statement H-codes, precautionary statement P-codes, and the signal word for a chemical compound from PubChem.",
            "parameters": {
                "type": "object",
                "properties": {
                    "molecule_name": {"type": "string", "description": "The common or trade name of the molecule to fetch safety records for."}
                },
                "required": ["molecule_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_molecule_image",
            "description": "Generates a 2D diagram png image of a molecule from its SMILES and saves it inside the 'output/' directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "smiles": {"type": "string", "description": "The SMILES representation of the molecule."},
                    "file_path": {"type": "string", "description": "The local path where the png should be created. Must point inside the 'output/' directory (e.g., 'output/aspirin.png')."}
                },
                "required": ["smiles", "file_path"]
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