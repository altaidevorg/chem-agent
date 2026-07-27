# tests/test_rdkit_tools.py
import pytest
from src.tools.rdkit_tools import (
    ResolveNameToSmilesTool,
    CalculateMolecularPropertiesTool,
    CalculateMolecularSimilarityTool,
    FindMaximumCommonSubstructureTool,
    InterpretSmartsTool,
    DeconstructCoreAndSidechainsTool,
    GenerateMoleculeImageTool,
    FetchChemicalSafetyDataTool,
    SearchSubstructureTool,
    SearchAdvancedSubstructureTool,
    CanonicalizeAndValidateSmilesTool,
    GetMolecularFormulaAndChargeTool,
    ConvertSmilesToInchiTool,
    CountHeavyAtomsAndRingsTool,
    DetectFunctionalGroupsTool,
    ResolveSmilesToNameTool,
    CalculateHansenParametersTool,
    EstimatePkaAndLogDTool
)
import os

def test_generate_molecule_image():
    tool = GenerateMoleculeImageTool()
    smiles = "CCO"
    file_path = "output/test_ethanol.png"
    os.makedirs("output", exist_ok=True)
    result = tool.execute(smiles=smiles, file_path=file_path)
    assert result["status"] == "success"
    if os.path.exists(file_path):
        os.remove(file_path)

def test_fetch_chemical_safety_data():
    tool = FetchChemicalSafetyDataTool()
    result = tool.execute(molecule_name="Benzene")
    assert "status" in result

def test_resolve_name_to_smiles():
    tool = ResolveNameToSmilesTool()
    result = tool.execute(molecule_name="Aspirin")
    assert result["status"] == "success"
    assert "CC(=O)OC1=CC=CC=C1C(=O)O" in result["smiles"]

def test_calculate_molecular_properties():
    tool = CalculateMolecularPropertiesTool()
    result = tool.execute(smiles="CCO")
    assert result["parsing_status"] == "Success"
    assert result["molecular_weight"] > 40.0

def test_calculate_molecular_similarity():
    tool = CalculateMolecularSimilarityTool()
    res = tool.execute(smiles1="CCO", smiles2="CCC")
    assert "tanimoto_similarity" in res

def test_search_substructure():
    tool = SearchSubstructureTool()
    res = tool.execute(smiles="c1ccccc1", pattern="c1ccccc1")
    assert res["has_match"] is True

def test_find_maximum_common_substructure():
    tool = FindMaximumCommonSubstructureTool()
    res = tool.execute(smiles_list=["CCO", "CCC"])
    assert "smarts" in res

def test_canonicalize_and_validate_smiles():
    tool = CanonicalizeAndValidateSmilesTool()
    res = tool.execute(smiles="C1=CC=CC=C1")
    assert res["canonical_smiles"] == "c1ccccc1"

def test_get_molecular_formula_and_charge():
    tool = GetMolecularFormulaAndChargeTool()
    res = tool.execute(smiles="[Na+].[Cl-]")
    assert "ClNa" in res["molecular_formula"]

def test_convert_smiles_to_inchi():
    tool = ConvertSmilesToInchiTool()
    res = tool.execute(smiles="CCO")
    assert "InChI" in res["inchi"]

def test_count_heavy_atoms_and_rings():
    tool = CountHeavyAtomsAndRingsTool()
    res = tool.execute(smiles="c1ccccc1")
    assert res["heavy_atom_count"] == 6
    assert res["total_ring_count"] == 1

def test_detect_functional_groups():
    tool = DetectFunctionalGroupsTool()
    res = tool.execute(smiles="CC(=O)O")
    assert res["functional_groups"]["carboxylic_acid"]["present"] is True

def test_resolve_smiles_to_name():
    tool = ResolveSmilesToNameTool()
    res = tool.execute(smiles="CC(=O)OC1=CC=CC=C1C(=O)O")
    assert "status" in res

def test_search_advanced_substructure():
    tool = SearchAdvancedSubstructureTool()
    res = tool.execute(smiles="CCC", pattern="CC", constraint_atom_idx=1, query_type="alkyl")
    assert "total_filtered_matches" in res

def test_interpret_smarts_pattern():
    tool = InterpretSmartsTool()
    result = tool.execute(smarts="c1ccccc1")
    assert "Benzene ring" in result["identified_motifs"]

def test_deconstruct_core_and_sidechains():
    tool = DeconstructCoreAndSidechainsTool()
    result = tool.execute(smiles="CCO", core_smarts_or_smiles="CO")
    assert result["status"] == "success"

def test_calculate_hansen_parameters():
    tool = CalculateHansenParametersTool()
    result = tool.execute("CCO")
    assert result["status"] == "success"
    assert "delta_d" in result
    assert "delta_h" in result
    assert result["delta_h"] > 10.0

def test_estimate_pka_and_logd():
    tool = EstimatePkaAndLogDTool()
    # Test Benzoic Acid (acidic)
    res = tool.execute("c1ccccc1C(=O)O", ph=7.4)
    assert res["status"] == "success"
    assert res["molecule_type"] == "Acidic"
    assert res["logd_at_ph"] < res["logp_neutral"] # LogD should be lower at pH > pKa
    
    # Test Ethylamine (basic)
    res_base = tool.execute("CCN", ph=3.0)
    assert res_base["status"] == "success"
    assert res_base["molecule_type"] == "Basic"
    assert res_base["logd_at_ph"] < res_base["logp_neutral"]
