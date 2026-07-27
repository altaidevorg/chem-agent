# src/tools/structure_tools.py
from typing import Any, Dict, List, Optional
from rdkit import Chem
from rdkit.Chem import rdBase, Descriptors
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
            "neutralizes charges, and finds the canonical tautomer. Essential for duplicate "
            "detection, validation, and accurate physicochemical property estimation."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "smiles": {"type": "string", "description": "The raw SMILES string to validate and standardize."},
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
            "required": ["smiles"]
        }

    def execute(
        self, 
        smiles: str, 
        remove_salts: bool = True, 
        neutralize: bool = True, 
        canonicalize_tautomer: bool = True
    ) -> Dict[str, Any]:
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

            return {
                "status": "success",
                "is_valid": True,
                "original_smiles": original_smiles,
                "standardized_smiles": standardized_smiles,
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
