# 🏭 Industrial Data Analysis Test Plan for ChemAgent

This plan outlines the testing strategy for evaluating the ChemAgent's performance in industrial data analysis tasks, including Exploratory Data Analysis (EDA), statistical analysis, and report generation.

## 🎯 Objectives
1.  Evaluate the agent's ability to read and interpret various industrial data formats (CSV, JSONL, JSON, MD, TXT).
2.  Assess the agent's accuracy in performing basic statistical calculations.
3.  Test the agent's reasoning capabilities in identifying trends and anomalies in process data.
4.  Identify gaps in the agent's current "skill set" for industrial applications.

## 📂 Test Data (Mock Files)
The following mock files have been prepared in the `data/` directory:
-   `industrial_process.csv`: Time-series sensor data (temperature, pressure, yield).
-   `batch_records.jsonl`: Structured batch production records.
-   `chemical_inventory.json`: Inventory levels and purity data.
-   `maintenance_logs.txt`: Unstructured maintenance history.
-   `sensor_metadata.jsonl`: Metadata about the sensors used in the process.
-   `quality_control_report.md`: A sample QC report for a specific batch.

## 🧪 Test Scenarios

### Scenario 1: Basic Data Extraction & Summary
-   **Query**: "Read `data/industrial_process.csv` and summarize the data. What columns are present and what is the time range?"
-   **Expected Result**: Correct identification of columns and the start/end timestamps.

### Scenario 2: Statistical Analysis (Base Version)
-   **Query**: "Calculate the average temperature and the maximum pressure from `data/industrial_process.csv`."
-   **Expected Result**: The agent should attempt to calculate these. *Note: The base version might struggle with precision if the dataset is large.*

### Scenario 3: Trend Analysis & Reasoning
-   **Query**: "In `data/industrial_process.csv`, there is a drop in yield at one point. Can you identify which timestamp it was and if any other sensor values were unusual at that time?"
-   **Expected Result**: Identification of the 03:00:00 timestamp (Yield: 82.3) and noting the high temperature (80.1) and pressure (1.5).

### Scenario 4: Cross-File Data Correlation
-   **Query**: "Check `data/batch_records.jsonl` for Batch B003. What was its quality score? Then check `data/chemical_inventory.json` to see if we have enough Aspirin in stock (more than 40kg)."
-   **Expected Result**: Correct extraction of 0.88 quality score and confirmation of 50kg Aspirin stock.

### Scenario 5: Unstructured Data Interpretation
-   **Query**: "Based on `data/maintenance_logs.txt`, what was the last action performed on Reactor R-101?"
-   **Expected Result**: Extraction of "Replaced seal on main agitator shaft."

## 📈 Success Metrics
-   **Accuracy**: Are the extracted values and calculated statistics correct?
-   **Completeness**: Did the agent address all parts of the query?
-   **Reasoning**: Did the agent correctly link cause and effect (e.g., high temp -> low yield)?
-   **Tool Usage**: Did the agent use `read_file` correctly?

## 🚀 Next Steps (Post-Testing)
Based on the results, we will implement new skills:
-   `DataAnalysisSkill`: Using `pandas` for robust statistical analysis.
-   `PlottingSkill`: Using `matplotlib` or `plotly` for data visualization.
-   `AnomalyDetectionSkill`: For automated identification of process deviations.
