import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from src.tools.rdkit_tools import export_molecule_file

def test_export():
    # Test Aspirin
    smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"
    
    # 1. Test MOL Export (2D)
    mol_path = "output/test_aspirin.mol"
    res_mol = export_molecule_file(smiles, mol_path, generate_3d=False)
    print(f"MOL Export Result: {res_mol}")
    if os.path.exists(mol_path):
        print(f"SUCCESS: {mol_path} created.")
    
    # 2. Test SDF Export (3D)
    sdf_path = "output/test_aspirin_3d.sdf"
    res_sdf = export_molecule_file(smiles, sdf_path, generate_3d=True)
    print(f"SDF Export Result: {res_sdf}")
    if os.path.exists(sdf_path):
        print(f"SUCCESS: {sdf_path} created.")

if __name__ == "__main__":
    test_export()
