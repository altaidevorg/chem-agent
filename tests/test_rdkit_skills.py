import pytest
from src.skills.rdkit_skills import (
    ResolveNameToSmilesSkill,
    CalculateMolecularPropertiesSkill,
    CalculateMolecularSimilaritySkill,
    FindMaximumCommonSubstructureSkill,
    InterpretSmartsSkill,
    DeconstructCoreAndSidechainsSkill
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

def test_find_maximum_common_substructure():
    skill = FindMaximumCommonSubstructureSkill()
    # Case 1: Simple alcohols
    result = skill.execute(smiles_list=["CCO", "CCCO"])
    assert "smarts" in result
    assert result["num_atoms"] > 0
    
    # Case 2: Ibuprofen and Naproxen
    smiles_list = [
        "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O",
        "C[C@@H](C1=CC2=C(C=C1)C=C(C=C2)OC)C(=O)O"
    ]
    result = skill.execute(smiles_list=smiles_list)
    assert result["status"] == "success"
    assert result["num_atoms"] > 0

def test_interpret_smarts_pattern():
    skill = InterpretSmartsSkill()
    # Case 1: Benzene ring
    result = skill.execute(smarts="c1ccccc1")
    assert result["status"] == "success"
    assert "Benzene ring" in result["identified_motifs"]
    
    # Case 2: Carboxylic acid
    result = skill.execute(smarts="C(=O)O")
    assert result["status"] == "success"
    assert "Carboxylic acid group" in result["identified_motifs"]

def test_deconstruct_core_and_sidechains():
    skill = DeconstructCoreAndSidechainsSkill()
    # Case 1: Ethanol with CO core
    result = skill.execute(smiles="CCO", core_smarts_or_smiles="CO")
    assert result["status"] == "success"
    assert len(result["isolated_sidechains"]) > 0
    
    # Case 2: Toluene with Benzene core
    result = skill.execute(smiles="Cc1ccccc1", core_smarts_or_smiles="c1ccccc1")
    assert result["status"] == "success"
    assert "*C" in result["isolated_sidechains"]
