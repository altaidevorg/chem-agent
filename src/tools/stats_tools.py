# src/tools/stats_tools.py
import json
import math
import os
from typing import Any, Dict, List, Optional

import duckdb
import pandas as pd
from scipy import stats

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
        if isinstance(value, str):
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
            "Use this for correlation, descriptive stats, ratio ranking, outliers, and group comparisons. "
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
                    "enum": ["correlation", "describe", "ratio_rank", "outlier", "group_compare", "rolling_stats", "lag_analysis", "shift_analysis"],
                    "description": "Type of statistical analysis to perform.",
                },
                "columns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Column names involved in the analysis.",
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
        if len(columns) != 2:
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
        if not columns:
            return {"error": "describe requires at least one column in 'columns'."}

        validation_error = _validate_requested_columns(file_path, columns)
        if validation_error:
            return validation_error

        df = self._load_dataframe(file_path, where_body)
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
        if not columns or len(columns) != 1:
            return {"error": "outlier requires exactly one numeric column in 'columns'."}

        validation_error = _validate_requested_columns(file_path, columns)
        if validation_error:
            return validation_error

        col = columns[0]
        col_ref = sql_column_reference(col)
        source_query = self._build_source_query(file_path, where_body)
        
        with duckdb.connect(database=":memory:") as con:
            # Create a temporary table to store source results so we only scan the file once
            con.execute(f"CREATE TEMP TABLE source AS {source_query}")
            
            stats_row = con.execute(f"""
                SELECT
                    AVG({col_ref}) AS mean_value,
                    STDDEV({col_ref}) AS std_value,
                    COUNT(*) AS n
                FROM source
            """).fetchone()

            mean_value, std_value, n = stats_row
            if std_value is None or std_value == 0 or n == 0:
                return {"error": "Cannot detect outliers: zero variance or empty dataset."}

            # Directly interpolate calculated stats for high-performance outlier discovery
            outliers = con.execute(f"""
                SELECT
                    *,
                    ABS(({col_ref} - {float(mean_value)}) / {float(std_value)}) AS z_score
                FROM source
                WHERE ABS(({col_ref} - {float(mean_value)}) / {float(std_value)}) > {float(z_threshold)}
                ORDER BY z_score DESC
                LIMIT {int(limit)}
            """).df()

        return {
            "analysis_type": "outlier",
            "column": col,
            "z_threshold": z_threshold,
            "population_stats": {
                "mean": round(float(mean_value), 4),
                "std": round(float(std_value), 4),
                "n": int(n),
            },
            "outlier_count_returned": len(outliers),
            "result": _sanitize_records(outliers),
            "status": "success",
        }

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
        where_clause: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not os.path.exists(file_path):
            return {"error": f"File not found at path: {file_path}"}

        columns = columns or []
        where_body = _merge_where_clauses(where_clause, filters)

        try:
            if analysis_type == "correlation":
                return self._run_correlation(
                    file_path, columns, granularity, group_by, method, where_body
                )
            if analysis_type == "describe":
                return self._run_describe(file_path, columns, where_body)
            if analysis_type == "ratio_rank":
                return self._run_ratio_rank(
                    file_path, numerator, denominator, group_by, ratio_method, order, limit, where_body
                )
            if analysis_type == "outlier":
                return self._run_outlier(file_path, columns, z_threshold, limit, where_body)
            if analysis_type == "group_compare":
                return self._run_group_compare(file_path, columns, group_by, where_body)
            if analysis_type == "rolling_stats":
                return self._run_rolling_stats(
                    file_path, columns, timestamp_column, window_size, group_by, where_body
                )
            if analysis_type == "lag_analysis":
                return self._run_lag_analysis(
                    file_path, columns, timestamp_column, lag_steps, group_by, method, where_body
                )
            if analysis_type == "shift_analysis":
                return self._run_shift_analysis(
                    file_path, columns, timestamp_column, where_body
                )

            return {
                "error": f"Unsupported analysis_type: {analysis_type}",
                "supported_types": ["correlation", "describe", "ratio_rank", "outlier", "group_compare", "rolling_stats", "lag_analysis", "shift_analysis"],
            }
        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}"}


ToolRegistry.register(AnalyzeDatasetTool())
