# src/skills/rdkit_skills.py
import urllib.request
import urllib.parse
import json
import sys
from io import StringIO
from collections import deque
from rdkit import Chem
from rdkit import rdBase  # İleri düzey hata log yönetimi için
from rdkit.Chem import Descriptors
from rdkit import DataStructs
from rdkit.Chem import rdFingerprintGenerator 
from rdkit.Chem import AllChem

# RDKit'in C++ loglarını Python standart hata akışına yönlendiriyoruz
rdBase.WrapLogs()

def calculate_molecular_properties(smiles: str) -> dict:
    """Parses a SMILES string and computes standard physicochemical properties using advanced RDKit features."""
    # RDKit C++ konsol çıktısını yakalamak için bellek içi bir buffer oluşturuyoruz
    sio = StringIO()
    sys.stderr = sio
    
    try:
        # 1. ADIM: İleri düzey parser parametrelerini hazırlıyoruz
        params = Chem.SmilesParserParams()
        params.sanitize = True
        params.allowCXSMILES = True  # Veri tabanlarından gelebilecek genişletilmiş şemaları destekler
        
        mol = Chem.MolFromSmiles(smiles, params)
        sanitized = True
        fallback_reason = None
        
        # 2. ADIM: Eğer katı süzgeçli ayrıştırma başarısız olursa Fallback mekanizmasını çalıştır
        if mol is None:
            # RDKit'in C++ tarafında ürettiği gerçek hata mesajını yakalıyoruz
            error_msg = sio.getvalue().strip()
            
            # Sanitizasyonu kapatıp sadece ham topolojiyi okumayı deniyoruz
            params.sanitize = False
            mol = Chem.MolFromSmiles(smiles, params)
            
            if mol is not None:
                # Topoloji başarıyla okundu, şimdi sadece hataya sebep olan 'PROPERTIES' aşamasını dışarıda bırakarak süzüyoruz
                try:
                    Chem.SanitizeMol(mol, Chem.SanitizeFlags.SANITIZE_ALL ^ Chem.SanitizeFlags.SANITIZE_PROPERTIES)
                    sanitized = False
                    fallback_reason = f"Partial Sanitization applied. Native parser error: {error_msg}"
                except Exception as sanit_err:
                    return {"error": f"SMILES topology loaded but sanitization completely failed: {str(sanit_err)}. Parser log: {error_msg}"}
            else:
                return {"error": f"SMILES Parse/Syntax Error. RDKit Core Log: {error_msg}"}
        
        # 3. ADIM: Hesaplamaları süzgeç durumuna göre esneterek yapıyoruz
        # Eğer kısmi moddaysak değerlik hatası üretebilecek hassas descriptor'ları güvenli değerlerle geçiyoruz
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
        # Sistem stderr akışını orijinal haline geri döndürüyoruz
        sys.stderr = sys.__stderr__


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