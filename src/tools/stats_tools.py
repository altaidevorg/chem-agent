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
                    "enum": ["correlation", "describe", "ratio_rank", "outlier", "group_compare"],
                    "description": "Type of statistical analysis to perform.",
                },
                "columns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Column names involved in the analysis.",
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

        x = df_clean[columns[0]]
        y = df_clean[columns[1]]

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
            stats_row = con.execute(f"""
                SELECT
                    AVG({col_ref}) AS mean_value,
                    STDDEV({col_ref}) AS std_value,
                    COUNT(*) AS n
                FROM ({source_query})
            """).fetchone()

            mean_value, std_value, n = stats_row
            if std_value is None or std_value == 0 or n == 0:
                return {"error": "Cannot detect outliers: zero variance or empty dataset."}

            outliers = con.execute(f"""
                WITH source AS ({source_query}),
                stats AS (
                    SELECT
                        AVG({col_ref}) AS mean_value,
                        STDDEV({col_ref}) AS std_value
                    FROM source
                )
                SELECT
                    source.*,
                    ABS((source.{col_ref} - stats.mean_value) / stats.std_value) AS z_score
                FROM source, stats
                WHERE ABS((source.{col_ref} - stats.mean_value) / stats.std_value) > {float(z_threshold)}
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

    def execute(
        self,
        file_path: str,
        analysis_type: str,
        columns: Optional[List[str]] = None,
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

            return {
                "error": f"Unsupported analysis_type: {analysis_type}",
                "supported_types": ["correlation", "describe", "ratio_rank", "outlier", "group_compare"],
            }
        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}"}


ToolRegistry.register(AnalyzeDatasetTool())
