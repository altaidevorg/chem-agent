---
name: chemical_math
description: Perform laboratory calculations including dilutions, stoichiometry, and unit conversions.
---

# Chemical Math & Lab Calculations Skill

This skill enables the agent to act as a precise laboratory assistant for mathematical operations involving chemical concentrations, volumes, and masses.

## 🔴 MANDATORY EXECUTION PROTOCOL
- **NO MENTAL MATH:** Even for simple $C_1V_1=C_2V_2$ calculations, you **MUST** call `calculate_dilution`. This ensures that all units and molecular weights are handled by the validated RDKit-backed engine.
- **MW VERIFICATION:** Never use your internal memory for molecular weights. You **MUST** provide the SMILES to the tools so the engine can calculate the exact MW.
- **TRACEABILITY:** Using tools provides a traceable log of the calculation parameters. Manual math is forbidden for professional lab safety and precision.

## Core Tools
- `calculate_dilution`: Solves $C_1V_1 = C_2V_2$. Supports auto-conversion between Molar and mass units if SMILES is provided.
- `calculate_stoichiometry`: Converts between mass (g, mg) and moles (mol, mmol) using molecular weight derived from SMILES.

## Workflow

### 1. Dilution Planning
- To prepare a solution, identify the stock concentration ($C_1$), target concentration ($C_2$), and target volume ($V_2$).
- If the concentrations are in different units (e.g., Stock is 1M, Target is 10mg/L), ensure you provide the **SMILES** string so the tool can use the molecular weight for conversion.
- Use `calculate_dilution` by leaving the parameter you want to find (usually $V_1$) as `null` or omitting it.

### 2. Sample Preparation & Stoichiometry
- When asked how much of a substance to weigh, use `calculate_stoichiometry`.
- Provide the **SMILES** and the desired **moles** to get the **mass** in grams or milligrams.
- This is essential for preparing exact molar solutions from solid reagents.

### 3. Unit Conversions
- Both tools handle internal unit conversions. 
- Supported Concentration Units: `M`, `mM`, `uM`, `mg/L`, `g/L`, `ppm`, `%`.
- Supported Volume Units: `L`, `mL`, `uL`.

## Guidelines
- **Always use SMILES**: Whenever possible, resolve the chemical name to SMILES first using `resolve_name_to_smiles` to ensure accurate molecular weight for calculations.
- **Precision**: Report results with appropriate significant figures as provided by the tool.
- **Verification**: If a calculation seems unusual (e.g., taking 0.001 uL of a stock), warn the user that a serial dilution might be more practical.
