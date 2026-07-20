# tests/test_data_tools.py
import os
import sys

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.tools.data_tools import InspectDatasetTool, QueryDatasetTool
from src.tools.schema_cache import SchemaCache, sql_column_reference


DATASET_PATH = "data/smart_manufacturing_dataset.csv"


@pytest.fixture(autouse=True)
def clear_schema_cache():
    SchemaCache.clear()
    yield
    SchemaCache.clear()


def test_sql_column_reference_quotes_special_names():
    assert sql_column_reference("Machine ID") == '"Machine ID"'
    assert sql_column_reference("Energy Consumption (kWh)") == '"Energy Consumption (kWh)"'
    assert sql_column_reference("batch_id") == "batch_id"


def test_inspect_dataset_returns_sql_ready_metadata():
    tool = InspectDatasetTool()
    result = tool.execute(DATASET_PATH)

    assert result["status"] == "success"
    assert result["total_rows"] == 10000
    assert '"Machine ID"' in result["sql_column_list"]
    assert result["example_select"].startswith("SELECT ")
    assert "data/smart_manufacturing_dataset.csv" in result["example_select"]

    machine_col = next(col for col in result["columns"] if col["name"] == "Machine ID")
    assert machine_col["sql_reference"] == '"Machine ID"'
    assert machine_col["type"] == "VARCHAR"


def test_inspect_dataset_registers_schema_cache():
    tool = InspectDatasetTool()
    tool.execute(DATASET_PATH)

    cached = SchemaCache.get(DATASET_PATH)
    assert cached is not None
    assert "Machine ID" in cached["column_names"]
    assert cached["example_select"] is not None


def test_query_dataset_success_with_exact_column_names():
    inspect_tool = InspectDatasetTool()
    inspect_tool.execute(DATASET_PATH)

    query_tool = QueryDatasetTool()
    result = query_tool.execute(
        "SELECT \"Machine ID\", COUNT(*) as row_count "
        "FROM 'data/smart_manufacturing_dataset.csv' "
        "GROUP BY \"Machine ID\" "
        "ORDER BY row_count DESC "
        "LIMIT 3"
    )

    assert result["status"] == "success"
    assert result["total_found"] == 3
    assert "Machine ID" in result["results"][0]


def test_query_dataset_error_includes_schema_suggestions():
    inspect_tool = InspectDatasetTool()
    inspect_tool.execute(DATASET_PATH)

    query_tool = QueryDatasetTool()
    result = query_tool.execute(
        "SELECT Machine_ID FROM 'data/smart_manufacturing_dataset.csv' LIMIT 1"
    )

    assert "error" in result
    assert result["did_you_mean"] == "Machine ID"
    assert result["did_you_mean_sql"] == '"Machine ID"'
    assert "Machine ID" in result["available_columns"]
    assert '"Machine ID"' in result["sql_column_list"]
    assert result["cached_schemas"][0]["example_select"] is not None
