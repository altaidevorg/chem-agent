# tests/test_structure_tools.py
import pytest
from src.tools.structure_tools import StandardizeMoleculeTool

def test_salt_stripping():
    tool = StandardizeMoleculeTool()
    # Sodium Acetate: CC(=O)[O-].[Na+]
    smiles = "CC(=O)[O-].[Na+]"
    result = tool.execute(smiles=smiles, remove_salts=True, neutralize=True)
    assert result["status"] == "success"
    # Should be Acetic acid (standardized/neutralized)
    assert result["standardized_smiles"] == "CC(=O)O"
    assert "Removed salts/solvents (stripped to parent)" in result["changes_made"]
    assert result["mw_difference"] > 20 # Na weight is ~23

def test_tautomer_canonicalization():
    tool = StandardizeMoleculeTool()
    # Keto form: CC(=O)C
    # Enol form: CC(O)=C (Propen-2-ol)
    enol = "CC(O)=C"
    result = tool.execute(smiles=enol, canonicalize_tautomer=True)
    assert result["status"] == "success"
    # RDKit canonical tautomer for acetone is the keto form
    assert result["standardized_smiles"] == "CC(C)=O"
    assert "Converted to canonical tautomer" in result["changes_made"]

def test_neutralization():
    tool = StandardizeMoleculeTool()
    # Ammonium: [NH4+]
    smiles = "[NH4+]"
    result = tool.execute(smiles=smiles, neutralize=True)
    assert result["status"] == "success"
    assert result["standardized_smiles"] == "N" # Ammonia
    assert "Neutralized formal charges" in result["changes_made"]
