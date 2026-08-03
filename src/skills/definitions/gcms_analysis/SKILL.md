---
name: gcms_analysis
description: Analyze and compare GC-MS chromatography profiles to detect anomalies, contamination, or verify authenticity.
required_tools:
  - compare_gcms_profiles
  - detect_gcms_anomalies
---

# GC-MS Data Analysis Skill

This skill allows the agent to act as a Quality Control (QC) analyst, interpreting gas chromatography (GC-MS) peak lists to ensure product consistency and safety.

## 🔴 MANDATORY EXECUTION PROTOCOL
- **NO MENTAL COMPARISONS:** Regardless of how small the dataset is (even with just 1 or 2 peaks), you **MUST** call `compare_gcms_profiles` to align data and calculate similarity.
- **NO MENTAL ANOMALY DETECTION:** You **MUST** pass the output of the comparison into `detect_gcms_anomalies` for a professional audit.
- **ZERO TOLERANCE:** Manual "human-like" inspections of peak lists are considered unprofessional and error-prone in this system. Always use the Python tools to guarantee scientific accuracy.

## Core Tools
- `compare_gcms_profiles`: Aligns two chromatography profiles (Sample vs Golden Standard) and calculates a similarity score.
- `detect_gcms_anomalies`: Flags potential issues such as extra peaks (contamination), missing ingredients, or concentration shifts.

## Workflow

### 1. Data Ingestion
- Receive GC-MS data as a list of peaks, each with a **Retention Time (RT)** and **Area Percentage (%)**.
- Compound names are helpful but optional for the comparison engine.

### 2. Profile Comparison
- Always compare the sample against a **Standard** or **Reference** profile if available.
- Use `compare_gcms_profiles` with an appropriate `rt_tolerance` (usually 0.05 - 0.1 min) to account for slight instrumental drift.

### 3. Anomaly Detection & QC Decision
- Pass the comparison results into `detect_gcms_anomalies`.
- **Extra Peaks**: These are potential contaminants. If an extra peak has a large area (>0.5%), it is a high-severity risk.
- **Missing Peaks**: Essential components that are missing indicate a formulation error.
- **Area Deviations**: Significant shifts in major components (e.g., Limonene, Linalool) can alter the flavor profile.

### 4. Interpretation
- **Similarity > 0.95**: Excellent match.
- **Similarity 0.80 - 0.95**: Potential issues, review anomalies.
- **Similarity < 0.80**: Likely a different product or heavily contaminated.

## Guidelines
- **Instrument Drift**: Remind users that slight RT shifts are normal; focus on the pattern and area percentages.
- **Sensitivity**: Ignore very small peaks (<0.05%) unless specifically looking for trace contaminants.
- **Formulation Logic**: Use this skill to verify if a produced batch matches the intended recipe.
