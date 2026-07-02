# src/skills/rdkit_skills.py
from rdkit import Chem
from rdkit.Chem import Descriptors
from rdkit import DataStructs
from rdkit.Chem import rdFingerprintGenerator # Import the modern generator module

def calculate_molecular_properties(smiles: str) -> dict:
    """Parses a SMILES string and computes standard physicochemical properties using RDKit."""
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return {"error": f"Invalid SMILES format provided: {smiles}"}
        
        return {
            "smiles": smiles,
            "molecular_weight": round(Descriptors.MolWt(mol), 2),
            "log_p": round(Descriptors.MolLogP(mol), 2),
            "h_bond_donors": Descriptors.NumHDonors(mol),
            "h_bond_acceptors": Descriptors.NumHAcceptors(mol)
        }
    except Exception as e:
        return {"error": str(e)}


def search_substructure(smiles: str, pattern: str, use_chirality: bool = False) -> dict:
    """
    Checks if a specific substructure pattern (SMILES or SMARTS) exists within a target molecule.
    Returns matches and their corresponding atom indices.
    """
    try:
        # Load the target molecule
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return {"error": f"Invalid target SMILES: {smiles}"}
        
        # Try loading pattern as SMARTS first, fallback to SMILES
        patt = Chem.MolFromSmarts(pattern)
        if patt is None:
            patt = Chem.MolFromSmiles(pattern)
            if patt is None:
                return {"error": f"Invalid substructure pattern (not valid SMARTS/SMILES): {pattern}"}
        
        # Perform matching
        has_match = mol.HasSubstructMatch(patt, useChirality=use_chirality)
        matches = mol.GetSubstructMatches(patt, useChirality=use_chirality)
        
        return {
            "target_smiles": smiles,
            "pattern": pattern,
            "has_match": has_match,
            "match_count": len(matches),
            "atom_indices": [list(match) for match in matches],
            "chirality_enforced": use_chirality
        }
    except Exception as e:
        return {"error": str(e)}


from rdkit import DataStructs
from rdkit.Chem import AllChem

def calculate_molecular_similarity(smiles1: str, smiles2: str) -> dict:
    """
    Computes the structural Tanimoto similarity between two molecules 
    using the modern rdFingerprintGenerator Morgan interface (radius=2, ECFP4).
    """
    try:
        mol1 = Chem.MolFromSmiles(smiles1)
        mol2 = Chem.MolFromSmiles(smiles2)
        
        if mol1 is None or mol2 is None:
            return {"error": f"Invalid SMILES provided. smiles1: {smiles1}, smiles2: {smiles2}"}
        
        # Using the modern Morgan Fingerprint Generator interface to avoid deprecation warnings
        morgan_generator = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
        
        fp1 = morgan_generator.GetFingerprint(mol1)
        fp2 = morgan_generator.GetFingerprint(mol2)
        
        # Calculate Tanimoto Similarity
        similarity_score = DataStructs.TanimotoSimilarity(fp1, fp2)
        
        return {
            "smiles1": smiles1,
            "smiles2": smiles2,
            "tanimoto_similarity": round(float(similarity_score), 4),
            "similarity_percentage": f"{round(float(similarity_score) * 100, 2)}%"
        }
    except Exception as e:
        return {"error": str(e)}

# Insert this at the bottom of src/skills/rdkit_skills.py

class SidechainChecker:
    matchers = {
        'alkyl': lambda at: not at.GetIsAromatic(),
        'all_carbon': lambda at: at.GetAtomicNum() == 6
    }

    def __init__(self, query, pName="queryType"):
        self._atsToExamine = [(x.GetIdx(), x.GetProp(pName)) for x in query.GetAtoms() if x.HasProp(pName)]
        self._pName = pName

    def __call__(self, mol, vect):
        seen = [0] * mol.GetNumAtoms()
        for idx in vect:
            seen[idx] = 1
        
        for idx, qtyp in self._atsToExamine:
            midx = vect[idx]
            atom = mol.GetAtomWithIdx(midx)
            stack = [atom]
            while stack:
                atom = stack.pop(0)
                if not self.matchers[qtyp](atom):
                    return False
                seen[atom.GetIdx()] = 1
                for nbr in atom.GetNeighbors():
                    if not seen[nbr.GetIdx()]:
                        stack.append(nbr)
        return True


def search_advanced_substructure(smiles: str, pattern: str, constraint_atom_idx: int, query_type: str) -> dict:
    """
    Performs advanced substructure matching with dynamic sidechain filtering (Markush-like).
    Valid types: 'alkyl' (non-aromatic sidechains) or 'all_carbon' (pure hydrocarbon sidechains).
    """
    try:
        mol = Chem.MolFromSmiles(smiles)
        patt = Chem.MolFromSmarts(pattern)
        
        if mol is None or patt is None:
            return {"error": "Invalid target SMILES or SMARTS pattern."}
        
        if query_type not in ['alkyl', 'all_carbon']:
            return {"error": f"Unsupported query_type constraint: {query_type}. Choose 'alkyl' or 'all_carbon'."}
            
        if constraint_atom_idx >= patt.GetNumAtoms():
            return {"error": f"Target constraint index {constraint_atom_idx} is out of bounds for pattern length."}

        # Setup standard matches first
        default_matches = mol.GetSubstructMatches(patt)
        
        # Setup advanced checker parameters
        patt.GetAtomWithIdx(constraint_atom_idx).SetProp("queryType", query_type)
        params = Chem.SubstructMatchParameters()
        checker = SidechainChecker(patt)
        params.setExtraFinalCheck(checker)
        
        # Execute filtered match
        filtered_matches = mol.GetSubstructMatches(patt, params)
        
        return {
            "target_smiles": smiles,
            "core_pattern": pattern,
            "constraint_applied": {
                "atom_index_in_pattern": constraint_atom_idx,
                "required_type": query_type
            },
            "total_unfiltered_matches": len(default_matches),
            "total_filtered_matches": len(filtered_matches),
            "unfiltered_atom_indices": [list(m) for m in default_matches],
            "filtered_atom_indices": [list(m) for m in filtered_matches]
        }
    except Exception as e:
        return {"error": str(e)}