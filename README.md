# 🔬 ChemAgent: Professional Chemistry AI

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![RDKit](https://img.shields.io/badge/chemistry-RDKit-green.svg)](https://rdkit.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A sophisticated, stateful AI agent designed for professional chemical analysis, molecular property prediction, and industrial structural informatics. ChemAgent orchestrates a suite of specialized tools—from **RDKit** cheminformatics to **DuckDB**-powered analytics—to provide accurate, evidence-based chemical insights.

---

## 🌟 Key Capabilities

### 🧪 Cheminformatics (RDKit & PubChem)
- **Advanced Resolution**: Convert common names to verified isomeric SMILES via PubChem.
- **Structural Analysis**: Calculate LogP, MW, TPSA, and detect 200+ functional groups.
- **Drug Discovery**: Lipinski/Veber rules, QED scores, and solubility (logS) estimation.
- **Substructure Search**: High-precision SMARTS matching with advanced sidechain filtering.
- **Common Scaffold Discovery**: Identify the Maximum Common Substructure (MCS) between multiple compounds.

### 🏭 Industrial Data Analytics
- **High-Performance SQL**: Execute complex queries on large CSV/JSONL datasets using DuckDB.
- **Process Control**: Evaluate process capability (Cp/Cpk) and perform SPC (Statistical Process Control).
- **Time-Series Analysis**: Lag analysis, seasonal decomposition, and trend projections.
- **Root Cause Analysis**: Multiple regression and Pareto analysis for yield optimization.

### ⚖️ Regulatory & Safety
- **Compliance Audits**: Automated screening against **IFRA 51st Amendment** and **EU 1334/2008** regulations.
- **Safety Dossiers**: Retrieval of official GHS hazard classifications (H-codes/P-codes) and signal words.
- **Reactivity Audits**: Detect chemical incompatibilities and reactivity risks in complex formulations.

---

## 🚀 Getting Started

### 📋 Prerequisites
- **Python 3.10+**
- **RDKit** (`conda install -c conda-forge rdkit` or `pip install rdkit`)
- **OpenAI-compatible LLM** (e.g., vLLM, OpenAI, or any provider following the same API spec)

### ⚙️ Installation
1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-repo/chem-agent.git
   cd chem-agent
   ```
2. **Install dependencies**:
   ```bash
   pip install -e .
   ```
3. **Configure environment**:
   Create a `.env` file in the root directory:
   ```env
   LLM_BASE_URL=http://localhost:8000/v1
   LLM_API_KEY=your-api-key
   MODEL_NAME=your-model-name
   WORKSPACE_DIR=./data
   ```

### 🏃 Running the Agent
Start the interactive CLI session:
```bash
chem-agent
```
Or run via module:
```bash
python -m src.main
```

---

## 📂 Project Architecture

```text
chem-agent/
├── data/                   # Dynamic storage for datasets and knowledge DBs
├── logs/                   # Reasoning traces (Chain-of-Thought) and telemetry
├── src/                    # Core source code
│   ├── agent/              # ReAct orchestration, memory, and prompts
│   ├── skills/             # High-level task-specific workflow definitions
│   ├── tools/              # Atomic tool implementations (RDKit, DuckDB, etc.)
│   └── database/           # DuckDB schema management and seed data
├── output/                 # Generated molecule diagrams and images
├── reports/                # Saved analytical and industrial reports
└── tests/                  # Comprehensive unit and integration test suite
```

### 🧠 Intelligence Engine
ChemAgent operates on a **Reasoning-Act-Observe (ReAct)** cycle:
1.  **Reasoning**: Analyzes user intent and selects appropriate **Skills**.
2.  **Act**: Executes atomic **Tools** (e.g., `calculate_molecular_properties`).
3.  **Observe**: Processes tool outputs and updates persistent **Memory**.
4.  **Refine**: Summarizes history dynamically to maintain an efficient context window.

---

## 🛠 Skills Index

ChemAgent is equipped with 15 specialized skills:

| Skill | Description |
| :--- | :--- |
| **Molecule Analysis** | Deep structural and physicochemical profiling using RDKit. |
| **Regulatory Screening** | Legal safety audits against IFRA and EU food regulations. |
| **Industrial Analytics** | Multi-step root cause analysis on massive industrial datasets. |
| **Reactivity Audit** | Detection of chemical incompatibilities in complex mixtures. |
| **Solubility Opt.** | HSP (Hansen) and HLB-based solvent selection optimization. |
| **Stability Forecast** | Shelf-life prediction using Arrhenius degradation modeling. |
| **Sensory Analysis** | Panel consistency checks (Cronbach's Alpha) and ANOVA testing. |
| **GC-MS Analysis** | Automated anomaly detection in chromatography profiles. |

---

## 📝 Logging & Observability

- **Thought Logs**: Every reasoning step is recorded in `logs/thoughts/` as Markdown, providing full transparency into the AI's logic.
- **Telemetry**: Structured execution data is saved to `logs/agent_execution_logs.jsonl` for performance auditing.

---

## 🧪 Testing
Run the verification suite to ensure all tools and skills are correctly configured:
```bash
python scripts/verify_all_tools.py
```
Or use pytest for unit tests:
```bash
pytest tests/
```

---

*Note: This agent is designed for professional use. Always verify critical chemical calculations with laboratory experiments.*
