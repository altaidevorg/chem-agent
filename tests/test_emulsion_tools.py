# tests/test_emulsion_tools.py
import pytest
from src.tools.rdkit_tools import CalculateEmulsionPropertiesTool

def test_calculate_emulsion_properties_hydrophilic():
    tool = CalculateEmulsionPropertiesTool()
    # Glycerol (Very hydrophilic)
    # SMILES: OCC(O)CO
    result = tool.execute(smiles="OCC(O)CO")
    assert result["status"] == "success"
    # Glycerol is hydrophilic, but its HLB depends on the mass ratio.
    # In our simplified Griffin, OH groups are counted.
    assert result["hlb_value"] > 10
    assert result["logp"] < 0

def test_calculate_emulsion_properties_lipophilic():
    tool = CalculateEmulsionPropertiesTool()
    # Limonene (Very lipophilic)
    # SMILES: CC1=CCC(CC1)C(=C)C
    result = tool.execute(smiles="CC1=CCC(CC1)C(=C)C")
    assert result["status"] == "success"
    # Limonene should have a very low HLB and high LogP
    assert result["hlb_value"] < 5
    assert result["logp"] > 3

def test_calculate_emulsion_properties_surfactant():
    tool = CalculateEmulsionPropertiesTool()
    # Simple fatty acid ester (e.g., Glyceryl monostearate - simplified)
    # SMILES: CCCCCCCCCCCCCCCCCC(=O)OCC(O)CO
    result = tool.execute(smiles="CCCCCCCCCCCCCCCCCC(=O)OCC(O)CO")
    assert result["status"] == "success"
    # Should be in the middle-ish emulsifier range
    assert 3 < result["hlb_value"] < 10

def test_calculate_emulsion_invalid_smiles():
    tool = CalculateEmulsionPropertiesTool()
    result = tool.execute(smiles="INVALID")
    assert "error" in result
