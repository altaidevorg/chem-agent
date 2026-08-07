# src/tools/structure_tools.py
import os
from typing import Any, Dict, List, Optional
from rdkit import Chem
from rdkit.Chem import rdBase, Descriptors, rdMolDescriptors
from rdkit.Chem.MolStandardize import rdMolStandardize
from src.tools.base import BaseTool, ToolRegistry

class StandardizeMoleculeTool(BaseTool):
    """
    Standardizes chemical structures by removing salts, neutralizing charges, 
    and finding the canonical tautomer form.
    """

    @property
    def name(self) -> str:
        return "standardize_molecule"

    @property
    def description(self) -> str:
        return (
            "Standardizes chemical structures and validates SMILES. Removes salts/solvents, "
            "neutralizes charges, and finds the canonical tautomer. Returns standardized SMILES, "
            "InChI, InChIKey, formula, formal charge, and MW difference in a single call. "
            "No need to call other formula or InChI tools alongside this."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "smiles": {"type": "string", "description": "The raw SMILES string to validate and standardize."},
                "molecule_name": {"type": "string", "description": "Optional name of the molecule if SMILES is unknown."},
                "remove_salts": {
                    "type": "boolean", 
                    "description": "Whether to remove salts and solvents (strip to parent molecule). Defaults to True.",
                    "default": True
                },
                "neutralize": {
                    "type": "boolean", 
                    "description": "Whether to neutralize formal charges. Defaults to True.",
                    "default": True
                },
                "canonicalize_tautomer": {
                    "type": "boolean", 
                    "description": "Whether to find the canonical tautomer form. Defaults to True.",
                    "default": True
                }
            },
            "required": []
        }

    def execute(self, **kwargs) -> Dict[str, Any]:
        smiles = kwargs.get("smiles")
        molecule_name = kwargs.get("molecule_name")
        remove_salts = kwargs.get("remove_salts", True)
        neutralize = kwargs.get("neutralize", True)
        canonicalize_tautomer = kwargs.get("canonicalize_tautomer", True)

        # First, try to resolve a valid SMILES using our cross-tool helper
        # We need to import it here or move it to a more central place.
        # Since it's in rdkit_tools, let's do a dynamic import to avoid circular dependencies
        try:
            from src.tools.rdkit_tools import _resolve_smiles_or_name
            smiles_valid, err = _resolve_smiles_or_name(smiles, molecule_name)
            if err:
                return err
            smiles = smiles_valid
        except ImportError:
            # Fallback if rdkit_tools isn't available for some reason
            if not smiles:
                return {"error": "SMILES string is required."}

        try:
            with rdBase.BlockLogs():
                mol = Chem.MolFromSmiles(smiles)
            
            if mol is None:
                return {
                    "is_valid": False,
                    "error": f"The provided string '{smiles}' is not a valid SMILES pattern.",
                    "status": "fail"
                }

            original_smiles = Chem.MolToSmiles(mol, canonical=True)
            original_mw = Descriptors.MolWt(mol)
            
            changes = []
            current_mol = mol

            # 1. Cleanup & Standardization
            current_mol = rdMolStandardize.Cleanup(current_mol)

            # 2. Salt & Fragment Removal
            if remove_salts:
                remover = rdMolStandardize.FragmentRemover()
                mol_before = current_mol
                current_mol = remover.remove(current_mol)
                if Chem.MolToSmiles(current_mol) != Chem.MolToSmiles(mol_before):
                    changes.append("Removed salts/solvents (stripped to parent)")

            # 3. Neutralization (Uncharger)
            if neutralize:
                uncharger = rdMolStandardize.Uncharger()
                mol_before = current_mol
                current_mol = uncharger.uncharge(current_mol)
                if Chem.MolToSmiles(current_mol) != Chem.MolToSmiles(mol_before):
                    changes.append("Neutralized formal charges")

            # 4. Tautomer Canonicalization
            if canonicalize_tautomer:
                enumerator = rdMolStandardize.TautomerEnumerator()
                mol_before = current_mol
                current_mol = enumerator.Canonicalize(current_mol)
                if Chem.MolToSmiles(current_mol) != Chem.MolToSmiles(mol_before):
                    changes.append("Converted to canonical tautomer")

            standardized_smiles = Chem.MolToSmiles(current_mol, canonical=True)
            final_mw = Descriptors.MolWt(current_mol)
            inchi = Chem.MolToInchi(current_mol)
            inchikey = Chem.MolToInchiKey(current_mol)

            # Calculate formula and formal charge
            formula = rdMolDescriptors.CalcMolFormula(current_mol)
            formal_charge = Chem.GetFormalCharge(current_mol)

            return {
                "status": "success",
                "is_valid": True,
                "original_smiles": original_smiles,
                "standardized_smiles": standardized_smiles,
                "formula": formula,
                "formal_charge": formal_charge,
                "inchi": inchi,
                "inchikey": inchikey,
                "original_mw": round(original_mw, 2),
                "final_mw": round(final_mw, 2),
                "mw_difference": round(original_mw - final_mw, 2),
                "changes_made": changes,
                "is_same": original_smiles == standardized_smiles,
                "summary": (
                    f"Validation successful. Standardization complete. "
                    f"{'No structural changes needed.' if not changes else 'Changes: ' + '; '.join(changes) + '.'}"
                )
            }

        except Exception as e:
            return {"error": f"Standardization failed: {str(e)}"}

# Register tool
ToolRegistry.register(StandardizeMoleculeTool())


class ImportAndStandardizeFileTool(BaseTool):
    """
    Imports chemical structures from MOL, SDF, or InChI files, 
    standardizes them, and returns canonical SMILES/InChI.
    """

    @property
    def name(self) -> str:
        return "import_and_standardize_file"

    @property
    def description(self) -> str:
        return (
            "Imports chemical structures from local files (.mol, .sdf, .inchi). "
            "Automatically standardizes the structure (removes salts, neutralizes, tautomers) "
            "and returns clean SMILES and properties. Use this as the entry point for "
            "file-based chemical data."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the chemical file (.mol, .sdf, or .inchi).",
                },
                "remove_salts": {"type": "boolean", "default": True},
                "neutralize": {"type": "boolean", "default": True},
                "canonicalize_tautomer": {
                    "type": "boolean",
                    "description": "Whether to find the canonical tautomer form. Defaults to True.",
                    "default": True,
                },
            },
            "required": ["file_path"],
        }

    def execute(self, **kwargs) -> Dict[str, Any]:
        file_path = kwargs.get("file_path")
        remove_salts = kwargs.get("remove_salts", True)
        neutralize = kwargs.get("neutralize", True)
        canonicalize_tautomer = kwargs.get("canonicalize_tautomer", True)
        workspace = kwargs.get("workspace")
        
        try:
            if workspace:
                try:
                    real_path = workspace.resolve(file_path)
                    file_path = str(real_path)
                except PermissionError as e:
                    return {"error": str(e)}

            if not os.path.exists(file_path):
                return {"error": f"File not found: {file_path}"}

            ext = os.path.splitext(file_path)[1].lower()
            mol = None

            if ext == ".mol" or ext == ".sdf":
                mol = Chem.MolFromMolFile(file_path)
            elif ext == ".inchi":
                with open(file_path, "r") as f:
                    inchi_str = f.read().strip()
                mol = Chem.MolFromInchi(inchi_str)
            else:
                return {
                    "error": f"Unsupported file extension: {ext}. Supported: .mol, .sdf, .inchi"
                }

            if mol is None:
                return {"error": "Failed to parse molecule from file. Invalid format."}

            # Use the core standardization logic
            std_tool = StandardizeMoleculeTool()
            # Convert to SMILES first to use the existing standardization pipeline
            raw_smiles = Chem.MolToSmiles(mol)
            res = std_tool.execute(
                smiles=raw_smiles,
                remove_salts=remove_salts,
                neutralize=neutralize,
                canonicalize_tautomer=canonicalize_tautomer,
            )

            if res.get("status") == "success":
                res["file_imported"] = file_path
                res["input_format"] = ext

            return res

        except Exception as e:
            return {"error": f"Import and standardization failed: {str(e)}"}


ToolRegistry.register(ImportAndStandardizeFileTool())
