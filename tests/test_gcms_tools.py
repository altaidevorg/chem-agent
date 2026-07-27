# tests/test_gcms_tools.py
import pytest
from src.tools.gcms_tools import CompareGCMSProfilesTool, DetectGCMSAnomaliesTool

def test_compare_gcms_profiles_success():
    tool = CompareGCMSProfilesTool()
    
    std = [
        {"rt": 1.20, "area_pct": 80.0, "name": "Limonene"},
        {"rt": 2.50, "area_pct": 20.0, "name": "Linalool"}
    ]
    
    # Slight RT drift and area shift
    sample = [
        {"rt": 1.21, "area_pct": 78.0, "name": "Limonene"},
        {"rt": 2.52, "area_pct": 22.0, "name": "Linalool"}
    ]
    
    result = tool.execute(sample_peaks=sample, standard_peaks=std, rt_tolerance=0.05)
    
    assert result["status"] == "success"
    assert result["similarity_score"] > 0.99
    assert result["match_count"] == 2
    assert len(result["matches"]) == 2

def test_detect_anomalies_contamination():
    tool_compare = CompareGCMSProfilesTool()
    tool_anomaly = DetectGCMSAnomaliesTool()
    
    std = [{"rt": 1.20, "area_pct": 100.0, "name": "Standard"}]
    # Sample has an extra peak at 3.0 min
    sample = [
        {"rt": 1.20, "area_pct": 95.0, "name": "Standard"},
        {"rt": 3.00, "area_pct": 5.0, "name": "Contaminant"}
    ]
    
    comp_res = tool_compare.execute(sample, std)
    anom_res = tool_anomaly.execute(comp_res)
    
    assert anom_res["status"] == "success"
    assert anom_res["quality_status"] == "FAIL"
    # Find contamination anomaly
    anoms = [a for a in anom_res["anomalies"] if a["type"] == "CONTAMINATION_RISK"]
    assert len(anoms) == 1
    assert anoms[0]["area_pct"] == 5.0

def test_detect_anomalies_missing():
    tool_compare = CompareGCMSProfilesTool()
    tool_anomaly = DetectGCMSAnomaliesTool()
    
    std = [
        {"rt": 1.0, "area_pct": 50.0, "name": "A"},
        {"rt": 2.0, "area_pct": 50.0, "name": "B"}
    ]
    # Component B is missing
    sample = [{"rt": 1.0, "area_pct": 100.0, "name": "A"}]
    
    comp_res = tool_compare.execute(sample, std)
    anom_res = tool_anomaly.execute(comp_res)
    
    assert any(a["type"] == "MISSING_COMPONENT" for a in anom_res["anomalies"])
