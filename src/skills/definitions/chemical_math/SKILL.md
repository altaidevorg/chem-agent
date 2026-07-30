---
name: chemical_math
description: Perform laboratory calculations including dilutions, stoichiometry, and unit conversions.
---

# Chemical Math & Lab Calculations Skill

This skill enables the agent to act as a precise laboratory assistant for mathematical operations involving chemical concentrations, volumes, and masses.

## 🛑 MANDATORY EXECUTION PROTOCOL
- **STRICT PROHIBITION ON MENTAL MATH:** You are ABSOLUTELY FORBIDDEN from performing any manual or mental calculations. Even for the simplest $C_1V_1=C_2V_2$ operations, you **MUST** call `calculate_dilution`.
- **ZERO TOLERANCE FOR GUESSING:** All results presented to the user must be the exact output of a tool execution. Suggesting a number without a tool call is a violation of safety protocols.
- **MW & DENSITY VERIFICATION:** Never use internal memory for molecular weights or densities. You **MUST** provide the SMILES or explicit density values to the tools.
- **TRACEABILITY:** Tool execution is the only way to ensure laboratory-grade precision and safety audit trails. Manual math is non-compliant.

## Core Tools
- `calculate_dilution`: Solves $C_1V_1 = C_2V_2$. Supports auto-conversion between Molar and mass units. **MANDATORY** for all concentration changes.
- `calculate_stoichiometry`: Converts mass to moles. **MANDATORY** for weight-based formulation planning.
- `calculate_density_conversion`: Solves $m = V \times d$. **MANDATORY** for liquid handling instructions.
- `calculate_mixture_composition`: Handles multi-component combinations. **MANDATORY** for batch reconciliation.
- `calculate_dosage`: Calculates target percentages for large batches. **MANDATORY** for production scale-up.
- `calculate_voc_content`: Calculates Volatile Organic Compound content. **MANDATORY** for coatings and paint industrial compliance.

## Workflow

### 1. Dilution Planning
- To prepare a solution, identify the stock concentration ($C_1$), target concentration ($C_2$), and target volume ($V_2$).
- If the concentrations are in different units (e.g., Stock is 1M, Target is 10mg/L), ensure you provide the **SMILES** string so the tool can use the molecular weight for conversion.
- For oil-based flavor concentrates, provide the **density** (g/mL) to ensure accurate weight-to-volume conversion if using percentage (%) units.
- Use `calculate_dilution` by leaving the parameter you want to find (usually $V_1$) as `null` or omitting it.

### 2. Sample Preparation & Stoichiometry
- When asked how much of a substance to weigh, use `calculate_stoichiometry`.
- Provide the **SMILES** and the desired **moles** to get the **mass** in grams or milligrams.
- This is essential for preparing exact molar solutions from solid reagents.

### 3. Mixture and Dosage Math
- **Density Conversions**: Use `calculate_density_conversion` to quickly move between mass and volume for liquids with known density.
- **Complex Mixtures**: If combining multiple batches of the same flavor with different concentrations, use `calculate_mixture_composition` to find the final batch concentration and volume.
- **Production Dosage**: Use `calculate_dosage` for factory-scale instructions (e.g., "Add 0.5% flavor to a 500kg batch").

### 4. VOC Compliance Audit
- For industrial coatings or paint formulations, use `calculate_voc_content`.
- Provide a list of components with their **SMILES**, **mass**, and **density**.
- **Regional Standards**: Always check if the user requires **EU** (250°C), **US_EPA** (250°C with exemptions like Acetone), or **US_CARB** (216°C) standards. If not specified, ask the user or default to EU while stating the assumption.
- The tool will classify each component as VOC or Non-VOC and report the total g/L and weight %.

## Guidelines
- **Always use SMILES**: Whenever possible, resolve the chemical name to SMILES first using `resolve_name_to_smiles` to ensure accurate molecular weight for calculations.
- **Density Matters**: In flavor chemistry, liquids are often not 1.0 g/mL. Always check for density before converting volume to mass.
- **Precision**: Report results with appropriate significant figures as provided by the tool.
- **Verification**: If a calculation seems unusual (e.g., taking 0.001 uL of a stock), warn the user that a serial dilution might be more practical.
