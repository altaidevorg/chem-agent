# tests/test_stats_tools.py
import os
import sys

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.tools.data_tools import InspectDatasetTool
from src.tools.stats_tools import AnalyzeDatasetTool, PredictShelfLifeArrheniusTool
from src.tools.schema_cache import SchemaCache


DATASET_PATH = "data/smart_manufacturing_dataset.csv"


@pytest.fixture(autouse=True)
def clear_schema_cache():
    SchemaCache.clear()
    yield
    SchemaCache.clear()


@pytest.fixture
def inspected_dataset():
    inspect = InspectDatasetTool()
    inspect.execute(DATASET_PATH)


def test_correlation_row_level(inspected_dataset):
    tool = AnalyzeDatasetTool()
    result = tool.execute(
        file_path=DATASET_PATH,
        analysis_type="correlation",
        columns=["Recycled Material (%)", "Defect Rate (%)"],
        granularity="row_level",
        method="pearson",
    )

    assert result["status"] == "success"
    assert result["granularity"] == "row_level"
    assert result["n"] == 10000
    assert abs(result["result"]["correlation_coefficient"] - (-0.0024)) < 0.001
    assert "interpretation_hint" in result["result"]


def test_correlation_group_by(inspected_dataset):
    tool = AnalyzeDatasetTool()
    result = tool.execute(
        file_path=DATASET_PATH,
        analysis_type="correlation",
        columns=["Recycled Material (%)", "Defect Rate (%)"],
        granularity="group_by",
        group_by="Machine ID",
        method="pearson",
    )

    assert result["status"] == "success"
    assert result["granularity"] == "group_by"
    assert result["n"] == 10
    assert abs(result["result"]["correlation_coefficient"] - (-0.4230)) < 0.01
    assert "warning" in result


def test_ratio_rank_sum_ratio(inspected_dataset):
    tool = AnalyzeDatasetTool()
    result = tool.execute(
        file_path=DATASET_PATH,
        analysis_type="ratio_rank",
        numerator="Energy Consumption (kWh)",
        denominator="Production Output (Units)",
        group_by="Machine ID",
        ratio_method="sum_ratio",
        order="desc",
        limit=5,
    )

    assert result["status"] == "success"
    assert len(result["result"]) == 5
    assert result["result"][0]["group_value"] == "M005"
    assert abs(result["result"][0]["ratio_value"] - 0.2581) < 0.001


def test_describe_columns(inspected_dataset):
    tool = AnalyzeDatasetTool()
    result = tool.execute(
        file_path=DATASET_PATH,
        analysis_type="describe",
        columns=["Defect Rate (%)", "Recycled Material (%)"],
    )

    assert result["status"] == "success"
    assert result["n_rows"] == 10000
    assert len(result["result"]) == 2
    assert result["result"][0]["mean"] > 0


def test_group_compare(inspected_dataset):
    tool = AnalyzeDatasetTool()
    result = tool.execute(
        file_path=DATASET_PATH,
        analysis_type="group_compare",
        columns=["Defect Rate (%)"],
        group_by="Material Category",
    )

    assert result["status"] == "success"
    assert len(result["result"]) >= 3
    assert "mean_value" in result["result"][0]


def test_outlier_detection(inspected_dataset):
    tool = AnalyzeDatasetTool()
    result = tool.execute(
        file_path=DATASET_PATH,
        analysis_type="outlier",
        columns=["Energy Consumption (kWh)"],
        z_threshold=3.0,
        limit=5,
    )

    assert result["status"] == "success"
    assert "population_stats" in result
    assert result["outlier_count_returned"] <= 5


def test_filters_parameter(inspected_dataset):
    tool = AnalyzeDatasetTool()
    result = tool.execute(
        file_path=DATASET_PATH,
        analysis_type="describe",
        columns=["Defect Rate (%)"],
        filters={"Machine ID": "M005"},
    )

    assert result["status"] == "success"
    assert result["n_rows"] == 1004


def test_invalid_column_rejected(inspected_dataset):
    tool = AnalyzeDatasetTool()
    result = tool.execute(
        file_path=DATASET_PATH,
        analysis_type="correlation",
        columns=["Recycled Material (%)", "Cycle Time (min)"],
        granularity="row_level",
    )

    assert "error" in result
    assert "Cycle Time (min)" in result["invalid_columns"]


def test_correlation_without_cache_uses_live_schema():
    tool = AnalyzeDatasetTool()
    result = tool.execute(
        file_path=DATASET_PATH,
        analysis_type="correlation",
        columns=["Recycled Material (%)", "Defect Rate (%)"],
        granularity="row_level",
    )

    assert result["status"] == "success"
    assert result["n"] == 10000


def test_predict_shelf_life_arrhenius():
    tool = PredictShelfLifeArrheniusTool()
    
    # Mock data for 0th order degradation
    # Temp 40C (313.15K): y = -2*t + 100
    # Temp 50C (323.15K): y = -5*t + 100
    stability_data = [
        {"temperature": 40, "time": 0, "value": 100},
        {"temperature": 40, "time": 5, "value": 90},
        {"temperature": 40, "time": 10, "value": 80},
        {"temperature": 50, "time": 0, "value": 100},
        {"temperature": 50, "time": 2, "value": 90},
        {"temperature": 50, "time": 4, "value": 80},
    ]
    
    result = tool.execute(
        stability_data=stability_data,
        failure_threshold=70,
        target_temperature=25
    )
    
    assert result["status"] == "success"
    assert result["reaction_order"] == 0
    assert "predicted_shelf_life" in result["prediction"]
    assert result["activation_energy_kj_mol"] > 0
    assert len(result["temperature_fits"]) == 2
    
    # Check if target shelf life is longer than accelerated
    # k_40 = 2, k_50 = 5. At 25C, k should be < 2.
    # Shelf life at 40C = (100-70)/2 = 15 days
    # Shelf life at 25C should be > 15 days
    assert result["prediction"]["predicted_shelf_life"] > 15
