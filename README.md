# 🔬 Professional Chemistry AI Agent 

A sophisticated, stateful AI agent designed for professional chemical analysis, molecular property prediction, and structural informatics. This agent leverages Large Language Models (LLMs) combined with the powerful **RDKit** cheminformatics library and **PubChem** integration to provide accurate chemical insights.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- RDKit
- OpenAI-compatible API (vLLM or similar)

### Installation
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd chem-agent
   ```
2. Install the package in editable mode:
   ```bash
   pip install -e .
   ```

### Running the Agent
To start the interactive CLI session, you can now use the installed command:
```bash
chem-agent
```
Alternatively, you can still run it via python:
```bash
python -m src.main
```

---

## 📂 Project Structure

```text
chem-agent/
├── logs/                   # Execution and session logs
│   ├── sessions/           # Persistent JSON session memory
│   ├── thoughts/           # Markdown logs of agent reasoning (CoT)
│   └── agent_execution_logs.jsonl # Structured telemetry data
├── src/                    # Source code
│   ├── agent/              # Core agent logic
│   │   ├── core.py         # Orchestration and execution loop
│   │   ├── memory.py       # Context and entity tracking
│   │   └── prompts.py      # System instructions
│   ├── skills/             # Tool/Skill implementations
│   │   ├── base.py         # Skill registry and base class
│   │   ├── rdkit_skills.py # Chemical informatics tools
│   │   └── file_skills.py  # I/O operations
│   ├── config.py           # System configuration
│   └── vllm_client.py      # LLM API client
├── scripts/                # Utility and test scripts
│   └── test_vllm.py        # LLM connection test script
├── tests/                  # Unit and integration tests
├── output/                 # Generated molecule images (.png)
├── reports/                # Saved analytical reports
├── pyproject.toml          # Project configuration and dependencies
└── README.md               # Project documentation
```

---

## 🛠 Skills & Tools

The agent is equipped with specialized "skills" that allow it to interact with chemical databases and perform complex calculations:

### Chemical Informatics (RDKit & PubChem)
- **`resolve_name_to_smiles`**: Converts common drug or chemical names (e.g., "Aspirin") into verified SMILES strings using the PubChem API.
- **`calculate_molecular_properties`**: Computes physicochemical properties like Molecular Weight, LogP, Hydrogen Bond Donors (HBD), and Acceptors (HBA).
- **`generate_molecule_image`**: Creates high-quality 2D diagrams of molecules and saves them to the `output/` directory.
- **`fetch_chemical_safety_data`**: Retrieves GHS hazard classifications, H-codes, P-codes, and signal words from official safety dossiers.
- **`search_substructure`**: Identifies if a specific chemical pattern (SMARTS/SMILES) exists within a molecule.
- **`calculate_molecular_similarity`**: Computes Tanimoto similarity scores between two molecules using ECFP4 fingerprints.
- **`search_advanced_substructure`**: Performs Markush-like matching with dynamic sidechain filtering (e.g., alkyl or all-carbon constraints).
- **`find_maximum_common_substructure`**: Identifies the largest common atom/bond mapping (MCS) shared among a list of molecules, useful for pharmacophore detection.
- **`interpret_smarts_pattern`**: Deconstructs complex SMARTS strings into human-readable atom counts and structural motifs (e.g., identifying benzene rings or carboxylic acids).
- **`deconstruct_core_and_sidechains`**: Removes a specified core scaffold from a molecule to isolate its sidechains (R-groups).
- **`canonicalize_and_validate_smiles`**: Validates SMILES strings and converts them into their unique canonical form.
- **`get_molecular_formula_and_charge`**: Calculates the exact molecular formula and net formal charge of a compound.
- **`convert_smiles_to_inchi`**: Converts SMILES strings into IUPAC InChI and InChIKey identifiers.
- **`count_heavy_atoms_and_rings`**: Counts non-hydrogen atoms and total number of rings in a molecule.
- **`detect_functional_groups`**: Scans for common functional groups (Alcohols, Amines, Acids, etc.) using SMARTS patterns.
- **`resolve_smiles_to_name`**: Reverse-resolves a SMILES string into its common or IUPAC name via PubChem.

### System & File Operations
- **`read_file`**: Extracts text from `.txt`, `.md`, `.json`, and even `.pdf` documents.
- **`write_file`**: Saves analytical reports or results to disk for later use.

---

## 🧠 Memory & Context Management

The agent features a persistent **AgentMemory** system that tracks:
1.  **Conversation History**: Full dialogue history between the user and the agent.
2.  **Entity Tracking**: A structured registry of all chemical entities discussed, including their SMILES strings and calculated properties.
3.  **Context Injection**: At every turn, the agent's current "Chemical Context" is injected into the system prompt, ensuring it "remembers" previously resolved structures.

**Persistence**: Every session is saved as a JSON file in `logs/sessions/`, allowing for session recovery and audit trails.

---

## 🤖 How the LLM Works

The agent operates on a **Reasoning-Act-Observe (ReAct)** cycle. Below is a step-by-step trace of a real-world complex query:

### Case Study: Pharmacophore Detection (Ibuprofen & Naproxen)
**User Query**: *"Identify the common structural core shared by the drugs 'Ibuprofen' and 'Naproxen'. Use the MCS tool to find the largest shared substructure and explain the resulting SMARTS pattern."*

1.  **Step 1: Entity Resolution**
    - The agent recognizes it needs SMILES strings for both names.
    - **Action**: Calls `resolve_name_to_smiles` for "Ibuprofen" and "Naproxen".
    - **Result**: Obtains `CC(C)CC1=CC=C(C=C1)C(C)C(=O)O` and `C[C@@H](C1=CC2=C(C=C1)C=C(C=C2)OC)C(=O)O`.

2.  **Step 2: Substructure Discovery (MCS)**
    - The agent feeds both SMILES into the Maximum Common Substructure engine.
    - **Action**: Calls `find_maximum_common_substructure`.
    - **Result**: Returns a complex SMARTS pattern with **14 atoms** and **14 bonds**.

3.  **Step 3: Pattern Interpretation**
    - To ensure chemical accuracy and avoid "hallucinating" the SMARTS meaning, the agent verifies the pattern.
    - **Action**: Calls `interpret_smarts_pattern`.
    - **Result**: Confirms the presence of a **Benzene ring** and a **Propionic acid backbone** (12 Carbons, 2 Oxygens).

4.  **Step 4: Final Synthesis**
    - The agent combines all findings into a professional report, explaining that both drugs share the fundamental **2-arylpropionic acid** scaffold responsible for their COX-inhibiting activity.

---

## 📊 Examples

### 1. Structure Resolution (Aspirin)
**User**: "Resolve the structure of 'Aspirin' and print its verified SMILES string."
**Agent Result**:
```text
Verified SMILES: CC(=O)OC1=CC=CC=C1C(=O)O
Description: Acetylsalicylic acid, consisting of a benzene ring with ortho carboxylic acid and acetoxy groups.
```

### 2. Isomeric SMILES (Vitamin C)
**User**: "Resolve 'Vitamin C' to its exact isomeric SMILES representation."
**Agent Result**:
```text
Isomeric SMILES: C([C@@H]([C@@H]1C(=C(C(=O)O1)O)O)O)O
Note: Specifically identifies the L-ascorbic acid enantiomer with S-configuration at C4 and C5.
```

### 3. Complex Drug Analysis (Remdesivir)
**User**: "Resolve the structure of 'Remdesivir' and retrieve its database SMILES."
**Agent Result**:
```text
SMILES: CCC(CC)COC(=O)[C@H](C)N[P@](=O)(OC[C@@H]1[C@H]([C@H]([C@](O1)(C#N)C2=CC=C3N2N=CN=C3N)O)O)OC4=CC=CC=C4
Analysis: Identifies prodrug moieties, phosphoramidate linkage, and the modified adenine nucleobase.
```

### 4. Physicochemical Evaluation
**User**: "Evaluate the physicochemical properties of [Complex SMILES] to verify RDKit parsing."
**Agent Result**:
- **Molecular Weight**: 977.17 g/mol
- **LogP**: -1.84
- **Lipinski Assessment**: Identifies violations (MW > 500, HBD > 5) characteristic of peptidomimetic compounds.

---

## 📝 Logging & Telemetry

- **Telemetry**: Every action, tool call, and error is recorded in `logs/agent_execution_logs.jsonl` for performance monitoring.
- **Thought Logs**: Detailed markdown files in `logs/thoughts/` provide transparency into the agent's decision-making process.
