# src/tools/regulatory_tools.py
import os
import duckdb
import pandas as pd
from typing import Any, Dict, List, Optional
from src.tools.base import BaseTool, ToolRegistry
from src.database.manager import DatabaseManager
from src.database.standardizer import ChemicalStandardizer
from src.database.fetchers import DGSanteFetcher, IFRAFetcher

class UpdateRegulatoryDatabaseTool(BaseTool):
    """
    Updates regulatory tables (IFRA, EU Flavorings) from external sources.
    Uses a staging/atomic swap strategy to ensure data integrity.
    """

    @property
    def name(self) -> str:
        return "update_regulatory_database"

    @property
    def description(self) -> str:
        return (
            "Updates regulatory information from external API sources (IFRA, DG SANTE). "
            "Implements a staging strategy to prevent data corruption during updates. "
            "Use this to keep the agent's regulatory knowledge current. "
            "For IFRA, you can provide a local file_path to an Excel/CSV file."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "enum": ["IFRA", "DG_SANTE"],
                    "description": "The regulatory source to update from.",
                },
                "file_path": {
                    "type": "string",
                    "description": "Optional path to a local file (required for IFRA Excel updates).",
                },
                "force_full_refresh": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether to perform a full reload of the data source.",
                }
            },
            "required": ["source"],
        }

    def execute(self, source: str, file_path: Optional[str] = None, force_full_refresh: bool = False) -> Dict[str, Any]:
        db = DatabaseManager()
        standardizer = ChemicalStandardizer()
        
        try:
            # 1. Fetch Data using specialized Fetchers
            if source == "IFRA":
                fetcher = IFRAFetcher()
                df = fetcher.fetch(file_path=file_path)
                target_table = "ifra_standards"
            elif source == "DG_SANTE":
                fetcher = DGSanteFetcher()
                df = fetcher.fetch()
                target_table = "eu_flavorings"
            else:
                return {"error": f"Source {source} not yet implemented."}

            if df.empty:
                return {"error": f"No data retrieved from {source}."}

            # 2. Process and Standardize (Cross-Reference Preparation)
            processed_rows = []
            xref_rows = []
            
            for _, row in df.iterrows():
                # Handle potential missing SMILES or CAS
                smiles = row.get('smiles', None)
                cas = row.get('cas_no', None)
                
                if not cas and not smiles:
                    continue
                
                cas_clean = standardizer.clean_cas(str(cas)) if cas else None
                ikey = standardizer.get_inchikey(smiles) if smiles else None
                
                # Cross-Reference Record
                if ikey:
                    xref_rows.append({
                        "inchikey": ikey,
                        "smiles": smiles,
                        "cas_no": str(cas) if cas else None,
                        "cas_no_clean": cas_clean,
                        "chemical_name": str(row.get('chemical_name', row.get('substance_name', 'Unknown'))),
                        "updated_at": pd.Timestamp.now()
                    })
                
                # Table Specific Logic
                if source == "IFRA":
                    processed_rows.append({
                        "inchikey": ikey,
                        "category_code": str(row['category_code']),
                        "max_concentration_pct": float(row['max_concentration_pct']),
                        "restriction_type": str(row['restriction_type']),
                        "source": f"IFRA (Updated {pd.Timestamp.now().date()})"
                    })
                elif source == "DG_SANTE":
                    processed_rows.append({
                        "fl_no": str(row.get('fl_no', '')),
                        "inchikey": ikey,
                        "restrictions": str(row.get('restrictions', '')),
                        "conditions_of_use": str(row.get('conditions_of_use', '')),
                        "status": str(row.get('status', 'Active')),
                        "source": str(row.get('source', 'DG SANTE'))
                    })

            xref_df = pd.DataFrame(xref_rows).drop_duplicates(subset=['inchikey']) if xref_rows else pd.DataFrame()
            final_df = pd.DataFrame(processed_rows)

            # 3. Atomic Swap using Staging Tables
            with db.get_connection(read_only=False) as conn:
                # Update XREF if we have new data
                if not xref_df.empty:
                    conn.execute("CREATE TEMP TABLE stg_xref AS SELECT * FROM xref_df")
                    conn.execute("""
                        INSERT INTO compound_cross_reference (inchikey, smiles, cas_no, cas_no_clean, chemical_name, updated_at)
                        SELECT inchikey, smiles, cas_no, cas_no_clean, chemical_name, updated_at FROM stg_xref 
                        ON CONFLICT (inchikey) DO UPDATE SET 
                            smiles = COALESCE(excluded.smiles, compound_cross_reference.smiles),
                            cas_no = COALESCE(excluded.cas_no, compound_cross_reference.cas_no),
                            cas_no_clean = COALESCE(excluded.cas_no_clean, compound_cross_reference.cas_no_clean),
                            chemical_name = COALESCE(excluded.chemical_name, compound_cross_reference.chemical_name),
                            updated_at = excluded.updated_at
                    """)
                
                # Update Target Table (STAGING logic)
                stg_table_name = f"stg_{target_table}"
                conn.execute(f"DROP TABLE IF EXISTS {stg_table_name}")
                conn.execute(f"CREATE TABLE {stg_table_name} AS SELECT * FROM final_df")
                db.atomic_swap(stg_table_name, target_table)

            # 4. Audit Log
            db.log_audit(source=source, event_type="UPDATE", records=len(final_df), status="SUCCESS")

            return {
                "status": "success",
                "source": source,
                "records_updated": len(final_df),
                "summary": f"Successfully updated {source} database with {len(final_df)} entries."
            }

        except Exception as e:
            db.log_audit(source=source, event_type="UPDATE", records=0, status="FAILED", error=str(e))
            return {"error": f"Database update failed: {str(e)}"}

# Register Tool
ToolRegistry.register(UpdateRegulatoryDatabaseTool())
