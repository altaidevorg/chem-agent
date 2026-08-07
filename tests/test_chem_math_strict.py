# tests/test_chem_math_strict.py
import pytest
from src.tools.chem_math_tools import CalculateDilutionTool, CalculateDosageTool, CalculateVocContentTool, CalculateStoichiometryTool

def test_dilution_strict_params():
    tool = CalculateDilutionTool()
    # C1 (uppercase) should NOT be recognized now
    result = tool.execute(C1=10, u1="mg/L", c2=1, u2="mg/L", v2=100, uv2="mL")
    assert result["status"] == "error"
    assert "Exactly one parameter" in result["error"]

def test_dilution_unsupported_unit():
    tool = CalculateDilutionTool()
    # "vol%" is not supported
    with pytest.raises(ValueError, match="Unsupported concentration unit"):
        tool._to_standard_unit(5.0, "vol%")

def test_dosage_unsupported_unit():
    tool = CalculateDosageTool()
    # "uL" is not supported for batch_unit in CalculateDosageTool
    result = tool.execute(batch_size=500, batch_unit="uL", target_dosage=2.5)
    assert result["status"] == "error"
    assert "Unsupported batch_unit" in result["error"]

def test_voc_missing_smiles():
    tool = CalculateVocContentTool()
    # One component missing SMILES
    components = [{"smiles": "", "mass_g": 100}]
    result = tool.execute(components=components)
    assert result["status"] == "error"
    assert "missing a valid 'smiles' string" in result["error"]

def test_stoichiometry_strict_smiles():
    tool = CalculateStoichiometryTool()
    # 'molecular_weight' should NOT be recognized now
    result = tool.execute(molecular_weight=180.16, mass=18.016, mass_unit="g")
    assert result["status"] == "error"
    assert "Missing required 'smiles' argument" in result["error"]
