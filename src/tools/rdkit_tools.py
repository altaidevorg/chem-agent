# src/tools/rdkit_tools.py
import json
import math
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

import numpy as np
from src.config import KNOWLEDGE_DB_FILE
from src.tools.base import BaseTool, ToolRegistry
from src.tools.structure_tools import StandardizeMoleculeTool


# Redirect RDKit C++ warnings/errors to Python stream
rdBase.WrapLogs()

class ResolveNameToSmilesTool(BaseTool):
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

class CalculateMolecularPropertiesTool(BaseTool):
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
            tpsa_val = round(Descriptors.TPSA(mol), 2)
            rot_bonds = Descriptors.NumRotatableBonds(mol)
            
            return {
                "smiles": smiles,
                "molecular_weight": round(Descriptors.MolWt(mol), 2),
                "log_p": log_p_val,
                "h_bond_donors": hbd_val,
                "h_bond_acceptors": hba_val,
                "tpsa": tpsa_val,
                "rotatable_bonds": rot_bonds,
                "parsing_status": "Success"
            }
        except Exception as e:
            return {"error": f"Critical error during molecular property calculation: {str(e)}"}

class GenerateMoleculeImageTool(BaseTool):
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

class FetchChemicalSafetyDataTool(BaseTool):
    _GHS_DICTIONARY = None

    @property
    def name(self) -> str:
        return "fetch_chemical_safety_data"

    @property
    def description(self) -> str:
        return "Retrieves official GHS hazard classifications, hazard statement H-codes, precautionary statement P-codes, and the signal word for a chemical compound from PubChem."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "molecule_name": {"type": "string", "description": "The common or trade name of the molecule to fetch safety records for."}
            },
            "required": ["molecule_name"]
        }

    def _ensure_dictionary_loaded(self) -> None:
        """Lazily loads the GHS dictionary from PubChem on the first live execution run."""
        if self._GHS_DICTIONARY is not None:
            return
        
        try:
            # Official source for GHS codes and descriptions from PubChem
            url = "https://pubchem.ncbi.nlm.nih.gov/ghs/ghscode_11.txt"
            req = urllib.request.Request(url, headers={'User-Agent': 'ChemAgent/1.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                # Use latin-1 encoding as PubChem TSV files often contain non-UTF-8 characters
                content = response.read().decode('latin-1')
                
            new_dict = {}
            for line in content.splitlines():
                parts = line.split('\t')
                if len(parts) >= 2:
                    code = parts[0].strip()
                    desc = parts[1].strip()
                    
                    if not code or not desc or desc == "Hazard Statement":
                        continue
                        
                    # Match Hxxx or Pxxx (with optional suffixes like H360F or P301+P310)
                    if re.match(r'^[HP]\d{3}', code):
                        # Clean up description (remove (Deleted) or (Obsolete) tags)
                        clean_desc = desc.replace('(Deleted)', '').replace('(Obsolete)', '').strip()
                        if clean_desc:
                            new_dict[code] = clean_desc
                            # Also store numeric key for simple codes (e.g., "210" for "P210")
                            if '+' not in code and len(code) >= 4:
                                numeric_key = code[1:]
                                if numeric_key not in new_dict:
                                    new_dict[numeric_key] = clean_desc
            
            self._GHS_DICTIONARY = new_dict
        except Exception:
            # Fallback to empty dict if network is down or URL changes
            self._GHS_DICTIONARY = {}

    def execute(self, molecule_name: str) -> Dict[str, Any]:
        """Uses PubChem PUG-VIEW API and cross-references the live GHS dictionary mapping."""
        try:
            self._ensure_dictionary_loaded()
            
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
            precautionary_blocks = []
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
                    if len(s_clean) < 250 and s_clean not in precautionary_blocks:
                        precautionary_blocks.append(s_clean)
                        
            hazard_statements.sort()
            
            resolved_precautionary = []
            for p_block in precautionary_blocks:
                found_codes = re.findall(r'P\d{3}(?:\+P\d{3})*', p_block)
                
                for code in found_codes:
                    sub_codes = code.split('+')
                    sub_descriptions = []
                    
                    for sub_code in sub_codes:
                        numeric_key = sub_code[1:] if sub_code.startswith('P') else sub_code
                        # Bulletproof lookup trying both raw string and numeric string variants
                        desc = self._GHS_DICTIONARY.get(sub_code) or self._GHS_DICTIONARY.get(numeric_key)
                        if desc:
                            sub_descriptions.append(desc.strip())
                    
                    if sub_descriptions:
                        description = " / ".join(sub_descriptions)
                    else:
                        description = "Official safety statement description unavailable."
                        
                    resolved_line = f"{code}: {description}"
                    if resolved_line not in resolved_precautionary:
                        resolved_precautionary.append(resolved_line)
            
            return {
                "molecule_name": molecule_name,
                "cid": int(cid),
                "signal_word": signal_word,
                "hazard_statements": hazard_statements if hazard_statements else ["No explicit hazardous statements found."],
                "precautionary_statements": resolved_precautionary if resolved_precautionary else ["No explicit precautionary statements found."],
                "status": "success"
            }
        except Exception as e:
            return {"error": f"Failed to parse chemical safety dossier: {str(e)}"}

class SearchSubstructureTool(BaseTool):
    @property
    def name(self) -> str:
        return "search_substructure"

    @property
    def description(self) -> str:
        return "Searches for a specific substructure or SMARTS pattern within a target molecule, with optional strict stereochemistry/chirality matching."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "smiles": {
                    "type": "string", 
                    "description": "The SMILES representation of the target molecule to search within."
                },
                "pattern": {
                    "type": "string", 
                    "description": "The SMARTS or SMILES pattern to look for inside the target molecule."
                },
                "chirality_enforced": {
                    "type": "boolean", 
                    "description": "Set to true to strictly match stereochemical configurations and tetrahedral chiral centers. Defaults to false."
                }
            },
            "required": ["smiles", "pattern", "chirality_enforced"]
        }

    def execute(self, smiles: str, pattern: str, chirality_enforced: bool = False) -> Dict[str, Any]:
        """Checks if a specific substructure pattern exists within a target molecule using RDKit."""
        try:
            with rdBase.BlockLogs():
                mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return {"error": f"Invalid target SMILES: {smiles}"}
            
            # Attempt to parse as SMARTS first, fallback to SMILES if necessary
            patt = Chem.MolFromSmarts(pattern)
            if patt is None:
                patt = Chem.MolFromSmiles(pattern)
                if patt is None:
                    return {"error": f"Invalid substructure pattern (not valid SMARTS/SMILES): {pattern}"}
            
            # Execute RDKit substructure matching with strict chirality flag
            has_match = mol.HasSubstructMatch(patt, useChirality=chirality_enforced)
            matches = mol.GetSubstructMatches(patt, useChirality=chirality_enforced)
            
            return {
                "target_smiles": smiles,
                "pattern": pattern,
                "has_match": has_match,
                "match_count": len(matches),
                "atom_indices": [list(match) for match in matches],
                "chirality_enforced": chirality_enforced,
                "status": "success"
            }
        except Exception as e:
            return {"error": f"Substructure search failed: {str(e)}"}

            
class CalculateMolecularSimilarityTool(BaseTool):
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

class DeconstructCoreAndSidechainsTool(BaseTool):
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

class SearchAdvancedSubstructureTool(BaseTool):
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

class FindMaximumCommonSubstructureTool(BaseTool):
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

class InterpretSmartsTool(BaseTool):
    # Pure topological registry (No valence/implicit H primitives to prevent C++ crashes)
    # The size-based overlap engine handles structural differentiation automatically.
    _FUNCTIONAL_GROUPS = {
        "Propionic acid backbone": "CCC(=O)O",
        "Ester group": "C(=O)O[#6]",
        "Carboxylic acid group": "C(=O)O",
        "Amide group": "C(=O)N",
        "Nitro group": "N(=O)=O",
        "Nitrile group": "C#N",
        "Carbonyl group": "C=O",
        "Amine group": "N-[#6]",
        "Ether linkage": "O-[#6]",
        "Thiol group": "S-[#6]"
    }

    @property
    def name(self) -> str:
        return "interpret_smarts_pattern"

    @property
    def description(self) -> str:
        return "Deconstructs a SMARTS string into a human-readable structural description by safely analyzing atomic topology."

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
        """Deconstructs SMARTS strings using non-destructive topological graph isomorphism."""
        try:
            with rdBase.BlockLogs():
                query = Chem.MolFromSmarts(smarts)
            
            if not query:
                return {"error": f"Invalid SMARTS pattern: {smarts}"}

            Chem.FastFindRings(query)

            # 1. Bulletproof Atomic Number Counting Engine
            atom_counts = {}
            for atom in query.GetAtoms():
                atomic_num = atom.GetAtomicNum()
                if atomic_num == 6: symbol = "Carbon"
                elif atomic_num == 8: symbol = "Oxygen"
                elif atomic_num == 7: symbol = "Nitrogen"
                elif atomic_num == 16: symbol = "Sulfur"
                elif atomic_num == 9: symbol = "Fluorine"
                elif atomic_num == 17: symbol = "Chlorine"
                elif atomic_num == 0: symbol = "Generic/Wildcard"
                else: symbol = f"Element_{atomic_num}"
                
                atom_counts[symbol] = atom_counts.get(symbol, 0) + 1

            num_rings = query.GetRingInfo().NumRings()
            
            # 2. Native Benzene Ring Detector
            motifs = []
            ring_info = query.GetRingInfo()
            for ring in ring_info.AtomRings():
                if len(ring) == 6:
                    if all(query.GetAtomWithIdx(i).GetIsAromatic() and query.GetAtomWithIdx(i).GetAtomicNum() == 6 for i in ring):
                        motifs.append("Benzene ring")
                        break

            # 3. Size-Based Hierarchical Overlap Suppression Engine
            compiled_registry = []
            for name, smarts_str in self._FUNCTIONAL_GROUPS.items():
                patt = Chem.MolFromSmarts(smarts_str)
                if patt:
                    compiled_registry.append({
                        "name": name,
                        "patt": patt,
                        "size": patt.GetNumAtoms()
                    })
            
            # Sort strictly by size descending (Ester size 4 > Carboxylic acid size 3)
            compiled_registry.sort(key=lambda x: x["size"], reverse=True)
            
            claimed_atoms = set()
            for motif in compiled_registry:
                matches = query.GetSubstructMatches(motif["patt"])
                if not matches:
                    continue
                
                for match in matches:
                    match_set = set(match)
                    # Claim sub-graphs safely without querying atomic implicit valence states
                    if not match_set.issubset(claimed_atoms):
                        if motif["name"] not in motifs:
                            motifs.append(motif["name"])
                        claimed_atoms.update(match_set)

            return {
                "smarts": smarts,
                "total_atoms": query.GetNumAtoms(),
                "atom_breakdown": atom_counts,
                "ring_count": num_rings,
                "identified_motifs": sorted(motifs),
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

class GetMolecularFormulaAndChargeTool(BaseTool):
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

class CalculateAllDescriptorsTool(BaseTool):
    """
    Calculates 200+ physicochemical descriptors for a molecule using RDKit.
    Returns a comprehensive dictionary of all available descriptors.
    """

    @property
    def name(self) -> str:
        return "calculate_all_descriptors"

    @property
    def description(self) -> str:
        return (
            "Calculates a comprehensive set of 200+ molecular descriptors using RDKit. "
            "Use this for deep structural analysis or when building predictive models."
        )

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
        try:
            with rdBase.BlockLogs():
                mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return {"error": f"Invalid SMILES: {smiles}"}

            results = {}
            for name, func in Descriptors._descList:
                try:
                    val = func(mol)
                    # Round floats for cleanliness, keep ints as is
                    if isinstance(val, float):
                        results[name] = round(val, 4)
                    else:
                        results[name] = val
                except:
                    results[name] = None

            return {
                "smiles": smiles,
                "descriptor_count": len(results),
                "descriptors": results,
                "status": "success"
            }
        except Exception as e:
            return {"error": f"Failed to calculate all descriptors: {str(e)}"}

class ExportMoleculeFileTool(BaseTool):
    @property
    def name(self) -> str:
        return "export_molecule_file"

    @property
    def description(self) -> str:
        return (
            "Converts a SMILES string into a standard .mol or .sdf file format and saves it inside the 'output/' directory. "
            "These formats are compatible with external chemistry software like ChemDraw, PyMOL, or Discovery Studio. "
            "Supports optional 3D coordinate generation."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "smiles": {"type": "string", "description": "The SMILES representation of the molecule to export."},
                "file_path": {"type": "string", "description": "The local path where the file should be created. Must end in .mol or .sdf (e.g., 'output/molecule.mol')."},
                "generate_3d": {
                    "type": "boolean", 
                    "description": "If true, generates optimized 3D coordinates using the ETKDG method. Defaults to false (2D only).",
                    "default": False
                }
            },
            "required": ["smiles", "file_path"]
        }

    def execute(self, smiles: str, file_path: str, generate_3d: bool = False) -> Dict[str, Any]:
        """Exports a SMILES string to a MOL or SDF file with coordinate generation."""
        try:
            parent_dir = os.path.dirname(file_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
                
            with rdBase.BlockLogs():
                mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return {"error": f"Invalid SMILES format provided for export: {smiles}"}
            
            # Always add hydrogens for proper file export and 3D modeling
            mol = Chem.AddHs(mol)
            
            if generate_3d:
                # Use ETKDG (Experimental-Torsion Knowledge Distance Geometry) for 3D embedding
                AllChem.EmbedMolecule(mol, AllChem.ETKDG())
                AllChem.MMFFOptimizeMolecule(mol) # Quick force-field cleanup
            else:
                AllChem.Compute2DCoords(mol)
            
            _, ext = os.path.splitext(file_path.lower())
            
            if ext == '.mol':
                Chem.MolToMolFile(mol, file_path)
            elif ext == '.sdf':
                with Chem.SDWriter(file_path) as writer:
                    writer.write(mol)
            else:
                return {"error": f"Unsupported file extension '{ext}'. Please use .mol or .sdf"}
            
            return {
                "smiles": smiles,
                "file_path": file_path,
                "format": ext[1:].upper(),
                "coordinates": "3D (optimized)" if generate_3d else "2D",
                "status": "success",
                "message": f"Molecule successfully exported to {file_path} in {ext[1:].upper()} format."
            }
        except Exception as e:
            return {"error": f"Failed to export molecule file: {str(e)}"}

class ConvertSmilesToInchiTool(BaseTool):
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
            
class CountHeavyAtomsAndRingsTool(BaseTool):
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

class DetectFunctionalGroupsTool(BaseTool):
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

class ResolveSmilesToNameTool(BaseTool):
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

class EstimateVolatilityAndNoteTool(BaseTool):
    """
    Estimates the boiling point and volatility classification (Top, Heart, Base note)
    using a Joback-inspired Group Contribution Method.
    """
    # Simplified Joback constants for boiling point: Tb = 198.2 + sum(contribution)
    # These are standard Joback parameters in Kelvin
    _JOBACK_GROUPS = {
        "-[CH3]": (Chem.MolFromSmarts("[CH3;X4]"), 23.58),
        "-[CH2]-": (Chem.MolFromSmarts("[CH2;X4]"), 22.88),
        ">CH-": (Chem.MolFromSmarts("[CH1;X4]"), 21.74),
        ">C<": (Chem.MolFromSmarts("[CH0;X4]"), 18.25),
        "=CH2": (Chem.MolFromSmarts("[CH2;X3]"), 26.88),
        "=CH-": (Chem.MolFromSmarts("[CH1;X3]"), 24.96),
        "=C<": (Chem.MolFromSmarts("[CH0;X3]"), 24.14),
        "#CH": (Chem.MolFromSmarts("[CH1;X2]"), 9.20),
        "#C-": (Chem.MolFromSmarts("[CH0;X2]"), 27.38),
        "-OH (alcohol)": (Chem.MolFromSmarts("[OX2H1;!$(O-C=O)]"), 92.88),
        "-O- (ether)": (Chem.MolFromSmarts("[OX2H0;!$(O-C=O)]"), 31.22),
        ">C=O (ketone)": (Chem.MolFromSmarts("[CX3](=[OX1])[#6]"), 76.75),
        "-CHO (aldehyde)": (Chem.MolFromSmarts("[CX3H1](=[OX1])"), 72.24),
        "-COOH (acid)": (Chem.MolFromSmarts("[CX3](=[OX1])[OX2H1]"), 169.09),
        "-COO- (ester)": (Chem.MolFromSmarts("[CX3](=[OX1])[OX2H0]"), 81.10),
        "Benzene ring atom": (Chem.MolFromSmarts("[c]"), 3.84), # Simplified ring contribution
    }

    @property
    def name(self) -> str:
        return "estimate_volatility_and_note"

    @property
    def description(self) -> str:
        return "Estimates the boiling point (C) and classifies the chemical as a Top, Heart, or Base note based on structural group contributions. Essential for flavor and fragrance formulation."

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
        try:
            with rdBase.BlockLogs():
                mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return {"error": f"Invalid SMILES: {smiles}"}

            total_contribution = 0
            found_groups = {}
            
            # Match each Joback group
            # Note: This is a simplified greedy match. In professional implementations, 
            # we would use a more rigorous atom-typing to avoid double-counting.
            # Here we count matches but try to keep patterns distinct.
            for group_name, (pattern, contribution) in self._JOBACK_GROUPS.items():
                if pattern:
                    matches = mol.GetSubstructMatches(pattern)
                    count = len(matches)
                    if count > 0:
                        total_contribution += (count * contribution)
                        found_groups[group_name] = count

            # Joback Equation for Normal Boiling Point (K)
            # Tb = 198.2 + Σ(ΔTb)
            estimated_bp_k = 198.2 + total_contribution
            estimated_bp_c = estimated_bp_k - 273.15
            
            # Classification logic based on Aromsa proposal
            # Top Note: < 150-180C
            # Heart Note: 180-260C
            # Base Note: > 260C
            if estimated_bp_c < 180:
                note_type = "Top Note"
                desc = "High volatility, first to be perceived, light and fresh."
            elif estimated_bp_c < 260:
                note_type = "Heart Note"
                desc = "Medium volatility, the core character of the flavor."
            else:
                note_type = "Base Note"
                desc = "Low volatility, provides depth and longevity to the formulation."

            return {
                "smiles": smiles,
                "estimated_boiling_point_c": round(estimated_bp_c, 1),
                "odor_note_classification": note_type,
                "volatility_description": desc,
                "detected_structural_groups": found_groups,
                "method": "Simplified Joback Group Contribution",
                "status": "success"
            }
        except Exception as e:
            return {"error": f"Volatility estimation failed: {str(e)}"}

class AuditChemicalCompatibilityTool(BaseTool):
    """
    Scans a list of molecules for reactive functional groups and flags 
    potential incompatibilities based on a unified knowledge database.
    """
    _MATRIX_CACHE = None

    def _load_knowledge(self) -> Dict[str, Any]:
        """Lazily loads the reactivity matrix from DuckDB."""
        if self._MATRIX_CACHE is not None:
            return self._MATRIX_CACHE
        
        try:
            import duckdb
            if os.path.exists(KNOWLEDGE_DB_FILE):
                conn = duckdb.connect(KNOWLEDGE_DB_FILE)
                
                # 1. Load Groups
                groups_df = conn.execute("SELECT group_name, smarts_pattern FROM reactivity_groups").df()
                compiled_groups = {}
                for _, row in groups_df.iterrows():
                    pattern = Chem.MolFromSmarts(row['smarts_pattern'])
                    if pattern:
                        compiled_groups[row['group_name']] = pattern
                
                # 2. Load Rules
                rules = conn.execute("SELECT * FROM reactivity_rules").df().to_dict('records')
                
                conn.close()
                self._MATRIX_CACHE = {
                    "groups": compiled_groups,
                    "rules": rules
                }
                return self._MATRIX_CACHE
        except Exception as e:
            print(f"[Error] Failed to load reactivity knowledge from DB: {e}")
        
        self._MATRIX_CACHE = {"groups": {}, "rules": []}
        return self._MATRIX_CACHE

    @property
    def name(self) -> str:
        return "audit_chemical_compatibility"

    @property
    def description(self) -> str:
        return (
            "Analyzes a list of chemical compounds for potential reactive incompatibilities using the knowledge database. "
            "Flags risks like color changes, aroma loss, toxic gas release (e.g. HCN), or precipitation in mixtures."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "smiles_list": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "A list of SMILES strings representing the formulation components."
                }
            },
            "required": ["smiles_list"]
        }

    def execute(self, smiles_list: List[str]) -> Dict[str, Any]:
        try:
            if not smiles_list or len(smiles_list) < 1:
                return {"error": "Provide at least one SMILES string."}

            knowledge = self._load_knowledge()
            groups_registry = knowledge["groups"]
            rules = knowledge["rules"]

            # 1. Map functional groups for each molecule
            molecule_metadata = []
            for i, smiles in enumerate(smiles_list):
                with rdBase.BlockLogs():
                    mol = Chem.MolFromSmiles(smiles)
                if mol is None:
                    return {"error": f"Invalid SMILES at index {i}: {smiles}"}
                
                detected = set()
                for group_name, pattern in groups_registry.items():
                    if pattern and mol.HasSubstructMatch(pattern):
                        detected.add(group_name)
                
                molecule_metadata.append({
                    "index": i,
                    "smiles": smiles,
                    "groups": detected
                })

            # 2. Audit interactions
            risks_found = []
            from itertools import combinations
            
            for meta in molecule_metadata:
                for rule in rules:
                    # Individual group risk (where group_b is None/NaN)
                    if rule.get("group_b") is None or (isinstance(rule.get("group_b"), float) and np.isnan(rule["group_b"])):
                        if rule["group_a"] in meta["groups"]:
                            risks_found.append({
                                "rule_id": rule["rule_id"],
                                "rule_name": rule["rule_name"],
                                "severity": rule["severity"],
                                "involved_components": [meta["smiles"]],
                                "involved_indices": [meta["index"]],
                                "consequence": rule["consequence"],
                                "description": rule.get("description", "")
                            })

            if len(molecule_metadata) >= 2:
                for m1, m2 in combinations(molecule_metadata, 2):
                    for rule in rules:
                        gA = rule.get("group_a")
                        gB = rule.get("group_b")
                        if gA and gB and not (isinstance(gB, float) and np.isnan(gB)):
                            match = (gA in m1["groups"] and gB in m2["groups"]) or (gB in m1["groups"] and gA in m2["groups"])
                            if match:
                                risks_found.append({
                                    "rule_id": rule["rule_id"],
                                    "rule_name": rule["rule_name"],
                                    "severity": rule["severity"],
                                    "involved_components": [m1["smiles"], m2["smiles"]],
                                    "involved_indices": [m1["index"], m2["index"]],
                                    "consequence": rule["consequence"],
                                    "description": rule.get("description", "")
                                })

            return {
                "total_components_audited": len(smiles_list),
                "risks_detected": risks_found,
                "status": "success",
                "summary": f"Detected {len(risks_found)} potential stability/safety risks in the formulation."
            }
        except Exception as e:
            return {"error": f"Chemical audit failed: {str(e)}"}

class CalculateEmulsionPropertiesTool(BaseTool):
    """
    Calculates hydrophilic-lipophilic balance (HLB) using Griffin's method
    and partitions characteristics (LogP) to assess emulsion stability.
    """
    
    # Hydrophilic groups for Griffin's method (simplified mass-based detection)
    _HYDROPHILIC_PATTERNS = {
        "Hydroxyl (-OH)": Chem.MolFromSmarts("[OX2H1]"),
        "Carboxyl (-COOH)": Chem.MolFromSmarts("[CX3](=[OX1])[OX2H1]"),
        "Ether (-O-)": Chem.MolFromSmarts("[OX2H0;!$(O-C=O)]"),
        "Ester (-COO-)": Chem.MolFromSmarts("[CX3](=[OX1])[OX2H0][#6]"),
        "Amine (-NH2/NH)": Chem.MolFromSmarts("[NX3;H2,H1;!$(N-C=O)]"),
        "Amide (-CONH-)": Chem.MolFromSmarts("[CX3](=[OX1])[NX3H1]"),
        "Ethylene Oxide (EO)": Chem.MolFromSmarts("COCC"), # PEG chain unit
    }

    @property
    def name(self) -> str:
        return "calculate_emulsion_properties"

    @property
    def description(self) -> str:
        return "Calculates HLB (Griffin method) and LogP for a molecule to predict its behavior in oil-in-water or water-in-oil emulsions. Vital for beverage and food emulsion stability."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "smiles": {"type": "string", "description": "The SMILES representation of the molecule."}
            },
            "required": ["smiles"]
        }

    def _get_hydrophilic_mass(self, mol) -> float:
        """Estimates the mass of the hydrophilic portion of the molecule."""
        hydrophilic_atoms = set()
        for name, pattern in self._HYDROPHILIC_PATTERNS.items():
            matches = mol.GetSubstructMatches(pattern)
            for match in matches:
                for idx in match:
                    hydrophilic_atoms.add(idx)
        
        # Calculate sum of atomic weights for these indices
        total_h_mass = 0.0
        for idx in hydrophilic_atoms:
            atom = mol.GetAtomWithIdx(idx)
            total_h_mass += atom.GetMass()
            # Add implicit hydrogens' mass
            total_h_mass += atom.GetTotalNumHs() * 1.008
            
        return total_h_mass

    def execute(self, smiles: str) -> Dict[str, Any]:
        try:
            with rdBase.BlockLogs():
                mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return {"error": f"Invalid SMILES: {smiles}"}

            # 1. Total Molecular Weight
            total_mw = Descriptors.MolWt(mol)
            
            # 2. Hydrophilic Mass (Mh)
            mh = self._get_hydrophilic_mass(mol)
            
            # 3. Griffin HLB = 20 * (Mh / M)
            # Griffin's method scale is 0 to 20
            hlb = 20.0 * (mh / total_mw) if total_mw > 0 else 0.0
            
            # 4. LogP (Hydrophobicity)
            logp = round(Descriptors.MolLogP(mol), 2)
            
            # 5. Interpretation
            if hlb < 6:
                application = "Water-in-Oil (W/O) Emulsifier / Hydrophobic"
                suitability = "Low solubility in water. Best for oil-based flavor concentrates."
            elif hlb < 8:
                application = "Wetting Agent"
                suitability = "Moderate solubility. Good for dispersing powders in liquids."
            elif hlb < 16:
                application = "Oil-in-Water (O/W) Emulsifier"
                suitability = "High water solubility. Ideal for beverage emulsions and clouding agents."
            else:
                application = "Solubilizer or Detergent"
                suitability = "Very high water solubility. Used for creating transparent flavor solutions."

            return {
                "smiles": smiles,
                "molecular_weight": round(total_mw, 2),
                "hydrophilic_mass_estimate": round(mh, 2),
                "hlb_value": round(hlb, 2),
                "logp": logp,
                "recommended_application": application,
                "matrix_suitability": suitability,
                "method": "Griffin's HLB Approximation",
                "status": "success"
            }
        except Exception as e:
            return {"error": f"Emulsion property calculation failed: {str(e)}"}

class CheckRegulatoryComplianceTool(BaseTool):
    """
    Checks a list of chemicals against the unified knowledge database 
    (IFRA and EU 1334/2008) for restrictions or bans.
    """

    @property
    def name(self) -> str:
        return "check_regulatory_compliance"

    @property
    def description(self) -> str:
        return "Checks formulation components against IFRA (Fragrance) and EU 1334/2008 (Food) regulations using the knowledge database. Essential for legal safety audits."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "queries": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "A list of common names, chemical names, or CAS numbers to check."
                }
            },
            "required": ["queries"]
        }

    def execute(self, queries: List[str]) -> Dict[str, Any]:
        """Checks a list of names or CAS numbers against regulatory data in the knowledge DB."""
        try:
            import duckdb
            if not os.path.exists(KNOWLEDGE_DB_FILE):
                return {"error": "Knowledge database not found. Run initialize script first."}
            
            conn = duckdb.connect(KNOWLEDGE_DB_FILE)
            results = []
            
            for query in queries:
                is_cas = "-" in query and any(char.isdigit() for char in query)
                
                if is_cas:
                    ifra_res = conn.execute(
                        "SELECT * FROM ifra_standards WHERE cas_no = ?", [query]
                    ).df()
                    eu_res = conn.execute(
                        "SELECT * FROM eu_flavorings WHERE cas_no = ?", [query]
                    ).df()
                else:
                    ifra_res = conn.execute(
                        "SELECT * FROM ifra_standards WHERE substance_name ILIKE ?", 
                        [f"%{query}%"]
                    ).df()
                    eu_res = conn.execute(
                        "SELECT * FROM eu_flavorings WHERE substance_name ILIKE ?", 
                        [f"%{query}%"]
                    ).df()
                
                mol_summary = {
                    "query": query,
                    "ifra_status": "Not Found / GRAS" if ifra_res.empty else "RESTRICTED/BANNED",
                    "eu_status": "Not Found / GRAS" if eu_res.empty else "RESTRICTED/BANNED",
                    "details": []
                }
                
                if not ifra_res.empty:
                    for _, row in ifra_res.iterrows():
                        mol_summary["details"].append({
                            "source": "IFRA 51st Amendment",
                            "substance": row['substance_name'],
                            "cas": row['cas_no'],
                            "status": row['status'],
                            "limit": row['max_limit'],
                            "type": row['restriction_type']
                        })
                
                if not eu_res.empty:
                    for _, row in eu_res.iterrows():
                        mol_summary["details"].append({
                            "source": "EU 1334/2008",
                            "substance": row['substance_name'],
                            "cas": row['cas_no'],
                            "status": row['status'],
                            "restrictions": row['restrictions']
                        })
                
                results.append(mol_summary)
            
            conn.close()
            
            return {
                "total_checked": len(queries),
                "compliance_report": results,
                "status": "success",
                "notice": "This is a preliminary screen. Final compliance must be verified against current official legal texts."
            }
        except Exception as e:
            return {"error": f"Regulatory check failed: {str(e)}"}

class CalculateHansenParametersTool(BaseTool):
    """
    Calculates Hansen Solubility Parameters (HSP) using Van Krevelen 
    Group Contribution Method. Estimates Dispersion (dD), Polar (dP), 
    and Hydrogen Bonding (dH) components.
    """

    # Van Krevelen Group Contributions (simplified)
    # Fd (Dispersive), Fp (Polar), Eh (H-bonding energy), V (Molar volume)
    # Values based on standard Van Krevelen tables
    _GROUPS = [
        # Halogens
        ("[Cl]", {"fd": 450, "fp": 550, "eh": 400, "v": 24.0, "name": "Chloride"}),
        ("[Br]", {"fd": 550, "fp": 340, "eh": 0, "v": 30.0, "name": "Bromide"}),
        ("[F]", {"fd": 80, "fp": 420, "eh": 0, "v": 10.0, "name": "Fluoride"}),
        
        # Carbonyls & Oxygen groups
        ("[CX3H1](=[OX1])", {"fd": 470, "fp": 800, "eh": 4500, "v": 17.0, "name": "Aldehyde"}),
        ("[CX3](=[OX1])[OX2H0]", {"fd": 390, "fp": 400, "eh": 7000, "v": 18.0, "name": "Ester"}),
        ("[CX3](=[OX1])", {"fd": 290, "fp": 770, "eh": 2000, "v": 10.8, "name": "Ketone"}),
        ("[CX3](=[OX1])[OX2H1]", {"fd": 530, "fp": 420, "eh": 10000, "v": 28.5, "name": "Acid"}),
        ("[OX2H1]", {"fd": 210, "fp": 500, "eh": 20000, "v": 10.0, "name": "Hydroxyl"}),
        ("[OX2H0]", {"fd": 100, "fp": 400, "eh": 3000, "v": 3.8, "name": "Ether"}),
        
        # Nitrogen groups
        ("[NX3H2]", {"fd": 280, "fp": 400, "eh": 10000, "v": 19.2, "name": "Amine (Primary)"}),
        ("[NX3H1]", {"fd": 160, "fp": 210, "eh": 3100, "v": 4.5, "name": "Amine (Secondary)"}),
        ("[NX3H0]", {"fd": 20, "fp": 800, "eh": 5000, "v": -9.0, "name": "Amine (Tertiary)"}),
        ("[CX2]#[NX1]", {"fd": 350, "fp": 1100, "eh": 2500, "v": 24.0, "name": "Nitrile"}),
        
        # Hydrocarbons (Aromatic)
        ("[cX3H1]", {"fd": 190, "fp": 17, "eh": 0, "v": 16.7, "name": "Aromatic CH"}),
        ("[cX3H0]", {"fd": 143, "fp": 34, "eh": 0, "v": 11.5, "name": "Aromatic C"}),
        
        # Hydrocarbons (Aliphatic)
        ("[CH3;X4]", {"fd": 420, "fp": 0, "eh": 0, "v": 33.5, "name": "Methyl"}),
        ("[CH2;X4]", {"fd": 270, "fp": 0, "eh": 0, "v": 16.1, "name": "Methylene"}),
        ("[CH1;X4]", {"fd": 80, "fp": 0, "eh": 0, "v": -1.0, "name": "Methine"}),
        ("[CH0;X4]", {"fd": -70, "fp": 0, "eh": 0, "v": -19.2, "name": "Quaternary C"}),
        ("[CH2;X3]", {"fd": 400, "fp": 0, "eh": 0, "v": 28.5, "name": "Vinyl =CH2"}),
        ("[CH1;X3]", {"fd": 200, "fp": 0, "eh": 0, "v": 13.5, "name": "Vinyl =CH-"}),
        ("[CH0;X3]", {"fd": 70, "fp": 0, "eh": 0, "v": -5.5, "name": "Vinyl =C<"}),
    ]

    @property
    def name(self) -> str:
        return "calculate_hansen_parameters"

    @property
    def description(self) -> str:
        return (
            "Calculates Hansen Solubility Parameters (dD, dP, dH) using the Van Krevelen group contribution method. "
            "Helps predict solubility, solvent compatibility, and resin behavior."
        )

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
        try:
            with rdBase.BlockLogs():
                mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return {"error": f"Invalid SMILES: {smiles}"}
            
            # Ensure hydrogens are added for correct valence matching if needed, 
            # though our SMARTS are designed for heavy atoms.
            
            total_fd = 0.0
            total_fp2 = 0.0
            total_eh = 0.0
            total_v = 0.0
            
            matched_atoms = set()
            details = []
            
            # Pre-compile SMARTS patterns
            compiled_groups = []
            for smarts, data in self._GROUPS:
                compiled_groups.append((Chem.MolFromSmarts(smarts), data))
            
            # Apply group contribution
            # We sort groups by complexity (number of atoms) to ensure specific groups match first
            for pattern, data in compiled_groups:
                if pattern is None: continue
                matches = mol.GetSubstructMatches(pattern)
                for match in matches:
                    # Check if any atom in this match was already counted in a more specific group
                    if any(idx in matched_atoms for idx in match):
                        continue
                    
                    total_fd += data["fd"]
                    total_fp2 += data["fp"]**2
                    total_eh += data["eh"]
                    total_v += data["v"]
                    
                    for idx in match:
                        matched_atoms.add(idx)
                    
                    details.append(data["name"])

            # Safety check for unassigned heavy atoms
            unmatched_heavy = [a.GetSymbol() for a in mol.GetAtoms() if a.GetIdx() not in matched_atoms and a.GetAtomicNum() > 1]
            
            if total_v <= 0:
                return {"error": "Could not determine molar volume for this structure. Group contribution may be incomplete."}

            # Final calculations (Van Krevelen equations)
            dd = total_fd / total_v
            dp = math.sqrt(total_fp2) / total_v
            dh = math.sqrt(total_eh / total_v)
            dtot = math.sqrt(dd**2 + dp**2 + dh**2)

            return {
                "smiles": smiles,
                "delta_d": round(dd, 2),
                "delta_p": round(dp, 2),
                "delta_h": round(dh, 2),
                "delta_total": round(dtot, 2),
                "molar_volume_est": round(total_v, 2),
                "units": "MPa^0.5",
                "groups_detected": list(set(details)),
                "unmatched_heavy_atoms": unmatched_heavy,
                "status": "success"
            }
        except Exception as e:
            return {"error": f"HSP calculation failed: {str(e)}"}

class EstimatePkaAndLogDTool(BaseTool):
    """
    Estimates the pKa of ionizable groups and calculates the distribution 
    coefficient (logD) at a given pH. Essential for food/beverage applications 
    where pH affects solubility and flavor release.
    """

    # Typical pKa values for common industrial/food chemical groups
    # Note: These are 'screening-grade' estimates.
    _ACIDIC_GROUPS = [
        ("Sulfonic Acid", Chem.MolFromSmarts("S(=O)(=O)[OH]"), -1.0),
        ("Carboxylic Acid (Aromatic)", Chem.MolFromSmarts("c1ccccc1C(=O)[OH]"), 4.2),
        ("Carboxylic Acid (Aliphatic)", Chem.MolFromSmarts("C(=O)[OH]"), 4.8),
        ("Phenol", Chem.MolFromSmarts("[OX2H1]c1ccccc1"), 10.0),
        ("Alcohol", Chem.MolFromSmarts("[OX2H1]"), 16.0), # Virtually non-ionizable in water
    ]

    _BASIC_GROUPS = [
        ("Amine (Aliphatic)", Chem.MolFromSmarts("[NX3;H2,H1,H0;!$(N-C=O);!$(N-c)]"), 10.6),
        ("Amine (Aromatic/Aniline)", Chem.MolFromSmarts("[NX3;H2,H1,H0;!$(N-C=O)]c1ccccc1"), 4.6),
        ("Pyridine", Chem.MolFromSmarts("c1ccncc1"), 5.2),
        ("Amide", Chem.MolFromSmarts("[CX3](=O)[NX3]"), -0.5), # Very weak base
    ]

    @property
    def name(self) -> str:
        return "estimate_pka_and_logd"

    @property
    def description(self) -> str:
        return (
            "Estimates the pKa of the most acidic or basic group and calculates the "
            "logD (distribution coefficient) at a specified pH. Use this to understand "
            "how a molecule behaves in acidic (e.g., beverages) vs. neutral environments."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "smiles": {"type": "string", "description": "The SMILES representation of the molecule."},
                "ph": {
                    "type": "number", 
                    "description": "The pH at which to calculate logD (default is 7.4).",
                    "default": 7.4
                }
            },
            "required": ["smiles"]
        }

    def execute(self, smiles: str, ph: float = 7.4) -> Dict[str, Any]:
        try:
            with rdBase.BlockLogs():
                mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                return {"error": f"Invalid SMILES: {smiles}"}

            # 1. Calculate base LogP
            logp = float(Descriptors.MolLogP(mol))

            # 2. Identify pKa
            # Find the strongest acid (lowest pKa) and strongest base (highest pKa)
            acidic_found = []
            for name, pattern, val in self._ACIDIC_GROUPS:
                if mol.HasSubstructMatch(pattern):
                    acidic_found.append({"group": name, "pka": val})
            
            basic_found = []
            for name, pattern, val in self._BASIC_GROUPS:
                if mol.HasSubstructMatch(pattern):
                    basic_found.append({"group": name, "pka": val})

            # Sort to find the most relevant pKa
            # For acids, we care about the most acidic one (lowest pKa)
            # For bases, we care about the most basic one (highest pKa)
            strongest_acid = min(acidic_found, key=lambda x: x["pka"]) if acidic_found else None
            strongest_base = max(basic_found, key=lambda x: x["pka"]) if basic_found else None

            # 3. Determine dominant ionizable state and calculate LogD
            # Henderson-Hasselbalch derived formulas
            logd = logp
            pka_used = None
            mol_type = "Neutral"

            if strongest_acid and strongest_base:
                # Amphoteric (e.g. amino acids) - simplify to the more extreme one
                # This is a rough approximation
                if abs(ph - strongest_acid["pka"]) < abs(ph - strongest_base["pka"]):
                    mol_type = "Acidic (Amphoteric)"
                    pka_used = strongest_acid["pka"]
                    logd = logp - math.log10(1 + 10**(ph - pka_used))
                else:
                    mol_type = "Basic (Amphoteric)"
                    pka_used = strongest_base["pka"]
                    logd = logp - math.log10(1 + 10**(pka_used - ph))
            elif strongest_acid:
                mol_type = "Acidic"
                pka_used = strongest_acid["pka"]
                # For acids: logD = logP - log10(1 + 10^(pH - pKa))
                logd = logp - math.log10(1 + 10**(ph - pka_used))
            elif strongest_base:
                mol_type = "Basic"
                pka_used = strongest_base["pka"]
                # For bases: logD = logP - log10(1 + 10^(pKa - pH))
                logd = logp - math.log10(1 + 10**(pka_used - ph))

            return {
                "smiles": smiles,
                "ph": ph,
                "logp_neutral": round(logp, 2),
                "logd_at_ph": round(logd, 2),
                "estimated_pka": round(pka_used, 2) if pka_used is not None else None,
                "molecule_type": mol_type,
                "ionizable_groups_found": {
                    "acidic": [g["group"] for g in acidic_found],
                    "basic": [g["group"] for g in basic_found]
                },
                "interpretation": (
                    f"At pH {ph}, the molecule is estimated to have a distribution coefficient (logD) of {round(logd, 2)}. "
                    f"A lower logD compared to logP indicates the molecule is partially ionized, making it more water-soluble."
                ),
                "status": "success"
            }

        except Exception as e:
            return {"error": f"pKa/logD estimation failed: {str(e)}"}

# Register all RDKit tools
ToolRegistry.register(ResolveNameToSmilesTool())
ToolRegistry.register(CalculateMolecularPropertiesTool())
ToolRegistry.register(GenerateMoleculeImageTool())
ToolRegistry.register(FetchChemicalSafetyDataTool())
ToolRegistry.register(SearchSubstructureTool())
ToolRegistry.register(CalculateMolecularSimilarityTool())
ToolRegistry.register(SearchAdvancedSubstructureTool())
ToolRegistry.register(FindMaximumCommonSubstructureTool())
ToolRegistry.register(InterpretSmartsTool())
ToolRegistry.register(DeconstructCoreAndSidechainsTool())
ToolRegistry.register(GetMolecularFormulaAndChargeTool())
ToolRegistry.register(ConvertSmilesToInchiTool())
ToolRegistry.register(CountHeavyAtomsAndRingsTool())
ToolRegistry.register(DetectFunctionalGroupsTool())
ToolRegistry.register(ResolveSmilesToNameTool())
ToolRegistry.register(EstimateVolatilityAndNoteTool())
ToolRegistry.register(AuditChemicalCompatibilityTool())
ToolRegistry.register(CalculateEmulsionPropertiesTool())
ToolRegistry.register(CheckRegulatoryComplianceTool())
ToolRegistry.register(CalculateHansenParametersTool())
ToolRegistry.register(EstimatePkaAndLogDTool())
ToolRegistry.register(CalculateAllDescriptorsTool())
ToolRegistry.register(ExportMoleculeFileTool())

# Legacy functions kept for backward compatibility
# but the agent should now use ToolRegistry.
def calculate_molecular_properties(smiles: str) -> dict:
    return CalculateMolecularPropertiesTool().execute(smiles)

def generate_molecule_image(smiles: str, file_path: str) -> dict:
    return GenerateMoleculeImageTool().execute(smiles, file_path)

def fetch_chemical_safety_data(molecule_name: str) -> dict:
    return FetchChemicalSafetyDataTool().execute(molecule_name)

def resolve_name_to_smiles(molecule_name: str) -> dict:
    return ResolveNameToSmilesTool().execute(molecule_name)

def search_substructure(smiles: str, pattern: str, use_chirality: bool = False) -> dict:
    return SearchSubstructureTool().execute(smiles, pattern, use_chirality)

def calculate_molecular_similarity(smiles1: str, smiles2: str) -> dict:
    return CalculateMolecularSimilarityTool().execute(smiles1, smiles2)

def search_advanced_substructure(smiles: str, pattern: str, constraint_atom_idx: int, query_type: str) -> dict:
    return SearchAdvancedSubstructureTool().execute(smiles, pattern, constraint_atom_idx, query_type)

def find_maximum_common_substructure(smiles_list: List[str], ring_matches_ring_only: bool = False, complete_rings_only: bool = False) -> dict:
    return FindMaximumCommonSubstructureTool().execute(smiles_list, ring_matches_ring_only, complete_rings_only)

def interpret_smarts_pattern(smarts: str) -> dict:
    return InterpretSmartsTool().execute(smarts)

def deconstruct_core_and_sidechains(smiles: str, core_smarts_or_smiles: str) -> dict:
    return DeconstructCoreAndSidechainsTool().execute(smiles, core_smarts_or_smiles)

def canonicalize_and_validate_smiles(smiles: str) -> dict:
    # Now maps to the more comprehensive StandardizeMoleculeTool
    return StandardizeMoleculeTool().execute(
        smiles=smiles, 
        remove_salts=False, 
        neutralize=False, 
        canonicalize_tautomer=False
    )

def get_molecular_formula_and_charge(smiles: str) -> dict:
    return GetMolecularFormulaAndChargeTool().execute(smiles)

def convert_smiles_to_inchi(smiles: str) -> dict:
    return ConvertSmilesToInchiTool().execute(smiles)

def count_heavy_atoms_and_rings(smiles: str) -> dict:
    return CountHeavyAtomsAndRingsTool().execute(smiles)

def detect_functional_groups(smiles: str) -> dict:
    return DetectFunctionalGroupsTool().execute(smiles)

def resolve_smiles_to_name(smiles: str) -> dict:
    return ResolveSmilesToNameTool().execute(smiles)

def estimate_volatility_and_note(smiles: str) -> dict:
    return EstimateVolatilityAndNoteTool().execute(smiles)

def audit_chemical_compatibility(smiles_list: List[str]) -> dict:
    return AuditChemicalCompatibilityTool().execute(smiles_list)

def calculate_emulsion_properties(smiles: str) -> dict:
    return CalculateEmulsionPropertiesTool().execute(smiles)

def check_regulatory_compliance(molecule_names: List[str]) -> dict:
    return CheckRegulatoryComplianceTool().execute(molecule_names)

def calculate_hansen_parameters(smiles: str) -> dict:
    return CalculateHansenParametersTool().execute(smiles)

def estimate_pka_and_logd(smiles: str, ph: float = 7.4) -> dict:
    return EstimatePkaAndLogDTool().execute(smiles, ph)

def calculate_all_descriptors(smiles: str) -> dict:
    return CalculateAllDescriptorsTool().execute(smiles)

def export_molecule_file(smiles: str, file_path: str, generate_3d: bool = False) -> dict:
    return ExportMoleculeFileTool().execute(smiles, file_path, generate_3d)
