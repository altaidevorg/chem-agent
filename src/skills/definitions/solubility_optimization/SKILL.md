---
name: solubility_optimization
description: Optimize solvent selection and formulation stability using Hansen Solubility Parameters (HSP) and HLB.
required_tools:
  - calculate_hansen_parameters
  - calculate_emulsion_properties
  - calculate_molecular_similarity
  - estimate_volatility_and_note
  - detect_functional_groups
  - fetch_chemical_safety_data
  - check_regulatory_compliance
---

# Solubility & Formulation Optimization Skill

This skill is designed to help chemists select the best solvents for a given solute (resin, active ingredient, or aroma) and optimize the stability of liquid formulations.

## Core Tools
- `calculate_hansen_parameters`: Computes Dispersion (dD), Polar (dP), and Hydrogen Bonding (dH) parameters.
- `calculate_emulsion_properties`: Computes HLB (Griffin method) for surfactant/emulsifier selection.
- `calculate_molecular_similarity`: Used to find structurally similar solvents.
- `estimate_volatility_and_note`: Analyzes vapor pressure and evaporation behavior.

## Workflow

### 1. Target Characterization
- If the target solute is known, calculate its HSP values using `calculate_hansen_parameters`.
- Identify key functional groups using `detect_functional_groups` to understand chemical interactions.

### 2. Solvent Selection (HSP Distance)
- To find a good solvent, look for substances with HSP values close to the solute.
- **Hansen Distance (Ra)**: The closer the Ra, the better the solubility. 
  - Formula: $Ra^2 = 4(\delta D1 - \delta D2)^2 + (\delta P1 - \delta P2)^2 + (\delta H1 - \delta H2)^2$
- Compare candidate solvents' HSP against the target solute.

### 3. Emulsion Stability (For Beverages/Food)
- If creating an O/W emulsion (beverage), select emulsifiers with **HLB 8-16** using `calculate_emulsion_properties`.
- For W/O emulsions, look for **HLB < 6**.

### 4. Volatility Balancing
- Check the evaporation profile of the solvent system using `estimate_volatility_and_note`. 
- Ensure a balance between fast-evaporating (Top Note) and slow-evaporating (Base Note) components to maintain stability during application or storage.

## Guidelines
- **Data Sovereignty**: Remind the user that all calculations are performed locally on the server.
- **Safety First**: Always check the safety profiles (`fetch_chemical_safety_data`) of proposed solvents to ensure they are appropriate for the application (e.g., food-grade vs. industrial).
- **Regulatory Check**: Use `check_regulatory_compliance` to ensure the selected solvents are permitted in the target market (EU/IFRA).
