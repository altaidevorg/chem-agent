# src/tools/schema_cache.py
import os
import re
from difflib import get_close_matches
from typing import Any, Dict, List, Optional


def sql_column_reference(column_name: str) -> str:
    """Returns a DuckDB-safe SQL column reference."""
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", column_name):
        return column_name
    escaped = column_name.replace('"', '""')
    return f'"{escaped}"'


def normalize_column_name(name: str) -> str:
    """Normalizes column names for fuzzy comparison."""
    normalized = name.lower().strip()
    normalized = normalized.replace("_", " ")
    normalized = re.sub(r"[^a-z0-9 ]+", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def extract_file_paths_from_sql(sql_query: str) -> List[str]:
    """Extracts quoted file paths from a SQL query."""
    paths = re.findall(r"'([^']+\.(?:csv|jsonl|parquet))'", sql_query, flags=re.IGNORECASE)
    # Preserve order while removing duplicates
    seen = set()
    ordered_paths: List[str] = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            ordered_paths.append(path)
    return ordered_paths


def parse_candidate_bindings(error_message: str) -> List[str]:
    """Parses DuckDB candidate binding suggestions from an error message."""
    match = re.search(r"Candidate bindings:\s*(.+)", error_message, flags=re.DOTALL)
    if not match:
        return []

    bindings_text = match.group(1).split("\n", 1)[0]
    return re.findall(r'"([^"]+)"', bindings_text)


def parse_missing_column(error_message: str) -> Optional[str]:
    """Extracts the missing column name from a DuckDB binder error."""
    patterns = [
        r'Referenced column "([^"]+)" not found',
        r"Referenced column '([^']+)' not found",
        r"column \"([^\"]+)\" not found",
    ]
    for pattern in patterns:
        match = re.search(pattern, error_message, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return None


class SchemaCache:
    """Session-scoped cache for inspected dataset schemas."""

    _schemas: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def _normalize_path(cls, file_path: str) -> str:
        return os.path.normpath(file_path)

    @classmethod
    def register(
        cls,
        file_path: str,
        columns: List[Dict[str, Any]],
        total_rows: int = 0,
        example_select: Optional[str] = None,
    ) -> None:
        normalized_path = cls._normalize_path(file_path)
        column_names = [col["name"] for col in columns]
        sql_column_list = ", ".join(col["sql_reference"] for col in columns)

        cls._schemas[normalized_path] = {
            "file_path": file_path,
            "total_rows": total_rows,
            "columns": columns,
            "column_names": column_names,
            "sql_column_list": sql_column_list,
            "example_select": example_select,
        }

    @classmethod
    def get(cls, file_path: str) -> Optional[Dict[str, Any]]:
        return cls._schemas.get(cls._normalize_path(file_path))

    @classmethod
    def get_for_paths(cls, file_paths: List[str]) -> List[Dict[str, Any]]:
        schemas = []
        for path in file_paths:
            schema = cls.get(path)
            if schema:
                schemas.append(schema)
        return schemas

    @classmethod
    def suggest_column(cls, invalid_column: str, available_columns: List[str]) -> Optional[str]:
        if not available_columns:
            return None

        normalized_invalid = normalize_column_name(invalid_column)
        normalized_map = {normalize_column_name(col): col for col in available_columns}

        if normalized_invalid in normalized_map:
            return normalized_map[normalized_invalid]

        close_matches = get_close_matches(
            normalized_invalid,
            list(normalized_map.keys()),
            n=1,
            cutoff=0.6,
        )
        if close_matches:
            return normalized_map[close_matches[0]]

        return None

    @classmethod
    def build_error_context(cls, sql_query: str, error_message: str) -> Dict[str, Any]:
        """Builds actionable schema hints for failed SQL queries."""
        file_paths = extract_file_paths_from_sql(sql_query)
        cached_schemas = cls.get_for_paths(file_paths)

        missing_column = parse_missing_column(error_message)
        duckdb_candidates = parse_candidate_bindings(error_message)

        suggestions: List[str] = []
        available_columns: List[str] = []
        did_you_mean: Optional[str] = None

        for schema in cached_schemas:
            available_columns.extend(schema["column_names"])

        if missing_column and available_columns:
            did_you_mean = cls.suggest_column(missing_column, available_columns)
            if did_you_mean:
                suggestions.append(
                    f'Did you mean {sql_column_reference(did_you_mean)} instead of "{missing_column}"?'
                )

        if duckdb_candidates and not did_you_mean:
            did_you_mean = duckdb_candidates[0]
            suggestions.append(f'DuckDB suggests: {sql_column_reference(did_you_mean)}')

        context: Dict[str, Any] = {
            "hint": "Use exact column names from inspect_dataset. Copy sql_reference values verbatim.",
        }

        if missing_column:
            context["invalid_column"] = missing_column

        if did_you_mean:
            context["did_you_mean"] = did_you_mean
            context["did_you_mean_sql"] = sql_column_reference(did_you_mean)

        if available_columns:
            context["available_columns"] = available_columns
            context["sql_column_list"] = ", ".join(sql_column_reference(col) for col in available_columns)

        if cached_schemas:
            context["cached_schemas"] = [
                {
                    "file_path": schema["file_path"],
                    "total_rows": schema["total_rows"],
                    "sql_column_list": schema["sql_column_list"],
                    "example_select": schema.get("example_select"),
                }
                for schema in cached_schemas
            ]
        elif file_paths:
            context["hint"] = (
                "No cached schema found for referenced files. Run inspect_dataset first, "
                "then copy sql_reference values exactly into your SQL query."
            )

        if suggestions:
            context["suggestions"] = suggestions

        return context

    @classmethod
    def clear(cls) -> None:
        cls._schemas.clear()

    @classmethod
    def validate_columns(cls, file_path: str, column_names: List[str]) -> Dict[str, Any]:
        """Validates column names against cached schema or live DuckDB describe."""
        schema = cls.get(file_path)
        available = schema["column_names"] if schema else cls._load_column_names(file_path)

        if available is None:
            return {
                "valid": False,
                "error": f"No schema available for '{file_path}'. Run inspect_dataset first.",
            }

        invalid = []
        suggestions = {}
        for col in column_names:
            if col not in available:
                invalid.append(col)
                suggestion = cls.suggest_column(col, available)
                if suggestion:
                    suggestions[col] = suggestion

        return {
            "valid": len(invalid) == 0,
            "available_columns": available,
            "invalid_columns": invalid,
            "suggestions": suggestions,
        }

    @classmethod
    def _load_column_names(cls, file_path: str) -> Optional[List[str]]:
        """Loads column names directly from DuckDB when cache is missing."""
        if not os.path.exists(file_path):
            return None
        try:
            import duckdb
            con = duckdb.connect(database=":memory:")
            # Escape single quotes in file path for safe SQL execution
            escaped_path = file_path.replace("'", "''")
            description = con.execute(f"DESCRIBE SELECT * FROM '{escaped_path}' LIMIT 0").df()
            return description["column_name"].tolist()
        except Exception:
            return None
