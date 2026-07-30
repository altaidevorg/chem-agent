# scripts/test_specialized_tools.py
from src.tools.rdkit_tools import CalculateDrugLikenessTool
from src.tools.chem_math_tools import CalculateVocContentTool
import json

def test_drug_likeness():
    print("\n--- Testing Drug-Likeness Tool ---")
    tool = CalculateDrugLikenessTool()
    
    # 1. Ibuprofen (Drug-like)
    ibuprofen_smiles = "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O"
    res1 = tool.execute(ibuprofen_smiles)
    print(f"Ibuprofen: {res1.get('drug_likeness_score')} (Violations: {res1.get('violations', {}).get('total')})")
    
    # 2. A very large non-drug-like molecule (e.g., a long peptide or polymer fragment)
    large_smiles = "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"
    res2 = tool.execute(large_smiles)
    print(f"Large Alkane: {res2.get('drug_likeness_score')} (Violations: {res2.get('violations', {}).get('total')})")

def test_voc_calculation():
    print("\n--- Testing VOC Calculation Tool ---")
    tool = CalculateVocContentTool()
    
    # Mixture: 
    # - Ethanol (VOC, BP ~78C)
    # - Water (Non-organic, but let's see how BP works, usually treated as non-VOC)
    # - Glycerol (High BP, ~290C, should be Non-VOC)
    
    components = [
        {"smiles": "CCO", "mass_g": 50, "density_g_ml": 0.789},  # Ethanol
        {"smiles": "O", "mass_g": 40, "density_g_ml": 1.0},     # Water
        {"smiles": "OCC(O)CO", "mass_g": 10, "density_g_ml": 1.26} # Glycerol
    ]
    
    res = tool.execute(components)
    print(f"Total Mass: {res.get('total_mass_g')}g")
    print(f"VOC Percentage: {res.get('voc_percentage')}%")
    print(f"VOC g/L: {res.get('voc_g_l')} g/L")
    
    print("\nComponent Breakdown:")
    for comp in res.get("component_audit", []):
        print(f"SMILES: {comp['smiles']}, BP: {comp['boiling_point_c']}C, IS_VOC: {comp['is_voc']}")

if __name__ == "__main__":
    test_drug_likeness()
    test_voc_calculation()
