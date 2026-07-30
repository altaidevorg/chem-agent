---
name: sensory_analysis
description: Perform professional sensory panel analysis, including consistency checks (Cronbach's Alpha) and sample significance testing (ANOVA).
---

# Sensory Panel Analysis Skill

## Purpose
To evaluate sensory data scientifically by assessing panelist consistency, identifying significant differences between samples (ANOVA/Tukey), and performing preference mapping using PCA. This skill ensures that subjective sensory feedback is transformed into objective, statistically valid R&D decisions.

## Workflow

1.  **Data Exploration**: Use `inspect_dataset` and `profile_dataset_health` to understand the sensory data structure (panelists, samples, attributes).
2.  **Panel Analysis**: Call `analyze_sensory_panel` providing the raw data, attributes (e.g., 'sweetness', 'off-note'), and identifying columns for samples and panelists.
3.  **Consistency Check**: Review Cronbach's Alpha in the tool output. If Alpha < 0.7 for an attribute, warn the user that panelist consensus is low for that specific trait.
4.  **Significance Test**: Check the ANOVA results. If `is_sample_significant` is true, use the `significant_differences` list to explain which products actually differ.
5.  **Preference Mapping (PCA)**: Use `analyze_dataset` with `analysis_type='pca'` on the sensory attributes to visualize sample clusters and identify which attributes drive product separation.
6.  **Reporting**: Synthesize the results: "Sample A is significantly sweeter than B (p < 0.05), and PCA shows that Aroma Intensity is the primary differentiator between the prototypes."

## 🔴 MANDATORY EXECUTION PROTOCOL
- **NO MENTAL ANOVA**: Never assume products are different based on raw averages. You **MUST** call `analyze_sensory_panel` to calculate p-values.
- **NO MENTAL CONSISTENCY**: Do not guess if panelists agree. You **MUST** check Cronbach's Alpha from the tool.
- **STATISTICAL RIGOR**: Only report differences as "significant" if the tool's p-value is < 0.05.
- **PCA FOR MAPPING**: Use the `pca` analysis type in `analyze_dataset` for any request involving "mapping", "grouping", or "attribute drivers".

## Example Query
"Analyze the sensory data in 'sensory_test_v1.csv' for sweetness and aroma. Do the panelists agree, and are there real differences between Sample_X and Sample_Y?"
