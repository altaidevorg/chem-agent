# src/tools/regulatory_tools.py
import os
import duckdb
import pandas as pd
from typing import Any, Dict, List, Optional
from rdkit import Chem
from rdkit.Chem import rdBase
from src.tools.base import BaseTool, ToolRegistry
from src.database.manager import DatabaseManager
from src.database.standardizer import ChemicalStandardizer
from src.database.fetchers import DGSanteFetcher, IFRAFetcher

class CheckRegulatoryComplianceTool(BaseTool):
    """
    Checks a list of chemicals against the unified knowledge database 
    (IFRA and EU 1334/2008) for restrictions or bans.
    """

    @property
    def name(self) -> str:
        return "check_regulatory_compliance"

    @property
    def description(self) -> str:
        return "Checks formulation components against IFRA (Fragrance) and EU 1334/2008 (Food) regulations using the knowledge database. Essential for legal safety audits."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "queries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "A list of common names, chemical names, or CAS numbers to check."
                }
            },
            "required": ["queries"]
        }

    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Checks a list of names or CAS numbers against regulatory data.
        Uses InChIKey-based resolution and JOIN queries for high accuracy.
        """
        queries = kwargs.get("queries")
        if not queries:
            return {"status": "error", "error": "Missing required parameter 'queries'."}

        try:
            from src.database.manager import DatabaseManager
            from src.database.standardizer import ChemicalStandardizer
            
            db = DatabaseManager()
            standardizer = ChemicalStandardizer()
            
            with db.get_connection(read_only=True) as conn:
                # 1. Load structural restrictions once
                structural_rules = conn.execute("SELECT * FROM structural_restrictions").df().to_dict('records')
                structural_patterns = []
                for r in structural_rules:
                    patt = Chem.MolFromSmarts(r['smarts_pattern'])
                    if patt:
                        structural_patterns.append({"pattern": patt, "metadata": r})

                results = []
                
                for query in queries:
                    # Identifier Resolution Strategy
                    ikey = None
                    smiles = None
                    resolved_name = query
                    
                    # A. Check if query is already SMILES
                    if "[" in query or "=" in query or "(" in query:
                        ikey = standardizer.get_inchikey(query)
                        smiles = query
                    
                    # B. Check if query is CAS
                    is_cas = "-" in query and any(char.isdigit() for char in query)
                    cas_clean = standardizer.clean_cas(query) if is_cas else None
                    
                    # C. Database Lookup (Cross-Reference)
                    if ikey:
                        xref_data = conn.execute(
                            "SELECT * FROM compound_cross_reference WHERE inchikey = ?", [ikey]
                        ).df()
                    elif is_cas:
                        xref_data = conn.execute(
                            "SELECT * FROM compound_cross_reference WHERE cas_no_clean = ?", [cas_clean]
                        ).df()
                    else:
                        # Search by name
                        xref_data = conn.execute(
                            "SELECT * FROM compound_cross_reference WHERE chemical_name ILIKE ?", [f"%{query}%"]
                        ).df()
                    
                    if not xref_data.empty:
                        ikey = xref_data.iloc[0]['inchikey']
                        smiles = xref_data.iloc[0]['smiles']
                        resolved_name = xref_data.iloc[0]['chemical_name']
                    
                    # 2. Regulatory JOIN Queries
                    ifra_res = pd.DataFrame()
                    eu_res = pd.DataFrame()
                    
                    if ikey:
                        # IFRA JOIN
                        ifra_res = conn.execute("""
                            SELECT i.*, x.chemical_name, x.cas_no 
                            FROM ifra_standards i
                            JOIN compound_cross_reference x ON i.inchikey = x.inchikey
                            WHERE i.inchikey = ?
                        """, [ikey]).df()
                        
                        # EU JOIN
                        eu_res = conn.execute("""
                            SELECT e.*, x.chemical_name, x.cas_no 
                            FROM eu_flavorings e
                            JOIN compound_cross_reference x ON e.inchikey = x.inchikey
                            WHERE e.inchikey = ?
                        """, [ikey]).df()
                    elif is_cas:
                        # Fallback for CAS only (if InChIKey not in DB)
                        eu_res = conn.execute("SELECT * FROM eu_flavorings WHERE fl_no IN (SELECT fl_no FROM compound_cross_reference WHERE cas_no_clean = ?)", [cas_clean]).df()

                    mol_summary = {
                        "query": query,
                        "resolved_name": resolved_name,
                        "inchikey": ikey,
                        "ifra_status": "Not Found / GRAS" if ifra_res.empty else "RESTRICTED/BANNED",
                        "eu_status": "Not Found / GRAS" if eu_res.empty else "RESTRICTED/BANNED",
                        "details": [],
                        "structural_class_matches": []
                    }
                    
                    # 3. Structural Screening (SMARTS)
                    if smiles:
                        with rdBase.BlockLogs():
                            mol = Chem.MolFromSmiles(smiles)
                        if mol:
                            for item in structural_patterns:
                                if mol.HasSubstructMatch(item["pattern"]):
                                    mol_summary["structural_class_matches"].append({
                                        "class": item["metadata"]["class_name"],
                                        "severity": item["metadata"]["severity"],
                                        "description": item["metadata"]["description"]
                                    })

                    # Populate details
                    if not ifra_res.empty:
                        for _, row in ifra_res.iterrows():
                            mol_summary["details"].append({
                                "source": "IFRA 51st Amendment",
                                "category": row['category_code'],
                                "limit": row['max_concentration_pct'],
                                "type": row['restriction_type']
                            })
                    
                    if not eu_res.empty:
                        for _, row in eu_res.iterrows():
                            mol_summary["details"].append({
                                "source": "EU 1334/2008",
                                "fl_no": row['fl_no'],
                                "status": row['status'],
                                "restrictions": row['restrictions']
                            })
                    
                    results.append(mol_summary)
                
                return {
                    "total_checked": len(queries),
                    "compliance_report": results,
                    "status": "success",
                    "notice": "JOIN queries on InChIKey used for maximum regulatory precision."
                }
        except Exception as e:
            return {"error": f"Regulatory check failed: {str(e)}"}

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

    def execute(self, **kwargs) -> Dict[str, Any]:
        source = kwargs.get("source")
        file_path = kwargs.get("file_path")
        force_full_refresh = kwargs.get("force_full_refresh", False)
        workspace = kwargs.get("workspace")
        
        db = DatabaseManager()
        standardizer = ChemicalStandardizer()
        
        try:
            # 1. Resolve path via workspace if provided
            if workspace and file_path:
                try:
                    file_path = str(workspace.resolve(file_path))
                except PermissionError as e:
                    return {"error": f"Workspace access denied: {str(e)}"}

            # 2. Fetch Data using specialized Fetchers
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
ToolRegistry.register(CheckRegulatoryComplianceTool())
ToolRegistry.register(UpdateRegulatoryDatabaseTool())
