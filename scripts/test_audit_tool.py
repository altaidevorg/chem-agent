import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from src.tools.rdkit_tools import AuditChemicalCompatibilityTool

def test_audit():
    tool = AuditChemicalCompatibilityTool()
    
    # Test 1: Cyanide + Acid (Extreme Risk)
    # Sodium Cyanide (simplified as C#N) + Acetic Acid (CC(=O)O)
    smiles_list = ["C#N", "CC(=O)O"]
    res = tool.execute(smiles_list)
    print(f"\nTest 1 (Cyanide + Acid) Result:")
    for risk in res["risks_detected"]:
        print(f"- [{risk['severity']}] {risk['rule_name']}: {risk['consequence']}")
    
    # Test 2: Aldehyde + Amine (Schiff Base)
    # Benzaldehyde (c1ccccc1C=O) + Methylamine (CN)
    smiles_list = ["c1ccccc1C=O", "CN"]
    res = tool.execute(smiles_list)
    print(f"\nTest 2 (Aldehyde + Amine) Result:")
    for risk in res["risks_detected"]:
        print(f"- [{risk['severity']}] {risk['rule_name']}: {risk['consequence']}")

if __name__ == "__main__":
    test_audit()
