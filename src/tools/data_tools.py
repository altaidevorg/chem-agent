# src/tools/data_tools.py
import json
import os
import duckdb
import pandas as pd
from typing import Any, Dict, List
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

    def execute(self, file_path: str) -> Dict[str, Any]:
        """Inspects the schema of a dataset using DuckDB."""
        if not os.path.exists(file_path):
            return {"error": f"File not found at path: {file_path}"}

        try:
            con = duckdb.connect(database=':memory:')
            
            # Escape single quotes in file path for safe SQL execution
            escaped_path = file_path.replace("'", "''")

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

    def execute(self, sql_query: str, max_results: int = 50) -> Dict[str, Any]:
        """Executes a SQL query on files and returns results as dictionaries."""
        try:
            con = duckdb.connect(database=':memory:')
            res_df = con.execute(sql_query).df()
            total_found = len(res_df)

            if total_found > max_results:
                results = self._sanitize_results(res_df.head(max_results))
                message = (
                    f"Query returned {total_found} rows. Returning the first {max_results} rows. "
                    "Consider refining your SQL query for more specific results."
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


# Register tools
ToolRegistry.register(InspectDatasetTool())
ToolRegistry.register(QueryDatasetTool())
