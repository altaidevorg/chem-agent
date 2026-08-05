# src/tools/sensory_tools.py
import json
import os
from typing import Any, Dict, List, Optional

import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm
from statsmodels.formula.api import ols
from statsmodels.stats.multicomp import pairwise_tukeyhsd

from src.tools.base import BaseTool, ToolRegistry

class AnalyzeSensoryPanelTool(BaseTool):
    """
    Analyzes sensory panel data for panelist consistency, 
    product differences (ANOVA), and sensory profiling.
    """

    @property
    def name(self) -> str:
        return "analyze_sensory_panel"

    @property
    def description(self) -> str:
        return (
            "Analyzes sensory panel data. Evaluates panelist consistency (Cronbach's Alpha), "
            "performs sensory ANOVA (Sample, Panelist, Interaction), and identifies "
            "significant differences between samples using Tukey HSD post-hoc tests."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "sensory_data": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "List of panelist evaluations. Each dict must contain 'sample_id', 'panelist_id', and attribute scores (e.g. 'sweetness', 'aroma_intensity')."
                },
                "attributes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "The sensory attributes to analyze (e.g., ['sweetness', 'bitterness'])."
                },
                "sample_col": {
                    "type": "string",
                    "default": "sample_id",
                    "description": "Column name identifying the sample/product."
                },
                "panelist_col": {
                    "type": "string",
                    "default": "panelist_id",
                    "description": "Column name identifying the panelist."
                }
            },
            "required": ["sensory_data", "attributes"]
        }

    def _calculate_cronbach_alpha(self, df: pd.DataFrame, attribute: str, sample_col: str, panelist_col: str) -> float:
        """Calculates Cronbach's Alpha for panelist consistency on a specific attribute."""
        try:
            # Pivot to have samples as rows and panelists as columns
            matrix = df.pivot(index=sample_col, columns=panelist_col, values=attribute)
            # Remove columns/rows with all NaNs
            matrix = matrix.dropna(axis=0, how='any').dropna(axis=1, how='any')
            
            if matrix.shape[1] < 2:
                return 0.0
            
            item_vars = matrix.var(axis=0, ddof=1)
            total_var = matrix.sum(axis=1).var(ddof=1)
            n_items = matrix.shape[1]
            
            if total_var == 0:
                return 0.0
            
            alpha = (n_items / (n_items - 1)) * (1 - (item_vars.sum() / total_var))
            return float(alpha)
        except:
            return 0.0

    def execute(
        self, 
        sensory_data: List[Dict[str, Any]], 
        attributes: List[str],
        sample_col: str = "sample_id",
        panelist_col: str = "panelist_id",
        **kwargs
    ) -> Dict[str, Any]:
        try:
            df = pd.DataFrame(sensory_data)
            
            # 1. Validation
            missing = [c for c in [sample_col, panelist_col] + attributes if c not in df.columns]
            if missing:
                return {"error": f"Missing columns in data: {missing}"}
            
            if len(df) < 6:
                return {"error": "Insufficient data points for sensory analysis. Need at least 6 observations."}

            results = {}
            summary_parts = []

            for attr in attributes:
                attr_res = {}
                
                # A. Consistency Check (Cronbach's Alpha)
                alpha = self._calculate_cronbach_alpha(df, attr, sample_col, panelist_col)
                attr_res["cronbach_alpha"] = round(alpha, 3)
                attr_res["consistency_label"] = (
                    "Excellent" if alpha > 0.9 else 
                    "Good" if alpha > 0.8 else 
                    "Acceptable" if alpha > 0.7 else 
                    "Poor"
                )

                # B. Sensory ANOVA (2-way: Sample + Panelist)
                # Formula: score ~ C(Sample) + C(Panelist)
                try:
                    formula = f"Q('{attr}') ~ C(Q('{sample_col}')) + C(Q('{panelist_col}'))"
                    model = ols(formula, data=df).fit()
                    anova_table = sm.stats.anova_lm(model, typ=2)
                    
                    attr_res["anova"] = {
                        "sample_p_value": round(float(anova_table.loc[f"C(Q('{sample_col}'))", "PR(>F)"]), 5),
                        "panelist_p_value": round(float(anova_table.loc[f"C(Q('{panelist_col}'))", "PR(>F)"]), 5),
                        "is_sample_significant": bool(anova_table.loc[f"C(Q('{sample_col}'))", "PR(>F)"] < 0.05)
                    }
                    
                    # C. Post-hoc (Tukey HSD) if samples are significant
                    if attr_res["anova"]["is_sample_significant"]:
                        tukey = pairwise_tukeyhsd(endog=df[attr], groups=df[sample_col], alpha=0.05)
                        tukey_df = pd.DataFrame(data=tukey._results_table.data[1:], columns=tukey._results_table.data[0])
                        
                        # Filter only significant differences
                        sig_diffs = tukey_df[tukey_df["reject"] == True]
                        attr_res["significant_differences"] = [
                            f"{row['group1']} vs {row['group2']} (diff={round(row['meandiff'], 2)})"
                            for _, row in sig_diffs.iterrows()
                        ]
                except Exception as e:
                    attr_res["anova_error"] = str(e)

                # D. Attribute Means
                means = df.groupby(sample_col)[attr].mean().round(2).to_dict()
                attr_res["sample_means"] = means
                
                results[attr] = attr_res
                
                # Add to summary
                sig_text = "Significant differences found" if attr_res.get("anova", {}).get("is_sample_significant") else "No significant differences"
                summary_parts.append(f"{attr}: {sig_text} (Alpha: {round(alpha, 2)})")

            return {
                "status": "success",
                "attribute_analysis": results,
                "summary": " | ".join(summary_parts)
            }
            
        except Exception as e:
            return {"error": f"Sensory analysis failed: {str(e)}"}

ToolRegistry.register(AnalyzeSensoryPanelTool())
