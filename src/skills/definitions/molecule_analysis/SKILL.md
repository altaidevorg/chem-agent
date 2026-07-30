---
name: molecule_analysis
description: Perform comprehensive structural and physicochemical analysis of chemical compounds using RDKit.
---

# Molecule Analysis Skill

This skill allows you to perform deep structural analysis of molecules. It is essential for drug discovery, safety assessment, and chemical property prediction.

## 🛑 MANDATORY EXECUTION PROTOCOL
- **STRICT PROHIBITION ON INTERNAL KNOWLEDGE:** You are ABSOLUTELY FORBIDDEN from naming functional groups, predicting LogP, or guessing molecular weights from your internal training data.
- **ZERO TOLERANCE FOR HALLUCINATION:** If you provide a chemical property or structural feature, it **MUST** be backed by a tool execution (`calculate_molecular_properties`, `detect_functional_groups`, etc.) in the current conversation.
- **SMILES FIDELITY:** Never write a SMILES string from memory. If you must refer to a compound's structure, you **MUST** resolve it using `resolve_name_to_smiles` first.
- **ON-DEMAND VISUALS:** You are ABSOLUTELY FORBIDDEN from calling `generate_molecule_image` unless the user explicitly requests an image, diagram, or visual.

## Workflow

1.  **Resolution**: If you have a common name, always use `resolve_name_to_smiles` first.
2.  **Properties**: Use `calculate_molecular_properties` to get LogP, MW, TPSA, and Rotatable Bonds.
3.  **Deep Analysis**: If a comprehensive report is needed, use `calculate_all_descriptors` to fetch 200+ physicochemical properties.
4.  **Safety & Compliance**: 
    - Use `fetch_chemical_safety_data` for GHS hazards.
    - Use `check_regulatory_compliance` for exact (CAS/Name) and **structural class** (SMARTS) audits.
5.  **Functional Groups**: Use `detect_functional_groups` to identify key chemical motifs.
6.  **Visualization**: Use `generate_molecule_image` **ONLY IF** the user explicitly asks for a visual representation (diagram, image, etc.).
7.  **Pharmaceutical Assessment**: Use `calculate_drug_likeness` for QED, logS, and Lipinski/Veber rules.

## Guidelines

-   Always validate SMILES using `standardize_molecule` if you are unsure of the input format.
-   When comparing two molecules, use `calculate_molecular_similarity` (Tanimoto).
-   For complex structural queries, use `search_substructure` with SMARTS patterns.
-   If you need to understand a SMARTS pattern, use `interpret_smarts_pattern`.
-   **Pharma Use-Case**: When assessing drug candidates, always check the `drug_likeness_score`, `qed_score`, and `logs_est` (solubility). A high QED score (>0.67) indicates a very attractive lead, while a low logS (<-4) suggests significant formulation challenges due to poor solubility.
