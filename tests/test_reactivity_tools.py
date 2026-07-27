# tests/test_reactivity_tools.py
import pytest
from src.tools.rdkit_tools import AuditChemicalCompatibilityTool

def test_audit_schiff_base_risk():
    tool = AuditChemicalCompatibilityTool()
    # Vanillin (Aldehyde) + Methyl anthranilate (Primary Amine) -> Classic Schiff Base pair
    # Vanillin: COc1cc(C=O)ccc1O
    # Methyl anthranilate: COC(=O)c1ccccc1N
    smiles_list = ["COc1cc(C=O)ccc1O", "COC(=O)c1ccccc1N"]
    result = tool.execute(smiles_list)
    
    assert result["status"] == "success"
    risks = result["risks_detected"]
    # Check if Schiff Base rule is triggered
    schiff_risks = [r for r in risks if r["rule_id"] == "R1_SCHIFF_BASE"]
    assert len(schiff_risks) > 0
    assert "discoloration" in schiff_risks[0]["consequence"].lower()

def test_audit_acetal_risk():
    tool = AuditChemicalCompatibilityTool()
    # Benzaldehyde (Aldehyde) + Ethanol (Alcohol)
    smiles_list = ["Cc1ccccc1C=O", "CCO"]
    result = tool.execute(smiles_list)
    
    assert result["status"] == "success"
    acetal_risks = [r for r in result["risks_detected"] if r["rule_id"] == "R2_ACETAL"]
    assert len(acetal_risks) > 0

def test_audit_oxidation_risk():
    tool = AuditChemicalCompatibilityTool()
    # Limonene (Terpene)
    smiles_list = ["CC1=CCC(CC1)C(=C)C"]
    result = tool.execute(smiles_list)
    
    assert result["status"] == "success"
    ox_risks = [r for r in result["risks_detected"] if r["rule_id"] == "R4_OXIDATION"]
    assert len(ox_risks) > 0

def test_audit_no_risk():
    tool = AuditChemicalCompatibilityTool()
    # Water and Methane (no functional groups in our list)
    smiles_list = ["O", "C"]
    result = tool.execute(smiles_list)
    assert result["status"] == "success"
    assert len(result["risks_detected"]) == 0
