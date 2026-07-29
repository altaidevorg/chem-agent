# tests/test_sensory_tools.py
import pytest
import pandas as pd
import numpy as np
from src.tools.sensory_tools import AnalyzeSensoryPanelTool

def test_analyze_sensory_panel_basic():
    tool = AnalyzeSensoryPanelTool()
    
    # Create mock sensory data: 3 samples, 3 panelists, 2 attributes
    # Sample 1: high sweetness, Sample 3: low sweetness
    # Panelists are consistent
    data = [
        {"sample_id": "S1", "panelist_id": "P1", "sweetness": 8, "aroma": 5},
        {"sample_id": "S1", "panelist_id": "P2", "sweetness": 9, "aroma": 6},
        {"sample_id": "S1", "panelist_id": "P3", "sweetness": 8, "aroma": 5},
        {"sample_id": "S2", "panelist_id": "P1", "sweetness": 5, "aroma": 5},
        {"sample_id": "S2", "panelist_id": "P2", "sweetness": 6, "aroma": 5},
        {"sample_id": "S2", "panelist_id": "P3", "sweetness": 5, "aroma": 6},
        {"sample_id": "S3", "panelist_id": "P1", "sweetness": 2, "aroma": 5},
        {"sample_id": "S3", "panelist_id": "P2", "sweetness": 1, "aroma": 4},
        {"sample_id": "S3", "panelist_id": "P3", "sweetness": 2, "aroma": 5},
    ]
    
    result = tool.execute(
        sensory_data=data,
        attributes=["sweetness", "aroma"],
        sample_col="sample_id",
        panelist_col="panelist_id"
    )
    
    assert result["status"] == "success"
    assert "sweetness" in result["attribute_analysis"]
    assert "aroma" in result["attribute_analysis"]
    
    # Sweetness should be highly significant
    assert result["attribute_analysis"]["sweetness"]["anova"]["is_sample_significant"] is True
    # Aroma should NOT be significant (all around 5)
    assert result["attribute_analysis"]["aroma"]["anova"]["is_sample_significant"] is False
    
    # Cronbach's Alpha for sweetness should be high
    assert result["attribute_analysis"]["sweetness"]["cronbach_alpha"] > 0.8
    
    # Tukey check for sweetness
    assert len(result["attribute_analysis"]["sweetness"]["significant_differences"]) > 0

def test_analyze_sensory_panel_inconsistency():
    tool = AnalyzeSensoryPanelTool()
    
    # Panelists are completely random
    data = []
    for s in ["S1", "S2"]:
        for p in ["P1", "P2", "P3"]:
            data.append({
                "sample_id": s,
                "panelist_id": p,
                "sweetness": np.random.randint(1, 10)
            })
            
    result = tool.execute(sensory_data=data, attributes=["sweetness"])
    assert result["status"] == "success"
    # Consistency should likely be low or "Poor"
    assert "sweetness" in result["attribute_analysis"]
