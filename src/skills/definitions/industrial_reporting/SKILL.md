---
name: industrial_reporting
description: Generate professional chemical analysis and industrial process reports.
---

# Industrial Reporting Skill

This skill is used to compile data from various sources (CSV logs, lab results, molecular analysis) into a structured markdown report.

## Workflow

1.  **Data Gathering**: Use `read_file` to collect data from `data/industrial_process.csv`, `data/lab_results.csv`, etc.
2.  **Analysis**: Perform necessary calculations (averages, trends, molecular properties).
3.  **Compilation**: Format the findings into a clear Markdown structure.
4.  **Export**: Use `write_file` to save the report into the `reports/` or `output/` directory.

## 🛑 MANDATORY EXECUTION PROTOCOL
- **ON-DEMAND ONLY**: You are STRICTLY FORBIDDEN from proactively creating or saving report files in the `reports/` or `output/` directories.
- **EXPLICIT CONSENT**: You MUST only call `write_file` to export a report if the user has explicitly asked to "save a report", "export a document", "create a file", or used similar phrasing.
- **DEFAULT TO CHAT**: If no explicit export request is made, present your analysis directly in the chat interface using standard markdown formatting.

## Report Structure Template

-   **Title**: Clear and descriptive.
-   **Executive Summary**: High-level findings.
-   **Process Data**: Summary of sensor readings and yields.
-   **Chemical Analysis**: Detailed molecular properties and safety data.
-   **Recommendations**: Actions based on the analysis.
