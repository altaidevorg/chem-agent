import pytest
from src.skills.rdkit_skills import (
    ResolveNameToSmilesSkill,
    CalculateMolecularPropertiesSkill,
    CalculateMolecularSimilaritySkill,
    FindMaximumCommonSubstructureSkill,
    InterpretSmartsSkill,
    DeconstructCoreAndSidechainsSkill,
    GenerateMoleculeImageSkill,
    FetchChemicalSafetyDataSkill,
    SearchSubstructureSkill,
    SearchAdvancedSubstructureSkill,
    CanonicalizeAndValidateSmilesSkill,
    GetMolecularFormulaAndChargeSkill,
    ConvertSmilesToInchiSkill,
    CountHeavyAtomsAndRingsSkill,
    DetectFunctionalGroupsSkill,
    ResolveSmilesToNameSkill
)
import os
import shutil

def test_generate_molecule_image():
    skill = GenerateMoleculeImageSkill()
    smiles = "CCO"
    file_path = "output/test_ethanol.png"
    
    # Ensure output directory exists
    os.makedirs("output", exist_ok=True)
    
    result = skill.execute(smiles=smiles, file_path=file_path)
    assert result["status"] == "success"
    assert os.path.exists(file_path)
    
    # Cleanup
    if os.path.exists(file_path):
        os.remove(file_path)

def test_fetch_chemical_safety_data():
    skill = FetchChemicalSafetyDataSkill()
    # Test with a well-known molecule
    result = skill.execute(molecule_name="Benzene")
    assert "status" in result
    if result.get("status") == "success":
        assert "hazard_statements" in result
        assert "signal_word" in result
    else:
        # PubChem API might be flaky or rate-limited in CI
        assert "error" in result

def test_search_substructure():
    skill = SearchSubstructureSkill()
    # Ethanol contains a C-O bond
    result = skill.execute(smiles="CCO", pattern="CO")
    assert result["has_match"] is True
    assert result["match_count"] > 0

def test_search_advanced_substructure():
    skill = SearchAdvancedSubstructureSkill()
    # Toluene (Cc1ccccc1) with benzene pattern and alkyl constraint on the methyl group? 
    # Actually the constraint is on the pattern atom.
    # Pattern: [c]C (benzene carbon attached to another carbon)
    # Let's use a simpler one: C-C where the second C must be alkyl.
    result = skill.execute(smiles="CCO", pattern="CC", constraint_atom_idx=1, query_type="alkyl")
    assert result["total_filtered_matches"] > 0

def test_canonicalize_and_validate_smiles():
    skill = CanonicalizeAndValidateSmilesSkill()
    # Non-canonical ethanol
    result = skill.execute(smiles="OCC")
    assert result["is_valid"] is True
    assert result["canonical_smiles"] == "CCO"
    
    # Invalid SMILES
    result_invalid = skill.execute(smiles="INVALID")
    assert result_invalid["is_valid"] is False

def test_get_molecular_formula_and_charge():
    skill = GetMolecularFormulaAndChargeSkill()
    # Ethanol: C2H6O
    result = skill.execute(smiles="CCO")
    assert result["status"] == "success"
    assert "C2H6O" in result["molecular_formula"]
    assert result["net_charge"] == 0

def test_convert_smiles_to_inchi():
    skill = ConvertSmilesToInchiSkill()
    # Ethanol
    result = skill.execute(smiles="CCO")
    assert result["status"] == "success"
    assert "InChI=" in result["inchi"]
    assert result["inchikey"] is not None

def test_count_heavy_atoms_and_rings():
    skill = CountHeavyAtomsAndRingsSkill()
    # Benzene: 6 heavy atoms, 1 ring
    result = skill.execute(smiles="c1ccccc1")
    assert result["status"] == "success"
    assert result["heavy_atom_count"] == 6
    assert result["total_ring_count"] == 1

def test_detect_functional_groups():
    skill = DetectFunctionalGroupsSkill()
    # Ethanol has an alcohol group
    result = skill.execute(smiles="CCO")
    assert result["status"] == "success"
    assert result["functional_groups"]["alcohol"]["present"] is True

def test_resolve_smiles_to_name():
    skill = ResolveSmilesToNameSkill()
    # Ethanol SMILES
    result = skill.execute(smiles="CCO")
    assert "status" in result
    if result.get("status") == "success":
        assert "ethanol" in result["common_name"].lower() or "ethanol" in result["iupac_name"].lower()
    else:
        assert "error" in result

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
