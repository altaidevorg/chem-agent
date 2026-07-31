# src/database/standardizer.py
import re
from rdkit import Chem
from typing import Optional

class ChemicalStandardizer:
    """
    Standardizes identifiers for cross-referencing across different databases.
    Ensures CAS-123-45-6 matches 123456.
    """

    @staticmethod
    def clean_cas(cas_no: str) -> str:
        """Removes dashes and spaces from CAS numbers."""
        if not cas_no:
            return ""
        return re.sub(r'[^0-9]', '', cas_no)

    @staticmethod
    def get_inchikey(smiles: str) -> Optional[str]:
        """Generates the 27-char InChIKey from a SMILES string."""
        if not smiles:
            return None
        try:
            mol = Chem.MolFromSmiles(smiles)
            if mol:
                # Remove salts and standardize before hashing
                from rdkit.Chem.MolStandardize import rdMolStandardize
                clean_mol = rdMolStandardize.Cleanup(mol)
                return Chem.MolToInchiKey(clean_mol)
            return None
        except:
            return None

    @staticmethod
    def is_valid_cas(cas_no: str) -> bool:
        """Simple regex validation for CAS format."""
        return bool(re.match(r'^\d{2,7}-\d{2}-\d$', cas_no))
