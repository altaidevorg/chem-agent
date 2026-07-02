# 🔬 Professional Chemistry AI Agent (v2.1)

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
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Agent
To start the interactive CLI session:
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
├── output/                 # Generated molecule images (.png)
├── reports/                # Saved analytical reports
└── requirements.txt        # Project dependencies
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

The agent operates on a **Reasoning-Act-Observe (ReAct)** cycle:

1.  **Thought (`<think>`)**: The LLM first generates an internal reasoning process (Chain of Thought) to plan its next steps. These thoughts are logged in `logs/thoughts/`.
2.  **Action**: The agent identifies the necessary tools and generates either a native tool call or an XML-based fallback.
3.  **Observation**: The system executes the tool, captures the result, and feeds it back to the LLM.
4.  **Report**: Once the task is complete, the agent synthesizes the findings into a professional report.

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
