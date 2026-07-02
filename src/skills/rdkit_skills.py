# src/skills/rdkit_skills.py
import os
import urllib.request
import urllib.parse
import json
import sys
import re
from io import StringIO
from collections import deque
from rdkit import Chem
from rdkit import rdBase
from rdkit.Chem import Descriptors
from rdkit import DataStructs
from rdkit.Chem import rdFingerprintGenerator 
from rdkit.Chem import AllChem
from rdkit.Chem import Draw
from rdkit.Chem import rdChemReactions  # Imported for core C++ reaction simulation

# Redirect RDKit C++ warnings/errors to Python stream
rdBase.WrapLogs()

def calculate_molecular_properties(smiles: str) -> dict:
    """Parses a SMILES string and computes standard physicochemical properties using advanced RDKit features."""
    sio = StringIO()
    sys.stderr = sio
    
    try:
        params = Chem.SmilesParserParams()
        params.sanitize = True
        params.allowCXSMILES = True
        
        mol = Chem.MolFromSmiles(smiles, params)
        sanitized = True
        fallback_reason = None
        
        if mol is None:
            error_msg = sio.getvalue().strip()
            params.sanitize = False
            mol = Chem.MolFromSmiles(smiles, params)
            
            if mol is not None:
                try:
                    Chem.SanitizeMol(mol, Chem.SanitizeFlags.SANITIZE_ALL ^ Chem.SanitizeFlags.SANITIZE_PROPERTIES)
                    sanitized = False
                    fallback_reason = f"Partial Sanitization applied. Native parser error: {error_msg}"
                except Exception as sanit_err:
                    return {"error": f"SMILES topology loaded but sanitization completely failed: {str(sanit_err)}. Parser log: {error_msg}"}
            else:
                return {"error": f"SMILES Parse/Syntax Error. RDKit Core Log: {error_msg}"}
        
        log_p_val = round(Descriptors.MolLogP(mol), 2) if sanitized else "N/A (Complex Structure)"
        hbd_val = Descriptors.NumHDonors(mol) if sanitized else "N/A (Complex Structure)"
        hba_val = Descriptors.NumHAcceptors(mol) if sanitized else "N/A (Complex Structure)"
        
        return {
            "smiles": smiles,
            "molecular_weight": round(Descriptors.MolWt(mol), 2),
            "log_p": log_p_val,
            "h_bond_donors": hbd_val,
            "h_bond_acceptors": hba_val,
            "parsing_status": "Success" if sanitized else "Partial Fallback",
            "fallback_notes": fallback_reason
        }
    except Exception as e:
        return {"error": f"Critical error during molecular property calculation: {str(e)}"}
    finally:
        sys.stderr = sys.__stderr__


def generate_molecule_image(smiles: str, file_path: str) -> dict:
    """Generates a 2D image diagram of a molecule from its SMILES string and saves it to disk."""
    try:
        parent_dir = os.path.dirname(file_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir, exist_ok=True)
            
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            params = Chem.SmilesParserParams()
            params.sanitize = False
            mol = Chem.MolFromSmiles(smiles, params)
            if mol is None:
                return {"error": f"Invalid SMILES format provided for visualization: {smiles}"}
        
        AllChem.Compute2DCoords(mol)
        Draw.MolToFile(mol, file_path, size=(400, 400))
        
        return {
            "smiles": smiles,
            "file_path": file_path,
            "status": "success",
            "message": "Molecule image successfully generated and saved to disk."
        }
    except Exception as e:
        return {"error": f"Failed to generate molecule image: {str(e)}"}


def simulate_chemical_reaction(reactant_smiles_list: list, reaction_type: str) -> dict:
    """Simulates an organic chemical reaction between reactants using SMARTS transformation templates."""
    try:
        # Standardized robust reaction SMARTS blueprints
        reaction_templates = {
            "esterification": "[C:1](=[O:2])[OH:3].[OH:4][C:5]>>[C:1](=[O:2])[O:3][C:5]",
            "amide_coupling": "[C:1](=[O:2])[OH:3].[NX3;H2,H1,H0:4][C:5]>>[C:1](=[O:2])[N:4][C:5]"
        }
        
        rxn_type_clean = reaction_type.lower().strip().replace(" ", "_")
        if rxn_type_clean not in reaction_templates:
            return {"error": f"Unsupported reaction type: '{reaction_type}'. Supported: {list(reaction_templates.keys())}"}
            
        reactant_mols = []
        for smiles in reactant_smiles_list:
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return {"error": f"Invalid reactant SMILES string provided: '{smiles}'"}
            reactant_mols.append(mol)
            
        # Compile the reaction rule from the SMARTS pattern
        rxn_smarts = reaction_templates[rxn_type_clean]
        rxn = rdChemReactions.ReactionFromSmarts(rxn_smarts)
        
        # Run reaction simulation on the C++ layer (returns a matrix of possible product sets)
        products_matrix = rxn.RunReactants(tuple(reactant_mols))
        if not products_matrix:
            return {"error": f"Reaction simulation failed. Reactants do not match the transformation template for '{reaction_type}'."}
            
        # Isolate the primary molecule from the first product outcome set
        primary_product_mol = products_matrix[0][0]
        
        try:
            # Perform basic sanitization to validate ring structures and connectivity bonds
            Chem.SanitizeMol(primary_product_mol)
        except Exception:
            pass
            
        product_smiles = Chem.MolToSmiles(primary_product_mol)
        
        return {
            "reaction_type": rxn_type_clean,
            "reactants": reactant_smiles_list,
            "product_smiles": product_smiles,
            "status": "success",
            "message": "Chemical reaction successfully simulated and product structure generated."
        }
    except Exception as e:
        return {"error": f"Critical error during chemical reaction simulation: {str(e)}"}


def fetch_chemical_safety_data(molecule_name: str) -> dict:
    """Uses PubChem PUG-VIEW API to fetch official GHS hazard classifications (H-codes and P-codes) for a chemical compound."""
    try:
        safe_name = urllib.parse.quote(molecule_name)
        cid_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{safe_name}/cids/JSON"
        
        req_cid = urllib.request.Request(cid_url, headers={'User-Agent': 'ChemAgent/1.0'})
        try:
            with urllib.request.urlopen(req_cid, timeout=5) as response:
                cid_data = json.loads(response.read().decode('utf-8'))
                cid = cid_data["IdentifierList"]["CID"][0]
        except Exception:
            return {"error": f"Could not find verified PubChem CID for molecule name '{molecule_name}'."}
            
        safety_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON?heading=Safety+and+Hazards"
        req_safety = urllib.request.Request(safety_url, headers={'User-Agent': 'ChemAgent/1.0'})
        
        with urllib.request.urlopen(req_safety, timeout=5) as response:
            safety_data = json.loads(response.read().decode('utf-8'))
            
        def _find_section_by_heading(node, heading):
            if isinstance(node, dict):
                if node.get("TOCHeading") == heading:
                    return node
                for v in node.values():
                    res = _find_section_by_heading(v, heading)
                    if res:
                        return res
            elif isinstance(node, list):
                for item in node:
                    res = _find_section_by_heading(item, heading)
                    if res:
                        return res
            return None

        def _collect_strings_recursively(node, out_list):
            if isinstance(node, str):
                out_list.append(node)
            elif isinstance(node, dict):
                for v in node.values():
                    _collect_strings_recursively(v, out_list)
            elif isinstance(node, list):
                for item in node:
                    _collect_strings_recursively(item, out_list)

        ghs_section = _find_section_by_heading(safety_data, "GHS Classification")
        target_node = ghs_section if ghs_section else safety_data
        
        raw_strings = []
        _collect_strings_recursively(target_node, raw_strings)
        
        hazard_statements = []
        precautionary_statements = []
        signal_word = "Not Classified / Unknown"
        
        for s in raw_strings:
            s_clean = s.strip()
            if s_clean == "Danger":
                signal_word = "Danger"
            elif s_clean == "Warning" and signal_word != "Danger":
                signal_word = "Warning"
                
            if re.match(r'^H\d{3}', s_clean) or (':' in s_clean and re.search(r'\bH\d{3}\b', s_clean)):
                if len(s_clean) < 250 and s_clean not in hazard_statements:
                    hazard_statements.append(s_clean)
                    
            if re.match(r'^P\d{3}', s_clean) or (':' in s_clean and re.search(r'\bP\d{3}\b', s_clean)):
                if len(s_clean) < 250 and s_clean not in precautionary_statements:
                    precautionary_statements.append(s_clean)
                    
        hazard_statements.sort()
        precautionary_statements.sort()
        
        return {
            "molecule_name": molecule_name,
            "cid": int(cid),
            "signal_word": signal_word,
            "hazard_statements": hazard_statements if hazard_statements else ["No explicit hazardous statements found."],
            "precautionary_statements": precautionary_statements if precautionary_statements else ["No explicit precautionary statements found."],
            "status": "success"
        }
    except Exception as e:
        return {"error": f"Failed to parse chemical safety dossier: {str(e)}"}


def resolve_name_to_smiles(molecule_name: str) -> dict:
    """Resolves a common drug or molecule name to its canonical/isomeric SMILES string using PubChem API."""
    try:
        safe_name = urllib.parse.quote(molecule_name)
        url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{safe_name}/property/SMILES,ConnectivitySMILES,IsomericSMILES,CanonicalSMILES/JSON"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'ChemAgent/1.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            properties = data["PropertyTable"]["Properties"][0]
            
            smiles = (properties.get("SMILES") or 
                      properties.get("ConnectivitySMILES") or 
                      properties.get("IsomericSMILES") or 
                      properties.get("CanonicalSMILES"))
            
            if not smiles:
                return {"error": f"No valid SMILES fields found in PubChem response for '{molecule_name}'"}
                
            return {
                "molecule_name": molecule_name,
                "smiles": smiles,
                "status": "success"
            }
    except Exception as e:
        return {"error": f"Could not resolve molecule name '{molecule_name}' to SMILES via PubChem. Error: {str(e)}"}


def search_substructure(smiles: str, pattern: str, use_chirality: bool = False) -> dict:
    """Checks if a specific substructure pattern (SMILES or SMARTS) exists within a target molecule."""
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return {"error": f"Invalid target SMILES: {smiles}"}
        
        patt = Chem.MolFromSmarts(pattern)
        if patt is None:
            patt = Chem.MolFromSmiles(pattern)
            if patt is None:
                return {"error": f"Invalid substructure pattern (not valid SMARTS/SMILES): {pattern}"}
        
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


def calculate_molecular_similarity(smiles1: str, smiles2: str) -> dict:
    """Computes the structural Tanimoto similarity between two molecules (radius=2, ECFP4)."""
    try:
        mol1 = Chem.MolFromSmiles(smiles1)
        mol2 = Chem.MolFromSmiles(smiles2)
        
        if mol1 is None or mol2 is None:
            return {"error": f"Invalid SMILES provided. smiles1: {smiles1}, smiles2: {smiles2}"}
        
        morgan_generator = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)
        fp1 = morgan_generator.GetFingerprint(mol1)
        fp2 = morgan_generator.GetFingerprint(mol2)
        
        similarity_score = DataStructs.TanimotoSimilarity(fp1, fp2)
        
        return {
            "smiles1": smiles1,
            "smiles2": smiles2,
            "tanimoto_similarity": round(float(similarity_score), 4),
            "similarity_percentage": f"{round(float(similarity_score) * 100, 2)}%"
        }
    except Exception as e:
        return {"error": str(e)}


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
            
            stack = deque([atom])
            seen[atom.GetIdx()] = 1 
            
            while stack:
                atom = stack.popleft()
                if not self.matchers[qtyp](atom):
                    return False
                for nbr in atom.GetNeighbors():
                    if not seen[nbr.GetIdx()]:
                        seen[nbr.GetIdx()] = 1  
                        stack.append(nbr)
        return True


def search_advanced_substructure(smiles: str, pattern: str, constraint_atom_idx: int, query_type: str) -> dict:
    """Performs advanced substructure matching with dynamic sidechain filtering (Markush-like)."""
    try:
        mol = Chem.MolFromSmiles(smiles)
        patt = Chem.MolFromSmarts(pattern)
        
        if mol is None or patt is None:
            return {"error": "Invalid target SMILES or SMARTS pattern."}
        
        if query_type not in ['alkyl', 'all_carbon']:
            return {"error": f"Unsupported query_type constraint: {query_type}. Choose 'alkyl' or 'all_carbon'."}
            
        if constraint_atom_idx >= patt.GetNumAtoms():
            return {"error": f"Target constraint index {constraint_atom_idx} is out of bounds for pattern length."}

        default_matches = mol.GetSubstructMatches(patt)
        patt.GetAtomWithIdx(constraint_atom_idx).SetProp("queryType", query_type)
        
        params = Chem.SubstructMatchParameters()
        checker = SidechainChecker(patt)
        params.setExtraFinalCheck(checker)
        
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