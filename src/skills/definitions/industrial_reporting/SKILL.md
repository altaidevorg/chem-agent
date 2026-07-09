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

## Report Structure Template

-   **Title**: Clear and descriptive.
-   **Executive Summary**: High-level findings.
-   **Process Data**: Summary of sensor readings and yields.
-   **Chemical Analysis**: Detailed molecular properties and safety data.
-   **Recommendations**: Actions based on the analysis.
