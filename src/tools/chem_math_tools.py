# src/tools/chem_math_tools.py
import json
from typing import Any, Dict, Optional
from rdkit import Chem
from rdkit.Chem import Descriptors
from src.tools.base import BaseTool, ToolRegistry

class CalculateDilutionTool(BaseTool):
    """
    Calculates dilution parameters using the C1V1 = C2V2 equation.
    Supports unit conversions between Molarity, mass concentration, and percentage.
    """

    @property
    def name(self) -> str:
        return "calculate_dilution"

    @property
    def description(self) -> str:
        return (
            "Solves the dilution equation C1*V1 = C2*V2. Given any three parameters, "
            "it calculates the fourth. Can also convert between Molar (M) and mass-based (mg/L, %) "
            "concentrations if a SMILES string is provided."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "c1": {"type": "number", "description": "Initial concentration."},
                "u1": {"type": "string", "enum": ["M", "mM", "uM", "mg/L", "g/L", "ppm", "%"], "description": "Unit of c1."},
                "v1": {"type": "number", "description": "Initial volume (volume to take from stock)."},
                "uv1": {"type": "string", "enum": ["L", "mL", "uL"], "description": "Unit of v1."},
                "c2": {"type": "number", "description": "Final concentration."},
                "u2": {"type": "string", "enum": ["M", "mM", "uM", "mg/L", "g/L", "ppm", "%"], "description": "Unit of c2."},
                "v2": {"type": "number", "description": "Final volume (total target volume)."},
                "uv2": {"type": "string", "enum": ["L", "mL", "uL"], "description": "Unit of v2."},
                "smiles": {"type": "string", "description": "SMILES of the solute (required if converting between Molar and mass units)."}
            },
            "required": ["u1", "u2", "uv1", "uv2"]
        }

    def _to_standard_unit(self, value: float, unit: str, mw: Optional[float] = None) -> float:
        """Converts any concentration to mg/L (standard internal unit)."""
        if unit == "mg/L" or unit == "ppm":
            return value
        if unit == "g/L":
            return value * 1000.0
        if unit == "%":
            return value * 10000.0 # 1% = 10g/L = 10000mg/L
        
        # Molar units require MW
        if unit in ["M", "mM", "uM"]:
            if mw is None:
                raise ValueError(f"Molecular weight (SMILES) required for unit: {unit}")
            if unit == "M":
                return value * mw * 1000.0
            if unit == "mM":
                return value * mw
            if unit == "uM":
                return value * mw / 1000.0
        
        return value

    def _from_standard_unit(self, value: float, unit: str, mw: Optional[float] = None) -> float:
        """Converts from mg/L to target unit."""
        if unit == "mg/L" or unit == "ppm":
            return value
        if unit == "g/L":
            return value / 1000.0
        if unit == "%":
            return value / 10000.0
        
        if unit in ["M", "mM", "uM"]:
            if mw is None:
                raise ValueError(f"Molecular weight (SMILES) required for unit: {unit}")
            if unit == "M":
                return value / (mw * 1000.0)
            if unit == "mM":
                return value / mw
            if unit == "uM":
                return (value * 1000.0) / mw
        
        return value

    def _vol_to_ml(self, value: float, unit: str) -> float:
        if unit == "mL": return value
        if unit == "L": return value * 1000.0
        if unit == "uL": return value / 1000.0
        return value

    def _vol_from_ml(self, value: float, unit: str) -> float:
        if unit == "mL": return value
        if unit == "L": return value / 1000.0
        if unit == "uL": return value * 1000.0
        return value

    def execute(self, **kwargs) -> Dict[str, Any]:
        try:
            c1, u1 = kwargs.get("c1"), kwargs.get("u1")
            v1, uv1 = kwargs.get("v1"), kwargs.get("uv1")
            c2, u2 = kwargs.get("c2"), kwargs.get("u2")
            v2, uv2 = kwargs.get("v2"), kwargs.get("uv2")
            smiles = kwargs.get("smiles")

            mw = None
            if smiles:
                mol = Chem.MolFromSmiles(smiles)
                if mol:
                    mw = Descriptors.MolWt(mol)

            # Check which one is missing
            params = {"c1": c1, "v1": v1, "c2": c2, "v2": v2}
            missing = [k for k, v in params.items() if v is None]

            if len(missing) != 1:
                return {"error": "Exactly one parameter (c1, v1, c2, or v2) must be missing to solve the equation."}

            target = missing[0]

            # Convert knowns to standard units (mg/L and mL)
            c1_std = self._to_standard_unit(c1, u1, mw) if c1 is not None else None
            v1_std = self._vol_to_ml(v1, uv1) if v1 is not None else None
            c2_std = self._to_standard_unit(c2, u2, mw) if c2 is not None else None
            v2_std = self._vol_to_ml(v2, uv2) if v2 is not None else None

            if target == "v1":
                # v1 = c2*v2 / c1
                v1_std = (c2_std * v2_std) / c1_std
                v1 = self._vol_from_ml(v1_std, uv1)
                result = {"v1": round(v1, 4), "unit": uv1}
            elif target == "c1":
                # c1 = c2*v2 / v1
                c1_std = (c2_std * v2_std) / v1_std
                c1 = self._from_standard_unit(c1_std, u1, mw)
                result = {"c1": round(c1, 4), "unit": u1}
            elif target == "v2":
                # v2 = c1*v1 / c2
                v2_std = (c1_std * v1_std) / c2_std
                v2 = self._vol_from_ml(v2_std, uv2)
                result = {"v2": round(v2, 4), "unit": uv2}
            elif target == "c2":
                # c2 = c1*v1 / v2
                c2_std = (c1_std * v1_std) / v2_std
                c2 = self._from_standard_unit(c2_std, u2, mw)
                result = {"c2": round(c2, 4), "unit": u2}

            return {
                "status": "success",
                "calculated_parameter": target,
                "result": result,
                "molecular_weight": round(mw, 2) if mw else None,
                "summary": f"Calculated {target} = {result[target]} {result['unit']} using C1V1=C2V2."
            }

        except Exception as e:
            return {"error": f"Dilution calculation failed: {str(e)}"}

class CalculateStoichiometryTool(BaseTool):
    """
    Converts between mass, moles, and number of molecules.
    """

    @property
    def name(self) -> str:
        return "calculate_stoichiometry"

    @property
    def description(self) -> str:
        return "Converts between mass (g, mg), moles (mol, mmol), and molecular weight using n = m/MW."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "smiles": {"type": "string", "description": "SMILES of the substance."},
                "mass": {"type": "number", "description": "Mass of the substance."},
                "mass_unit": {"type": "string", "enum": ["g", "mg", "kg"], "default": "g"},
                "moles": {"type": "number", "description": "Amount in moles."},
                "moles_unit": {"type": "string", "enum": ["mol", "mmol", "umol"], "default": "mol"}
            },
            "required": ["smiles"]
        }

    def execute(self, **kwargs) -> Dict[str, Any]:
        try:
            smiles = kwargs.get("smiles")
            mass = kwargs.get("mass")
            m_unit = kwargs.get("mass_unit", "g")
            moles = kwargs.get("moles")
            n_unit = kwargs.get("moles_unit", "mol")

            mol = Chem.MolFromSmiles(smiles)
            if not mol:
                return {"error": f"Invalid SMILES: {smiles}"}
            mw = Descriptors.MolWt(mol)

            if mass is not None and moles is not None:
                return {"error": "Provide either mass or moles, not both, to calculate the other."}
            
            if mass is not None:
                # Convert to grams
                m_g = mass
                if m_unit == "mg": m_g = mass / 1000.0
                if m_unit == "kg": m_g = mass * 1000.0
                
                n_mol = m_g / mw
                
                # Convert to target mole unit
                res_n = n_mol
                if n_unit == "mmol": res_n = n_mol * 1000.0
                if n_unit == "umol": res_n = n_mol * 1000000.0
                
                return {
                    "status": "success",
                    "input": {"mass": mass, "unit": m_unit},
                    "calculated": {"moles": round(res_n, 6), "unit": n_unit},
                    "molecular_weight": round(mw, 2),
                    "summary": f"{mass} {m_unit} of substance (MW: {round(mw,2)}) is {round(res_n, 6)} {n_unit}."
                }

            if moles is not None:
                # Convert to moles
                n_mol = moles
                if n_unit == "mmol": n_mol = moles / 1000.0
                if n_unit == "umol": n_mol = moles / 1000000.0
                
                m_g = n_mol * mw
                
                # Convert to target mass unit
                res_m = m_g
                if m_unit == "mg": res_m = m_g * 1000.0
                if m_unit == "kg": res_m = m_g / 1000.0

                return {
                    "status": "success",
                    "input": {"moles": moles, "unit": n_unit},
                    "calculated": {"mass": round(res_m, 4), "unit": m_unit},
                    "molecular_weight": round(mw, 2),
                    "summary": f"{moles} {n_unit} of substance (MW: {round(mw,2)}) weighs {round(res_m, 4)} {m_unit}."
                }

            return {"error": "Provide either mass or moles."}

        except Exception as e:
            return {"error": f"Stoichiometry calculation failed: {str(e)}"}

# Register tools
ToolRegistry.register(CalculateDilutionTool())
ToolRegistry.register(CalculateStoichiometryTool())
