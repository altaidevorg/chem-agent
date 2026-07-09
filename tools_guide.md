# 🧪 ChemAgent Skills Documentation

This document provides a detailed overview of the 16 specialized chemical informatics skills available to the ChemAgent. Each section includes the skill's purpose, how it works, and real-world execution examples.

---

## 1. `ResolveNameToSmilesSkill`

### 📝 Description
Resolves common drug names, commercial names, or chemical names (e.g., "Ibuprofen", "Aspirin") into their accurate, verified SMILES strings using the PubChem API. This is typically the first step in any chemical analysis when a name is provided instead of a structure.

### 🛠 How it Works
1. Receives a molecule name as input.
2. Sends a robust HTTP POST request to the PubChem PUG REST API.
3. Parses the JSON response to extract canonical or isomeric SMILES.
4. Returns the verified SMILES string to the agent for further processing.

### 📊 Execution Examples

#### Example 1: Aspirin Resolution (Easy)
- **User Query:** "Could you resolve the common drug name 'Aspirin' into its accurate SMILES string?"
- **Tool Call:** `resolve_name_to_smiles(molecule_name="Aspirin")`
- **Result:**
  ```json
  {
    "molecule_name": "Aspirin",
    "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
    "status": "success"
  }
  ```
- **Final Response:** "I've successfully resolved the common drug name **Aspirin** into its accurate SMILES string: `CC(=O)OC1=CC=CC=C1C(=O)O`..."

#### Example 2: D-Glucose (Hard - Stereochemistry Preserved)
- **User Query:** "Please find the exact verified SMILES string for 'D-Glucose', ensuring the stereochemistry is preserved."
- **Tool Call:** `resolve_name_to_smiles(molecule_name="D-Glucose")`
- **Result:**
  ```json
  {
    "molecule_name": "D-Glucose",
    "smiles": "C([C@@H]1[C@H]([C@@H]([C@H](C(O1)O)O)O)O)O",
    "status": "success"
  }
  ```
- **Final Response:** "I've successfully resolved **D-Glucose** into its accurate SMILES string with stereochemistry preserved: `C([C@@H]1[C@H]([C@@H]([C@H](C(O1)O)O)O)O)O`..."

---

## 2. `CalculateMolecularPropertiesSkill`

### 📝 Description
Calculates essential physicochemical properties of a chemical compound given its SMILES string. This tool is fundamental for understanding a molecule's behavior, solubility, and drug-likeness (e.g., Lipinski's Rule of Five).

### 🛠 How it Works
1. Receives a SMILES string as input.
2. Uses RDKit's `Descriptors` module to compute:
   - **Molecular Weight**: Total mass of the molecule.
   - **LogP**: Octanol-water partition coefficient (lipophilicity).
   - **Hydrogen Bond Donors (HBD)**: Count of NH or OH groups.
   - **Hydrogen Bond Acceptors (HBA)**: Count of N or O atoms.
3. Returns a structured dictionary containing these values.

### 📊 Execution Examples

#### Example 1: Ethanol Properties (Easy)
- **User Query:** "Calculate the molecular weight, LogP, and hydrogen bond donors/acceptors for this simple structure: CCO"
- **Tool Call:** `calculate_molecular_properties(smiles="CCO")`
- **Result:**
  ```json
  {
    "smiles": "CCO",
    "molecular_weight": 46.07,
    "log_p": -0.0,
    "h_bond_donors": 1,
    "h_bond_acceptors": 1,
    "parsing_status": "Success"
  }
  ```
- **Final Response Summary:** "Molecular Weight: 46.07 g/mol, LogP: -0.0, H-Bond Donors: 1, H-Bond Acceptors: 1. This profile confirms ethanol is a polar, water-soluble alcohol..."

#### Example 2: Complex Drug Molecule (Hard)
- **User Query:** "What are the physicochemical properties of this complex compound? SMILES: CC1=C(C(=O)N(C2=CC=CC=C12)C)C3=CC=C(C=C3)Cl"
- **Tool Call:** `calculate_molecular_properties(smiles="CC1=C(C(=O)N(C2=CC=CC=C12)C)C3=CC=C(C=C3)Cl")`
- **Result:**
  ```json
  {
    "smiles": "CC1=C(C(=O)N(C2=CC=CC=C12)C)C3=CC=C(C=C3)Cl",
    "molecular_weight": 283.76,
    "log_p": 4.17,
    "h_bond_donors": 0,
    "h_bond_acceptors": 1,
    "parsing_status": "Success"
  }
  ```
- **Final Response Summary:** "This complex compound has a molecular weight of 283.76 g/mol and a high LogP of 4.17, indicating significant lipophilicity. It has no hydrogen bond donors and one acceptor."

---

## 3. `GenerateMoleculeImageSkill`

### 📝 Description
Generates a high-quality 2D chemical structure diagram (PNG) from a SMILES string and saves it to a specified path within the `output/` directory. This is essential for visual verification of molecular structures.

### 🛠 How it Works
1. Receives a SMILES string and a target file path.
2. Automatically creates parent directories if they don't exist.
3. Uses RDKit's `AllChem.Compute2DCoords` to calculate optimal atom placements.
4. Renders the molecule using `Draw.MolToFile` at a standard 400x400 resolution.
5. Returns the status and the local path of the generated image.

### 📊 Execution Examples

#### Example 1: Simple Molecule (Ethanol) (Easy)
- **User Query:** "Generate a 2D image diagram for the SMILES 'CCO' and save it to 'output/ethanol.png'"
- **Tool Call:** `generate_molecule_image(smiles="CCO", file_path="output/ethanol.png")`
- **Result:**
  ```json
  {
    "smiles": "CCO",
    "file_path": "output/ethanol.png",
    "status": "success",
    "message": "Molecule image successfully generated and saved to disk."
  }
  ```
- **Generated Image:**
![Ethanol Structure](/home/ubuntu/chem-agent/output/ethanol.png)

#### Example 2: Complex Fused Ring System (Hard - Nested Directory)
- **User Query:** "Please render a 2D structure of this fused steroid skeleton and save it inside a nested directory: 'output/complex/steroid_derivative.png' for SMILES: CC12CCC3C(C1CCC2=O)CCC4=CC(=O)CCC34C"
- **Tool Call:** `generate_molecule_image(smiles="CC12CCC3C(C1CCC2=O)CCC4=CC(=O)CCC34C", file_path="output/complex/steroid_derivative.png")`
- **Result:**
  ```json
  {
    "smiles": "CC12CCC3C(C1CCC2=O)CCC4=CC(=O)CCC34C",
    "file_path": "output/complex/steroid_derivative.png",
    "status": "success"
  }
  ```
- **Generated Image:**
![Steroid Derivative](/home/ubuntu/chem-agent/output/complex/steroid_derivative.png)

---

## 4. `FetchChemicalSafetyDataSkill`

### 📝 Description
Retrieves official GHS hazard classifications, hazard statement H-codes, precautionary statement P-codes, and the signal word for a chemical compound from PubChem. This tool is critical for safety assessments and regulatory compliance.

### 🛠 How it Works
1. Receives a `molecule_name` as input.
2. Resolves the name to a PubChem CID using a robust HTTP POST request.
3. Fetches the "Safety and Hazards" section from the PubChem PUG-VIEW API.
4. Parses the JSON response to extract GHS classifications, signal words, H-codes, and P-codes.
5. Cross-references P-codes with a lazily-loaded GHS dictionary to provide human-readable descriptions.

### 📊 Execution Examples

#### Example 1: Acetone Safety Data (Easy)
- **User Query:** "Fetch the official GHS hazard classifications, H-codes, and P-codes for 'Acetone'."
- **Tool Call:** `fetch_chemical_safety_data(molecule_name="Acetone")`
- **Result:**
  ```json
  {
    "molecule_name": "Acetone",
    "cid": 180,
    "signal_word": "Danger",
    "hazard_statements": [
      "H225: Highly Flammable liquid and vapor [Danger Flammable liquids]",
      "H319: Causes serious eye irritation [Warning Serious eye damage/eye irritation]",
      "H336: May cause drowsiness or dizziness [Warning Specific target organ toxicity, single exposure; Narcotic effects]"
    ],
    "precautionary_statements": [
      "P210: Keep away from heat, hot surface, sparks, open flames and other ignition sources. No smoking.",
      "P233: Keep container tightly closed.",
      "P280: Wear protective gloves/protective clothing/eye protection/face protection/hearing protection/...",
      "P305+P351+P338: IF IN EYES: / Rinse cautiously with water for several minutes. / Remove contact lenses, if present and easy to do. Continue rinsing."
    ],
    "status": "success"
  }
  ```

#### Example 2: Methotrexate Safety Data (Hard - Chemotherapy Drug)
- **User Query:** "I need the full chemical safety dossier and precautionary statements for 'Methotrexate' from PubChem."
- **Tool Call:** `fetch_chemical_safety_data(molecule_name="Methotrexate")`
- **Result:**
  ```json
  {
    "molecule_name": "Methotrexate",
    "cid": 126941,
    "signal_word": "Danger",
    "hazard_statements": [
      "H301: Toxic if swallowed [Danger Acute toxicity, oral]",
      "H340: May cause genetic defects [Danger Germ cell mutagenicity]",
      "H360: May damage fertility or the unborn child [Danger Reproductive toxicity]",
      "..."
    ],
    "precautionary_statements": [
      "P203: Obtain, read and follow all safety instructions before use.",
      "P301+P316: IF SWALLOWED: / Get emergency medical help immediately.",
      "P318: if exposed or concerned, get medical advice.",
      "..."
    ],
    "status": "success"
  }
  ```

---

## 5. `SearchSubstructureSkill`

### 📝 Description
Searches for a specific substructure or SMARTS pattern within a target molecule, with optional strict stereochemistry/chirality matching.

### 🛠 How it Works
1. Receives a `smiles` string and a `pattern` (SMILES or SMARTS).
2. Optionally receives a `chirality_enforced` boolean (defaults to `false`).
3. Uses RDKit's `HasSubstructMatch` and `GetSubstructMatches` to find occurrences.
4. Returns the match count and the atom indices of the matches.

### 📊 Execution Examples

#### Example 1: Benzene Ring in Toluene (Easy)
- **User Query:** "Check if this molecule contains a benzene ring pattern. Target: CC1=CC=CC=C1, Pattern: c1ccccc1"
- **Tool Call:** `search_substructure(smiles="CC1=CC=CC=C1", pattern="c1ccccc1", chirality_enforced=false)`
- **Result:**
  ```json
  {
    "target_smiles": "CC1=CC=CC=C1",
    "pattern": "c1ccccc1",
    "has_match": true,
    "match_count": 1,
    "atom_indices": [[1, 2, 3, 4, 5, 6]],
    "chirality_enforced": false,
    "status": "success"
  }
  ```

#### Example 2: Chirality Enforced Match (Hard - Lactic Acid)
- **User Query:** "Perform a substructure match enforcing chirality for this pattern inside the target. Target: CC(O)C(=O)O, Pattern: [CX4H]([OH])(C)C(=O)O"
- **Tool Call:** `search_substructure(smiles="CC(O)C(=O)O", pattern="[CX4H]([OH])(C)C(=O)O", chirality_enforced=true)`
- **Result:**
  ```json
  {
    "target_smiles": "CC(O)C(=O)O",
    "pattern": "[CX4H]([OH])(C)C(=O)O",
    "has_match": true,
    "match_count": 1,
    "atom_indices": [[1, 2, 0, 3, 4, 5]],
    "chirality_enforced": true,
    "status": "success"
  }
  ```

---

## 6. `CalculateMolecularSimilaritySkill`

### 📝 Description
Calculates the structural Tanimoto similarity score between two molecules using Morgan fingerprints.

### 🛠 How it Works
1. Receives two SMILES strings (`smiles1`, `smiles2`).
2. Generates Morgan fingerprints (radius=2, 2048 bits) for both molecules.
3. Computes the Tanimoto similarity coefficient.
4. Returns the score as a decimal and a percentage.

### 📊 Execution Examples

#### Example 1: Ethanol vs. Propanol (Easy)
- **User Query:** "Calculate the Tanimoto similarity score between Ethanol (CCO) and Propanol (CCCO)."
- **Tool Call:** `calculate_molecular_similarity(smiles1="CCO", smiles2="CCCO")`
- **Result:**
  ```json
  {
    "smiles1": "CCO",
    "smiles2": "CCCO",
    "tanimoto_similarity": 0.5556,
    "similarity_percentage": "55.56%"
  }
  ```

#### Example 2: Caffeine vs. Aspirin (Hard - Different Scaffolds)
- **User Query:** "Compare the structural similarity of Caffeine (CN1C=NC2=C1C(=O)N(C(=O)N2C)C) and Aspirin (CC(=O)Oc1ccccc1C(=O)O)."
- **Tool Call:** `calculate_molecular_similarity(smiles1="CN1C=NC2=C1C(=O)N(C(=O)N2C)C", smiles2="CC(=O)Oc1ccccc1C(=O)O")`
- **Result:**
  ```json
  {
    "smiles1": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
    "smiles2": "CC(=O)Oc1ccccc1C(=O)O",
    "tanimoto_similarity": 0.0889,
    "similarity_percentage": "8.89%"
  }
  ```

---

## 7. `DeconstructCoreAndSidechainsSkill`

### 📝 Description
Removes a specified core scaffold from a molecule, isolating the remaining sidechains (R-groups).

### 🛠 How it Works
1. Receives a target `smiles` and a `core_smarts_or_smiles`.
2. Uses RDKit's `ReplaceCore` to chop away the core and label attachment points.
3. Returns a list of isolated sidechain SMILES strings.

### 📊 Execution Examples

#### Example 1: Toluene Sidechain Isolation (Easy)
- **User Query:** "Chop away the benzene core from toluene to isolate its sidechains. SMILES: CC1=CC=CC=C1, Core: c1ccccc1"
- **Tool Call:** `deconstruct_core_and_sidechains(smiles="CC1=CC=CC=C1", core_smarts_or_smiles="c1ccccc1")`
- **Result:**
  ```json
  {
    "target_smiles": "CC1=CC=CC=C1",
    "core_pattern_used": "c1ccccc1",
    "isolated_sidechains": ["*C"],
    "total_sidechains_found": 1,
    "status": "success"
  }
  ```

#### Example 2: Beta-Lactam Deconstruction (Hard - Complex Core)
- **User Query:** "Isolate the remaining R-groups from this beta-lactam structure by removing the core scaffold. SMILES: CC1(C(N2C(S1)C(C2=O)NC(=O)CC3=CC=CC=C3)C(=O)O)C, Core: C12SSCC(N1=O)N2"
- **Tool Call:** `deconstruct_core_and_sidechains(smiles="CC1(C(N2C(S1)C(C2=O)NC(=O)CC3=CC=CC=C3)C(=O)O)C", core_smarts_or_smiles="C12SSCC(N1=O)N2")`
- **Result:**
  ```json
  {
    "error": "The specified core scaffold was not found within the target molecule."
  }
  ```
- **Note:** This example demonstrates error handling when the provided core scaffold does not match the target structure.

---

## 8. `SearchAdvancedSubstructureSkill`

### 📝 Description
Performs advanced substructure matching with dynamic sidechain filtering (Markush-like constraints).

### 🛠 How it Works
1. Receives a `smiles`, a `pattern`, a `constraint_atom_idx`, and a `query_type` (e.g., 'alkyl').
2. Finds all matches of the pattern.
3. Filters matches based on the nature of the substituent at the specified atom index.
4. Returns both unfiltered and filtered match counts and indices.

### 📊 Execution Examples

#### Example 1: Alkyl Sidechain Filter (Easy)
- **User Query:** "Search for this pattern within the molecule applying an 'alkyl' sidechain filter on index 0. SMILES: CCC1=CC=CC=C1, Pattern: CCC, Index: 0, Type: alkyl"
- **Tool Call:** `search_advanced_substructure(smiles="CCC1=CC=CC=C1", pattern="[#6]-[#6]-[#6]", constraint_atom_idx=0, query_type="alkyl")`
- **Result:**
  ```json
  {
    "target_smiles": "CCC1=CC=CC=C1",
    "core_pattern": "[#6]-[#6]-[#6]",
    "constraint_applied": {
      "atom_index_in_pattern": 0,
      "required_type": "alkyl"
    },
    "total_unfiltered_matches": 1,
    "total_filtered_matches": 1,
    "status": "success"
  }
  ```

#### Example 2: All-Carbon Constraint (Hard - Heterocyclic Target)
- **User Query:** "Perform an advanced substructure search with an 'all_carbon' constraint at atom index 1 for this heterocyclic target: C1CC(NC1)C2CCCCC2"
- **Tool Call:** `search_advanced_substructure(smiles="C1CC(NC1)C2CCCCC2", pattern="C1CC(NC1)C2CCCCC2", constraint_atom_idx=1, query_type="all_carbon")`
- **Result:**
  ```json
  {
    "target_smiles": "C1CC(NC1)C2CCCCC2",
    "core_pattern": "C1CC(NC1)C2CCCCC2",
    "constraint_applied": {
      "atom_index_in_pattern": 1,
      "required_type": "all_carbon"
    },
    "total_unfiltered_matches": 1,
    "total_filtered_matches": 1,
    "status": "success"
  }
  ```

---

## 9. `FindMaximumCommonSubstructureSkill`

### 📝 Description
Identifies the largest common substructure (MCS) shared among a list of molecules. Useful for identifying common pharmacophores or scaffolds in a set of active compounds.

### 🛠 How it Works
1. Receives a `smiles_list`.
2. Uses RDKit's `rdFMCS.FindMCS` to find the largest shared atom/bond mapping.
3. Returns the resulting SMARTS pattern, atom count, and bond count.

### 📊 Execution Examples

#### Example 1: Acetaminophen vs. Aspirin (Analgesic Core) (Easy)
- **User Query:** "Find the Maximum Common Substructure (MCS) between these two molecules: CC(=O)NC1=CC=C(O)C=C1 and CC(=O)Oc1ccccc1C(=O)O"
- **Tool Call:** `find_maximum_common_substructure(smiles_list=["CC(=O)NC1=CC=C(O)C=C1", "CC(=O)Oc1ccccc1C(=O)O"])`
- **Result:**
  ```json
  {
    "smarts": "[#6]1:[#6]:[#6]:[#6](:[#6]:[#6]:1)-[#8]",
    "num_atoms": 7,
    "num_bonds": 7,
    "status": "success"
  }
  ```
- **Final Response Summary:** "The MCS represents a benzene ring with an oxygen substituent (phenoxy/acetoxy core), which is the shared pharmacophore between acetaminophen and aspirin."

#### Example 2: Diverse Compounds (No Meaningful MCS) (Hard)
- **User Query:** "Identify the shared pharmacophore among these three diverse compounds: ['CN1CCCCCC1(=O)', 'CC1=CC=CC=C1O', 'CC(=O)O']"
- **Tool Call:** `find_maximum_common_substructure(smiles_list=["CN1CCCCCC1(=O)", "CC1=CC=CC=C1O", "CC(=O)O"])`
- **Result:**
  ```json
  {
    "smarts": "[#6]-[#6]",
    "num_atoms": 2,
    "num_bonds": 1,
    "status": "success"
  }
  ```
- **Final Response Summary:** "The MCS is simply a C-C bond, indicating no meaningful shared pharmacophore among these structurally diverse compounds."


---

## 10. `InterpretSmartsSkill`

### 📝 Description
Deconstructs a SMARTS string into a human-readable structural description. Use this to verify your understanding of a substructure pattern before reporting it to the user.

### 🛠 How it Works
1. Receives a `smarts` string.
2. Analyzes the pattern to count atom types and identify specific motifs (e.g., rings, functional groups).
3. Returns a breakdown of atoms and identified motifs.

### 📊 Execution Examples

#### Example 1: Basic Carboxylic Acid (Easy)
- **User Query:** "Deconstruct and explain this basic SMARTS string in plain language: C(=O)O"
- **Tool Call:** `interpret_smarts_pattern(smarts="C(=O)O")`
- **Result:**
  ```json
  {
    "smarts": "C(=O)O",
    "total_atoms": 3,
    "atom_breakdown": {
      "Carbon": 1,
      "Oxygen": 2
    },
    "ring_count": 0,
    "identified_motifs": ["Carboxylic acid group"],
    "status": "success"
  }
  ```
- **Final Response Summary:** "This SMARTS string represents a carboxylic acid functional group. It describes a carbon atom double-bonded to one oxygen (carbonyl) and single-bonded to another (hydroxyl)."

#### Example 2: Advanced Ester with Constraints (Hard)
- **User Query:** "Provide a human-readable structural breakdown for this advanced query pattern: [CX3](=O)[OX2H0][#6;!$(C(=O))]"
- **Tool Call:** `interpret_smarts_pattern(smarts="[CX3](=O)[OX2H0][#6;!$(C(=O))]")`
- **Result:**
  ```json
  {
    "smarts": "[CX3](=O)[OX2H0][#6;!$(C(=O))]",
    "total_atoms": 4,
    "atom_breakdown": {
      "Carbon": 2,
      "Oxygen": 2
    },
    "ring_count": 0,
    "identified_motifs": ["Ester group"],
    "status": "success"
  }
  ```
- **Final Response Summary:** "This advanced pattern represents an ester functional group with specific connectivity and constraints, ensuring it matches simple esters while excluding anhydrides."


---

## 11. `CanonicalizeAndValidateSmilesSkill`

### 📝 Description
Validates a SMILES string and converts it into its unique canonical form.

### 🛠 How it Works
1. Receives a `smiles` string.
2. Attempts to parse it with RDKit.
3. If valid, returns the unique canonical SMILES representation.

### 📊 Execution Examples

#### Example 1: Canonicalizing Benzene
- **User Query:** "Is 'C1=CC=CC=C1' a valid SMILES? If so, what is its canonical form?"
- **Tool Call:** `canonicalize_and_validate_smiles(smiles="C1=CC=CC=C1")`
- **Result:**
  ```json
  {
    "is_valid": true,
    "raw_smiles": "C1=CC=CC=C1",
    "canonical_smiles": "c1ccccc1",
    "status": "success"
  }
  ```

#### Example 2: Validating Non-Canonical Ethanol
- **User Query:** "Please validate this non-canonical SMILES string and convert it into its standard form: OCC"
- **Tool Call:** `canonicalize_and_validate_smiles(smiles="OCC")`
- **Result:**
  ```json
  {
    "is_valid": true,
    "raw_smiles": "OCC",
    "canonical_smiles": "CCO",
    "status": "success"
  }
  ```
- **Final Response Summary:** "The SMILES string **OCC** has been successfully validated and canonicalized to **CCO** (Ethanol)."


---

## 12. `GetMolecularFormulaAndChargeSkill`

### 📝 Description
Calculates the molecular formula and net charge of a compound.

### 🛠 How it Works
1. Receives a `smiles` string.
2. Computes the molecular formula and sums the formal charges of all atoms.
3. Returns the formula and the net charge.

### 📊 Execution Examples

#### Example 1: Sodium Chloride
- **User Query:** "What is the molecular formula and net charge of sodium chloride ([Na+].[Cl-])?"
- **Tool Call:** `get_molecular_formula_and_charge(smiles="[Na+].[Cl-]")`
- **Result:**
  ```json
  {
    "smiles": "[Na+].[Cl-]",
    "molecular_formula": "ClNa",
    "net_charge": 0,
    "status": "success"
  }
  ```

#### Example 2: Ethanol Formula and Charge
- **User Query:** "What is the exact molecular formula and net formal charge for ethanol (CCO)?"
- **Tool Call:** `get_molecular_formula_and_charge(smiles="CCO")`
- **Result:**
  ```json
  {
    "smiles": "CCO",
    "molecular_formula": "C2H6O",
    "net_charge": 0,
    "status": "success"
  }
  ```
- **Final Response Summary:** "The exact molecular formula for ethanol (CCO) is C₂H₆O and its net formal charge is 0 (neutral)."


---

## 13. `ConvertSmilesToInchiSkill`

### 📝 Description
Converts a SMILES string into IUPAC InChI and InChIKey identifiers.

### 🛠 How it Works
1. Receives a `smiles` string.
2. Uses RDKit's `inchi` module to generate the InChI string and InChIKey.
3. Returns both identifiers.

### 📊 Execution Examples

#### Example 1: Acetic Acid (Easy)
- **User Query:** "Convert the standard SMILES string 'CC(=O)O' into IUPAC InChI and InChIKey."
- **Tool Call:** `convert_smiles_to_inchi(smiles="CC(=O)O")`
- **Result:**
  ```json
  {
    "smiles": "CC(=O)O",
    "inchi": "InChI=1S/C2H4O2/c1-2(3)4/h1H3,(H,3,4)",
    "inchikey": "QTBSBXVTEAMEQO-UHFFFAOYSA-N",
    "status": "success"
  }
  ```
- **Final Response Summary:** "The IUPAC identifiers for acetic acid (CC(=O)O) are InChI=1S/C2H4O2/c1-2(3)4/h1H3,(H,3,4) and InChIKey=QTBSBXVTEAMEQO-UHFFFAOYSA-N."

#### Example 2: Stereospecific Molecule (Hard)
- **User Query:** "Convert this highly stereospecific drug structure into InChIKey for database lookup: C/C=C\\C1=CC=C(O)C=C1"
- **Tool Call:** `convert_smiles_to_inchi(smiles="C/C=C\\C1=CC=C(O)C=C1")`
- **Result:**
  ```json
  {
    "smiles": "C/C=C\\C1=CC=C(O)C=C1",
    "inchi": "InChI=1S/C9H10O/c1-2-3-8-4-6-9(10)7-5-8/h2-7,10H,1H3/b3-2-",
    "inchikey": "UMFCIIBZHQXRCJ-IHWYPQMZSA-N",
    "status": "success"
  }
  ```
- **Final Response Summary:** "The stereospecific SMILES string `C/C=C\C1=CC=C(O)C=C1` (trans-configuration) has been converted to InChIKey: UMFCIIBZHQXRCJ-IHWYPQMZSA-N."


---

## 14. `CountHeavyAtomsAndRingsSkill`

### 📝 Description
Counts the number of heavy atoms (non-hydrogen) and rings in a molecule.

### 🛠 How it Works
1. Receives a `smiles` string.
2. Counts all atoms where atomic number > 1.
3. Uses RDKit's `GetRingInfo` to count the number of rings.

### 📊 Execution Examples

#### Example 1: Cyclohexane (Easy)
- **User Query:** "Count the total number of rings and heavy atoms for cyclohexane: C1CCCCC1"
- **Tool Call:** `count_heavy_atoms_and_rings(smiles="C1CCCCC1")`
- **Result:**
  ```json
  {
    "smiles": "C1CCCCC1",
    "heavy_atom_count": 6,
    "total_ring_count": 1,
    "status": "success"
  }
  ```
- **Final Response Summary:** "Cyclohexane (C1CCCCC1) consists of 6 heavy atoms (carbons) arranged in a single six-membered ring."

#### Example 2: Bridged Bicyclic Structure (Hard)
- **User Query:** "How many heavy atoms and rings are inside this bridged bicyclic structure? SMILES: CC1(C)C2CCC1(C)C(=O)C2"
- **Tool Call:** `count_heavy_atoms_and_rings(smiles="CC1(C)C2CCC1(C)C(=O)C2")`
- **Result:**
  ```json
  {
    "smiles": "CC1(C)C2CCC1(C)C(=O)C2",
    "heavy_atom_count": 11,
    "total_ring_count": 2,
    "status": "success"
  }
  ```
- **Final Response Summary:** "This bridged bicyclic structure contains 11 heavy atoms and features a complex framework with 2 fused/bridged rings."


---

## 15. `DetectFunctionalGroupsSkill`

### 📝 Description
Scans a molecule for common functional groups using pre-compiled SMARTS patterns.

### 🛠 How it Works
1. Receives a `smiles` string.
2. Uses a set of pre-compiled SMARTS patterns for groups like alcohols, acids, amines, etc.
3. Returns a dictionary indicating the presence and count of each group.

### 📊 Execution Examples

#### Example 1: Ketone Group in Acetone (Easy)
- **User Query:** "Scan this compound to check if it contains any ketone groups: CC(=O)C"
- **Tool Call:** `detect_functional_groups(smiles="CC(=O)C")`
- **Result:**
  ```json
  {
    "smiles": "CC(=O)C",
    "functional_groups": {
      "ketone": { "present": true, "count": 1 },
      "alcohol": { "present": false, "count": 0 },
      "..." : "..."
    },
    "status": "success"
  }
  ```
- **Final Response Summary:** "The compound CC(=O)C (acetone) contains one ketone group, correctly identified by its central carbonyl bonded to two methyl groups."

#### Example 2: Distinguishing Esters from Ethers (Hard)
- **User Query:** "Run a functional group scan on this molecule to verify it correctly distinguishes esters from ethers: CC(=O)OCC"
- **Tool Call:** `detect_functional_groups(smiles="CC(=O)OCC")`
- **Result:**
  ```json
  {
    "smiles": "CC(=O)OCC",
    "functional_groups": {
      "ester": { "present": true, "count": 1 },
      "ether": { "present": false, "count": 0 },
      "..." : "..."
    },
    "status": "success"
  }
  ```
- **Final Response Summary:** "The scan correctly identifies an ester group in ethyl acetate (CC(=O)OCC) while confirming the absence of a separate ether group, demonstrating the tool's specificity for carbonyl-bonded oxygens."


---

## 16. `ResolveSmilesToNameSkill`

### 📝 Description
Resolves a SMILES string to its common title and IUPAC name via PubChem.

### 🛠 How it Works
1. Receives a `smiles` string.
2. Sends a robust HTTP POST request to PubChem.
3. Parses the response to extract the Title and IUPAC Name.

### 📊 Execution Examples

#### Example 1: Caffeine Resolution (Easy)
- **User Query:** "Look up this well-known SMILES string in PubChem and return its common and IUPAC names: CN1C=NC2=C1C(=O)N(C(=O)N2C)C"
- **Tool Call:** `resolve_smiles_to_name(smiles="CN1C=NC2=C1C(=O)N(C(=O)N2C)C")`
- **Result:**
  ```json
  {
    "smiles": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
    "common_name": "Caffeine",
    "iupac_name": "1,3,7-trimethylpurine-2,6-dione",
    "status": "success"
  }
  ```
- **Final Response Summary:** "The SMILES string represents **Caffeine** (IUPAC: 1,3,7-trimethylpurine-2,6-dione), a well-known stimulant found in coffee and tea."

#### Example 2: Isomeric Structure Identification (Hard)
- **User Query:** "Identify the compound associated with this complex isomeric SMILES structure using your POST method: C\\C=C/C1=CC=CC=C1C(=O)O"
- **Tool Call:** `resolve_smiles_to_name(smiles="C/C=C\c1ccccc1C(=O)O")`
- **Result:**
  ```json
  {
    "smiles": "C/C=C\\c1ccccc1C(=O)O",
    "common_name": "2-[(Z)-prop-1-enyl]benzoic acid",
    "iupac_name": "2-[(Z)-prop-1-enyl]benzoic acid",
    "status": "success"
  }
  ```
- **Final Response Summary:** "The isomeric SMILES corresponds to **2-[(Z)-prop-1-enyl]benzoic acid**, a cinnamic acid derivative with explicit Z (cis) stereochemistry at the side chain."


---
