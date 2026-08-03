---
name: emulsion_logic
description: Specialized workflows for beverage and food emulsion stability, HLB calculations, and oil/water partitioning analysis.
required_tools:
  - calculate_emulsion_properties
  - resolve_name_to_smiles
  - calculate_molecular_properties
---

# 🥤 Emulsion & Solubility Logic Skill

This skill allows the agent to analyze the physical stability of flavors in different matrices, particularly in beverage emulsions (Oil-in-Water).

## 🚀 Analytical Workflow

### 1. Solubility & Matrix Check
When a flavor component is added to a beverage (water-based) or a snack (fat-based):
- **Action**: Use `calculate_emulsion_properties` to get the HLB and LogP.
- **Goal**: Predict if the molecule will dissolve easily or require an emulsifier.

### 2. Emulsifier Selection
If a user is designing an emulsion (e.g., a cloudy orange beverage):
- **HLB 8-16**: Recommend molecules/emulsifiers in this range for **Oil-in-Water (O/W)** stability.
- **HLB < 6**: These are hydrophobic and suitable for **Water-in-Oil (W/O)** or pure oil concentrates.

### 3. Stability Prediction
Compare the LogP and HLB:
- **High LogP (> 3)**: Indicates high lipophilicity. These components are prone to "ringing" (forming an oil ring at the top of a bottle) if the emulsion is not properly weighted or stabilized.

## ⚠️ Guidelines
- The **Griffin HLB** method is an approximation based on molecular mass. It is most accurate for non-ionic surfactants and small organic molecules.
- Use this skill alongside `aroma_analysis` to provide a complete report on both the sensory and physical performance of a flavor.
