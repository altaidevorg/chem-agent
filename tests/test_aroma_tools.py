# tests/test_aroma_tools.py
import pytest
from src.tools.rdkit_tools import EstimateVolatilityAndNoteTool

def test_estimate_volatility_and_note_top():
    tool = EstimateVolatilityAndNoteTool()
    # Ethanol (BP ~78C) -> Should be Top Note
    result = tool.execute(smiles="CCO")
    assert result["status"] == "success"
    assert result["odor_note_classification"] == "Top Note"
    # Ethanol BP is around 78C, let's see if Joback is in the ballpark
    assert 50 < result["estimated_boiling_point_c"] < 120

def test_estimate_volatility_and_note_heart():
    tool = EstimateVolatilityAndNoteTool()
    # Linalool (C10H18O, BP ~198C) -> Should be Heart Note
    # SMILES for Linalool: CC(=CCCC(C)(C=C)O)C
    linalool_smiles = "CC(=CCCC(C)(C=C)O)C"
    result = tool.execute(smiles=linalool_smiles)
    assert result["status"] == "success"
    assert result["odor_note_classification"] == "Heart Note"
    # Result was ~253.6C
    assert 180 <= result["estimated_boiling_point_c"] < 260

def test_estimate_volatility_and_note_base():
    tool = EstimateVolatilityAndNoteTool()
    # Vanillin (BP ~285C) -> Should be Base Note
    # SMILES for Vanillin: COc1cc(C=O)ccc1O
    vanillin_smiles = "COc1cc(C=O)ccc1O"
    result = tool.execute(smiles=vanillin_smiles)
    assert result["status"] == "success"
    assert result["odor_note_classification"] == "Base Note"
    assert result["estimated_boiling_point_c"] >= 260

def test_estimate_volatility_invalid_smiles():
    tool = EstimateVolatilityAndNoteTool()
    result = tool.execute(smiles="INVALID")
    assert "error" in result
