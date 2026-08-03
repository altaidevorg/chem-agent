---
name: industrial_data_analytics
description: Advanced multi-step strategy for analyzing large industrial datasets using DuckDB and Pandas. Use this for complex root cause analysis, correlation studies, and processing files too large for standard reading.
required_tools:
  - search_columns
  - inspect_dataset
  - profile_dataset_health
  - query_dataset
  - analyze_dataset
  - analyze_spc
---

# 🏭 Industrial Data Analytics Skill

This skill enables the agent to perform sophisticated analysis on large-scale industrial data by combining SQL-based filtering (DuckDB), deterministic statistics (`analyze_dataset`), and structured interpretation.

## 🚀 Analytical Workflow

### 1. Schema & Health Discovery (Always Start Here)
Never assume the column names, data types, or data quality of a dataset. 
- **Finding Specific Columns**: If you are looking for a specific data point (e.g., 'Yield', 'Temperature'), ALWAYS use `search_columns(pattern="...")` first to find which file contains it. Do NOT blindly inspect every file.
- **Schema Discovery**: Use `inspect_dataset` to understand the basic file structure of a specific file.
- **Data Quality Audit**: Use `profile_dataset_health` to detect missing values and understand the semantic meaning of each column.
- **Goal**: Identify key columns (e.g., `timestamp`, `batch_id`) and assess data readiness.
- **Action**: `search_columns(pattern="Yield")` followed by `inspect_dataset` on the relevant file.
- **Rule**: If you encounter an unknown dataset, you MUST run `inspect_dataset` before any analysis.

### 2. Targeted Filtering (SQL First)
For files larger than 5MB or containing thousands of rows, avoid `read_file`. Instead, use `query_dataset` to extract only the relevant subset of data.
- **Technique**: Use `WHERE` clauses to filter by Batch ID, Timestamp range, or specific sensor tags.
- **Example**: `SELECT "Machine ID", "Energy Consumption (kWh)" FROM 'data/sensor_data.csv' WHERE "Machine ID" = 'T-101'`
- **Starter Query**: Use the `example_select` returned by `inspect_dataset` as your SQL template.

### 3. Statistical Analysis & SPC (Tool Required)
For correlation, hypothesis testing, or monitoring process stability, you MUST use `analyze_dataset` or `analyze_spc`.

#### 📌 Efficiency & Strategy Rules:
- **Stability First**: If a user asks "how is the production going?" or "is the process stable?", ALWAYS use `analyze_spc` on the latest data.
- **Trend Detection**: Don't just look for limit violations; `analyze_spc` will also tell you if there are "runs" (7+ points on one side), which indicates a process shift before it becomes a failure.
- **Bulk First**: For descriptive statistics or outlier detection, do NOT call the tool separately for each column. Call it ONCE without the `columns` parameter (or with all columns) to get a full report in a single step.
- **Matrix First**: When asked to find "the strongest relationships" or "influencing factors," ALWAYS start with `analysis_type="correlation_matrix"`. Do NOT run multiple `correlation` calls for pairs; it is slow and token-expensive.
- **Root Cause Path**: First run a `correlation_matrix` to identify candidates, then run `regression` only on the significant variables.
- **Hypothesis Testing (t-test)**: 
    - **CRITICAL**: If comparing ONE numeric column between two groups (e.g. Yield of Batch A vs B), you **MUST** provide the grouping column in `group_by`. 
    - If comparing TWO different columns (e.g. Sensor_1 vs Sensor_2), do **NOT** use `group_by`.
- **Independence Testing (Chi-square)**: Use when checking if two categorical variables (e.g., Machine ID and Error Type) are related.
- **No Large Fallbacks**: If a statistical tool fails, do **NOT** attempt to fetch thousands of rows via `query_dataset` to "calculate it yourself." This will crash your context memory. Instead, check your parameters (especially `group_by` and `columns`).
- **Meaningful Findings**: If correlations are near zero (e.g., < 0.1), report them as "independent variables." Do not keep trying different groupings unless the user specifically asks for it.
- **Column Precision**: Use `inspect_dataset` to get exact column names. If a name has spaces, use it exactly as provided in the `sql_reference` field.

#### 📈 Example Actions:
- **SPC Analysis**: `analyze_spc(file_path="data/production.csv", target_column="Viscosity", timestamp_column="Timestamp")`
- **Comprehensive relationship check**: `analyze_dataset(analysis_type="correlation_matrix")`
- **Correlation**: `analyze_dataset(analysis_type="correlation", columns=["Recycled Material (%)", "Defect Rate (%)"])`
- **T-test (Two Groups)**: `analyze_dataset(analysis_type="t_test", columns=["Yield"], group_by="Machine ID", where_clause="\"Machine ID\" IN ('M1', 'M2')")`
- **T-test (Two Columns)**: `analyze_dataset(analysis_type="t_test", columns=["Temp_Sensor_1", "Temp_Sensor_2"])`
- **Chi-square (Independence)**: `analyze_dataset(analysis_type="chi_square", columns=["Shift", "Error_Type"])`
- **Pareto (80/20 Analysis)**: `analyze_dataset(analysis_type="pareto", group_by="Machine ID", columns=["Defect Rate (%)"])`
- **Regression (Root Cause)**: `analyze_dataset(analysis_type="regression", target_column="Yield", predictor_columns=["Temp", "Pressure"])`
- **Process Capability (Cp/Cpk)**: `analyze_dataset(analysis_type="process_capability", columns=["Reactor Temp"], usl=85, lsl=75)`
- **Trend Projection**: `analyze_dataset(analysis_type="trend_projection", target_column="Energy", timestamp_column="Timestamp")`
- **Seasonal Decomposition**: `analyze_dataset(analysis_type="seasonal_decomposition", columns=["Temperature"], timestamp_column="Timestamp", period=24)`
- **Correlation Matrix**: `analyze_dataset(analysis_type="correlation_matrix")`
- **Downsampling (LTTB)**: `analyze_dataset(analysis_type="downsample", columns=["Temp", "Yield"], timestamp_column="Timestamp", limit=40)`
- **Energy efficiency ranking**: `analyze_dataset(analysis_type="ratio_rank", numerator="Energy Consumption (kWh)", denominator="Production Output (Units)", group_by="Machine ID", order="asc", limit=5)`
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

### 5. Time-Series Analytics (New)
For data with timestamps, use specialized time-series tools to identify trends and periodic patterns.
- **Rolling Statistics**: Detect local trends or volatility spikes.
  - `analyze_dataset(analysis_type="rolling_stats", columns=["Temperature"], timestamp_column="Timestamp", window_size=20, group_by="Machine ID")`
- **Lag Analysis**: Identify delayed effects between variables (e.g., pressure impact on yield 5 minutes later).
  - `analyze_dataset(analysis_type="lag_analysis", columns=["Pressure", "Yield"], timestamp_column="Timestamp", lag_steps=5)`
- **Shift Analysis**: Compare performance across Morning, Evening, and Night shifts.
  - `analyze_dataset(analysis_type="shift_analysis", columns=["Defect Rate (%)"], timestamp_column="Timestamp")`

### 6. Interpretation Only
Once tools return numeric results, interpret them in plain language. Do NOT recalculate coefficients, averages, or rankings.

## ⚠️ Critical Rules
- **Quote File Paths**: Always use single quotes for file paths in SQL queries: `'data/file.csv'`.
- **Exact Column Names**: Use `sql_reference` from `inspect_dataset` verbatim. Columns with spaces or symbols must stay quoted, e.g. `"Production Output (Units)"`.
- **No Mental Math**: NEVER calculate correlation, p-values, z-scores, or rankings from memory. Use `analyze_dataset`.
- **Granularity Matters**: Use `granularity="row_level"` for record-level correlation unless the user explicitly asks for group-level analysis.
- **Ratio Method**: Prefer `ratio_method="sum_ratio"` for efficiency metrics (total energy / total output). Use `avg_ratio` only when explicitly requested.
- **No Guessing**: If `query_dataset` returns `did_you_mean`, replace the invalid column with `did_you_mean_sql` and retry immediately.
- **Token Efficiency**: Do not request more than 50 rows of raw data unless absolutely necessary. Summarize findings instead of printing entire tables.
- **Reporting Weak Results**: If correlations or statistical tests show "negligible" or "insignificant" results, REPORT THIS as a valid finding. Do not loop infinitely trying to find strong patterns in noisy or independent data.
- **Fallback**: If a SQL query fails due to complex JSON nesting, use `inspect_dataset` to see the parsed structure first.
