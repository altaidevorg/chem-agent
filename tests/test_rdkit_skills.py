import pytest
from src.skills.rdkit_skills import (
    ResolveNameToSmilesSkill,
    CalculateMolecularPropertiesSkill,
    CalculateMolecularSimilaritySkill
)

def test_resolve_name_to_smiles():
    skill = ResolveNameToSmilesSkill()
    # Test with a common molecule
    result = skill.execute(molecule_name="Water")
    assert "smiles" in result
    assert result["smiles"] == "O"

def test_calculate_molecular_properties():
    skill = CalculateMolecularPropertiesSkill()
    # Aspirin SMILES
    aspirin_smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"
    result = skill.execute(smiles=aspirin_smiles)
    
    assert "molecular_weight" in result
    assert pytest.approx(result["molecular_weight"], 0.1) == 180.1
    assert "log_p" in result

def test_molecular_similarity():
    skill = CalculateMolecularSimilaritySkill()
    # Ethanol and Isopropanol
    smiles1 = "CCO"
    smiles2 = "CC(O)C"
    result = skill.execute(smiles1=smiles1, smiles2=smiles2)
    
    assert "tanimoto_similarity" in result
    assert 0 <= result["tanimoto_similarity"] <= 1.0
