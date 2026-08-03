---
name: regulatory_screening
description: Specialized workflows for checking flavor and fragrance ingredients against IFRA and EU food regulations.
required_tools:
  - check_regulatory_compliance
  - resolve_name_to_smiles
  - list_files
  - read_file
---

# ⚖️ Regulatory Screening Skill

This skill ensures that flavor and fragrance formulations comply with international legal standards (IFRA for fragrance, EU 1334/2008 for food). It acts as a first-pass legal audit.

## 🚀 Analytical Workflow

### 1. Ingredient Audit
Before finalizing any formulation or answering safety queries:
- **Action**: Use `check_regulatory_compliance` with a list of molecule names.
- **Goal**: Identify banned or restricted substances in the local database.

### 2. Result Interpretation
- **Banned**: If a substance is marked as 'Banned' or 'Prohibited', advise immediate removal from the formulation.
- **Restricted**: If marked as 'Restricted', provide the user with the limit information (e.g., "Max 2 mg/kg in beverages").
- **Not Found**: If not found in the database, note that it is likely GRAS (Generally Recognized As Safe) but should be double-checked if it's a novel molecule.

### 3. Compliance Advice
Provide structured feedback:
- "Molecule X is prohibited in EU food flavorings. I recommend substituting it with Molecule Y."
- "This formulation contains Coumarin, which is limited to 2 mg/kg in beverages per EU 1334/2008."

## ⚠️ Guidelines
- The database contains a mix of seed data and dynamically learned data from PubChem.
- **Important**: This is a decision-support tool. Final regulatory sign-off must always be performed by a human regulatory expert using the current official legal texts.
