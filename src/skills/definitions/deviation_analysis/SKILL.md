---
name: deviation_analysis
description: Standard procedure for automated root-cause analysis of production deviations and quality failures.
---

# 🕵️ Deviation & Root-Cause Analysis Skill

This skill enables the agent to investigate why a specific production batch failed quality control by comparing its process parameters and material lots against historically successful batches.

## 🚀 Analytical Workflow

### 1. Identify the Failure
- **Action**: Check `Batch_ID` and the specific metric that failed (e.g., pH, Impurity, Color).
- **Tool**: `inspect_dataset` on the quality file.

### 2. Systematic Investigation (Tool Required)
You MUST use `analyze_deviation` to perform the heavy lifting of joining and comparing data.
- **Action**: Provide the failed batch ID and paths to quality, process, and ingredient files.
- **Rule**: Never attempt to manually JOIN these files or calculate deltas mentally.

### 3. Hierarchical Root-Cause Reasoning
Interpret the results from `analyze_deviation` in the following priority:
1. **Material Change (High Probability)**: If a new lot number was introduced for a key ingredient in the failed batch, this is the primary suspect.
2. **Process Deviation (High Probability)**: If temperature, pressure, or mixing speed is significantly different (e.g., > 2 standard deviations) from successful runs.
3. **Machine Difference**: If the failed batch was run on a different machine than successful ones.

### 4. Reporting
Present findings as "Root Cause Hypotheses" with supporting evidence (Deltas, Lot Numbers).

## 📈 Example Action
- `analyze_deviation(failed_batch_id="B005", quality_file="data/quality.csv", process_file="data/process.csv", ingredients_file="data/ingredients.csv", target_metric="Impurity_pct")`

## ⚠️ Critical Rules
- **No Mental Math**: Do not calculate average temperatures or lot frequencies yourself.
- **Evidence-Based**: Only propose hypotheses that are supported by the `analyze_deviation` output.
- **Check All Files**: If a user only provides one file, ASK for the others (process and ingredients) to perform a full audit.
