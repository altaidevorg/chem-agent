# src/skills/rdkit_skills.py
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from collections import deque
from io import StringIO
from typing import Any, Dict, List

from rdkit import Chem, DataStructs, rdBase
from rdkit.Chem import AllChem, Descriptors, Draw, rdFMCS, rdMolDescriptors
from rdkit.Chem import inchi
from rdkit.Chem import rdFingerprintGenerator

from src.skills.base import BaseSkill, SkillRegistry


# Redirect RDKit C++ warnings/errors to Python stream
rdBase.WrapLogs()

class ResolveNameToSmilesSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "resolve_name_to_smiles"

    @property
    def description(self) -> str:
        return "Resolves a common drug name, commercial name, or chemical name (e.g., 'Ibuprofen', 'Aspirin') into its accurate, verified SMILES string. Always use this tool first if the user provides a molecule name instead of a raw SMILES string."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "molecule_name": {"type": "string", "description": "The common name or drug name to resolve."}
            },
            "required": ["molecule_name"]
        }

    def execute(self, molecule_name: str) -> Dict[str, Any]:
        """Resolves a common drug or molecule name to its canonical/isomeric SMILES string using PubChem API via a robust POST request."""
        try:
            url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/property/SMILES,ConnectivitySMILES,IsomericSMILES,CanonicalSMILES/JSON"
            
            # Use POST to handle names with special characters or spaces safely
            data_dict = {"name": molecule_name}
            encoded_data = urllib.parse.urlencode(data_dict).encode("utf-8")
            
            req = urllib.request.Request(
                url, 
                data=encoded_data, 
                headers={'User-Agent': 'ChemAgent/1.0'}
            )
            
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                property_table = data.get("PropertyTable", {})
                properties_list = property_table.get("Properties", [])
                
                if not properties_list:
                    return {"error": f"No properties found in PubChem response for '{molecule_name}'"}
                
                properties = properties_list[0]
                
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

class CalculateMolecularPropertiesSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "calculate_molecular_properties"

    @property
    def description(self) -> str:
        return "Calculates physicochemical properties of a chemical compound given its SMILES string."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "smiles": {"type": "string", "description": "The SMILES representation of the molecule."}
            },
            "required": ["smiles"]
        }

    def execute(self, smiles: str) -> Dict[str, Any]:
        """Parses a SMILES string and computes standard physicochemical properties using advanced RDKit features."""
        try:
            params = Chem.SmilesParserParams()
            params.sanitize = True
            params.allowCXSMILES = True
            
            # Use BlockLogs to prevent global stderr pollution and ensure thread-safety
            with rdBase.BlockLogs():
                mol = Chem.MolFromSmiles(smiles, params)
            
            if mol is None:
                return {"error": f"SMILES Parse/Syntax Error for input: '{smiles}'. Please verify the chemical structure."}
            
            log_p_val = round(Descriptors.MolLogP(mol), 2)
            hbd_val = Descriptors.NumHDonors(mol)
            hba_val = Descriptors.NumHAcceptors(mol)
            
            return {
                "smiles": smiles,
                "molecular_weight": round(Descriptors.MolWt(mol), 2),
                "log_p": log_p_val,
                "h_bond_donors": hbd_val,
                "h_bond_acceptors": hba_val,
                "parsing_status": "Success"
            }
        except Exception as e:
            return {"error": f"Critical error during molecular property calculation: {str(e)}"}

class GenerateMoleculeImageSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "generate_molecule_image"

    @property
    def description(self) -> str:
        return "Generates a 2D diagram png image of a molecule from its SMILES and saves it inside the 'output/' directory."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "smiles": {"type": "string", "description": "The SMILES representation of the molecule."},
                "file_path": {"type": "string", "description": "The local path where the png should be created. Must point inside the 'output/' directory (e.g., 'output/aspirin.png')."}
            },
            "required": ["smiles", "file_path"]
        }

    def execute(self, smiles: str, file_path: str) -> Dict[str, Any]:
        """Generates a 2D image diagram of a molecule from its SMILES string and saves it to disk."""
        try:
            parent_dir = os.path.dirname(file_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
                
            with rdBase.BlockLogs():
                mol = Chem.MolFromSmiles(smiles)
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

class FetchChemicalSafetyDataSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "fetch_chemical_safety_data"

    @property
    def description(self) -> str:
        return "Retrieves official GHS hazardous classifications, hazard statement H-codes, precautionary statement P-codes, and the signal word for a chemical compound from PubChem."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "molecule_name": {"type": "string", "description": "The common or trade name of the molecule to fetch safety records for."}
            },
            "required": ["molecule_name"]
        }

    def execute(self, molecule_name: str) -> Dict[str, Any]:
        """Uses PubChem PUG-VIEW API to fetch official GHS hazard classifications for a chemical compound using a robust POST request for CID lookup."""
        try:
            # Step 1: Resolve name to CID using POST to handle special characters in names
            cid_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/cids/JSON"
            data_dict = {"name": molecule_name}
            encoded_data = urllib.parse.urlencode(data_dict).encode("utf-8")
            
            req_cid = urllib.request.Request(
                cid_url, 
                data=encoded_data, 
                headers={'User-Agent': 'ChemAgent/1.0'}
            )
            
            try:
                with urllib.request.urlopen(req_cid, timeout=5) as response:
                    cid_data = json.loads(response.read().decode('utf-8'))
                    cid = cid_data["IdentifierList"]["CID"][0]
            except Exception:
                return {"error": f"Could not find verified PubChem CID for molecule name '{molecule_name}'."}
                
            # Step 2: Fetch safety data using PUG-VIEW (PUG-VIEW uses CID in path)
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
                if s_clean.startswith("http"):
                    continue
                    
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

class SearchSubstructureSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "search_substructure"

    @property
    def description(self) -> str:
        return "Searches for a basic substructure or SMARTS pattern within a target molecule."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "smiles": {"type": "string", "description": "The SMILES representation of the molecule."},
                "pattern": {"type": "string", "description": "The SMARTS or SMILES pattern to find."}
            },
            "required": ["smiles", "pattern"]
        }

    def execute(self, smiles: str, pattern: str, use_chirality: bool = False) -> Dict[str, Any]:
        """Checks if a specific substructure pattern (SMILES or SMARTS) exists within a target molecule."""
        try:
            with rdBase.BlockLogs():
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

class CalculateMolecularSimilaritySkill(BaseSkill):
    @property
    def name(self) -> str:
        return "calculate_molecular_similarity"

    @property
    def description(self) -> str:
        return "Calculates the structural Tanimoto similarity score between two molecules."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "smiles1": {"type": "string", "description": "SMILES of the first molecule."},
                "smiles2": {"type": "string", "description": "SMILES of the second molecule."}
            },
            "required": ["smiles1", "smiles2"]
        }

    def execute(self, smiles1: str, smiles2: str) -> Dict[str, Any]:
        """Computes the structural Tanimoto similarity between two molecules (radius=2, ECFP4)."""
        try:
            with rdBase.BlockLogs():
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

class DeconstructCoreAndSidechainsSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "deconstruct_core_and_sidechains"

    @property
    def description(self) -> str:
        return "Chops away a specified core scaffold (SMILES/SMARTS) from a target molecule, isolating the remaining sidechains (R-groups) with their respective attachment indices."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "smiles": {"type": "string", "description": "The SMILES representation of the target molecule to deconstruct."},
                "core_smarts_or_smiles": {"type": "string", "description": "The SMARTS or SMILES pattern of the core scaffold to be removed."}
            },
            "required": ["smiles", "core_smarts_or_smiles"]
        }

    def execute(self, smiles: str, core_smarts_or_smiles: str) -> Dict[str, Any]:
        """Isolates sidechains by replacing the core scaffold with dummy atoms labeled by index."""
        try:
            with rdBase.BlockLogs():
                mol = Chem.MolFromSmiles(smiles)
                # Try parsing as SMILES first to preserve full chemical details, then fall back to SMARTS
                core = Chem.MolFromSmiles(core_smarts_or_smiles) or Chem.MolFromSmarts(core_smarts_or_smiles)
            
            if mol is None:
                return {"error": f"Invalid target SMILES provided: {smiles}"}
            if core is None:
                return {"error": f"Invalid core SMARTS/SMILES pattern: {core_smarts_or_smiles}"}
            
            # Remove the core scaffold from the molecule (labelByIndex=True preserves the attachment index)
            with rdBase.BlockLogs():
                sidechains_combined = Chem.ReplaceCore(mol, core, labelByIndex=True)
                
            if sidechains_combined is None:
                return {"error": "The specified core scaffold was not found within the target molecule."}
                
            # Separate the combined sidechains into individual molecule fragments
            frags = Chem.GetMolFrags(sidechains_combined, asMols=True)
            
            isolated_sidechains = []
            for frag in frags:
                frag_smiles = Chem.MolToSmiles(frag)
                isolated_sidechains.append(frag_smiles)
                
            return {
                "target_smiles": smiles,
                "core_pattern_used": core_smarts_or_smiles,
                "isolated_sidechains": isolated_sidechains,
                "total_sidechains_found": len(isolated_sidechains),
                "status": "success"
            }
        except Exception as e:
            return {"error": f"Core deconstruction failed: {str(e)}"}

class SearchAdvancedSubstructureSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "search_advanced_substructure"

    @property
    def description(self) -> str:
        return "Performs advanced substructure matching with dynamic sidechain filtering (Markush-like). Useful for finding specific chemical scaffolds with constraints."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "smiles": {"type": "string", "description": "The SMILES representation of the target molecule."},
                "pattern": {"type": "string", "description": "The SMARTS or SMILES pattern to find."},
                "constraint_atom_idx": {"type": "integer", "description": "The index of the atom in the pattern where the constraint is applied."},
                "query_type": {"type": "string", "description": "The type of constraint to apply. Supported: 'alkyl', 'all_carbon'."}
            },
            "required": ["smiles", "pattern", "constraint_atom_idx", "query_type"]
        }

    def execute(self, smiles: str, pattern: str, constraint_atom_idx: int, query_type: str) -> Dict[str, Any]:
        """Performs advanced substructure matching with dynamic sidechain filtering."""
        try:
            with rdBase.BlockLogs():
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

class FindMaximumCommonSubstructureSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "find_maximum_common_substructure"

    @property
    def description(self) -> str:
        return "Identifies the Maximum Common Substructure (MCS) shared among a list of molecules. Useful for identifying common pharmacophores or scaffolds in a set of active compounds. CRITICAL: When interpreting the returned SMARTS, remember that [#6] is Carbon and [#8] is Oxygen. Ensure your structural analysis matches the 'num_atoms' count exactly."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "smiles_list": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "A list of SMILES strings to analyze for a common substructure."
                },
                "ring_matches_ring_only": {
                    "type": "boolean",
                    "description": "If true, ring atoms in the MCS must match ring atoms in the target molecules.",
                    "default": False
                },
                "complete_rings_only": {
                    "type": "boolean",
                    "description": "If true, if any part of a ring is included in the MCS, the entire ring must be included.",
                    "default": False
                }
            },
            "required": ["smiles_list"]
        }

    def execute(self, smiles_list: List[str], ring_matches_ring_only: bool = False, complete_rings_only: bool = False) -> Dict[str, Any]:
        """Finds the largest common atom/bond mapping shared by multiple molecules."""
        try:
            if not smiles_list or len(smiles_list) < 2:
                return {"error": "At least two SMILES strings are required to find a common substructure."}

            mols = []
            with rdBase.BlockLogs():
                for s in smiles_list:
                    m = Chem.MolFromSmiles(s)
                    if m:
                        mols.append(m)
                    else:
                        return {"error": f"Invalid SMILES encountered in list: {s}"}

            # Perform MCS search
            res = rdFMCS.FindMCS(
                mols,
                maximizeBonds=True,
                ringMatchesRingOnly=ring_matches_ring_only,
                completeRingsOnly=complete_rings_only,
                timeout=30 # 30 second timeout for safety
            )

            if not res.smartsString:
                return {
                    "smarts": "",
                    "num_atoms": 0,
                    "num_bonds": 0,
                    "status": "no_common_substructure",
                    "message": "No common substructure found among the provided molecules."
                }

            return {
                "smarts": res.smartsString,
                "num_atoms": res.numAtoms,
                "num_bonds": res.numBonds,
                "ring_matches_ring_only": ring_matches_ring_only,
                "complete_rings_only": complete_rings_only,
                "status": "timeout" if res.canceled else "success",
                "timed_out": res.canceled
            }
        except Exception as e:
            return {"error": f"MCS calculation failed: {str(e)}"}

class InterpretSmartsSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "interpret_smarts_pattern"

    @property
    def description(self) -> str:
        return "Deconstructs a SMARTS string into a human-readable structural description. Use this to verify your understanding of a substructure pattern before reporting it to the user."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "smarts": {"type": "string", "description": "The SMARTS string to interpret."}
            },
            "required": ["smarts"]
        }

    def execute(self, smarts: str) -> Dict[str, Any]:
        """Provides a breakdown of a SMARTS pattern by counting atom types and identifying structural motifs."""
        try:
            with rdBase.BlockLogs():
                query = Chem.MolFromSmarts(smarts)
            
            if not query:
                return {"error": f"Invalid SMARTS pattern: {smarts}"}

            Chem.FastFindRings(query)

            atom_counts = {}
            for atom in query.GetAtoms():
                symbol = atom.GetSymbol() if atom.GetSymbol() != "*" else f"Type_{atom.GetAtomicNum()}"
                if atom.GetAtomicNum() == 6: symbol = "Carbon"
                elif atom.GetAtomicNum() == 8: symbol = "Oxygen"
                elif atom.GetAtomicNum() == 7: symbol = "Nitrogen"
                elif atom.GetAtomicNum() == 16: symbol = "Sulfur"
                elif atom.GetAtomicNum() == 9: symbol = "Fluorine"
                elif atom.GetAtomicNum() == 17: symbol = "Chlorine"
                
                atom_counts[symbol] = atom_counts.get(symbol, 0) + 1

            num_rings = query.GetRingInfo().NumRings()
            
            # Identify specific motifs
            motifs = []
            ring_info = query.GetRingInfo()
            for ring in ring_info.AtomRings():
                if len(ring) == 6:
                    if all(query.GetAtomWithIdx(i).GetIsAromatic() and query.GetAtomWithIdx(i).GetAtomicNum() == 6 for i in ring):
                        motifs.append("Benzene ring")
                        break
            
            if query.HasSubstructMatch(Chem.MolFromSmarts("C(=O)O")): 
                motifs.append("Carboxylic acid group")
            if query.HasSubstructMatch(Chem.MolFromSmarts("C(=O)N")): 
                motifs.append("Amide group")
            if query.HasSubstructMatch(Chem.MolFromSmarts("C-C-C(=O)O")): 
                motifs.append("Propionic acid backbone")

            return {
                "smarts": smarts,
                "total_atoms": query.GetNumAtoms(),
                "atom_breakdown": atom_counts,
                "ring_count": num_rings,
                "identified_motifs": motifs,
                "status": "success"
            }
        except Exception as e:
            return {"error": f"SMARTS interpretation failed: {str(e)}"}

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

class CanonicalizeAndValidateSmilesSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "canonicalize_and_validate_smiles"

    @property
    def description(self) -> str:
        return "Validates whether a given string is a valid SMILES and converts it into its unique canonical form. Use this to clean up user inputs before storing or comparing molecules."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "smiles": {"type": "string", "description": "The raw SMILES string to validate and canonicalize."}
            },
            "required": ["smiles"]
        }

    def execute(self, smiles: str) -> Dict[str, Any]:
        """Validates and returns the canonical version of a SMILES string."""
        try:
            with rdBase.BlockLogs():
                mol = Chem.MolFromSmiles(smiles)
            
            if mol is None:
                return {
                    "is_valid": False,
                    "error": f"The provided string '{smiles}' is not a valid SMILES pattern.",
                    "status": "fail"
                }
            
            canonical_smiles = Chem.MolToSmiles(mol, canonical=True)
            return {
                "is_valid": True,
                "raw_smiles": smiles,
                "canonical_smiles": canonical_smiles,
                "status": "success"
            }
        except Exception as e:
            return {"error": f"Validation failed due to a critical error: {str(e)}"}

class GetMolecularFormulaAndChargeSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "get_molecular_formula_and_charge"

    @property
    def description(self) -> str:
        return "Calculates the exact molecular formula (e.g., C6H12O6) and the total net formal charge of a molecule from its SMILES string."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "smiles": {"type": "string", "description": "The SMILES representation of the molecule."}
            },
            "required": ["smiles"]
        }

    def execute(self, smiles: str) -> Dict[str, Any]:
        """Computes the chemical formula and net charge of a molecule."""
        try:
            with rdBase.BlockLogs():
                mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return {"error": f"Invalid SMILES pattern: {smiles}"}
            
            formula = rdMolDescriptors.CalcMolFormula(mol)
            net_charge = Chem.GetFormalCharge(mol)
            
            return {
                "smiles": smiles,
                "molecular_formula": formula,
                "net_charge": net_charge,
                "status": "success"
            }
        except Exception as e:
            return {"error": f"Failed to compute formula/charge: {str(e)}"}

class ConvertSmilesToInchiSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "convert_smiles_to_inchi"

    @property
    def description(self) -> str:
        return "Converts a standard SMILES string into IUPAC InChI and InChIKey identifiers. InChIKey is highly recommended for web-based database lookups."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "smiles": {"type": "string", "description": "The SMILES representation of the molecule to convert."}
            },
            "required": ["smiles"]
        }

    def execute(self, smiles: str) -> Dict[str, Any]:
        """Converts SMILES to InChI and InChIKey safely with guard checks and optimized RDKit calls."""
        try:
            with rdBase.BlockLogs():
                mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return {"error": f"Invalid SMILES pattern for InChI conversion: {smiles}"}
            
            # 1. Generate InChI string
            inchi_str = inchi.MolToInchi(mol)
            
            # Guard check to prevent passing empty strings to further InChI functions
            if not inchi_str:
                return {"error": f"RDKit failed to generate a valid InChI string for SMILES: {smiles}"}
            
            # 2. Generate InChIKey directly from molecule (Optimization)
            inchikey = inchi.MolToInchiKey(mol)
            
            return {
                "smiles": smiles,
                "inchi": inchi_str,
                "inchikey": inchikey,
                "status": "success"
            }
        except Exception as e:
            return {"error": f"InChI conversion failed due to a critical error: {str(e)}"}
            
class CountHeavyAtomsAndRingsSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "count_heavy_atoms_and_rings"

    @property
    def description(self) -> str:
        return "Counts the number of heavy atoms (non-hydrogen atoms) and the total number of rings within a molecule from its SMILES string."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "smiles": {"type": "string", "description": "The SMILES representation of the molecule."}
            },
            "required": ["smiles"]
        }

    def execute(self, smiles: str) -> Dict[str, Any]:
        """Calculates heavy atom count and total ring count for a molecule."""
        try:
            with rdBase.BlockLogs():
                mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return {"error": f"Invalid SMILES pattern: {smiles}"}
            
            heavy_atoms = mol.GetNumHeavyAtoms()
            ring_count = mol.GetRingInfo().NumRings()
            
            return {
                "smiles": smiles,
                "heavy_atom_count": heavy_atoms,
                "total_ring_count": ring_count,
                "status": "success"
            }
        except Exception as e:
            return {"error": f"Failed to count atoms and rings: {str(e)}"}

class DetectFunctionalGroupsSkill(BaseSkill):
    # Pre-compile static SMARTS patterns at the class level for performance (runs only once)
    _FG_PATTERNS = {
        "alcohol": Chem.MolFromSmarts("[C,c;!$(C(=O))][OH]"),
        "carboxylic_acid": Chem.MolFromSmarts("C(=O)[OH,O-]"),
        "amine": Chem.MolFromSmarts("[NX3;H2,H1,H0;!$(N-C=O)]"),
        "halogen": Chem.MolFromSmarts("[F,Cl,Br,I]"),
        "ketone": Chem.MolFromSmarts("[#6][CX3](=O)[#6]"),
        "aldehyde": Chem.MolFromSmarts("[CX3H1,CX3H2](=O)"),
        "ester": Chem.MolFromSmarts("[CX3](=O)[OX2H0][#6]"),
        "ether": Chem.MolFromSmarts("[OD2]([#6;!$(C(=O))])[#6;!$(C(=O))]"),
        "amide": Chem.MolFromSmarts("[CX3](=O)[NX3]"),
        "nitro": Chem.MolFromSmarts("[$([NX3](=O)=O),$([NX3+]([O-])=O)]"),
        "thiol": Chem.MolFromSmarts("[C,c][SH]")
    }

    @property
    def name(self) -> str:
        return "detect_functional_groups"

    @property
    def description(self) -> str:
        return "Scans a molecule's SMILES string for basic functional groups like Alcohols, Carboxylic Acids, Amines, and Halogens using standard SMARTS patterns."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "smiles": {"type": "string", "description": "The SMILES representation of the molecule."}
            },
            "required": ["smiles"]
        }

    def execute(self, smiles: str) -> Dict[str, Any]:
        """Detects presence and counts of basic functional groups using pre-compiled SMARTS matching."""
        try:
            with rdBase.BlockLogs():
                mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return {"error": f"Invalid SMILES pattern: {smiles}"}
            
            detected_groups = {}
            # Use pre-compiled RDKit objects from class level for better performance
            for group_name, patt in self._FG_PATTERNS.items():
                if patt is None:
                    continue
                matches = mol.GetSubstructMatches(patt)
                detected_groups[group_name] = {
                    "present": len(matches) > 0,
                    "count": len(matches)
                }
                
            return {
                "smiles": smiles,
                "functional_groups": detected_groups,
                "status": "success"
            }
        except Exception as e:
            return {"error": f"Functional group detection failed: {str(e)}"}

class ResolveSmilesToNameSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "resolve_smiles_to_name"

    @property
    def description(self) -> str:
        return "Queries the PubChem API using a SMILES string to find the common, commercial, or IUPAC name of the compound."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "smiles": {"type": "string", "description": "The SMILES string to resolve into a common name."}
            },
            "required": ["smiles"]
        }

    def execute(self, smiles: str) -> Dict[str, Any]:
        """Resolves a SMILES string to its common title and IUPAC name via PubChem using a robust POST request."""
        try:
            # Use POST endpoint to avoid issues with slashes in SMILES and URL length limits
            url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/property/Title,IUPACName/JSON"
            
            # Encode SMILES data to be sent in the HTTP Body
            data_dict = {"smiles": smiles}
            encoded_data = urllib.parse.urlencode(data_dict).encode("utf-8")
            
            req = urllib.request.Request(
                url, 
                data=encoded_data, 
                headers={'User-Agent': 'ChemAgent/1.0'}
            )
            
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                property_table = data.get("PropertyTable", {})
                properties_list = property_table.get("Properties", [])
                
                if not properties_list:
                    return {"error": f"No names found in PubChem for SMILES: {smiles}"}
                
                properties = properties_list[0]
                
                common_name = properties.get("Title")
                iupac_name = properties.get("IUPACName")
                
                if not common_name and not iupac_name:
                    return {"error": f"No names found in PubChem for SMILES: {smiles}"}
                    
                return {
                    "smiles": smiles,
                    "common_name": common_name or "Unknown Common Name",
                    "iupac_name": iupac_name or "Unknown IUPAC Name",
                    "status": "success"
                }
        except Exception as e:
            return {"error": f"Could not resolve SMILES to name via PubChem. Error: {str(e)}"}

# Register all RDKit skills
SkillRegistry.register(ResolveNameToSmilesSkill())
SkillRegistry.register(CalculateMolecularPropertiesSkill())
SkillRegistry.register(GenerateMoleculeImageSkill())
SkillRegistry.register(FetchChemicalSafetyDataSkill())
SkillRegistry.register(SearchSubstructureSkill())
SkillRegistry.register(CalculateMolecularSimilaritySkill())
SkillRegistry.register(SearchAdvancedSubstructureSkill())
SkillRegistry.register(FindMaximumCommonSubstructureSkill())
SkillRegistry.register(InterpretSmartsSkill())
SkillRegistry.register(DeconstructCoreAndSidechainsSkill())
SkillRegistry.register(CanonicalizeAndValidateSmilesSkill())
SkillRegistry.register(GetMolecularFormulaAndChargeSkill())
SkillRegistry.register(ConvertSmilesToInchiSkill())
SkillRegistry.register(CountHeavyAtomsAndRingsSkill())
SkillRegistry.register(DetectFunctionalGroupsSkill())
SkillRegistry.register(ResolveSmilesToNameSkill())

# Legacy functions kept for backward compatibility if needed, 
# but the agent should now use SkillRegistry.
def calculate_molecular_properties(smiles: str) -> dict:
    return CalculateMolecularPropertiesSkill().execute(smiles)

def generate_molecule_image(smiles: str, file_path: str) -> dict:
    return GenerateMoleculeImageSkill().execute(smiles, file_path)

def fetch_chemical_safety_data(molecule_name: str) -> dict:
    return FetchChemicalSafetyDataSkill().execute(molecule_name)

def resolve_name_to_smiles(molecule_name: str) -> dict:
    return ResolveNameToSmilesSkill().execute(molecule_name)

def search_substructure(smiles: str, pattern: str, use_chirality: bool = False) -> dict:
    return SearchSubstructureSkill().execute(smiles, pattern, use_chirality)

def calculate_molecular_similarity(smiles1: str, smiles2: str) -> dict:
    return CalculateMolecularSimilaritySkill().execute(smiles1, smiles2)

def search_advanced_substructure(smiles: str, pattern: str, constraint_atom_idx: int, query_type: str) -> dict:
    return SearchAdvancedSubstructureSkill().execute(smiles, pattern, constraint_atom_idx, query_type)

def find_maximum_common_substructure(smiles_list: List[str], ring_matches_ring_only: bool = False, complete_rings_only: bool = False) -> dict:
    return FindMaximumCommonSubstructureSkill().execute(smiles_list, ring_matches_ring_only, complete_rings_only)

def interpret_smarts_pattern(smarts: str) -> dict:
    return InterpretSmartsSkill().execute(smarts)

def deconstruct_core_and_sidechains(smiles: str, core_smarts_or_smiles: str) -> dict:
    return DeconstructCoreAndSidechainsSkill().execute(smiles, core_smarts_or_smiles)

def canonicalize_and_validate_smiles(smiles: str) -> dict:
    return CanonicalizeAndValidateSmilesSkill().execute(smiles)

def get_molecular_formula_and_charge(smiles: str) -> dict:
    return GetMolecularFormulaAndChargeSkill().execute(smiles)

def convert_smiles_to_inchi(smiles: str) -> dict:
    return ConvertSmilesToInchiSkill().execute(smiles)

def count_heavy_atoms_and_rings(smiles: str) -> dict:
    return CountHeavyAtomsAndRingsSkill().execute(smiles)

def detect_functional_groups(smiles: str) -> dict:
    return DetectFunctionalGroupsSkill().execute(smiles)

def resolve_smiles_to_name(smiles: str) -> dict:
    return ResolveSmilesToNameSkill().execute(smiles)