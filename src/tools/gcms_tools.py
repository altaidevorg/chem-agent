# src/tools/gcms_tools.py
import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional
from src.tools.base import BaseTool, ToolRegistry

class CompareGCMSProfilesTool(BaseTool):
    """
    Compares two GC-MS peak profiles (Sample vs Standard).
    Performs peak alignment based on retention time and calculates similarity.
    """

    @property
    def name(self) -> str:
        return "compare_gcms_profiles"

    @property
    def description(self) -> str:
        return (
            "Compares a sample GC-MS peak list against a standard/reference profile. "
            "Matches peaks within a retention time window and calculates a similarity score."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "sample_peaks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "rt": {"type": "number", "description": "Retention time"},
                            "area_pct": {"type": "number", "description": "Area percentage (%)"},
                            "name": {"type": "string", "description": "Optional compound name"}
                        },
                        "required": ["rt", "area_pct"]
                    }
                },
                "standard_peaks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "rt": {"type": "number", "description": "Retention time"},
                            "area_pct": {"type": "number", "description": "Area percentage (%)"},
                            "name": {"type": "string", "description": "Optional compound name"}
                        },
                        "required": ["rt", "area_pct"]
                    }
                },
                "rt_tolerance": {
                    "type": "number", 
                    "description": "Retention time window for matching (default: 0.05 min)",
                    "default": 0.05
                }
            },
            "required": ["sample_peaks", "standard_peaks"]
        }

    def execute(self, sample_peaks: List[Dict[str, Any]], standard_peaks: List[Dict[str, Any]], rt_tolerance: float = 0.05, **kwargs) -> Dict[str, Any]:
        try:
            # Convert to DataFrames for easier processing
            df_sample = pd.DataFrame(sample_peaks).sort_values("rt")
            df_std = pd.DataFrame(standard_peaks).sort_values("rt")

            matched = []
            unmatched_sample = []
            unmatched_std = list(range(len(df_std)))

            for i, s_row in df_sample.iterrows():
                # Find best match in standard within RT tolerance
                match_idx = -1
                best_diff = float('inf')
                
                for j in unmatched_std:
                    diff = abs(s_row['rt'] - df_std.iloc[j]['rt'])
                    if diff <= rt_tolerance and diff < best_diff:
                        best_diff = diff
                        match_idx = j
                
                if match_idx != -1:
                    matched.append({
                        "sample_idx": i,
                        "std_idx": match_idx,
                        "rt_sample": s_row['rt'],
                        "rt_std": df_std.iloc[match_idx]['rt'],
                        "rt_diff": round(s_row['rt'] - df_std.iloc[match_idx]['rt'], 4),
                        "area_sample": s_row['area_pct'],
                        "area_std": df_std.iloc[match_idx]['area_pct'],
                        "area_diff": round(s_row['area_pct'] - df_std.iloc[match_idx]['area_pct'], 2),
                        "name": s_row.get('name') or df_std.iloc[match_idx].get('name') or "Unknown"
                    })
                    unmatched_std.remove(match_idx)
                else:
                    unmatched_sample.append(i)

            # Calculate Cosine Similarity on areas
            # To do this correctly, we need a common vector
            # We'll use all unique peaks found in either (aligned)
            all_peaks = []
            vec_sample = []
            vec_std = []

            for m in matched:
                vec_sample.append(m['area_sample'])
                vec_std.append(m['area_std'])
            
            for i in unmatched_sample:
                vec_sample.append(df_sample.iloc[i]['area_pct'])
                vec_std.append(0.0)
            
            for j in unmatched_std:
                vec_sample.append(0.0)
                vec_std.append(df_std.iloc[j]['area_pct'])

            v1 = np.array(vec_sample)
            v2 = np.array(vec_std)
            
            similarity = 0.0
            if np.linalg.norm(v1) > 0 and np.linalg.norm(v2) > 0:
                similarity = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

            return {
                "status": "success",
                "similarity_score": round(float(similarity), 4),
                "match_count": len(matched),
                "unmatched_sample_count": len(unmatched_sample),
                "unmatched_standard_count": len(unmatched_std),
                "matches": matched,
                "missing_peaks": df_std.iloc[unmatched_std].to_dict('records'),
                "extra_peaks": df_sample.iloc[unmatched_sample].to_dict('records'),
                "summary": (
                    f"Profile similarity is {round(similarity*100, 1)}%. "
                    f"Found {len(matched)} matching peaks, {len(unmatched_sample)} extra peaks, "
                    f"and {len(unmatched_std)} missing peaks."
                )
            }
        except Exception as e:
            return {"error": f"GC-MS comparison failed: {str(e)}"}

class DetectGCMSAnomaliesTool(BaseTool):
    """
    Analyzes a GC-MS profile for potential quality issues.
    """

    @property
    def name(self) -> str:
        return "detect_gcms_anomalies"

    @property
    def description(self) -> str:
        return (
            "Analyzes GC-MS profile for anomalies such as contamination (extra peaks), "
            "missing components, or significant concentration deviations."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "comparison_results": {
                    "type": "object",
                    "description": "Output from compare_gcms_profiles."
                },
                "area_threshold_pct": {
                    "type": "number",
                    "description": "Relative difference threshold for area deviation (default: 20%)",
                    "default": 20.0
                },
                "min_extra_peak_area": {
                    "type": "number",
                    "description": "Ignore extra peaks below this area % (default: 0.1%)",
                    "default": 0.1
                }
            },
            "required": ["comparison_results"]
        }

    def execute(self, comparison_results: Dict[str, Any], area_threshold_pct: float = 20.0, min_extra_peak_area: float = 0.1, **kwargs) -> Dict[str, Any]:
        try:
            if comparison_results.get("status") != "success":
                return {"error": "Invalid comparison results provided."}

            anomalies = []
            
            # 1. Check for significant area deviations in matched peaks
            for m in comparison_results["matches"]:
                # Relative difference: |A1 - A2| / A2 * 100
                if m["area_std"] > 0:
                    rel_diff = (abs(m["area_sample"] - m["area_std"]) / m["area_std"]) * 100
                    if rel_diff > area_threshold_pct:
                        anomalies.append({
                            "type": "AREA_DEVIATION",
                            "severity": "High" if rel_diff > 50 else "Medium",
                            "compound": m["name"],
                            "rt": m["rt_sample"],
                            "message": f"Component '{m['name']}' area deviate by {round(rel_diff, 1)}% from standard."
                        })

            # 2. Check for missing peaks
            for p in comparison_results["missing_peaks"]:
                anomalies.append({
                    "type": "MISSING_COMPONENT",
                    "severity": "High" if p["area_pct"] > 1.0 else "Medium",
                    "compound": p.get("name", "Unknown"),
                    "rt": p["rt"],
                    "message": f"Standard peak at RT {p['rt']} ({p.get('name', 'Unknown')}) is missing in sample."
                })

            # 3. Check for extra peaks (Contamination)
            for p in comparison_results["extra_peaks"]:
                if p["area_pct"] >= min_extra_peak_area:
                    anomalies.append({
                        "type": "CONTAMINATION_RISK",
                        "severity": "High" if p["area_pct"] > 0.5 else "Medium",
                        "rt": p["rt"],
                        "area_pct": p["area_pct"],
                        "message": f"Extra peak detected at RT {p['rt']} with {p['area_pct']}% area. Possible contaminant."
                    })

            # Overall Status
            status = "PASS" if not anomalies else "FAIL"
            if status == "FAIL" and all(a["severity"] == "Medium" for a in anomalies):
                status = "WARNING"

            return {
                "status": "success",
                "quality_status": status,
                "anomalies": anomalies,
                "anomaly_count": len(anomalies),
                "similarity_score": comparison_results["similarity_score"],
                "summary": (
                    f"QC Status: {status}. Detected {len(anomalies)} anomalies. "
                    f"Similarity Score: {comparison_results['similarity_score']}."
                )
            }
        except Exception as e:
            return {"error": f"Anomaly detection failed: {str(e)}"}

# Register tools
ToolRegistry.register(CompareGCMSProfilesTool())
ToolRegistry.register(DetectGCMSAnomaliesTool())
