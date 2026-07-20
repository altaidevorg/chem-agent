# tests/test_timeseries.py
import os
import sys
import json
from src.tools.stats_tools import AnalyzeDatasetTool

def test_rolling_stats():
    print("\n--- Testing Rolling Stats ---")
    tool = AnalyzeDatasetTool()
    result = tool.execute(
        file_path="data/smart_manufacturing_dataset.csv",
        analysis_type="rolling_stats",
        columns=["Energy Consumption (kWh)"],
        timestamp_column="Timestamp",
        window_size=5,
        group_by="Machine ID"
    )
    if result.get("status") == "success":
        print("Success!")
        sample = result["result"][0]
        print(f"Sample keys: {list(sample.keys())}")
        print(f"Rolling Avg Sample: {sample.get('rolling_avg_Energy Consumption (kWh)')}")
    else:
        print(f"Failed: {result.get('error')}")

def test_lag_analysis():
    print("\n--- Testing Lag Analysis ---")
    tool = AnalyzeDatasetTool()
    result = tool.execute(
        file_path="data/smart_manufacturing_dataset.csv",
        analysis_type="lag_analysis",
        columns=["Quantity Used (kg)", "Production Output (Units)"],
        timestamp_column="Timestamp",
        lag_steps=2
    )
    if result.get("status") == "success":
        print("Success!")
        print(f"Correlation: {result['result']['correlation_coefficient']}")
        print(f"Interpretation: {result['result']['interpretation_hint']}")
    else:
        print(f"Failed: {result.get('error')}")

def test_shift_analysis():
    print("\n--- Testing Shift Analysis ---")
    tool = AnalyzeDatasetTool()
    result = tool.execute(
        file_path="data/smart_manufacturing_dataset.csv",
        analysis_type="shift_analysis",
        columns=["Defect Rate (%)"],
        timestamp_column="Timestamp"
    )
    if result.get("status") == "success":
        print("Success!")
        print(f"Results: {json.dumps(result['result'], indent=2)}")
    else:
        print(f"Failed: {result.get('error')}")

if __name__ == "__main__":
    # Ensure src is in path
    sys.path.append(os.getcwd())
    test_rolling_stats()
    test_lag_analysis()
    test_shift_analysis()
