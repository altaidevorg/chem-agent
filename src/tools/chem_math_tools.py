# src/tools/chem_math_tools.py
import json
from typing import Any, Dict, List, Optional
from rdkit import Chem, rdBase
from rdkit.Chem import Descriptors
from src.tools.base import BaseTool, ToolRegistry
from src.tools.rdkit_tools import EstimateVolatilityAndNoteTool

class CalculateDilutionTool(BaseTool):
    """
    Calculates dilution parameters using the C1V1 = C2V2 equation.
    Supports unit conversions between Molarity, mass concentration, and percentage.
    Now supports density-aware conversions for industrial flavor concentrates.
    """

    @property
    def name(self) -> str:
        return "calculate_dilution"

    @property
    def description(self) -> str:
        return (
            "Solves the dilution equation C1*V1 = C2*V2. Given any three parameters, "
            "it calculates the fourth. Can also convert between Molar (M) and mass-based (mg/L, %) "
            "concentrations. Supports density (g/mL) for weight-to-volume conversions."
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
                "smiles": {"type": "string", "description": "SMILES of the solute (required if converting between Molar and mass units)."},
                "d1": {"type": "number", "description": "Density of stock solution (g/mL). Required for accurate % w/w conversions."},
                "d2": {"type": "number", "description": "Density of final solution (g/mL)."}
            },
            "required": ["u1", "u2", "uv1", "uv2"]
        }

    def _to_standard_unit(self, value: float, unit: str, mw: Optional[float] = None, density: Optional[float] = None) -> float:
        """Converts any concentration to mg/L (standard internal unit)."""
        if unit == "mg/L" or unit == "ppm":
            return value
        if unit == "g/L":
            return value * 1000.0
        if unit == "%":
            # 1% w/w = 10g/kg. If density is provided, convert to mg/L (w/v)
            if density:
                return value * 10000.0 * density
            return value * 10000.0 # Assume density 1.0 if not provided
        
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

    def _from_standard_unit(self, value: float, unit: str, mw: Optional[float] = None, density: Optional[float] = None) -> float:
        """Converts from mg/L to target unit."""
        if unit == "mg/L" or unit == "ppm":
            return value
        if unit == "g/L":
            return value / 1000.0
        if unit == "%":
            if density:
                return value / (10000.0 * density)
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
            d1 = kwargs.get("d1")
            d2 = kwargs.get("d2")

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
            c1_std = self._to_standard_unit(c1, u1, mw, d1) if c1 is not None else None
            v1_std = self._vol_to_ml(v1, uv1) if v1 is not None else None
            c2_std = self._to_standard_unit(c2, u2, mw, d2) if c2 is not None else None
            v2_std = self._vol_to_ml(v2, uv2) if v2 is not None else None

            if target == "v1":
                # v1 = c2*v2 / c1
                v1_std = (c2_std * v2_std) / c1_std
                v1 = self._vol_from_ml(v1_std, uv1)
                result = {"v1": round(v1, 4), "unit": uv1}
            elif target == "c1":
                # c1 = c2*v2 / v1
                c1_std = (c2_std * v2_std) / v1_std
                c1 = self._from_standard_unit(c1_std, u1, mw, d1)
                result = {"c1": round(c1, 4), "unit": u1}
            elif target == "v2":
                # v2 = c1*v1 / c2
                v2_std = (c1_std * v1_std) / c2_std
                v2 = self._vol_from_ml(v2_std, uv2)
                result = {"v2": round(v2, 4), "unit": uv2}
            elif target == "c2":
                # c2 = c1*v1 / v2
                c2_std = (c1_std * v1_std) / v2_std
                c2 = self._from_standard_unit(c2_std, u2, mw, d2)
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

class CalculateDensityConversionTool(BaseTool):
    """
    Converts between Mass, Volume, and Density (m = V * d).
    """
    @property
    def name(self) -> str:
        return "calculate_density_conversion"

    @property
    def description(self) -> str:
        return "Converts between Mass, Volume, and Density using the formula Mass = Volume * Density."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "mass": {"type": "number", "description": "Mass of the substance."},
                "mass_unit": {"type": "string", "enum": ["g", "mg", "kg"], "default": "g"},
                "volume": {"type": "number", "description": "Volume of the substance."},
                "volume_unit": {"type": "string", "enum": ["L", "mL", "uL"], "default": "mL"},
                "density": {"type": "number", "description": "Density of the substance (g/mL)."}
            }
        }

    def execute(self, **kwargs) -> Dict[str, Any]:
        try:
            mass = kwargs.get("mass")
            m_unit = kwargs.get("mass_unit", "g")
            volume = kwargs.get("volume")
            v_unit = kwargs.get("volume_unit", "mL")
            density = kwargs.get("density")

            # Check which one is missing
            params = {"mass": mass, "volume": volume, "density": density}
            missing = [k for k, v in params.items() if v is None]

            if len(missing) != 1:
                return {"error": "Exactly one parameter (mass, volume, or density) must be missing."}

            target = missing[0]

            # Standard units: g, mL, g/mL
            m_g = mass
            if mass is not None:
                if m_unit == "mg": m_g = mass / 1000.0
                if m_unit == "kg": m_g = mass * 1000.0

            v_ml = volume
            if volume is not None:
                if v_unit == "L": v_ml = volume * 1000.0
                if v_unit == "uL": v_ml = volume / 1000.0

            if target == "mass":
                m_g = v_ml * density
                res = m_g
                if m_unit == "mg": res = m_g * 1000.0
                if m_unit == "kg": res = m_g / 1000.0
                return {"status": "success", "calculated": "mass", "result": round(res, 4), "unit": m_unit}
            
            if target == "volume":
                v_ml = m_g / density
                res = v_ml
                if v_unit == "L": res = v_ml / 1000.0
                if v_unit == "uL": res = v_ml * 1000.0
                return {"status": "success", "calculated": "volume", "result": round(res, 4), "unit": v_unit}

            if target == "density":
                density = m_g / v_ml
                return {"status": "success", "calculated": "density", "result": round(density, 4), "unit": "g/mL"}

        except Exception as e:
            return {"error": f"Density conversion failed: {str(e)}"}

class CalculateMixtureCompositionTool(BaseTool):
    """
    Calculates the final composition of a mixture when multiple sources are combined.
    """
    @property
    def name(self) -> str:
        return "calculate_mixture_composition"

    @property
    def description(self) -> str:
        return "Calculates total mass, volume, and final concentration of a mixture from multiple ingredients."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ingredients": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "amount": {"type": "number"},
                            "unit": {"type": "string", "enum": ["g", "mg", "kg", "L", "mL", "uL"]},
                            "concentration": {"type": "number", "description": "Concentration in % w/w or mg/L."},
                            "conc_unit": {"type": "string", "enum": ["%", "mg/L", "g/L"], "default": "%"},
                            "density": {"type": "number", "description": "Density (g/mL). Default 1.0."}
                        },
                        "required": ["amount", "unit"]
                    }
                }
            },
            "required": ["ingredients"]
        }

    def execute(self, ingredients: list) -> Dict[str, Any]:
        try:
            total_mass_g = 0.0
            total_volume_ml = 0.0
            total_solute_mass_mg = 0.0

            for ing in ingredients:
                amt = ing["amount"]
                unit = ing["unit"]
                conc = ing.get("concentration", 0.0)
                c_unit = ing.get("conc_unit", "%")
                density = ing.get("density", 1.0)

                # Convert amount to mass (g) and volume (mL)
                if unit in ["g", "mg", "kg"]:
                    m_g = amt
                    if unit == "mg": m_g = amt / 1000.0
                    if unit == "kg": m_g = amt * 1000.0
                    v_ml = m_g / density
                else:
                    v_ml = amt
                    if unit == "L": v_ml = amt * 1000.0
                    if unit == "uL": v_ml = amt / 1000.0
                    m_g = v_ml * density

                # Calculate solute mass (mg)
                if c_unit == "%":
                    # % is w/w: 1% = 10g solute per 1kg total mass = 10mg per 1g
                    solute_mg = (conc / 100.0) * m_g * 1000.0
                elif c_unit == "mg/L":
                    solute_mg = (conc * v_ml) / 1000.0
                elif c_unit == "g/L":
                    solute_mg = conc * v_ml

                total_mass_g += m_g
                total_volume_ml += v_ml
                total_solute_mass_mg += solute_mg

            final_conc_pct = (total_solute_mass_mg / (total_mass_g * 1000.0)) * 100.0
            final_conc_mg_l = (total_solute_mass_mg / total_volume_ml) * 1000.0 if total_volume_ml > 0 else 0.0

            return {
                "status": "success",
                "total_mass_g": round(total_mass_g, 2),
                "total_volume_ml": round(total_volume_ml, 2),
                "final_concentration_pct": round(final_conc_pct, 4),
                "final_concentration_mg_l": round(final_conc_mg_l, 2),
                "summary": f"Mixture total: {round(total_mass_g, 2)}g ({round(total_volume_ml, 2)}mL) at {round(final_conc_pct, 4)}%."
            }
        except Exception as e:
            return {"error": f"Mixture calculation failed: {str(e)}"}

class CalculateDosageTool(BaseTool):
    """
    Calculates the amount of a substance to add to a batch based on target dosage.
    """
    @property
    def name(self) -> str:
        return "calculate_dosage"

    @property
    def description(self) -> str:
        return "Calculates the mass or volume of an ingredient required to reach a specific dosage in a batch."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "batch_size": {"type": "number", "description": "Size of the total batch."},
                "batch_unit": {"type": "string", "enum": ["kg", "g", "L", "mL"], "default": "kg"},
                "target_dosage": {"type": "number", "description": "Target dosage percentage (%)."},
                "ingredient_density": {"type": "number", "description": "Density of the ingredient to add (g/mL). Default 1.0."}
            },
            "required": ["batch_size", "target_dosage"]
        }

    def execute(self, **kwargs) -> Dict[str, Any]:
        try:
            batch_size = kwargs["batch_size"]
            unit = kwargs.get("batch_unit", "kg")
            dosage = kwargs["target_dosage"]
            density = kwargs.get("ingredient_density", 1.0)

            # Convert batch to grams
            if unit == "kg": m_g = batch_size * 1000.0
            elif unit == "g": m_g = batch_size
            elif unit == "L": m_g = batch_size * 1000.0 * 1.0 # Assume batch density 1.0 for simplicity
            elif unit == "mL": m_g = batch_size * 1.0

            # Dosage is typically % w/w
            ing_mass_g = (dosage / 100.0) * m_g
            ing_vol_ml = ing_mass_g / density

            return {
                "status": "success",
                "required_mass_g": round(ing_mass_g, 2),
                "required_volume_ml": round(ing_vol_ml, 2),
                "summary": f"To reach {dosage}% dosage in a {batch_size}{unit} batch, add {round(ing_mass_g, 2)}g of the ingredient."
            }
        except Exception as e:
            return {"error": f"Dosage calculation failed: {str(e)}"}

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

class CalculateVocContentTool(BaseTool):
    """
    Calculates the Volatile Organic Compound (VOC) content of a mixture.
    Supports EU (BP <= 250C) and US EPA (BP <= 250C with specific exemptions) standards.
    """
    # US EPA Negligibly Reactive (Exempt) Compounds
    # Standard List: Acetone, Ethane, Methane, Methyl Acetate, etc.
    _US_EPA_EXEMPT_SMILES = [
        "CC(=O)C",    # Acetone
        "CC",         # Ethane
        "C",          # Methane
        "COC(=O)C",   # Methyl Acetate
        "C(Cl)(F)(F)F", # Various CFCs/HCFCs could be added
    ]

    @property
    def name(self) -> str:
        return "calculate_voc_content"

    @property
    def description(self) -> str:
        return (
            "Calculates the total VOC content (g/L and %) of a mixture. "
            "Supports regional standards: 'EU' (BP <= 250°C), 'US_EPA' (BP <= 250°C with exemptions like Acetone), "
            "and 'US_CARB' (BP <= 216°C)."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "components": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "smiles": {"type": "string", "description": "SMILES of the component."},
                            "mass_g": {"type": "number", "description": "Mass of the component in grams."},
                            "density_g_ml": {"type": "number", "description": "Density of the component in g/mL. Default 1.0."}
                        },
                        "required": ["smiles", "mass_g"]
                    }
                },
                "region": {
                    "type": "string", 
                    "enum": ["EU", "US_EPA", "US_CARB"], 
                    "default": "EU",
                    "description": "The regulatory region for VOC definition. EU (250°C), US_EPA (250°C + exemptions), US_CARB (216°C)."
                }
            },
            "required": ["components"]
        }

    def execute(self, components: List[Dict[str, Any]], region: str = "EU") -> Dict[str, Any]:
        try:
            volatility_tool = EstimateVolatilityAndNoteTool()
            total_mass = 0.0
            total_volume = 0.0
            voc_mass = 0.0
            component_details = []

            # Define BP threshold based on region
            bp_threshold = 250.0
            if region == "US_CARB":
                bp_threshold = 216.0

            for comp in components:
                smiles = comp["smiles"]
                mass = comp["mass_g"]
                density = comp.get("density_g_ml", 1.0)
                
                total_mass += mass
                total_volume += (mass / density)
                
                with rdBase.BlockLogs():
                    mol = Chem.MolFromSmiles(smiles)
                
                # Check if organic (contains Carbon)
                is_organic = any(atom.GetAtomicNum() == 6 for atom in mol.GetAtoms()) if mol else False
                
                if not is_organic:
                    is_voc = False
                    bp = 0.0
                    reason = "Inorganic"
                else:
                    # Estimate boiling point
                    vol_res = volatility_tool.execute(smiles)
                    if "error" in vol_res:
                        return {"error": f"Volatility estimation failed for SMILES {smiles}: {vol_res['error']}"}
                    
                    bp = vol_res.get("estimated_boiling_point_c", 0.0)
                    
                    # Core VOC logic
                    is_voc = bp <= bp_threshold
                    reason = f"BP ({round(bp,1)}°C) <= {bp_threshold}°C" if is_voc else f"BP ({round(bp,1)}°C) > {bp_threshold}°C"
                    
                    # US EPA Exemption Check
                    if region == "US_EPA" and is_voc:
                        # Canonicalize smiles for comparison
                        can_smiles = Chem.MolToSmiles(mol, isomericSmiles=True)
                        exempt_can = [Chem.MolToSmiles(Chem.MolFromSmiles(s), isomericSmiles=True) for s in self._US_EPA_EXEMPT_SMILES]
                        
                        if can_smiles in exempt_can:
                            is_voc = False
                            reason = "US EPA Exempt (Negligibly Reactive)"
                
                if is_voc:
                    voc_mass += mass
                
                component_details.append({
                    "smiles": smiles,
                    "boiling_point_c": bp if is_organic else "N/A",
                    "is_voc": is_voc,
                    "mass_g": mass,
                    "is_organic": is_organic,
                    "classification_reason": reason
                })

            voc_pct = (voc_mass / total_mass * 100.0) if total_mass > 0 else 0.0
            voc_g_l = (voc_mass / total_volume * 1000.0) if total_volume > 0 else 0.0

            return {
                "region_applied": region,
                "bp_threshold_used": bp_threshold,
                "total_mass_g": round(total_mass, 2),
                "total_volume_ml": round(total_volume, 2),
                "voc_mass_g": round(voc_mass, 2),
                "voc_percentage": round(voc_pct, 2),
                "voc_g_l": round(voc_g_l, 2),
                "component_audit": component_details,
                "status": "success",
                "summary": f"[{region}] Mixture contains {round(voc_pct, 2)}% VOCs ({round(voc_g_l, 2)} g/L)."
            }
        except Exception as e:
            return {"error": f"VOC calculation failed: {str(e)}"}

# Register tools
ToolRegistry.register(CalculateDilutionTool())
ToolRegistry.register(CalculateStoichiometryTool())
ToolRegistry.register(CalculateDensityConversionTool())
ToolRegistry.register(CalculateMixtureCompositionTool())
ToolRegistry.register(CalculateDosageTool())
ToolRegistry.register(CalculateVocContentTool())
