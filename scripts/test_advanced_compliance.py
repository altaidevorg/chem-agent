# scripts/test_advanced_compliance.py
from src.tools.regulatory_tools import CheckRegulatoryComplianceTool
from src.tools.chem_math_tools import CalculateVocContentTool
import json

def test_structural_screening():
    print("\n--- Testing SMARTS Structural Screening ---")
    tool = CheckRegulatoryComplianceTool()
    
    # Bis(2-ethylhexyl) phthalate derivative (A Phthalate)
    # Even if this specific name/CAS isn't in our DB, the SMARTS should find it.
    phthalate_smiles = "CCCCC(CC)COC(=O)c1ccccc1C(=O)OCC(CC)CCCC"
    res = tool.execute([phthalate_smiles])
    
    print(f"Query: {phthalate_smiles}")
    for report in res.get("compliance_report", []):
        matches = report.get("structural_class_matches", [])
        if matches:
            print(f"Structural Matches Found: {len(matches)}")
            for m in matches:
                print(f" - Class: {m['class']}, Severity: {m['severity']}, Regulation: {m['regulation']}")
        else:
            print("No structural matches found.")

def test_regional_voc():
    print("\n--- Testing Regional VOC Support ---")
    tool = CalculateVocContentTool()
    
    # Mixture with Acetone (Exempt in US EPA, VOC in EU)
    # Acetone SMILES: CC(=O)C
    components = [
        {"smiles": "CC(=O)C", "mass_g": 100, "density_g_ml": 0.784}, # Acetone
        {"smiles": "O", "mass_g": 100, "density_g_ml": 1.0}           # Water
    ]
    
    # 1. EU Standard
    eu_res = tool.execute(components, region="EU")
    print(f"EU VOC g/L: {eu_res.get('voc_g_l')} (Summary: {eu_res.get('summary')})")
    
    # 2. US EPA Standard
    us_res = tool.execute(components, region="US_EPA")
    print(f"US EPA VOC g/L: {us_res.get('voc_g_l')} (Summary: {us_res.get('summary')})")

if __name__ == "__main__":
    test_structural_screening()
    test_regional_voc()
