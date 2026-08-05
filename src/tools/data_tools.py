# src/tools/data_tools.py
import json
import os
import re
import duckdb
import pandas as pd
from typing import Any, Dict, List, Optional
from src.tools.base import BaseTool, ToolRegistry
from src.tools.schema_cache import SchemaCache, sql_column_reference


def _build_column_metadata(description_df: pd.DataFrame) -> List[Dict[str, Any]]:
    columns: List[Dict[str, Any]] = []
    for _, row in description_df.iterrows():
        column_name = row["column_name"]
        columns.append({
            "name": column_name,
            "type": row["column_type"],
            "sql_reference": sql_column_reference(column_name),
        })
    return columns


class InspectDatasetTool(BaseTool):
    @property
    def name(self) -> str:
        return "inspect_dataset"

    @property
    def description(self) -> str:
        return (
            "Explores the structure, columns, and data types of a large CSV or JSONL dataset "
            "without loading it entirely into memory. Returns SQL-ready column references. "
            "Always use this before query_dataset."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute or relative local path to the target file (.csv or .jsonl)."
                }
            },
            "required": ["file_path"]
        }

    def _sanitize_results(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Converts a Pandas DataFrame to a JSON-serializable list of dictionaries."""
        return json.loads(df.to_json(orient='records', date_format='iso'))

    def execute(self, file_path: str, workspace: Optional[Any] = None, **kwargs) -> Dict[str, Any]:
        """Inspects the schema of a dataset using DuckDB."""
        if workspace:
            try:
                real_path = workspace.resolve(file_path)
                file_path = str(real_path)
            except PermissionError as e:
                return {"error": str(e), "status": "fail"}

        if not os.path.exists(file_path):
            return {"error": f"File not found at path: {file_path}"}

        try:
            # Escape single quotes in file path for safe SQL execution
            escaped_path = file_path.replace("'", "''")

            with duckdb.connect(database=':memory:') as con:
                description = con.execute(f"DESCRIBE SELECT * FROM '{escaped_path}' LIMIT 0").df()
                sample = con.execute(f"SELECT * FROM '{escaped_path}' LIMIT 5").df()
                count_res = con.execute(f"SELECT COUNT(*) FROM '{escaped_path}'").fetchone()
                total_rows = count_res[0] if count_res else 0

            columns = _build_column_metadata(description)
            sql_column_list = ", ".join(col["sql_reference"] for col in columns)
            example_select = f"SELECT {sql_column_list} FROM '{escaped_path}' LIMIT 5"

            SchemaCache.register(
                file_path,
                columns,
                total_rows=total_rows,
                example_select=example_select,
            )

            return {
                "file_path": file_path,
                "total_rows": total_rows,
                "columns": columns,
                "sql_column_list": sql_column_list,
                "example_select": example_select,
                "sample_rows": self._sanitize_results(sample),
                "usage_note": (
                    "Copy sql_reference values exactly in query_dataset. "
                    "Do not rename columns (e.g. do not convert spaces to underscores)."
                ),
                "status": "success"
            }
        except Exception as e:
            return {"error": f"Failed to inspect dataset: {str(e)}"}


class QueryDatasetTool(BaseTool):
    @property
    def name(self) -> str:
        return "query_dataset"

    @property
    def description(self) -> str:
        return (
            "Executes a SQL query on one or more local datasets (CSV/JSONL) using DuckDB. "
            "Use exact sql_reference column names from inspect_dataset."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "sql_query": {
                    "type": "string",
                    "description": (
                        "The SQL query to execute. Reference files in single quotes "
                        "(e.g., SELECT \"Machine ID\" FROM 'data/logs.csv'). "
                        "Use sql_reference values from inspect_dataset exactly."
                    )
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of rows to return to the agent's context. Defaults to 50.",
                    "default": 50
                }
            },
            "required": ["sql_query"]
        }

    def _sanitize_results(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Converts a Pandas DataFrame to a JSON-serializable list of dictionaries."""
        return json.loads(df.to_json(orient='records', date_format='iso'))

    def execute(self, sql_query: str, max_results: int = 50, workspace: Optional[Any] = None, **kwargs) -> Dict[str, Any]:
        """Executes a SQL query on files and returns results as dictionaries."""
        # Safety Hard-Cap: Never allow more than 100 rows to context to prevent memory crashes
        effective_max = min(max_results, 100)
        
        # FIX: Resolve file paths inside the SQL query if workspace is provided
        if workspace:
            # Find all single-quoted strings that look like file paths
            # e.g., 'data/logs.csv'
            matches = re.findall(r"'(.*?\.(?:csv|jsonl|db))'", sql_query, re.IGNORECASE)
            for path in matches:
                try:
                    real_path = workspace.resolve(path)
                    sql_query = sql_query.replace(f"'{path}'", f"'{str(real_path)}'")
                except PermissionError as e:
                    return {"error": f"Workspace access denied: {str(e)}", "status": "fail"}
        
        try:
            with duckdb.connect(database=':memory:') as con:
                res_df = con.execute(sql_query).df()
            total_found = len(res_df)

            if total_found > effective_max:
                results = self._sanitize_results(res_df.head(effective_max))
                message = (
                    f"Query returned {total_found} rows. Returning the first {effective_max} rows "
                    f"(hard-capped to protect memory). Consider refining your SQL query."
                )
            else:
                results = self._sanitize_results(res_df)
                message = f"Query returned {total_found} rows."

            return {
                "sql_query": sql_query,
                "total_found": total_found,
                "results": results,
                "message": message,
                "status": "success"
            }
        except Exception as e:
            error_message = str(e)
            error_context = SchemaCache.build_error_context(sql_query, error_message)
            return {
                "error": f"SQL Execution Error: {error_message}",
                **error_context,
            }


class ProfileDatasetHealthTool(BaseTool):
    @property
    def name(self) -> str:
        return "profile_dataset_health"

    @property
    def description(self) -> str:
        return (
            "Performs a comprehensive health check on a dataset. Detects missing values, "
            "unique value counts, and identifies the semantic meaning of columns "
            "(e.g., categorical, numeric, temporal). Use this for data quality audits."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute or relative local path to the target file (.csv or .jsonl)."
                }
            },
            "required": ["file_path"]
        }

    def execute(self, file_path: str, workspace: Optional[Any] = None, **kwargs) -> Dict[str, Any]:
        """Performs a comprehensive data quality and health profile."""
        if workspace:
            try:
                real_path = workspace.resolve(file_path)
                file_path = str(real_path)
            except PermissionError as e:
                return {"error": str(e), "status": "fail"}

        if not os.path.exists(file_path):
            return {"error": f"File not found at path: {file_path}"}

        try:
            escaped_path = file_path.replace("'", "''")
            with duckdb.connect(database=':memory:') as con:
                # 1. Get schema info
                cols_df = con.execute(f"DESCRIBE SELECT * FROM '{escaped_path}' LIMIT 0").df()
                col_names = cols_df["column_name"].tolist()
                
                # 2. Get total row count
                total_rows_res = con.execute(f"SELECT COUNT(*) FROM '{escaped_path}'").fetchone()
                total_rows = total_rows_res[0] if total_rows_res else 0
                
                if total_rows == 0:
                    return {
                        "file_path": file_path, 
                        "total_rows": 0, 
                        "status": "success",
                        "message": "Dataset is empty."
                    }

                # 3. Dynamic SQL for nulls and unique values
                null_counts_expr = ", ".join([f"COUNT(*) - COUNT({sql_column_reference(c)}) AS \"null_{c}\"" for c in col_names])
                unique_counts_expr = ", ".join([f"COUNT(DISTINCT {sql_column_reference(c)}) AS \"unique_{c}\"" for c in col_names])
                
                stats_df = con.execute(f"SELECT {null_counts_expr}, {unique_counts_expr} FROM '{escaped_path}'").df()
                
                health_report = []
                for col in col_names:
                    null_count = int(stats_df[f"null_{col}"].iloc[0])
                    unique_count = int(stats_df[f"unique_{col}"].iloc[0])
                    dtype = cols_df[cols_df["column_name"] == col]["column_type"].iloc[0]
                    
                    # Basic semantic detection logic
                    semantic_type = "string"
                    if any(t in dtype.upper() for t in ["INT", "DOUBLE", "DECIMAL", "FLOAT", "HUGEINT"]):
                        semantic_type = "numeric"
                    elif any(t in dtype.upper() for t in ["TIME", "DATE", "TIMESTAMP"]):
                        semantic_type = "temporal"
                    
                    # If few unique values relative to total rows, it's likely categorical
                    if unique_count < 50 and total_rows > 200:
                        semantic_type = "categorical"
                    
                    health_report.append({
                        "column": col,
                        "data_type": dtype,
                        "semantic_type": semantic_type,
                        "null_count": null_count,
                        "null_percentage": round((null_count / total_rows) * 100, 2),
                        "unique_count": unique_count,
                        "cardinality_ratio": round((unique_count / total_rows), 4)
                    })

                return {
                    "file_path": file_path,
                    "total_rows": total_rows,
                    "columns_analyzed": len(col_names),
                    "health_report": health_report,
                    "status": "success"
                }
        except Exception as e:
            return {"error": f"Failed to profile dataset: {str(e)}"}


class SearchColumnsTool(BaseTool):
    @property
    def name(self) -> str:
        return "search_columns"

    @property
    def description(self) -> str:
        return (
            "Searches for a column name pattern across all registered datasets or a specific directory. "
            "Use this to find which file contains the data you need (e.g., 'Temp_Sensor')."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The substring to search for in column names (case-insensitive)."
                },
                "directory_path": {
                    "type": "string",
                    "description": "Optional directory to scan for datasets (CSV/JSONL). Defaults to 'data'."
                }
            },
            "required": ["pattern"]
        }

    def execute(self, pattern: str, directory_path: str = "data", workspace: Optional[Any] = None, **kwargs) -> Dict[str, Any]:
        """Searches for columns matching a pattern across files."""
        if workspace:
            try:
                real_path = workspace.resolve(directory_path)
                directory_path = str(real_path)
            except PermissionError as e:
                return {"error": str(e), "status": "fail"}

        pattern = pattern.lower()
        matches = []
        
        # 1. Search in current data directory if it exists
        if os.path.exists(directory_path):
            for filename in os.listdir(directory_path):
                if filename.endswith(('.csv', '.jsonl')):
                    file_path = os.path.join(directory_path, filename)
                    cols = SchemaCache.validate_columns(file_path, [])["available_columns"]
                    if cols:
                        matching_cols = [c for c in cols if pattern in c.lower()]
                        if matching_cols:
                            matches.append({
                                "file": file_path,
                                "matched_columns": matching_cols
                            })

        if not matches:
            return {
                "status": "success",
                "message": f"No columns found matching '{pattern}'.",
                "matches": []
            }

        return {
            "status": "success",
            "pattern": pattern,
            "matches": matches,
            "count": len(matches)
        }


# Register tools
ToolRegistry.register(InspectDatasetTool())
ToolRegistry.register(QueryDatasetTool())
ToolRegistry.register(ProfileDatasetHealthTool())
ToolRegistry.register(SearchColumnsTool())
