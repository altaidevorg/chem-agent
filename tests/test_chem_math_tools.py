# tests/test_chem_math_tools.py
import pytest
from src.tools.chem_math_tools import CalculateDilutionTool, CalculateStoichiometryTool

def test_calculate_dilution_simple():
    tool = CalculateDilutionTool()
    # C1=10, V1=?, C2=1, V2=100 => V1 should be 10
    result = tool.execute(c1=10, u1="mg/L", v1=None, uv1="mL", c2=1, u2="mg/L", v2=100, uv2="mL")
    assert result["status"] == "success"
    assert result["result"]["v1"] == 10.0

def test_calculate_dilution_with_conversion():
    tool = CalculateDilutionTool()
    # Ethanol MW ~46.07
    # C1=1M, V1=?, C2=460.7 mg/L (which is 0.01M), V2=1000mL => V1 should be 10mL
    smiles = "CCO" 
    result = tool.execute(
        c1=1.0, u1="M", 
        v1=None, uv1="mL", 
        c2=460.7, u2="mg/L", 
        v2=1000, uv2="mL",
        smiles=smiles
    )
    assert result["status"] == "success"
    # 1M = 46070 mg/L. 
    # V1 = (460.7 * 1000) / 46070 = 10 mL
    assert abs(result["result"]["v1"] - 10.0) < 0.1

def test_calculate_stoichiometry_mass_to_mol():
    tool = CalculateStoichiometryTool()
    # Aspirin (C9H8O4) MW ~180.16
    smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"
    result = tool.execute(smiles=smiles, mass=1.8016, mass_unit="g", moles_unit="mmol")
    assert result["status"] == "success"
    assert abs(result["calculated"]["moles"] - 10.0) < 0.1

def test_calculate_stoichiometry_mol_to_mass():
    tool = CalculateStoichiometryTool()
    # Water MW ~18.02
    smiles = "O"
    result = tool.execute(smiles=smiles, moles=1, moles_unit="mol", mass_unit="g")
    assert result["status"] == "success"
    assert abs(result["calculated"]["mass"] - 18.02) < 0.1
