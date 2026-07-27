import pytest
from src.tools.stats_tools import AnalyzeDesignOfExperimentsTool

def test_analyze_doe_results_maximize():
    tool = AnalyzeDesignOfExperimentsTool()
    
    # Simple dataset: Y = 10 + 2*A - 3*B
    # We want to maximize Y. A is positive impact, B is negative.
    # A ranges 1-5, B ranges 1-5.
    # Expected Opt: A=5, B=1
    data = [
        {"temp": 1, "acid": 1, "yield": 9},
        {"temp": 5, "acid": 1, "yield": 17},
        {"temp": 1, "acid": 5, "yield": -3},
        {"temp": 5, "acid": 5, "yield": 5},
        {"temp": 3, "acid": 3, "yield": 7},
        {"temp": 2, "acid": 2, "yield": 8},
        {"temp": 4, "acid": 4, "yield": 6},
    ]
    
    result = tool.execute(
        experiment_data=data,
        target_column="yield",
        factors=["temp", "acid"],
        goal="maximize"
    )
    
    assert result["status"] == "success"
    assert result["optimization"]["goal"] == "maximize"
    assert result["optimization"]["optimal_settings"]["temp"] == 5.0
    assert result["optimization"]["optimal_settings"]["acid"] == 1.0
    assert result["r_squared"] > 0.9
    
    # Check ANOVA
    anova = result["anova"]
    assert any(row["source"] == "Q('temp')" for row in anova)
    assert any(row["source"] == "Q('acid')" for row in anova)

def test_analyze_doe_results_insufficient_data():
    tool = AnalyzeDesignOfExperimentsTool()
    data = [{"a": 1, "y": 10}]
    result = tool.execute(data, "y", ["a"])
    assert "error" in result
    assert "Need at least" in result["error"]
