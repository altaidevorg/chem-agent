
import sys
import os
from rdkit import Chem
from src.tools.rdkit_tools import EstimateVolatilityAndNoteTool, CheckRegulatoryComplianceTool
from src.tools.chem_math_tools import CalculateVocContentTool

def test_repairs():
    print("--- 🧪 Starting Repair Verification ---")
    
    # 1. Test Benzidine BP Estimation
    print("\n1. Testing Benzidine BP Estimation (Joback fix)...")
    vol_tool = EstimateVolatilityAndNoteTool()
    benzidine_smiles = "Nc1ccc(cc1)-c2ccc(N)cc2"
    res = vol_tool.execute(benzidine_smiles)
    print(f"SMILES: {benzidine_smiles}")
    print(f"BP: {res.get('estimated_boiling_point_c')} C (Method: {res.get('method')})")
    assert res.get('estimated_boiling_point_c', 0) > 350, "Benzidine BP should be high!"

    # 2. Test Acetone VOC Exemption (US EPA)
    print("\n2. Testing Acetone VOC Exemption (US EPA)...")
    voc_tool = CalculateVocContentTool()
    acetone_smiles = "CC(=O)C"
    components = [{"smiles": acetone_smiles, "mass_g": 100.0, "density_g_ml": 0.791}]
    
    # EU Check (Should be VOC)
    res_eu = voc_tool.execute(components, region="EU")
    print(f"EU Status: {res_eu['component_audit'][0]['is_voc']} (Reason: {res_eu['component_audit'][0]['classification_reason']})")
    assert res_eu['component_audit'][0]['is_voc'] == True

    # US EPA Check (Should be EXEMPT)
    res_epa = voc_tool.execute(components, region="US_EPA")
    print(f"US EPA Status: {res_epa['component_audit'][0]['is_voc']} (Reason: {res_epa['component_audit'][0]['classification_reason']})")
    assert res_epa['component_audit'][0]['is_voc'] == False
    assert "Exempt" in res_epa['component_audit'][0]['classification_reason']

    # 3. Test US_CARB Threshold (216C)
    print("\n3. Testing US_CARB Threshold (216C)...")
    # Compound with BP ~230C (e.g., n-Tridecane ~235C)
    # CCCCCCCCCCCCC
    tridecane = "CCCCCCCCCCCCC"
    comp_tri = [{"smiles": tridecane, "mass_g": 100.0}]
    
    res_carb = voc_tool.execute(comp_tri, region="US_CARB")
    print(f"US_CARB (216C) BP: {res_carb['component_audit'][0]['boiling_point_c']} C")
    print(f"US_CARB Status: {res_carb['component_audit'][0]['is_voc']} (Should be False if BP > 216)")
    # Joback for Tridecane: 198.2 + 2*23.58 + 11*22.88 = 497.04K = 223.9C
    # 223.9 > 216 -> NOT VOC in CARB
    
    res_eu_tri = voc_tool.execute(comp_tri, region="EU")
    print(f"EU (250C) Status: {res_eu_tri['component_audit'][0]['is_voc']} (Should be True if BP < 250)")
    
    assert res_carb['component_audit'][0]['is_voc'] == False
    assert res_eu_tri['component_audit'][0]['is_voc'] == True

    # 4. Test Toluene Regulatory Check (Expanded DB)
    print("\n4. Testing Toluene Regulatory Check (Industrial Table)...")
    reg_tool = CheckRegulatoryComplianceTool()
    res_reg = reg_tool.execute(["Toluene"])
    print(f"Toluene Status: {res_reg['compliance_report'][0]['industrial_status']}")
    print(f"Details: {res_reg['compliance_report'][0]['details'][0]['source'] if res_reg['compliance_report'][0]['details'] else 'None'}")
    assert res_reg['compliance_report'][0]['industrial_status'] == "RESTRICTED/BANNED"
    
    print("\n--- ✅ All Repairs Verified! ---")

if __name__ == "__main__":
    test_repairs()
