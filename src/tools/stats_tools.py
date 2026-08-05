# src/tools/stats_tools.py
import json
import math
import os
from typing import Any, Dict, List, Optional

import duckdb
import pandas as pd
import numpy as np
from scipy import stats, optimize
import statsmodels.api as sm
from statsmodels.formula.api import ols
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from src.tools.base import BaseTool, ToolRegistry
from src.tools.schema_cache import SchemaCache, sql_column_reference


def _interpret_correlation(r: float) -> str:
    """Returns a human-readable interpretation for a Pearson/Spearman coefficient."""
    if math.isnan(r):
        return "undefined correlation (NaN)"
    magnitude = abs(r)
    if magnitude < 0.1:
        strength = "negligible"
    elif magnitude < 0.3:
        strength = "weak"
    elif magnitude < 0.5:
        strength = "moderate"
    elif magnitude < 0.7:
        strength = "strong"
    else:
        strength = "very strong"

    if magnitude < 0.1:
        direction = "no meaningful linear"
    elif r > 0:
        direction = "positive"
    else:
        direction = "negative"

    return f"{strength} {direction} correlation"


def _filters_to_where(filters: Optional[Dict[str, Any]]) -> str:
    """Converts a simple filter dict into a SQL WHERE clause body."""
    if not filters:
        return ""

    clauses = []
    for column, value in filters.items():
        col_ref = sql_column_reference(column)
        if isinstance(value, list):
            # FIX: Support list values using SQL 'IN (...)' syntax
            escaped_vals = [f"'{str(v).replace('\'', '\'\'')}'" for v in value]
            clauses.append(f'{col_ref} IN ({", ".join(escaped_vals)})')
        elif isinstance(value, str):
            escaped = value.replace("'", "''")
            clauses.append(f"{col_ref} = '{escaped}'")
        elif isinstance(value, bool):
            clauses.append(f"{col_ref} = {str(value).upper()}")
        elif value is None:
            clauses.append(f"{col_ref} IS NULL")
        else:
            clauses.append(f"{col_ref} = {value}")

    return " AND ".join(clauses)


def _merge_where_clauses(where_clause: Optional[str], filters: Optional[Dict[str, Any]]) -> str:
    """Combines explicit where_clause and structured filters."""
    parts = []
    filter_clause = _filters_to_where(filters)
    if where_clause and where_clause.strip():
        parts.append(where_clause.strip())
    if filter_clause:
        parts.append(filter_clause)
    return " AND ".join(parts)


def _sanitize_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    return json.loads(df.to_json(orient="records", date_format="iso"))


def _validate_requested_columns(file_path: str, columns: List[str]) -> Optional[Dict[str, Any]]:
    validation = SchemaCache.validate_columns(file_path, columns)
    if not validation.get("valid", False):
        return {
            "error": "Invalid column name(s) for analysis.",
            "invalid_columns": validation.get("invalid_columns", []),
            "available_columns": validation.get("available_columns", []),
            "suggestions": validation.get("suggestions", {}),
            "hint": "Run inspect_dataset first and use exact column names.",
        }
    return None


class AnalyzeDatasetTool(BaseTool):
    @property
    def name(self) -> str:
        return "analyze_dataset"

    @property
    def description(self) -> str:
        return (
            "Performs deterministic statistical analysis on tabular datasets (CSV/JSONL). "
            "Use this for correlation, descriptive stats, ratio ranking, outliers, group comparisons, "
            "regression, process capability, pareto, trend projection, downsampling, correlation matrix, "
            "seasonal decomposition, PCA, t-tests, and chi-square tests. "
            "Never calculate statistics mentally — always use this tool."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the dataset file (.csv or .jsonl).",
                },
                "analysis_type": {
                    "type": "string",
                    "enum": ["correlation", "describe", "ratio_rank", "outlier", "group_compare", "rolling_stats", "lag_analysis", "shift_analysis", "regression", "process_capability", "pareto", "trend_projection", "downsample", "correlation_matrix", "seasonal_decomposition", "pca", "t_test", "chi_square"],
                    "description": "Type of statistical analysis to perform.",
                },
                "columns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Column names involved in the analysis. For 'describe' and 'outlier', this is optional and defaults to all numeric columns.",
                },
                "period": {
                    "type": "integer",
                    "description": "The seasonal period for decomposition (e.g., 24 for hourly data with daily seasonality, 7 for daily data with weekly seasonality).",
                },
                "target_column": {
                    "type": "string",
                    "description": "Target variable (Y) for regression analysis.",
                },
                "predictor_columns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Predictor variables (X) for regression analysis.",
                },
                "lsl": {
                    "type": "number",
                    "description": "Lower Specification Limit for process capability analysis.",
                },
                "usl": {
                    "type": "number",
                    "description": "Upper Specification Limit for process capability analysis.",
                },
                "timestamp_column": {
                    "type": "string",
                    "description": "The column containing timestamp data for time-series analysis.",
                },
                "window_size": {
                    "type": "integer",
                    "description": "The size of the window for rolling statistics (number of rows).",
                    "default": 10,
                },
                "lag_steps": {
                    "type": "integer",
                    "description": "The number of steps to lag for lag analysis.",
                    "default": 1,
                },
                "granularity": {
                    "type": "string",
                    "enum": ["row_level", "group_by"],
                    "description": "row_level = all records; group_by = aggregate first then analyze.",
                    "default": "row_level",
                },
                "group_by": {
                    "type": "string",
                    "description": "Grouping column for group_by granularity, ratio_rank, or group_compare.",
                },
                "method": {
                    "type": "string",
                    "enum": ["pearson", "spearman"],
                    "description": "Correlation method. Defaults to pearson.",
                    "default": "pearson",
                },
                "numerator": {
                    "type": "string",
                    "description": "Numerator column for ratio_rank (e.g. Energy Consumption (kWh)).",
                },
                "denominator": {
                    "type": "string",
                    "description": "Denominator column for ratio_rank (e.g. Production Output (Units)).",
                },
                "ratio_method": {
                    "type": "string",
                    "enum": ["sum_ratio", "avg_ratio"],
                    "description": "sum_ratio = SUM(num)/SUM(den); avg_ratio = AVG(num/den). Default sum_ratio.",
                    "default": "sum_ratio",
                },
                "order": {
                    "type": "string",
                    "enum": ["asc", "desc"],
                    "description": "Sort order for ranked outputs.",
                    "default": "desc",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum rows to return for ranked outputs.",
                    "default": 10,
                },
                "z_threshold": {
                    "type": "number",
                    "description": "Z-score threshold for outlier detection.",
                    "default": 3.0,
                },
                "where_clause": {
                    "type": "string",
                    "description": "Optional SQL WHERE body without the WHERE keyword.",
                },
                "filters": {
                    "type": "object",
                    "description": "Optional structured filters as column_name -> value pairs.",
                },
            },
            "required": ["file_path", "analysis_type"],
        }

    def _build_source_query(self, file_path: str, where_body: str) -> str:
        # Escape single quotes in file path for safe SQL execution
        escaped_path = file_path.replace("'", "''")
        if where_body:
            return f"SELECT * FROM '{escaped_path}' WHERE {where_body}"
        return f"SELECT * FROM '{escaped_path}'"

    def _load_dataframe(self, file_path: str, where_body: str) -> pd.DataFrame:
        source_query = self._build_source_query(file_path, where_body)
        with duckdb.connect(database=":memory:") as con:
            return con.execute(source_query).df()

    def _run_correlation(
        self,
        file_path: str,
        columns: List[str],
        granularity: str,
        group_by: Optional[str],
        method: str,
        where_body: str,
    ) -> Dict[str, Any]:
        if len(columns) > 2:
            # Auto-redirect to correlation_matrix for better efficiency if no group_by is requested
            if not group_by:
                return self._run_correlation_matrix(file_path, where_body)
            
            return {
                "error": f"The 'correlation' analysis type is only for exactly 2 columns when using 'group_by'. You provided {len(columns)} columns.",
                "hint": "To analyze relationships between multiple columns at once, use analysis_type='correlation_matrix' instead. It is much more efficient.",
                "provided_columns": columns
            }
        
        if len(columns) < 2:
            return {"error": "correlation requires exactly two columns in 'columns'."}

        validation_error = _validate_requested_columns(file_path, columns)
        if validation_error:
            return validation_error

        if granularity == "group_by":
            if not group_by:
                return {"error": "group_by column is required when granularity is 'group_by'."}
            validation_error = _validate_requested_columns(file_path, [group_by])
            if validation_error:
                return validation_error

            source_query = self._build_source_query(file_path, where_body)
            x_ref = sql_column_reference(columns[0])
            y_ref = sql_column_reference(columns[1])
            group_ref = sql_column_reference(group_by)

            with duckdb.connect(database=":memory:") as con:
                grouped = con.execute(f"""
                    SELECT
                        {group_ref} AS group_value,
                        AVG({x_ref}) AS x_avg,
                        AVG({y_ref}) AS y_avg
                    FROM ({source_query})
                    GROUP BY {group_ref}
                """).df()

            grouped_clean = grouped[["x_avg", "y_avg"]].apply(pd.to_numeric, errors="coerce").dropna()
            if len(grouped_clean) < 3:
                return {"error": "Need at least 3 groups with valid numeric averages for grouped correlation analysis."}
            
            if grouped_clean["x_avg"].std() == 0 or grouped_clean["y_avg"].std() == 0:
                return {"error": "Cannot compute correlation: one of the columns has zero variance (constant values)."}

            if method == "spearman":
                coef, p_value = stats.spearmanr(grouped_clean["x_avg"], grouped_clean["y_avg"])
            else:
                coef, p_value = stats.pearsonr(grouped_clean["x_avg"], grouped_clean["y_avg"])

            n = len(grouped)
            return {
                "analysis_type": "correlation",
                "method": method,
                "granularity": "group_by",
                "group_by": group_by,
                "column_x": columns[0],
                "column_y": columns[1],
                "n": n,
                "result": {
                    "correlation_coefficient": round(float(coef), 4),
                    "p_value": round(float(p_value), 6),
                    "interpretation_hint": _interpret_correlation(float(coef)),
                },
                "warning": f"Correlation computed on {n} group-level averages, not individual records.",
                "status": "success",
            }

        df = self._load_dataframe(file_path, where_body)
        df_clean = df[columns].apply(pd.to_numeric, errors="coerce").dropna()

        if len(df_clean) < 3:
            return {"error": "Need at least 3 valid numeric records for correlation analysis after cleaning missing values."}
        
        if df_clean[columns[0]].std() == 0 or df_clean[columns[1]].std() == 0:
            return {"error": "Cannot compute correlation: one of the columns has zero variance (constant values)."}

        x = df_clean.iloc[:, 0]
        y = df_clean.iloc[:, 1]

        if method == "spearman":
            coef, p_value = stats.spearmanr(x, y)
        else:
            coef, p_value = stats.pearsonr(x, y)

        return {
            "analysis_type": "correlation",
            "method": method,
            "granularity": "row_level",
            "column_x": columns[0],
            "column_y": columns[1],
            "n": len(df),
            "result": {
                "correlation_coefficient": round(float(coef), 4),
                "p_value": round(float(p_value), 6),
                "interpretation_hint": _interpret_correlation(float(coef)),
            },
            "warning": f"Correlation computed on {len(df)} individual records.",
            "status": "success",
        }

    def _run_describe(
        self,
        file_path: str,
        columns: List[str],
        where_body: str,
    ) -> Dict[str, Any]:
        df = self._load_dataframe(file_path, where_body)
        
        # Auto-select numeric columns if none provided
        if not columns:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()
            if not columns:
                return {"error": "No numeric columns found for descriptive statistics."}

        validation_error = _validate_requested_columns(file_path, columns)
        if validation_error:
            return validation_error

        summary = []
        for col in columns:
            series = pd.to_numeric(df[col], errors="coerce").dropna()
            if series.empty:
                summary.append({"column": col, "error": "No numeric values found."})
                continue
            mean_val = series.mean()
            std_val = series.std()
            min_val = series.min()
            max_val = series.max()
            median_val = series.median()

            summary.append({
                "column": col,
                "count": int(series.count()),
                "mean": round(float(mean_val), 4) if not pd.isna(mean_val) else None,
                "std": round(float(std_val), 4) if not pd.isna(std_val) else None,
                "min": round(float(min_val), 4) if not pd.isna(min_val) else None,
                "max": round(float(max_val), 4) if not pd.isna(max_val) else None,
                "median": round(float(median_val), 4) if not pd.isna(median_val) else None,
            })

        return {
            "analysis_type": "describe",
            "n_rows": len(df),
            "columns_analyzed": columns,
            "result": summary,
            "status": "success",
        }

    def _run_ratio_rank(
        self,
        file_path: str,
        numerator: Optional[str],
        denominator: Optional[str],
        group_by: Optional[str],
        ratio_method: str,
        order: str,
        limit: int,
        where_body: str,
    ) -> Dict[str, Any]:
        if not numerator or not denominator:
            return {"error": "ratio_rank requires 'numerator' and 'denominator' columns."}
        if not group_by:
            return {"error": "ratio_rank requires 'group_by' column."}

        validation_error = _validate_requested_columns(file_path, [numerator, denominator, group_by])
        if validation_error:
            return validation_error

        num_ref = sql_column_reference(numerator)
        den_ref = sql_column_reference(denominator)
        group_ref = sql_column_reference(group_by)
        source_query = self._build_source_query(file_path, where_body)

        if ratio_method == "avg_ratio":
            ratio_expr = f'AVG({num_ref} / NULLIF({den_ref}, 0))'
        else:
            ratio_expr = f'SUM({num_ref}) / NULLIF(SUM({den_ref}), 0)'

        sort_dir = "DESC" if order == "desc" else "ASC"
        with duckdb.connect(database=":memory:") as con:
            ranked = con.execute(f"""
                SELECT
                    {group_ref} AS group_value,
                    SUM({num_ref}) AS numerator_total,
                    SUM({den_ref}) AS denominator_total,
                    {ratio_expr} AS ratio_value
                FROM ({source_query})
                GROUP BY {group_ref}
                ORDER BY ratio_value {sort_dir}
                LIMIT {int(limit)}
            """).df()

        return {
            "analysis_type": "ratio_rank",
            "ratio_method": ratio_method,
            "numerator": numerator,
            "denominator": denominator,
            "group_by": group_by,
            "order": order,
            "result": _sanitize_records(ranked),
            "status": "success",
        }

    def _run_outlier(
        self,
        file_path: str,
        columns: List[str],
        z_threshold: float,
        limit: int,
        where_body: str,
    ) -> Dict[str, Any]:
        df = self._load_dataframe(file_path, where_body)
        
        # Auto-select numeric columns if none provided
        if not columns:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()
            if not columns:
                return {"error": "No numeric columns found for outlier detection.", "status": "fail"}

        validation_error = _validate_requested_columns(file_path, columns)
        if validation_error:
            validation_error["status"] = "fail"
            return validation_error

        results = {}
        overall_summary = []
        
        # Maintain backward compatibility for single-column tests
        single_column_stats = {}

        for col in columns:
            series = pd.to_numeric(df[col], errors="coerce").dropna()
            if series.empty:
                continue
            
            mean_val = series.mean()
            std_val = series.std()
            
            # Maintain backward compatibility for single-column case
            if len(columns) == 1:
                single_column_stats = {
                    "population_stats": {
                        "mean": round(float(mean_val), 4),
                        "std": round(float(std_val), 4) if not pd.isna(std_val) else 0,
                        "n": int(series.count())
                    },
                    "outlier_count_returned": 0,
                    "result": []
                }

            if std_val == 0 or pd.isna(std_val):
                continue

            z_scores = np.abs((series - mean_val) / std_val)
            outliers_mask = z_scores > z_threshold
            
            outlier_indices = series[outliers_mask].index
            outlier_data = df.loc[outlier_indices].copy()
            outlier_data["z_score"] = z_scores[outliers_mask]
            
            # Sort by z-score and limit
            outlier_data = outlier_data.sort_values("z_score", ascending=False).head(limit)
            
            col_summary = {
                "column": col,
                "count": len(outlier_indices),
                "mean": round(float(mean_val), 4),
                "std": round(float(std_val), 4),
                "max_z_score": round(float(z_scores.max()), 4) if not z_scores.empty else 0
            }
            overall_summary.append(col_summary)

            if not outlier_data.empty:
                results[col] = _sanitize_records(outlier_data)
                
                # Update backward compatibility stats
                if len(columns) == 1:
                    single_column_stats["outlier_count_returned"] = len(outlier_data)
                    single_column_stats["result"] = results[col]

        base_res = {
            "analysis_type": "outlier",
            "columns_analyzed": columns,
            "z_threshold": z_threshold,
            "summary": overall_summary,
            "results": results,
            "status": "success",
            "message": f"Detected outliers in {len(results)} out of {len(columns)} columns analyzed."
        }
        
        if len(columns) == 1:
            base_res.update(single_column_stats)
            
        return base_res

    def _run_group_compare(
        self,
        file_path: str,
        columns: List[str],
        group_by: Optional[str],
        where_body: str,
    ) -> Dict[str, Any]:
        if not columns or len(columns) != 1:
            return {"error": "group_compare requires exactly one numeric column in 'columns'."}
        if not group_by:
            return {"error": "group_compare requires 'group_by' column."}

        numeric_col = columns[0]
        validation_error = _validate_requested_columns(file_path, [numeric_col, group_by])
        if validation_error:
            return validation_error

        num_ref = sql_column_reference(numeric_col)
        group_ref = sql_column_reference(group_by)
        source_query = self._build_source_query(file_path, where_body)
        
        with duckdb.connect(database=":memory:") as con:
            comparison = con.execute(f"""
                SELECT
                    {group_ref} AS group_value,
                    COUNT(*) AS record_count,
                    AVG({num_ref}) AS mean_value,
                    STDDEV({num_ref}) AS std_value,
                    MIN({num_ref}) AS min_value,
                    MAX({num_ref}) AS max_value
                FROM ({source_query})
                GROUP BY {group_ref}
                ORDER BY mean_value DESC
            """).df()

        return {
            "analysis_type": "group_compare",
            "column": numeric_col,
            "group_by": group_by,
            "result": _sanitize_records(comparison),
            "status": "success",
        }

    def _run_rolling_stats(
        self,
        file_path: str,
        columns: List[str],
        timestamp_column: Optional[str],
        window_size: int,
        group_by: Optional[str],
        where_body: str,
    ) -> Dict[str, Any]:
        if not columns or not timestamp_column:
            return {"error": "rolling_stats requires 'columns' and 'timestamp_column'."}
        
        validation_cols = columns + [timestamp_column]
        if group_by:
            validation_cols.append(group_by)
            
        validation_error = _validate_requested_columns(file_path, validation_cols)
        if validation_error:
            return validation_error

        ts_ref = sql_column_reference(timestamp_column)
        source_query = self._build_source_query(file_path, where_body)
        partition_clause = f"PARTITION BY {sql_column_reference(group_by)}" if group_by else ""
        
        # Build rolling expressions and column selection
        rolling_exprs = []
        selected_cols = [ts_ref]
        if group_by:
            selected_cols.append(sql_column_reference(group_by))
            
        for col in columns:
            col_ref = sql_column_reference(col)
            selected_cols.append(col_ref)
            rolling_exprs.append(f"AVG({col_ref}) OVER ({partition_clause} ORDER BY {ts_ref} ROWS BETWEEN {window_size-1} PRECEDING AND CURRENT ROW) AS \"rolling_avg_{col}\"")
            rolling_exprs.append(f"STDDEV({col_ref}) OVER ({partition_clause} ORDER BY {ts_ref} ROWS BETWEEN {window_size-1} PRECEDING AND CURRENT ROW) AS \"rolling_std_{col}\"")

        rolling_exprs_str = ", ".join(rolling_exprs)
        selected_cols_str = ", ".join(selected_cols)
        
        with duckdb.connect(database=":memory:") as con:
            result = con.execute(f"""
                SELECT
                    {selected_cols_str},
                    {rolling_exprs_str}
                FROM ({source_query})
                ORDER BY {ts_ref}
                LIMIT 40
            """).df()

        return {
            "analysis_type": "rolling_stats",
            "columns": columns,
            "timestamp_column": timestamp_column,
            "window_size": window_size,
            "group_by": group_by,
            "result": _sanitize_records(result),
            "message": "Showing first 40 records with rolling statistics.",
            "status": "success",
        }

    def _run_lag_analysis(
        self,
        file_path: str,
        columns: List[str],
        timestamp_column: Optional[str],
        lag_steps: int,
        group_by: Optional[str],
        method: str,
        where_body: str,
    ) -> Dict[str, Any]:
        if len(columns) != 2 or not timestamp_column:
            return {"error": "lag_analysis requires exactly two 'columns' (predictor, target) and 'timestamp_column'."}
            
        validation_cols = columns + [timestamp_column]
        if group_by:
            validation_cols.append(group_by)
            
        validation_error = _validate_requested_columns(file_path, validation_cols)
        if validation_error:
            return validation_error

        predictor_col = columns[0]
        target_col = columns[1]
        ts_ref = sql_column_reference(timestamp_column)
        pred_ref = sql_column_reference(predictor_col)
        target_ref = sql_column_reference(target_col)
        source_query = self._build_source_query(file_path, where_body)
        partition_clause = f"PARTITION BY {sql_column_reference(group_by)}" if group_by else ""

        with duckdb.connect(database=":memory:") as con:
            # Create a lagged dataset
            lagged_df = con.execute(f"""
                SELECT
                    {target_ref} AS target,
                    LAG({pred_ref}, {lag_steps}) OVER ({partition_clause} ORDER BY {ts_ref}) AS lagged_predictor
                FROM ({source_query})
            """).df()

        lagged_df = lagged_df.dropna()
        if len(lagged_df) < 3:
            return {"error": "Not enough data points after lagging for correlation analysis."}

        if method == "spearman":
            coef, p_value = stats.spearmanr(lagged_df["lagged_predictor"], lagged_df["target"])
        else:
            coef, p_value = stats.pearsonr(lagged_df["lagged_predictor"], lagged_df["target"])

        return {
            "analysis_type": "lag_analysis",
            "predictor_column": predictor_col,
            "target_column": target_col,
            "lag_steps": lag_steps,
            "method": method,
            "result": {
                "correlation_coefficient": round(float(coef), 4),
                "p_value": round(float(p_value), 6),
                "interpretation_hint": _interpret_correlation(float(coef)),
            },
            "status": "success",
        }

    def _run_shift_analysis(
        self,
        file_path: str,
        columns: List[str],
        timestamp_column: Optional[str],
        where_body: str,
    ) -> Dict[str, Any]:
        if not columns or len(columns) != 1 or not timestamp_column:
            return {"error": "shift_analysis requires exactly one numeric column in 'columns' and 'timestamp_column'."}
            
        validation_error = _validate_requested_columns(file_path, columns + [timestamp_column])
        if validation_error:
            return validation_error

        num_ref = sql_column_reference(columns[0])
        ts_ref = sql_column_reference(timestamp_column)
        source_query = self._build_source_query(file_path, where_body)

        with duckdb.connect(database=":memory:") as con:
            comparison = con.execute(f"""
                WITH shifted AS (
                    SELECT
                        *,
                        CASE 
                            WHEN hour({ts_ref}) BETWEEN 8 AND 15 THEN '1_Morning_Shift'
                            WHEN hour({ts_ref}) BETWEEN 16 AND 23 THEN '2_Evening_Shift'
                            ELSE '3_Night_Shift'
                        END AS shift_name
                    FROM ({source_query})
                )
                SELECT
                    shift_name,
                    COUNT(*) AS record_count,
                    AVG({num_ref}) AS mean_value,
                    STDDEV({num_ref}) AS std_value
                FROM shifted
                GROUP BY shift_name
                ORDER BY shift_name ASC
            """).df()

        return {
            "analysis_type": "shift_analysis",
            "column": columns[0],
            "result": _sanitize_records(comparison),
            "status": "success",
        }

    def _run_regression(
        self,
        file_path: str,
        target: Optional[str],
        predictors: Optional[List[str]],
        where_body: str,
    ) -> Dict[str, Any]:
        if not target or not predictors:
            return {"error": "regression requires 'target_column' and 'predictor_columns'."}

        all_cols = [target] + predictors
        validation_error = _validate_requested_columns(file_path, all_cols)
        if validation_error:
            return validation_error

        df = self._load_dataframe(file_path, where_body)
        df_clean = df[all_cols].apply(pd.to_numeric, errors="coerce").dropna()

        if len(df_clean) < len(predictors) + 2:
            return {"error": f"Not enough data points for regression. Need at least {len(predictors) + 2} valid records after cleaning."}

        Y = df_clean[target].values
        X = df_clean[predictors].values
        # Add constant for intercept
        X_with_const = np.column_stack([np.ones(X.shape[0]), X])

        try:
            # Solve Normal Equation using least squares
            beta, residuals, rank, s = np.linalg.lstsq(X_with_const, Y, rcond=None)
            
            # Calculate R-squared
            y_mean = np.mean(Y)
            ss_tot = np.sum((Y - y_mean)**2)
            ss_res = np.sum((Y - np.dot(X_with_const, beta))**2)
            r_sq = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

            coef_map = {"intercept": round(float(beta[0]), 6)}
            for i, pred in enumerate(predictors):
                coef_map[pred] = round(float(beta[i+1]), 6)

            return {
                "analysis_type": "regression",
                "target_column": target,
                "predictor_columns": predictors,
                "n": len(df_clean),
                "result": {
                    "coefficients": coef_map,
                    "r_squared": round(float(r_sq), 4),
                    "residual_sum_of_squares": round(float(ss_res), 4),
                    "standard_error": round(float(np.sqrt(ss_res / (len(Y) - len(beta)))), 6) if len(Y) > len(beta) else None
                },
                "status": "success"
            }
        except Exception as e:
            return {"error": f"Regression calculation failed: {str(e)}"}

    def _run_process_capability(
        self,
        file_path: str,
        columns: List[str],
        lsl: Optional[float],
        usl: Optional[float],
        where_body: str,
    ) -> Dict[str, Any]:
        if not columns or len(columns) != 1:
            return {"error": "process_capability requires exactly one numeric column in 'columns'."}
        if lsl is None and usl is None:
            return {"error": "process_capability requires at least one of 'lsl' or 'usl' parameters."}

        validation_error = _validate_requested_columns(file_path, columns)
        if validation_error:
            return validation_error

        df = self._load_dataframe(file_path, where_body)
        series = pd.to_numeric(df[columns[0]], errors="coerce").dropna()

        if len(series) < 10:
            return {"error": "Need at least 10 valid numeric records for process capability analysis."}

        mean_val = float(series.mean())
        std_val = float(series.std())
        
        if std_val == 0:
            return {"error": "Process standard deviation is zero. Capability cannot be computed for constant processes."}

        cp = (usl - lsl) / (6 * std_val) if (lsl is not None and usl is not None) else None
        cpu = (usl - mean_val) / (3 * std_val) if usl is not None else None
        cpl = (mean_val - lsl) / (3 * std_val) if lsl is not None else None
        
        cpk = None
        if cpu is not None and cpl is not None:
            cpk = min(cpu, cpl)
        elif cpu is not None:
            cpk = cpu
        elif cpl is not None:
            cpk = cpl

        return {
            "analysis_type": "process_capability",
            "column": columns[0],
            "n": len(series),
            "lsl": lsl,
            "usl": usl,
            "mean": round(mean_val, 4),
            "std_dev": round(std_val, 4),
            "result": {
                "cp": round(cp, 4) if cp is not None else None,
                "cpk": round(cpk, 4) if cpk is not None else None,
                "cpu": round(cpu, 4) if cpu is not None else None,
                "cpl": round(cpl, 4) if cpl is not None else None,
            },
            "interpretation_hint": (
                "Cpk > 1.33: Capable process. "
                "Cpk < 1.00: Inadequate process (potential for defects)."
            ),
            "status": "success"
        }

    def _run_pareto(
        self,
        file_path: str,
        columns: List[str],
        group_by: Optional[str],
        where_body: str,
    ) -> Dict[str, Any]:
        if not columns or len(columns) != 1 or not group_by:
            return {"error": "pareto requires one numeric column in 'columns' and a 'group_by' column."}

        validation_error = _validate_requested_columns(file_path, columns + [group_by])
        if validation_error:
            return validation_error

        col_ref = sql_column_reference(columns[0])
        group_ref = sql_column_reference(group_by)
        source_query = self._build_source_query(file_path, where_body)

        with duckdb.connect(database=":memory:") as con:
            df = con.execute(f"""
                SELECT
                    {group_ref} AS category,
                    SUM({col_ref}) AS total_value
                FROM ({source_query})
                GROUP BY 1
                ORDER BY total_value DESC
            """).df()

        if df.empty:
            return {"error": "No data found for Pareto analysis."}

        total_sum = df["total_value"].sum()
        df["percentage"] = (df["total_value"] / total_sum) * 100
        df["cumulative_percentage"] = df["percentage"].cumsum()

        # Find the "Vital Few" (up to 80% cumulative)
        vital_few = df[df["cumulative_percentage"] <= 85].copy()
        
        return {
            "analysis_type": "pareto",
            "column": columns[0],
            "group_by": group_by,
            "total_sum": round(float(total_sum), 2),
            "result": _sanitize_records(df),
            "vital_few_count": len(vital_few),
            "message": f"Identified {len(vital_few)} categories contributing to ~80% of total {columns[0]}.",
            "status": "success"
        }

    def _run_trend_projection(
        self,
        file_path: str,
        target_column: Optional[str],
        timestamp_column: Optional[str],
        where_body: str,
    ) -> Dict[str, Any]:
        if not target_column or not timestamp_column:
            return {"error": "trend_projection requires 'target_column' and 'timestamp_column'."}

        validation_error = _validate_requested_columns(file_path, [target_column, timestamp_column])
        if validation_error:
            return validation_error

        source_query = self._build_source_query(file_path, where_body)
        ts_ref = sql_column_reference(timestamp_column)
        target_ref = sql_column_reference(target_column)

        with duckdb.connect(database=":memory:") as con:
            # Convert timestamp to epoch seconds for regression
            df = con.execute(f"""
                SELECT
                    epoch({ts_ref}) AS t_numeric,
                    {target_ref} AS val
                FROM ({source_query})
                ORDER BY t_numeric
            """).df()

        df_clean = df.apply(pd.to_numeric, errors="coerce").dropna()
        if len(df_clean) < 5:
            return {"error": "Not enough valid numeric data points for trend projection (need at least 5)."}

        X = df_clean["t_numeric"].values
        Y = df_clean["val"].values
        
        # Simple linear regression: Y = mx + b
        slope, intercept, r_value, p_value, std_err = stats.linregress(X, Y)

        trend_direction = "increasing" if slope > 0 else "decreasing"
        if abs(r_value) < 0.2:
            trend_direction = "stable / no clear linear trend"

        return {
            "analysis_type": "trend_projection",
            "target": target_column,
            "n": len(df_clean),
            "result": {
                "slope_per_second": round(float(slope), 8),
                "intercept": round(float(intercept), 4),
                "r_squared": round(float(r_value**2), 4),
                "p_value": round(float(p_value), 6),
                "trend_interpretation": trend_direction
            },
            "status": "success"
        }

    def _run_downsample(
        self,
        file_path: str,
        columns: List[str],
        timestamp_column: Optional[str],
        limit: int,
        where_body: str,
    ) -> Dict[str, Any]:
        if not columns or not timestamp_column:
            return {"error": "downsample requires 'columns' and 'timestamp_column'."}

        validation_error = _validate_requested_columns(file_path, columns + [timestamp_column])
        if validation_error:
            return validation_error

        source_query = self._build_source_query(file_path, where_body)
        ts_ref = sql_column_reference(timestamp_column)
        col_refs = [sql_column_reference(c) for c in columns]
        
        with duckdb.connect(database=":memory:") as con:
            # 1. Get total count
            total_count_res = con.execute(f"SELECT COUNT(*) FROM ({source_query})").fetchone()
            total_count = total_count_res[0] if total_count_res else 0
            
            if total_count <= limit:
                # No downsampling needed if dataset is already small
                result = con.execute(f"SELECT * FROM ({source_query}) ORDER BY {ts_ref}").df()
                return {
                    "analysis_type": "downsample",
                    "n_original": total_count,
                    "n_returned": len(result),
                    "result": _sanitize_records(result),
                    "status": "success"
                }

            # 2. Bucket-based aggregation (simplified LTTB-like approach)
            bucket_size = max(1, total_count // limit)
            avg_exprs = ", ".join([f"AVG({ref}) AS \"{c}\"" for c, ref in zip(columns, col_refs)])
            
            result = con.execute(f"""
                WITH numbered AS (
                    SELECT *, (row_number() OVER (ORDER BY {ts_ref}) - 1) / {bucket_size} AS bucket_id
                    FROM ({source_query})
                )
                SELECT
                    MIN({ts_ref}) AS {ts_ref},
                    {avg_exprs}
                FROM numbered
                GROUP BY bucket_id
                ORDER BY 1
                LIMIT {int(limit)}
            """).df()

        return {
            "analysis_type": "downsample",
            "n_original": total_count,
            "n_returned": len(result),
            "bucket_size": bucket_size,
            "result": _sanitize_records(result),
            "message": f"Dataset downsampled from {total_count} to {len(result)} records using bucketed averages.",
            "status": "success"
        }

    def _run_correlation_matrix(
        self,
        file_path: str,
        where_body: str,
    ) -> Dict[str, Any]:
        df = self._load_dataframe(file_path, where_body)
        # Auto-select numeric columns
        numeric_df = df.select_dtypes(include=[np.number])
        
        if numeric_df.empty:
            return {"error": "No numeric columns found for correlation matrix."}
            
        if len(numeric_df.columns) < 2:
            return {"error": "Need at least two numeric columns for a correlation matrix."}

        corr_matrix = numeric_df.corr().round(4)
        
        # Flatten matrix to find top relationships (excluding self-correlation)
        flat_corr = corr_matrix.unstack()
        flat_corr = flat_corr[flat_corr.index.get_level_values(0) != flat_corr.index.get_level_values(1)]
        top_corr = flat_corr.abs().sort_values(ascending=False).head(10)
        
        summary = []
        seen = set()
        for (c1, c2), val in top_corr.items():
            pair = tuple(sorted((c1, c2)))
            if pair not in seen:
                actual_val = corr_matrix.loc[c1, c2]
                summary.append({
                    "pair": f"{c1} vs {c2}",
                    "correlation": float(actual_val),
                    "interpretation": _interpret_correlation(float(actual_val))
                })
                seen.add(pair)

        return {
            "analysis_type": "correlation_matrix",
            "columns_analyzed": list(numeric_df.columns),
            "matrix_sample": corr_matrix.iloc[:10, :10].to_dict(),
            "matrix_dimensions": list(corr_matrix.shape),
            "top_relationships": summary[:5],
            "status": "success",
            "message": f"Showing a 10x10 sample of the {corr_matrix.shape[0]}x{corr_matrix.shape[1]} correlation matrix."
        }

    def _run_seasonal_decomposition(
        self,
        file_path: str,
        columns: List[str],
        timestamp_column: Optional[str],
        period: Optional[int],
        where_body: str,
    ) -> Dict[str, Any]:
        if not columns or len(columns) != 1 or not timestamp_column:
            return {"error": "seasonal_decomposition requires exactly one column in 'columns' and 'timestamp_column'."}
            
        validation_error = _validate_requested_columns(file_path, columns + [timestamp_column])
        if validation_error:
            return validation_error

        from statsmodels.tsa.seasonal import seasonal_decompose
        
        df = self._load_dataframe(file_path, where_body)
        df[timestamp_column] = pd.to_datetime(df[timestamp_column])
        df = df.sort_values(timestamp_column).set_index(timestamp_column)
        
        # Ensure we have numeric data and handle missing values for decomposition
        series = pd.to_numeric(df[columns[0]], errors="coerce").interpolate(method='linear')
        
        if series.isna().any():
            series = series.fillna(method='bfill').fillna(method='ffill')

        if len(series) < (period * 2 if period else 10):
            return {"error": "Not enough data points for seasonal decomposition with the given period."}

        try:
            result = seasonal_decompose(series, model='additive', period=period)
            
            # Create a summary of the components
            # We'll return a downsampled version of the components to keep the context size manageable
            decomp_df = pd.DataFrame({
                "observed": result.observed,
                "trend": result.trend,
                "seasonal": result.seasonal,
                "resid": result.resid
            }).dropna()
            
            # Downsample to 20 points for the summary
            step = max(1, len(decomp_df) // 20)
            summary_df = decomp_df.iloc[::step].head(20).reset_index()
            
            # Trend direction
            trend_values = decomp_df["trend"].values
            slope = (trend_values[-1] - trend_values[0]) / len(trend_values)
            trend_desc = "increasing" if slope > 0 else "decreasing"
            
            # Seasonality strength (variance ratio)
            seasonal_var = np.var(result.seasonal.dropna())
            resid_var = np.var(result.resid.dropna())
            total_var = np.var(series)
            seasonal_strength = round(float(seasonal_var / total_var), 4) if total_var != 0 else 0

            return {
                "analysis_type": "seasonal_decomposition",
                "column": columns[0],
                "period_used": period or result.nobs // 2, # statsmodels default if not provided
                "trend_direction": trend_desc,
                "seasonal_strength_ratio": seasonal_strength,
                "result_summary": _sanitize_records(summary_df),
                "message": f"Decomposition successful. Seasonal component explains {seasonal_strength*100}% of variance.",
                "status": "success"
            }
        except Exception as e:
            return {"error": f"Seasonal decomposition failed: {str(e)}"}

    def _run_pca(
        self,
        file_path: str,
        columns: List[str],
        where_body: str,
    ) -> Dict[str, Any]:
        df = self._load_dataframe(file_path, where_body)
        
        # Auto-select numeric columns if none provided
        if not columns:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()
            if not columns:
                return {"error": "No numeric columns found for PCA."}

        validation_error = _validate_requested_columns(file_path, columns)
        if validation_error:
            return validation_error

        # Drop rows with NaNs in the selected columns
        df_clean = df[columns].dropna()
        if len(df_clean) < 3:
            return {"error": "Need at least 3 valid numeric records for PCA."}

        # Standardize the data
        scaler = StandardScaler()
        x_scaled = scaler.fit_transform(df_clean)

        # Run PCA
        n_components = min(len(columns), 5) # Cap at 5 for summary
        pca = PCA(n_components=n_components)
        pca_result = pca.fit_transform(x_scaled)

        # Explained variance
        explained_variance = pca.explained_variance_ratio_.tolist()
        cumulative_variance = np.cumsum(explained_variance).tolist()

        # Loadings (how each original variable contributes to each PC)
        loadings = pd.DataFrame(
            pca.components_.T, 
            columns=[f"PC{i+1}" for i in range(n_components)], 
            index=columns
        )

        # Summary of results
        # Limit loadings to save context space (first 5 components, first 20 variables)
        loadings_sample = loadings.iloc[:20, :5]
        
        results = {
            "explained_variance_ratio": [round(float(v), 4) for v in explained_variance],
            "cumulative_variance_ratio": [round(float(v), 4) for v in cumulative_variance],
            "loadings_sample": loadings_sample.round(4).to_dict(),
            "n_samples": len(df_clean),
            "n_components": n_components,
            "total_variables": len(columns)
        }

        # Top factors for first two PCs
        top_pc1 = loadings["PC1"].abs().sort_values(ascending=False).head(3).index.tolist()
        top_pc2 = loadings["PC2"].abs().sort_values(ascending=False).head(3).index.tolist() if n_components > 1 else []

        return {
            "analysis_type": "pca",
            "columns_analyzed": columns,
            "result": results,
            "top_contributors": {
                "PC1": top_pc1,
                "PC2": top_pc2
            },
            "status": "success",
            "message": f"PCA completed. First 2 components explain {round(cumulative_variance[min(1, n_components-1)]*100, 1)}% of variance."
        }

    def _run_t_test(
        self,
        file_path: str,
        columns: List[str],
        group_by: Optional[str],
        where_body: str,
        target_column: Optional[str] = None,
    ) -> Dict[str, Any]:
        # Fallback for models that provide target_column instead of columns
        if not columns and target_column:
            columns = [target_column]

        df = self._load_dataframe(file_path, where_body)
        
        if group_by:
            # Mode 1: One numeric column across two groups in group_by
            if len(columns) != 1:
                return {"error": "t_test with group_by requires exactly one numeric column in 'columns'."}
            
            validation_error = _validate_requested_columns(file_path, columns + [group_by])
            if validation_error: return validation_error

            numeric_col = columns[0]
            groups = df[group_by].dropna().unique()
            
            if len(groups) != 2:
                return {
                    "error": f"t_test with group_by requires exactly two groups in the grouping column. Found {len(groups)}: {groups}",
                    "hint": "Filter your dataset using where_clause or filters to isolate exactly two groups."
                }
            
            g1_data = pd.to_numeric(df[df[group_by] == groups[0]][numeric_col], errors="coerce").dropna()
            g2_data = pd.to_numeric(df[df[group_by] == groups[1]][numeric_col], errors="coerce").dropna()
            
            name1, name2 = str(groups[0]), str(groups[1])
        else:
            # Mode 2: Two different numeric columns
            if len(columns) != 2:
                return {"error": "t_test without group_by requires exactly two numeric columns in 'columns'."}
            
            validation_error = _validate_requested_columns(file_path, columns)
            if validation_error: return validation_error
            
            g1_data = pd.to_numeric(df[columns[0]], errors="coerce").dropna()
            g2_data = pd.to_numeric(df[columns[1]], errors="coerce").dropna()
            
            name1, name2 = columns[0], columns[1]

        if len(g1_data) < 2 or len(g2_data) < 2:
            return {"error": "Insufficient data in one or both groups for a t-test (need at least 2 points per group)."}

        # Perform Independent Samples T-Test (Welch's t-test by default with equal_var=False)
        t_stat, p_val = stats.ttest_ind(g1_data, g2_data, equal_var=False)
        
        mean1, mean2 = g1_data.mean(), g2_data.mean()
        
        return {
            "analysis_type": "t_test",
            "group1": {"name": name1, "n": len(g1_data), "mean": round(float(mean1), 4)},
            "group2": {"name": name2, "n": len(g2_data), "mean": round(float(mean2), 4)},
            "result": {
                "t_statistic": round(float(t_stat), 4),
                "p_value": round(float(p_val), 6),
                "is_significant": bool(p_val < 0.05),
                "confidence_level": "95%"
            },
            "status": "success",
            "summary": f"t-test between {name1} and {name2}: p={round(float(p_val), 4)}. The difference is {'statistically significant' if p_val < 0.05 else 'not statistically significant'}."
        }

    def _run_chi_square(
        self,
        file_path: str,
        columns: List[str],
        where_body: str,
    ) -> Dict[str, Any]:
        if len(columns) != 2:
            return {"error": "chi_square requires exactly two categorical columns in 'columns'."}
        
        validation_error = _validate_requested_columns(file_path, columns)
        if validation_error: return validation_error
        
        df = self._load_dataframe(file_path, where_body)
        df_clean = df[columns].dropna()
        
        if len(df_clean) < 5:
            return {"error": "Insufficient data for chi-square test."}
            
        contingency_table = pd.crosstab(df_clean[columns[0]], df_clean[columns[1]])
        
        try:
            chi2, p, dof, expected = stats.chi2_contingency(contingency_table)
            
            # Limit the size of the contingency table returned to context
            table_sample = contingency_table.iloc[:10, :10]
            
            return {
                "analysis_type": "chi_square",
                "columns_analyzed": columns,
                "contingency_table_sample": table_sample.to_dict(),
                "table_dimensions": list(contingency_table.shape),
                "result": {
                    "chi2_statistic": round(float(chi2), 4),
                    "p_value": round(float(p), 6),
                    "degrees_of_freedom": int(dof),
                    "is_significant": bool(p < 0.05)
                },
                "status": "success",
                "message": f"Showing a 10x10 sample of the {contingency_table.shape[0]}x{contingency_table.shape[1]} contingency table.",
                "summary": f"Chi-square test of independence between {columns[0]} and {columns[1]}: p={round(float(p), 4)}."
            }
        except Exception as e:
            return {"error": f"Chi-square test failed: {str(e)}"}

    def execute(
        self,
        file_path: str,
        analysis_type: str,
        columns: Optional[List[str]] = None,
        timestamp_column: Optional[str] = None,
        window_size: int = 10,
        lag_steps: int = 1,
        granularity: str = "row_level",
        group_by: Optional[str] = None,
        method: str = "pearson",
        numerator: Optional[str] = None,
        denominator: Optional[str] = None,
        ratio_method: str = "sum_ratio",
        order: str = "desc",
        limit: int = 10,
        z_threshold: float = 3.0,
        period: Optional[int] = None,
        target_column: Optional[str] = None,
        predictor_columns: Optional[List[str]] = None,
        lsl: Optional[float] = None,
        usl: Optional[float] = None,
        where_clause: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        workspace: Optional[Any] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        if workspace:
            try:
                real_path = workspace.resolve(file_path)
                file_path = str(real_path)
            except PermissionError as e:
                return {"error": str(e), "status": "fail"}

        if not os.path.exists(file_path):
            return {"error": f"File not found at path: {file_path}", "status": "fail"}

        columns = columns or []
        
        # FIX: Clean quotes from all column-representing strings to prevent Pandas lookup errors
        columns = [c.strip("'\"") for c in columns]
        if group_by: group_by = group_by.strip("'\"")
        if target_column: target_column = target_column.strip("'\"")
        if predictor_columns: predictor_columns = [c.strip("'\"") for c in predictor_columns]
        if numerator: numerator = numerator.strip("'\"")
        if denominator: denominator = denominator.strip("'\"")
        if timestamp_column: timestamp_column = timestamp_column.strip("'\"")

        where_body = _merge_where_clauses(where_clause, filters)

        try:
            res = {}
            if analysis_type == "correlation":
                res = self._run_correlation(
                    file_path, columns, granularity, group_by, method, where_body
                )
            elif analysis_type == "describe":
                res = self._run_describe(file_path, columns, where_body)
            elif analysis_type == "ratio_rank":
                res = self._run_ratio_rank(
                    file_path, numerator, denominator, group_by, ratio_method, order, limit, where_body
                )
            elif analysis_type == "outlier":
                res = self._run_outlier(file_path, columns, z_threshold, limit, where_body)
            elif analysis_type == "group_compare":
                res = self._run_group_compare(file_path, columns, group_by, where_body)
            elif analysis_type == "rolling_stats":
                res = self._run_rolling_stats(
                    file_path, columns, timestamp_column, window_size, group_by, where_body
                )
            elif analysis_type == "lag_analysis":
                res = self._run_lag_analysis(
                    file_path, columns, timestamp_column, lag_steps, group_by, method, where_body
                )
            elif analysis_type == "shift_analysis":
                res = self._run_shift_analysis(
                    file_path, columns, timestamp_column, where_body
                )
            elif analysis_type == "regression":
                res = self._run_regression(
                    file_path, target_column, predictor_columns, where_body
                )
            elif analysis_type == "process_capability":
                res = self._run_process_capability(
                    file_path, columns, lsl, usl, where_body
                )
            elif analysis_type == "pareto":
                res = self._run_pareto(
                    file_path, columns, group_by, where_body
                )
            elif analysis_type == "trend_projection":
                res = self._run_trend_projection(
                    file_path, target_column, timestamp_column, where_body
                )
            elif analysis_type == "downsample":
                res = self._run_downsample(
                    file_path, columns, timestamp_column, limit, where_body
                )
            elif analysis_type == "correlation_matrix":
                res = self._run_correlation_matrix(
                    file_path, where_body
                )
            elif analysis_type == "seasonal_decomposition":
                res = self._run_seasonal_decomposition(
                    file_path, columns, timestamp_column, period, where_body
                )
            elif analysis_type == "pca":
                res = self._run_pca(
                    file_path, columns, where_body
                )
            elif analysis_type == "t_test":
                res = self._run_t_test(
                    file_path, columns, group_by, where_body, target_column
                )
            elif analysis_type == "chi_square":
                res = self._run_chi_square(
                    file_path, columns, where_body
                )
            else:
                res = {
                    "error": f"Unsupported analysis_type: {analysis_type}",
                    "supported_types": ["correlation", "describe", "ratio_rank", "outlier", "group_compare", "rolling_stats", "lag_analysis", "shift_analysis", "regression", "process_capability", "pareto", "trend_projection", "downsample", "correlation_matrix", "seasonal_decomposition", "pca", "t_test", "chi_square"],
                }

            if "error" in res and "status" not in res:
                res["status"] = "fail"
            return res
        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}", "status": "fail"}


class AnalyzeDesignOfExperimentsTool(BaseTool):
    """
    Analyzes experimental data (DoE) to calculate main effects, perform ANOVA, 
    and optimize for a target response using Response Surface Methodology (RSM).
    """

    @property
    def name(self) -> str:
        return "analyze_doe_results"

    @property
    def description(self) -> str:
        return (
            "Analyzes Design of Experiments (DoE) data. Calculates main effects, "
            "performs ANOVA to test significance, and suggests optimal factor levels "
            "to maximize/minimize the response. Never perform DoE analysis or ANOVA mentally — always use this tool."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "experiment_data": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "List of experiment records, each as a dict of factor values and the result."
                },
                "target_column": {
                    "type": "string",
                    "description": "The response/result column to optimize (e.g., 'yield', 'score')."
                },
                "factors": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "The independent variables (factors) to analyze."
                },
                "goal": {
                    "type": "string",
                    "enum": ["maximize", "minimize"],
                    "default": "maximize",
                    "description": "Whether to maximize or minimize the target response."
                }
            },
            "required": ["experiment_data", "target_column", "factors"]
        }

    def execute(
        self, 
        experiment_data: List[Dict[str, Any]], 
        target_column: str, 
        factors: List[str], 
        goal: str = "maximize",
        **kwargs
    ) -> Dict[str, Any]:
        try:
            df = pd.DataFrame(experiment_data)
            
            # 1. Validation
            missing_cols = [c for c in factors + [target_column] if c not in df.columns]
            if missing_cols:
                return {"error": f"Missing columns in data: {missing_cols}"}
            
            if len(df) < len(factors) + 1:
                return {"error": f"Need at least {len(factors) + 1} data points for analysis."}

            # 2. Fit Model (Response Surface)
            # We use a simple linear model with main effects. 
            # In a real DoE tool, we might add interactions or quadratic terms if n is high enough.
            formula = f"Q('{target_column}') ~ " + " + ".join([f"Q('{f}')" for f in factors])
            model = ols(formula, data=df).fit()
            
            # 3. ANOVA
            anova_table = sm.stats.anova_lm(model, typ=2)
            anova_report = []
            for idx, row in anova_table.iterrows():
                anova_report.append({
                    "source": str(idx),
                    "sum_sq": round(float(row['sum_sq']), 4),
                    "df": int(row['df']),
                    "f_value": round(float(row['F']), 4) if not pd.isna(row['F']) else None,
                    "p_value": round(float(row['PR(>F)']), 6) if not pd.isna(row['PR(>F)']) else None,
                    "significant": bool(row['PR(>F)'] < 0.05) if not pd.isna(row['PR(>F)']) else False
                })

            # 4. Main Effects
            effects = {}
            for f in factors:
                # Effect = Mean(High) - Mean(Low) for the factor
                # Simple approximation for continuous: coefficient * range
                f_min = df[f].min()
                f_max = df[f].max()
                coef = model.params[f"Q('{f}')"]
                impact = coef * (f_max - f_min)
                effects[f] = {
                    "coefficient": round(float(coef), 4),
                    "total_impact": round(float(impact), 4),
                    "direction": "positive" if impact > 0 else "negative"
                }

            # 5. Optimization
            # Find the bounds for each factor
            bounds = []
            x0 = []
            for f in factors:
                bounds.append((df[f].min(), df[f].max()))
                x0.append(df[f].mean())

            def objective(x):
                # Predict response for given x
                input_dict = {f: [val] for f, val in zip(factors, x)}
                input_df = pd.DataFrame(input_dict)
                pred = model.predict(input_df)[0]
                return -pred if goal == "maximize" else pred

            res = optimize.minimize(objective, x0, bounds=bounds, method='L-BFGS-B')
            
            optimal_settings = {}
            for i, f in enumerate(factors):
                optimal_settings[f] = round(float(res.x[i]), 4)
            
            predicted_optimum = -res.fun if goal == "maximize" else res.fun

            return {
                "status": "success",
                "anova": anova_report,
                "main_effects": effects,
                "r_squared": round(float(model.rsquared), 4),
                "optimization": {
                    "goal": goal,
                    "optimal_settings": optimal_settings,
                    "predicted_response": round(float(predicted_optimum), 4)
                },
                "summary": (
                    f"Model explaining {round(model.rsquared*100, 1)}% of variance. "
                    f"Key factor: {max(effects, key=lambda k: abs(effects[k]['total_impact']))}."
                )
            }
            
        except Exception as e:
            return {"error": f"DoE analysis failed: {str(e)}"}


class PredictShelfLifeArrheniusTool(BaseTool):
    """
    Predicts product shelf life using Arrhenius kinetic modeling. 
    Analyzes degradation data at multiple temperatures to extrapolate 
    stability at a target storage temperature.
    """

    @property
    def name(self) -> str:
        return "predict_shelf_life_arrhenius"

    @property
    def description(self) -> str:
        return (
            "Predicts product shelf life using Arrhenius kinetic modeling based on "
            "accelerated stability data. Determines reaction order, activation energy (Ea), "
            "and extrapolates stability to a target temperature (e.g., 25°C). "
            "Never calculate kinetic parameters or shelf life mentally — always use this tool."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "stability_data": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "List of observations with 'temperature' (Celsius), 'time' (days/hours), and 'value' (quality/concentration)."
                },
                "target_temperature": {
                    "type": "number",
                    "description": "The expected real-world storage temperature (default: 25°C).",
                    "default": 25.0
                },
                "failure_threshold": {
                    "type": "number",
                    "description": "The value at which the product is considered failed (e.g., 90 for 10% degradation if start is 100)."
                },
                "time_unit": {
                    "type": "string",
                    "description": "Units of time (e.g., 'days', 'hours', 'weeks').",
                    "default": "days"
                }
            },
            "required": ["stability_data", "failure_threshold"]
        }

    def execute(
        self, 
        stability_data: List[Dict[str, Any]], 
        failure_threshold: float,
        target_temperature: float = 25.0,
        time_unit: str = "days",
        **kwargs
    ) -> Dict[str, Any]:
        try:
            df = pd.DataFrame(stability_data)
            
            # 1. Validation
            required = ["temperature", "time", "value"]
            if not all(c in df.columns for c in required):
                return {"error": f"Data must contain: {required}"}
            
            temps = df["temperature"].unique()
            if len(temps) < 2:
                return {"error": "Need at least 2 different temperatures for Arrhenius modeling."}

            # 2. Determine Reaction Order and calculate k for each temp
            # k_results = {temp: {"k": val, "r2": val, "order": 0/1}}
            k_map = {}
            R = 8.314  # Gas constant J/(mol*K)
            
            for t_celsius in temps:
                sub_df = df[df["temperature"] == t_celsius].sort_values("time")
                if len(sub_df) < 2:
                    continue
                
                x = sub_df["time"].values
                y = sub_df["value"].values
                
                # Fit 0th order: y = -kt + y0
                slope0, intercept0, r0, _, _ = stats.linregress(x, y)
                k0 = -slope0
                r2_0 = r0**2
                
                # Fit 1st order: ln(y) = -kt + ln(y0)
                # Ensure y > 0 for log
                if all(y > 0):
                    slope1, intercept1, r1, _, _ = stats.linregress(x, np.log(y))
                    k1 = -slope1
                    r2_1 = r1**2
                else:
                    r2_1 = -1
                
                # Pick better fit
                if r2_1 > r2_0:
                    k_map[t_celsius] = {"k": k1, "r2": r2_1, "order": 1, "intercept": intercept1}
                else:
                    k_map[t_celsius] = {"k": k0, "r2": r2_0, "order": 0, "intercept": intercept0}

            if len(k_map) < 2:
                return {"error": "Insufficient data points at each temperature to calculate rate constants."}

            # 3. Arrhenius Plot: ln(k) vs 1/T (Kelvin)
            arr_x = [] # 1/T
            arr_y = [] # ln(k)
            for t_c, data in k_map.items():
                if data["k"] <= 0: continue # Skip if k is negative (increasing quality over time?)
                arr_x.append(1.0 / (t_c + 273.15))
                arr_y.append(np.log(data["k"]))
            
            if len(arr_x) < 2:
                return {"error": "Degradation rates are non-positive or inconsistent. Cannot fit Arrhenius model."}

            slope_arr, intercept_arr, r_arr, _, _ = stats.linregress(arr_x, arr_y)
            
            # ln(k) = -Ea/R * (1/T) + ln(A)
            ea = -slope_arr * R
            a_freq = np.exp(intercept_arr)
            r2_arr = r_arr**2
            
            # 4. Predict k at target temperature
            target_t_kelvin = target_temperature + 273.15
            k_target = a_freq * np.exp(-ea / (R * target_t_kelvin))
            
            # 5. Calculate Shelf Life
            # We assume the reaction order is the one that best fit the data overall
            # (Simplification: take the most frequent order)
            orders = [d["order"] for d in k_map.values()]
            dominant_order = max(set(orders), key=orders.count)
            
            # Find initial value (y0) - average of intercepts across temps if 0th/1st
            y0_candidates = []
            for t_c, data in k_map.items():
                if data["order"] == 0: y0_candidates.append(data["intercept"])
                else: y0_candidates.append(np.exp(data["intercept"]))
            y0 = np.mean(y0_candidates)

            if dominant_order == 0:
                # 0th: threshold = -k*t + y0  => t = (y0 - threshold) / k
                shelf_life = (y0 - failure_threshold) / k_target
            else:
                # 1st: ln(threshold) = -k*t + ln(y0) => t = (ln(y0) - ln(threshold)) / k
                shelf_life = (np.log(y0) - np.log(failure_threshold)) / k_target

            # 6. Warnings
            warnings = []
            if r2_arr < 0.9:
                warnings.append("Low Arrhenius correlation (R² < 0.9). Predictions may be unreliable.")
            if ea < 40000 or ea > 130000:
                warnings.append(f"Activation Energy ({round(ea/1000, 1)} kJ/mol) is outside typical food/flavor ranges (40-125 kJ/mol). Mechanism might have changed.")

            return {
                "status": "success",
                "reaction_order": dominant_order,
                "activation_energy_kj_mol": round(ea / 1000.0, 2),
                "frequency_factor_a": f"{a_freq:.2e}",
                "arrhenius_r2": round(r2_arr, 4),
                "prediction": {
                    "target_temperature_c": target_temperature,
                    "estimated_rate_constant_k": round(k_target, 6),
                    "predicted_shelf_life": round(shelf_life, 2),
                    "unit": time_unit,
                    "initial_value_est": round(y0, 2),
                    "failure_threshold": failure_threshold
                },
                "temperature_fits": [
                    {"temp_c": t, "k": round(d["k"], 6), "r2": round(d["r2"], 4), "order": d["order"]}
                    for t, d in k_map.items()
                ],
                "warnings": warnings,
                "summary": (
                    f"Predicted shelf life of {round(shelf_life, 1)} {time_unit} at {target_temperature}°C. "
                    f"Model fit R²={round(r2_arr, 3)} with Ea={round(ea/1000, 1)} kJ/mol."
                )
            }

        except Exception as e:
            return {"error": f"Shelf life prediction failed: {str(e)}"}


ToolRegistry.register(AnalyzeDatasetTool())
ToolRegistry.register(AnalyzeDesignOfExperimentsTool())
ToolRegistry.register(PredictShelfLifeArrheniusTool())


class AnalyzeDeviationTool(BaseTool):
    """
    Performs root-cause analysis by comparing a failed batch against successful batches.
    Joins quality, process, and ingredient data to identify anomalies.
    """

    @property
    def name(self) -> str:
        return "analyze_deviation"

    @property
    def description(self) -> str:
        return (
            "Performs automated root-cause analysis for a failed production batch. "
            "Compares the failed batch against successful 'PASS' batches of the same product. "
            "Requires paths to quality, process, and ingredients datasets. "
            "Never perform root-cause analysis mentally — always use this tool."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "failed_batch_id": {
                    "type": "string",
                    "description": "The ID of the batch that failed quality control.",
                },
                "quality_file": {
                    "type": "string",
                    "description": "Path to the batch quality dataset (must contain Batch_ID and Quality_Status).",
                },
                "process_file": {
                    "type": "string",
                    "description": "Path to the batch process dataset (must contain Batch_ID and sensor data).",
                },
                "ingredients_file": {
                    "type": "string",
                    "description": "Path to the batch ingredients dataset (must contain Batch_ID and Lot_Number).",
                },
                "target_metric": {
                    "type": "string",
                    "description": "The specific quality metric that deviated (e.g., 'Impurity_pct').",
                },
            },
            "required": [
                "failed_batch_id",
                "quality_file",
                "process_file",
                "ingredients_file",
            ],
        }

    def execute(
        self,
        failed_batch_id: str,
        quality_file: str,
        process_file: str,
        ingredients_file: str,
        target_metric: Optional[str] = None,
        workspace: Optional[Any] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        # FIX: Clean quotes from column names to prevent Pandas lookup errors
        if target_metric:
            target_metric = target_metric.strip("'\"")

        # Resolve paths via workspace if provided
        if workspace:
            try:
                quality_file = str(workspace.resolve(quality_file))
                process_file = str(workspace.resolve(process_file))
                ingredients_file = str(workspace.resolve(ingredients_file))
            except PermissionError as e:
                return {"error": f"Workspace access denied: {str(e)}"}

        try:
            # 1. Load Data
            with duckdb.connect(database=":memory:") as con:
                quality_df = con.execute(f"SELECT * FROM '{quality_file}'").df()
                process_df = con.execute(f"SELECT * FROM '{process_file}'").df()
                ingredients_df = con.execute(f"SELECT * FROM '{ingredients_file}'").df()

            # 2. Identify the product and failed batch
            failed_row = quality_df[quality_df["Batch_ID"] == failed_batch_id]
            if failed_row.empty:
                return {"error": f"Batch ID {failed_batch_id} not found in quality file."}

            product_name = failed_row["Product_Name"].iloc[0]
            failed_metric_val = failed_row[target_metric].iloc[0] if target_metric else None

            # 3. Get reference "PASS" batches for the same product
            pass_batches = quality_df[
                (quality_df["Product_Name"] == product_name)
                & (quality_df["Quality_Status"].str.upper() == "PASS")
            ]["Batch_ID"].tolist()

            if not pass_batches:
                return {
                    "error": f"No successful reference batches found for product {product_name}."
                }

            # 4. Process Data Comparison (Numeric)
            process_pass = process_df[process_df["Batch_ID"].isin(pass_batches)]
            process_fail = process_df[process_df["Batch_ID"] == failed_batch_id]

            numeric_cols = process_df.select_dtypes(include=[np.number]).columns.tolist()
            if "Batch_ID" in numeric_cols:
                numeric_cols.remove("Batch_ID")

            process_anomalies = []
            for col in numeric_cols:
                avg_pass = process_pass[col].mean()
                std_pass = process_pass[col].std()
                val_fail = process_fail[col].iloc[0] if not process_fail.empty else None

                if val_fail is not None and not pd.isna(avg_pass):
                    delta = val_fail - avg_pass
                    # Flag if more than 2 standard deviations away, or simple 10% if std is 0
                    is_anomaly = (
                        abs(delta) > (2 * std_pass)
                        if (not pd.isna(std_pass) and std_pass > 0)
                        else abs(delta / avg_pass) > 0.1
                        if avg_pass != 0
                        else False
                    )

                    if is_anomaly:
                        process_anomalies.append(
                            {
                                "parameter": col,
                                "failed_value": round(float(val_fail), 2),
                                "average_pass": round(float(avg_pass), 2),
                                "deviation": round(float(delta), 2),
                                "severity": "High" if (not pd.isna(std_pass) and std_pass > 0 and abs(delta) > (3 * std_pass)) else "Medium",
                            }
                        )

            # 5. Ingredient/Lot Comparison (Categorical)
            ing_pass = ingredients_df[ingredients_df["Batch_ID"].isin(pass_batches)]
            ing_fail = ingredients_df[ingredients_df["Batch_ID"] == failed_batch_id]

            ingredient_anomalies = []
            for _, row in ing_fail.iterrows():
                ing_name = row["Ingredient_Name"]
                fail_lot = row["Lot_Number"]

                # Check if this lot was used in PASS batches
                lot_usage_in_pass = ing_pass[
                    (ing_pass["Ingredient_Name"] == ing_name)
                    & (ing_pass["Lot_Number"] == fail_lot)
                ]

                if lot_usage_in_pass.empty:
                    # New lot detected!
                    # Check if there were OTHER lots used in PASS batches
                    other_lots = ing_pass[ing_pass["Ingredient_Name"] == ing_name][
                        "Lot_Number"
                    ].unique()
                    ingredient_anomalies.append(
                        {
                            "ingredient": ing_name,
                            "failed_batch_lot": fail_lot,
                            "pass_batch_lots": list(other_lots),
                            "issue": "New Lot Detected",
                            "severity": "Medium",
                        }
                    )

            # 6. Conclusion Synthesis
            hypotheses = []
            for anom in process_anomalies:
                hypotheses.append(
                    f"Process Deviation: {anom['parameter']} was {anom['failed_value']} (Avg: {anom['average_pass']})"
                )
            for anom in ingredient_anomalies:
                hypotheses.append(
                    f"Material Change: New lot {anom['failed_batch_lot']} for {anom['ingredient']}"
                )

            return {
                "status": "success",
                "product": product_name,
                "failed_batch": failed_batch_id,
                "target_metric": target_metric,
                "failed_value": round(float(failed_metric_val), 4) if failed_metric_val is not None else None,
                "process_anomalies": process_anomalies,
                "ingredient_anomalies": ingredient_anomalies,
                "root_cause_hypotheses": hypotheses,
                "reference_batches_count": len(pass_batches),
                "summary": f"Analyzed {failed_batch_id}. Found {len(process_anomalies)} process anomalies and {len(ingredient_anomalies)} ingredient anomalies."
            }

        except Exception as e:
            return {"error": f"Deviation analysis failed: {str(e)}"}


ToolRegistry.register(AnalyzeDeviationTool())


class AnalyzeSPCTool(BaseTool):
    """
    Performs Statistical Process Control (SPC) analysis using Individual-Moving Range (I-MR) charts.
    Detects if a process is stable and identifies out-of-control points.
    """

    @property
    def name(self) -> str:
        return "analyze_spc"

    @property
    def description(self) -> str:
        return (
            "Performs Statistical Process Control (SPC) using I-MR charts. "
            "Calculates Control Limits (UCL, LCL) and detects trend violations. "
            "Use this to monitor process stability over time. Never perform SPC mentally."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the production dataset (.csv or .jsonl).",
                },
                "target_column": {
                    "type": "string",
                    "description": "The numeric column to monitor (e.g., 'Viscosity_cP').",
                },
                "timestamp_column": {
                    "type": "string",
                    "description": "Column used for ordering the data chronologically.",
                },
            },
            "required": ["file_path", "target_column"],
        }

    def execute(
        self,
        file_path: str,
        target_column: str,
        timestamp_column: Optional[str] = None,
        workspace: Optional[Any] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        # FIX: Clean quotes from column names to prevent Pandas lookup errors
        target_column = target_column.strip("'\"")
        if timestamp_column:
            timestamp_column = timestamp_column.strip("'\"")

        # Resolve path via workspace if provided
        if workspace:
            try:
                file_path = str(workspace.resolve(file_path))
            except PermissionError as e:
                return {"error": f"Workspace access denied: {str(e)}"}

        try:
            # 1. Load and Sort Data
            with duckdb.connect(database=":memory:") as con:
                order_by = f'ORDER BY "{timestamp_column}"' if timestamp_column else ""
                df = con.execute(f'SELECT * FROM "{file_path}" {order_by}').df()

            data = pd.to_numeric(df[target_column], errors="coerce").dropna()
            if len(data) < 5:
                return {"error": "Need at least 5 data points for meaningful SPC analysis."}

            # 2. I-MR Chart Calculations
            # Individual Chart
            mean_x = data.mean()
            moving_ranges = np.abs(data.diff().dropna())
            avg_mr = moving_ranges.mean()

            # Constants for I-MR (Subgroup size 2)
            # 3-Sigma limits: Mean +/- (3 * AvgMR / 1.128) -> Mean +/- 2.66 * AvgMR
            sigma_est = avg_mr / 1.128
            ucl_x = mean_x + (3 * sigma_est)
            lcl_x = mean_x - (3 * sigma_est)

            # Moving Range Limits
            ucl_mr = 3.267 * avg_mr
            lcl_mr = 0

            # 3. Detect Violations (Nelson Rule 1: Beyond Limits)
            violations = []
            for i, val in enumerate(data):
                status = "Stable"
                if val > ucl_x:
                    status = "Above UCL"
                elif val < lcl_x:
                    status = "Below LCL"

                if status != "Stable":
                    violations.append({
                        "index": int(i),
                        "batch_id": str(df.iloc[i].get("Batch_ID", "N/A")),
                        "value": round(float(val), 2),
                        "violation": status
                    })

            # 4. Detect Runs (Rule: 7 or more consecutive points on one side of the mean)
            runs = []
            current_run = []
            last_side = None # 1 for above, -1 for below
            
            for i, val in enumerate(data):
                side = 1 if val > mean_x else -1
                if side == last_side:
                    current_run.append(i)
                else:
                    if len(current_run) >= 7:
                        runs.append({"indices": current_run, "type": "Run Detected"})
                    current_run = [i]
                    last_side = side

            return {
                "status": "success",
                "metric": target_column,
                "statistics": {
                    "mean": round(float(mean_x), 4),
                    "process_sigma": round(float(sigma_est), 4),
                    "ucl": round(float(ucl_x), 4),
                    "lcl": round(float(lcl_x), 4),
                    "avg_moving_range": round(float(avg_mr), 4),
                },
                "control_status": "Out of Control" if violations or runs else "Stable",
                "violations": violations,
                "runs": runs,
                "data_points_count": len(data),
                "summary": f"Process is {('Out of Control' if violations or runs else 'Stable')}. Found {len(violations)} limit violations."
            }

        except Exception as e:
            return {"error": f"SPC analysis failed: {str(e)}"}


ToolRegistry.register(AnalyzeSPCTool())
