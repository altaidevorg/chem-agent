import json
import urllib.parse
import urllib.request
import duckdb
import os
import time

def fetch_pubchem_regulatory_data(molecule_name):
    """
    Fetches regulatory information from PubChem PUG-VIEW API for a given molecule.
    """
    try:
        # 1. Resolve name to CID first
        safe_name = urllib.parse.quote(molecule_name)
        cid_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{safe_name}/cids/JSON"
        req_cid = urllib.request.Request(cid_url, headers={'User-Agent': 'ChemAgent/1.0'})
        
        with urllib.request.urlopen(req_cid, timeout=5) as response:
            cid_data = json.loads(response.read().decode('utf-8'))
            cid = cid_data["IdentifierList"]["CID"][0]
            
        # 2. Get Regulatory Information section from PUG-VIEW
        # Note: 'Regulatory Information' section index can vary, so we fetch the full compound summary
        view_url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON?heading=Regulatory+Information"
        req_view = urllib.request.Request(view_url, headers={'User-Agent': 'ChemAgent/1.0'})
        
        with urllib.request.urlopen(req_view, timeout=10) as response:
            view_data = json.loads(response.read().decode('utf-8'))
            
        return cid, view_data
    except Exception as e:
        print(f"Error fetching data for {molecule_name}: {e}")
        return None, None

def extract_regulatory_notes(view_data):
    """
    Helper to extract specific regulatory strings from PubChem's complex JSON structure.
    """
    notes = []
    
    def _find_strings(node):
        if isinstance(node, dict):
            if "Value" in node and "StringWithMarkup" in node["Value"]:
                for item in node["Value"]["StringWithMarkup"]:
                    notes.append(item["String"])
            for v in node.values():
                _find_strings(v)
        elif isinstance(node, list):
            for item in node:
                _find_strings(item)
                
    _find_strings(view_data)
    return notes

def update_db_for_molecule(molecule_name):
    db_path = "data/regulatory.db"
    conn = duckdb.connect(db_path)
    
    print(f"Updating data for: {molecule_name}...")
    cid, view_data = fetch_pubchem_regulatory_data(molecule_name)
    
    if not view_data:
        conn.close()
        return False
        
    notes = extract_regulatory_notes(view_data)
    combined_notes = " | ".join(notes)
    
    # Simple logic: If 'food' or 'flavor' is in notes, add to eu_flavorings
    # If 'fragrance' or 'cosmetic' is in notes, add to ifra_standards
    # In a real app, we would use regex to be more precise
    
    is_food = any(kw in combined_notes.lower() for kw in ['food', 'flavor', 'flavour', 'fema', 'gras'])
    is_fragrance = any(kw in combined_notes.lower() for kw in ['fragrance', 'cosmetic', 'ifra', 'skin'])
    
    status = "Identified"
    if any(kw in combined_notes.lower() for kw in ['banned', 'prohibited', 'forbidden']):
        status = "Banned"
    elif any(kw in combined_notes.lower() for kw in ['restricted', 'limit', 'max']):
        status = "Restricted"

    # Get CAS No from PubChem if possible
    cas_no = "Unknown"
    # (Simplified: in a full version we would fetch CAS from PubChem properties)

    if is_food:
        conn.execute("INSERT INTO eu_flavorings (cas_no, substance_name, restrictions, status, source) VALUES (?, ?, ?, ?, ?)", 
                     (cas_no, molecule_name, combined_notes[:500], status, 'PubChem Regulatory Data'))
        print(f"Added {molecule_name} to EU Flavorings table.")

    if is_fragrance:
        conn.execute("INSERT INTO ifra_standards (cas_no, substance_name, restriction_type, max_limit, status, source) VALUES (?, ?, ?, ?, ?, ?)", 
                     (cas_no, molecule_name, status, "See Notes", status, 'PubChem Regulatory Data'))
        print(f"Added {molecule_name} to IFRA Standards table.")

    conn.close()
    return True

if __name__ == "__main__":
    # Example: Update for a few more relevant molecules
    for mol in ['Cinnamaldehyde', 'Eugenol', 'Thymol', 'Menthol']:
        update_db_for_molecule(mol)
        time.sleep(1) # Be nice to API
