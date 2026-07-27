---
name: structure_standardization
description: Standardize chemical structures to ensure data consistency, remove salts, and find canonical tautomers.
---

# Structure Standardization & Validation Skill

This skill ensures that chemical data is valid, consistent, clean, and ready for accurate calculation or database comparison.

## Core Tool
- `standardize_molecule`: Validates SMILES syntax and performs a sequence of cleaning operations (cleanup, salt stripping, neutralization, tautomer canonicalization).

## Workflow

### 1. SMILES Validation & Cleaning
- Use `standardize_molecule` whenever you receive a SMILES string from a user or external source.
- It will return `is_valid: true` if the syntax is correct. If the SMILES is invalid, it will provide an error message.
- For simple validation without changing the chemical structure, set `remove_salts=False`, `neutralize=False`, and `canonicalize_tautomer=False`.

### 2. Parent Molecule Isolation (Salt Stripping)
- If a user provides a salt form (e.g., "Sodium Benzoate"), use this skill to strip the sodium and get the "Benzoic Acid" parent.
- **Why?** Physicochemical descriptors like logP, HSP, and pKa should generally be calculated on the neutral parent molecule, not the salt.

### 3. Tautomer Standardization
- Some molecules (like keto-enols) can be drawn in multiple ways. Use this skill to find the **canonical tautomer**.
- This ensures that your analysis is always performed on the most stable or standard representation.

### 4. Preparation for Calculations
- Before performing **Stoichiometry** or **Dilution** calculations, ask if the user wants the calculation based on the salt form or the parent form. 
- Use the `mw_difference` provided by the tool to adjust dosages if needed.

## Guidelines
- **Always standardize before comparison**: Never assume two SMILES strings are different just because the strings don't match; standardize them first.
- **MW Awareness**: Pay attention to `final_mw` vs `original_mw`. If a salt is removed, the molecular weight will decrease.
- **Transparency**: Inform the user when you have standardized a molecule (e.g., "I have stripped the sodium salt to calculate the properties of the parent acid").
