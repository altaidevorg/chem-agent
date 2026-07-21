import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from src.tools.data_tools import ProfileDatasetHealthTool
from src.tools.stats_tools import AnalyzeDatasetTool

def generate_test_data(file_path):
    """Generates a synthetic industrial dataset for testing."""
    np.random.seed(42)
    n_rows = 500
    
    # Generate timestamps
    start_time = datetime(2026, 7, 20, 8, 0, 0)
    timestamps = [start_time + timedelta(minutes=5*i) for i in range(n_rows)]
    
    # Generate machine IDs (categorical)
    machines = ['M-001', 'M-002', 'M-003', 'M-004', 'M-005']
    machine_ids = np.random.choice(machines, n_rows)
    
    # Generate Temperature with a trend and some nulls
    # Trend: increases slightly over time
    temp_trend = np.linspace(70, 80, n_rows)
    temperature = temp_trend + np.random.normal(0, 2, n_rows)
    # Add nulls (5%)
    temperature[np.random.choice(n_rows, 25, replace=False)] = np.nan
    
    # Generate Pressure
    pressure = 100 + np.random.normal(0, 5, n_rows)
    
    # Generate Yield (correlated with Temp and Pressure)
    # Yield = 0.5*Temp + 0.2*Pressure + noise
    # Since Temp is ~75 and Pressure is ~100, Yield is ~37.5 + 20 = 57.5
    yield_val = 0.5 * np.nan_to_num(temperature, nan=75) + 0.2 * pressure + np.random.normal(0, 1, n_rows)
    
    # Generate Defect Count (for Pareto)
    # M-001 has more defects
    defect_probs = [0.5, 0.1, 0.1, 0.1, 0.2]
    defect_counts = []
    for m in machine_ids:
        idx = machines.index(m)
        defect_counts.append(np.random.poisson(defect_probs[idx] * 5))
    
    # Energy
    energy = 50 + 0.3 * np.nan_to_num(temperature, nan=75) + np.random.normal(0, 2, n_rows)

    df = pd.DataFrame({
        "Timestamp": timestamps,
        "Machine ID": machine_ids,
        "Temperature": temperature,
        "Pressure": pressure,
        "Yield": yield_val,
        "Defect Count": defect_counts,
        "Energy": energy
    })
    
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    df.to_csv(file_path, index=False)
    print(f"Test data generated at {file_path}")

def test_profile_health(file_path):
    print("\n--- Testing profile_dataset_health ---")
    tool = ProfileDatasetHealthTool()
    result = tool.execute(file_path)
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Status: {result['status']}")
        print(f"Total Rows: {result['total_rows']}")
        for col in result['health_report']:
            print(f"Column: {col['column']}, Semantic: {col['semantic_type']}, Nulls: {col['null_count']} ({col['null_percentage']}%)")

def test_regression(file_path):
    print("\n--- Testing regression analysis ---")
    tool = AnalyzeDatasetTool()
    result = tool.execute(
        file_path=file_path,
        analysis_type="regression",
        target_column="Yield",
        predictor_columns=["Temperature", "Pressure"]
    )
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Status: {result['status']}")
        print(f"R-squared: {result['result']['r_squared']}")
        print(f"Coefficients: {result['result']['coefficients']}")

def test_process_capability(file_path):
    print("\n--- Testing process_capability analysis ---")
    tool = AnalyzeDatasetTool()
    # Test for Temperature with USL=85, LSL=65
    result = tool.execute(
        file_path=file_path,
        analysis_type="process_capability",
        columns=["Temperature"],
        usl=85,
        lsl=65
    )
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Status: {result['status']}")
        print(f"Mean: {result['mean']}, StdDev: {result['std_dev']}")
        print(f"Cp: {result['result']['cp']}, Cpk: {result['result']['cpk']}")

def test_pareto(file_path):
    print("\n--- Testing pareto analysis ---")
    tool = AnalyzeDatasetTool()
    result = tool.execute(
        file_path=file_path,
        analysis_type="pareto",
        group_by="Machine ID",
        columns=["Defect Count"]
    )
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Status: {result['status']}")
        print(f"Message: {result['message']}")
        for row in result['result']:
            print(f"Category: {row['category']}, Value: {row['total_value']}, Cumulative %: {round(row['cumulative_percentage'], 2)}%")

def test_trend_projection(file_path):
    print("\n--- Testing trend_projection analysis ---")
    tool = AnalyzeDatasetTool()
    result = tool.execute(
        file_path=file_path,
        analysis_type="trend_projection",
        target_column="Temperature",
        timestamp_column="Timestamp"
    )
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Status: {result['status']}")
        print(f"Trend: {result['result']['trend_interpretation']}")
        print(f"Slope (per sec): {result['result']['slope_per_second']}")

def test_downsample(file_path):
    print("\n--- Testing downsample analysis ---")
    tool = AnalyzeDatasetTool()
    result = tool.execute(
        file_path=file_path,
        analysis_type="downsample",
        columns=["Temperature", "Yield"],
        timestamp_column="Timestamp",
        limit=20
    )
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Status: {result['status']}")
        print(f"Original: {result['n_original']}, Returned: {result['n_returned']}")
        print(f"Message: {result['message']}")

def test_correlation_matrix(file_path):
    print("\n--- Testing correlation_matrix analysis ---")
    tool = AnalyzeDatasetTool()
    result = tool.execute(
        file_path=file_path,
        analysis_type="correlation_matrix"
    )
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Status: {result['status']}")
        print(f"Columns analyzed: {result['columns_analyzed']}")
        print(f"Top relationships:")
        for rel in result['top_relationships']:
            print(f"  {rel['pair']}: {rel['correlation']} ({rel['interpretation']})")

def test_seasonal_decomposition(file_path):
    print("\n--- Testing seasonal_decomposition analysis ---")
    tool = AnalyzeDatasetTool()
    result = tool.execute(
        file_path=file_path,
        analysis_type="seasonal_decomposition",
        columns=["Temperature"],
        timestamp_column="Timestamp",
        period=12
    )
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Status: {result['status']}")
        print(f"Trend Direction: {result['trend_direction']}")
        print(f"Seasonal Strength: {result['seasonal_strength_ratio']}")
        print(f"Message: {result['message']}")

if __name__ == "__main__":
    test_file = "/home/ubuntu/chem-agent/tests/data/synthetic_industrial.csv"
    generate_test_data(test_file)
    test_profile_health(test_file)
    test_regression(test_file)
    test_process_capability(test_file)
    test_pareto(test_file)
    test_trend_projection(test_file)
    test_downsample(test_file)
    test_correlation_matrix(test_file)
    test_seasonal_decomposition(test_file)
