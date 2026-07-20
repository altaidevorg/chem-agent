---
name: industrial_data_analytics
description: Advanced multi-step strategy for analyzing large industrial datasets using DuckDB and Pandas. Use this for complex root cause analysis, correlation studies, and processing files too large for standard reading.
---

# 🏭 Industrial Data Analytics Skill

This skill enables the agent to perform sophisticated analysis on large-scale industrial data by combining SQL-based filtering (DuckDB), deterministic statistics (`analyze_dataset`), and structured interpretation.

## 🚀 Analytical Workflow

### 1. Schema Discovery (Always Start Here)
Never assume the column names or data types of a dataset. Use the `inspect_dataset` tool to understand the file structure.
- **Goal**: Identify key columns (e.g., `timestamp`, `batch_id`, `sensor_value`, `yield`).
- **Action**: `inspect_dataset(file_path="data/production_logs.csv")`
- **Important**: Copy `sql_reference` values exactly. Do not rename columns (e.g. never convert `"Machine ID"` to `Machine_ID`).

### 2. Targeted Filtering (SQL First)
For files larger than 5MB or containing thousands of rows, avoid `read_file`. Instead, use `query_dataset` to extract only the relevant subset of data.
- **Technique**: Use `WHERE` clauses to filter by Batch ID, Timestamp range, or specific sensor tags.
- **Example**: `SELECT "Machine ID", "Energy Consumption (kWh)" FROM 'data/sensor_data.csv' WHERE "Machine ID" = 'T-101'`
- **Starter Query**: Use the `example_select` returned by `inspect_dataset` as your SQL template.

### 3. Statistical Analysis (Tool Required — Never Compute Mentally)
For correlation, descriptive statistics, ratio ranking, outliers, or group comparisons, you MUST use `analyze_dataset`.
- **Correlation**: `analyze_dataset(analysis_type="correlation", granularity="row_level", columns=["Recycled Material (%)", "Defect Rate (%)"], method="pearson")`
- **Energy efficiency ranking**: `analyze_dataset(analysis_type="ratio_rank", numerator="Energy Consumption (kWh)", denominator="Production Output (Units)", group_by="Machine ID", ratio_method="sum_ratio", order="desc", limit=5)`
- **Outliers**: `analyze_dataset(analysis_type="outlier", columns=["Energy Consumption (kWh)"], z_threshold=3.0)`
- **Group comparison**: `analyze_dataset(analysis_type="group_compare", columns=["Defect Rate (%)"], group_by="Material Category")`

### 4. Cross-File Correlation (Joining)
DuckDB allows you to join multiple files directly in a single SQL query.
- **Use Case**: Correlating a quality drop in a production log with a sensor fluctuation in a calibration file.
- **Example**: 
  ```sql
  SELECT logs.batch_id, logs.yield, sensors.value 
  FROM 'data/logs.csv' AS logs 
  JOIN 'data/sensors.csv' AS sensors ON logs.timestamp = sensors.timestamp 
  WHERE logs.batch_id = 'B003'
  ```

### 5. Interpretation Only
Once tools return numeric results, interpret them in plain language. Do NOT recalculate coefficients, averages, or rankings.

## ⚠️ Critical Rules
- **Quote File Paths**: Always use single quotes for file paths in SQL queries: `'data/file.csv'`.
- **Exact Column Names**: Use `sql_reference` from `inspect_dataset` verbatim. Columns with spaces or symbols must stay quoted, e.g. `"Production Output (Units)"`.
- **No Mental Math**: NEVER calculate correlation, p-values, z-scores, or rankings from memory. Use `analyze_dataset`.
- **Granularity Matters**: Use `granularity="row_level"` for record-level correlation unless the user explicitly asks for group-level analysis.
- **Ratio Method**: Prefer `ratio_method="sum_ratio"` for efficiency metrics (total energy / total output). Use `avg_ratio` only when explicitly requested.
- **No Guessing**: If `query_dataset` returns `did_you_mean`, replace the invalid column with `did_you_mean_sql` and retry immediately.
- **Token Efficiency**: Do not request more than 50 rows of raw data unless absolutely necessary. Summarize findings instead of printing entire tables.
- **Fallback**: If a SQL query fails due to complex JSON nesting, use `inspect_dataset` to see the parsed structure first.
