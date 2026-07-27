---
name: aroma_analysis
description: Specialized workflows for flavor and fragrance R&D, including volatility estimation, odor note classification, and formulation support.
---

# 🍎 Aroma & Fragrance Analysis Skill

This skill is designed for the specific needs of flavor and fragrance development (Aromsa use cases). It focuses on how molecules behave in mixtures, their volatility, and their sensory roles.

## 🚀 Analytical Workflow

### 1. Volatility & Odor Note Classification
Understanding the "evaporation profile" of a molecule is critical for balancing a flavor.
- **Action**: Use `estimate_volatility_and_note` to predict the boiling point and classify the molecule.
- **Top Notes**: High volatility (e.g., Limonene, Ethyl Acetate). These are the first impressions.
- **Heart Notes**: Medium volatility (e.g., Linalool, Geraniol). These form the body of the flavor.
- **Base Notes**: Low volatility (e.g., Vanillin, Musks). These provide longevity and depth.

### 2. Molecular Characterization
For any candidate molecule in a flavor brief:
- **Resolution**: Use `resolve_name_to_smiles` to get the structure.
- **Volatility**: Use `estimate_volatility_and_note` to see where it fits in the Top/Heart/Base structure.
- **Properties**: Use `calculate_molecular_properties` to check LogP (relevant for oil/water distribution).

### 3. Stability & Compatibility (Heuristic-based)
- Check for functional groups using `detect_functional_groups`.
- **Note**: Be aware of reactive pairs like Aldehydes and Amines which can form Schiff bases, changing the flavor profile and color over time.

## ⚠️ Guidelines
- Boiling point estimates are derived from structural group contributions (Joback Method) and are intended for **screening and ranking**, not as absolute physical constants.
- Always use the `odor_note_classification` to help the user balance their formulation (e.g., "Your formulation is heavy on Top notes but lacks a solid Base note").
