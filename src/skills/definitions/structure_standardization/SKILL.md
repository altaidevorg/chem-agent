---
name: structure_standardization
description: Standardize chemical structures from SMILES or local files (.mol, .sdf) to ensure consistency, remove salts, and find canonical tautomers.
required_tools:
  - standardize_molecule
  - import_and_standardize_file
---

# ⚗️ Structure Standardization & Validation Skill

This skill ensures that chemical data is valid, consistent, clean, and ready for accurate calculation or database comparison.

## Core Tools
- `standardize_molecule`: Validates SMILES syntax and performs cleanup (salt stripping, neutralization, tautomer canonicalization).
- `import_and_standardize_file`: Imports and cleans structures directly from local files (.mol, .sdf, .inchi).

## Workflow

### 1. Chemical Import & Validation
- **From SMILES**: Use `standardize_molecule` for any user-provided string.
- **From FILES**: ALWAYS use `import_and_standardize_file`. Never attempt to use `read_file` on chemical structure files.

### 2. Parent Molecule Isolation (Salt Stripping)
- If a structure contains a salt form (e.g., Sodium Benzoate), the tools will strip the counterions to get the neutral parent.
- **Why?** Physicochemical descriptors like logP, HSP, and pKa should generally be calculated on the neutral parent molecule.

### 3. Tautomer Standardization
- The tools automatically find the **canonical tautomer** (most stable/standard form).

### 4. Reporting
Always compare the original state vs the standardized state and list the specific changes made (e.g., "Removed salts").

## 📈 Example Actions
- **File Import**: `import_and_standardize_file(file_path="data/messy_sample.mol")`
- **Manual Cleanup**: `standardize_molecule(smiles="CC(=O)O.[Na]", remove_salts=True)`

## ⚠️ Critical Rules
- **No read_file for molecules**: `.mol` and `.sdf` are structured data. Do NOT use `read_file` or `query_dataset` on them.
- **Always Canonical**: Use the `standardized_smiles` for all subsequent calculations.

- Before performing **Stoichiometry** or **Dilution** calculations, ask if the user wants the calculation based on the salt form or the parent form. 
- Use the `mw_difference` provided by the tool to adjust dosages if needed.

## Guidelines
- **Always standardize before comparison**: Never assume two SMILES strings are different just because the strings don't match; standardize them first.
- **MW Awareness**: Pay attention to `final_mw` vs `original_mw`. If a salt is removed, the molecular weight will decrease.
- **Transparency**: Inform the user when you have standardized a molecule (e.g., "I have stripped the sodium salt to calculate the properties of the parent acid").
