---
name: reactivity_audit
description: Advanced multi-component strategy for detecting chemical incompatibilities and reactivity risks in flavor or fragrance formulations.
required_tools:
  - audit_chemical_compatibility
  - check_chemical_reactivity
  - resolve_name_to_smiles
---

# ⚡ Chemical Reactivity & Stability Audit Skill

This skill enables the agent to act as a stability expert, scanning complex mixtures for hidden chemical risks. It is essential for ensuring the shelf-life and quality of flavor/fragrance products.

## 🚀 Analytical Workflow

### 1. Mixture Screening
Whenever you receive a list of ingredients (SMILES) or a formulation:
- **Action**: Use `audit_chemical_compatibility` with the list of SMILES strings.
- **Goal**: Identify pairwise reactions (e.g., Schiff Base) or individual sensitivities (e.g., Oxidation).

### 2. Risk Interpretation
The tool returns a list of risks. Your role is to interpret these for the user:
- **Schiff Base**: Highlight the risk of **discoloration** (turning brown) and **aroma loss**.
- **Acetal Formation**: Mention that the odor might become "flatter" or more "ether-like" over time.
- **Oxidation**: Recommend adding **antioxidants** (like BHT or Tocopherol) if Terpenes are flagged.

### 3. Mitigation Advice
Don't just report the problem; suggest a way forward:
- "To avoid Schiff Base formation, consider replacing the primary amine with a secondary amine or encapsulated aldehyde."
- "The presence of high-concentration Terpenes suggests this formulation requires UV-protected packaging and antioxidants."

## ⚠️ Guidelines
- Pair this skill with `aroma_analysis` to provide a complete "Performance & Stability" report.
- Remember: These are **potential** risks based on functional group chemistry. The actual rate of reaction depends on pH, temperature, and solvent.
