---
name: molecule_analysis
description: Perform comprehensive structural and physicochemical analysis of chemical compounds using RDKit.
---

# Molecule Analysis Skill

This skill allows you to perform deep structural analysis of molecules. It is essential for drug discovery, safety assessment, and chemical property prediction.

## Workflow

1.  **Resolution**: If you have a common name, always use `resolve_name_to_smiles` first.
2.  **Properties**: Use `calculate_molecular_properties` to get LogP, MW, HBD, and HBA.
3.  **Safety**: Use `fetch_chemical_safety_data` to check for GHS hazards.
4.  **Functional Groups**: Use `detect_functional_groups` to identify key chemical motifs.
5.  **Visualization**: Use `generate_molecule_image` to create a 2D diagram for the user.

## Guidelines

-   Always validate SMILES using `standardize_molecule` if you are unsure of the input format.
-   When comparing two molecules, use `calculate_molecular_similarity` (Tanimoto).
-   For complex structural queries, use `search_substructure` with SMARTS patterns.
-   If you need to understand a SMARTS pattern, use `interpret_smarts_pattern`.
