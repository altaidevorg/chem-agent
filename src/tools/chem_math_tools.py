import json
from typing import Any, Dict, List, Optional
from rdkit import Chem, rdBase
from rdkit.Chem import Descriptors
from src.tools.base import BaseTool, ToolRegistry
from src.tools.rdkit_tools import EstimateVolatilityAndNoteTool

class CalculateDilutionTool(BaseTool):
    """
    Calculates dilution parameters using C1V1 = C2V2.
    Requires strict JSON schema parameter matching and fails fast on missing units.
    """

    @property
    def name(self) -> str:
        return "calculate_dilution"

    @property
    def description(self) -> str:
        return (
            "Solves the dilution equation C1*V1 = C2*V2. Given any three parameters, "
            "it calculates the fourth. Requires strict unit parameters (u1, u2, uv1, uv2)."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "c1": {"type": "number", "description": "Initial concentration."},
                "u1": {"type": "string", "enum": ["M", "mM", "uM", "mg/L", "g/L", "ppm", "%"], "description": "Unit of c1."},
                "v1": {"type": "number", "description": "Initial volume."},
                "uv1": {"type": "string", "enum": ["L", "mL", "uL"], "description": "Unit of v1."},
                "c2": {"type": "number", "description": "Final concentration."},
                "u2": {"type": "string", "enum": ["M", "mM", "uM", "mg/L", "g/L", "ppm", "%"], "description": "Unit of c2."},
                "v2": {"type": "number", "description": "Final volume."},
                "uv2": {"type": "string", "enum": ["L", "mL", "uL"], "description": "Unit of v2."},
                "smiles": {"type": "string", "description": "SMILES of the solute (required for Molar conversions)."},
                "d1": {"type": "number", "description": "Density of stock solution (g/mL)."},
                "d2": {"type": "number", "description": "Density of final solution (g/mL)."}
            },
            "required": ["u1", "u2", "uv1", "uv2"]
        }

    def _to_standard_unit(self, value: float, unit: str, mw: Optional[float] = None, density: Optional[float] = None) -> float:
        if not unit:
            raise ValueError("Concentration unit cannot be empty.")
        if unit in ["mg/L", "ppm"]:
            return value
        if unit == "g/L":
            return value * 1000.0
        if unit == "%":
            d = density if density is not None else 1.0
            return value * 10000.0 * d
        if unit in ["M", "mM", "uM"]:
            if mw is None:
                raise ValueError(f"SMILES/Molecular weight required for molar unit: '{unit}'")
            if unit == "M": return value * mw * 1000.0
            if unit == "mM": return value * mw
            if unit == "uM": return value * mw / 1000.0
            
        raise ValueError(f"Unsupported concentration unit: '{unit}'")

    def _from_standard_unit(self, value: float, unit: str, mw: Optional[float] = None, density: Optional[float] = None) -> float:
        if not unit:
            raise ValueError("Concentration unit cannot be empty.")
        if unit in ["mg/L", "ppm"]:
            return value
        if unit == "g/L":
            return value / 1000.0
        if unit == "%":
            d = density if density is not None else 1.0
            return value / (10000.0 * d)
        if unit in ["M", "mM", "uM"]:
            if mw is None:
                raise ValueError(f"SMILES/Molecular weight required for molar unit: '{unit}'")
            if unit == "M": return value / (mw * 1000.0)
            if unit == "mM": return value / mw
            if unit == "uM": return (value * 1000.0) / mw
            
        raise ValueError(f"Unsupported concentration unit: '{unit}'")

    def _vol_to_ml(self, value: float, unit: str) -> float:
        if unit == "mL": return value
        if unit == "L": return value * 1000.0
        if unit == "uL": return value / 1000.0
        raise ValueError(f"Unsupported volume unit: '{unit}'")

    def _vol_from_ml(self, value: float, unit: str) -> float:
        if unit == "mL": return value
        if unit == "L": return value / 1000.0
        if unit == "uL": return value * 1000.0
        raise ValueError(f"Unsupported volume unit: '{unit}'")

    def execute(self, **kwargs) -> Dict[str, Any]:
        try:
            c1, u1 = kwargs.get("c1"), kwargs.get("u1")
            v1, uv1 = kwargs.get("v1"), kwargs.get("uv1")
            c2, u2 = kwargs.get("c2"), kwargs.get("u2")
            v2, uv2 = kwargs.get("v2"), kwargs.get("uv2")
            smiles = kwargs.get("smiles")
            d1, d2 = kwargs.get("d1"), kwargs.get("d2")

            if not u1 or not u2 or not uv1 or not uv2:
                return {
                    "status": "error",
                    "error": "Missing required unit parameters. 'u1', 'u2', 'uv1', and 'uv2' are strictly required."
                }

            mw = None
            if smiles:
                mol = Chem.MolFromSmiles(smiles)
                if mol:
                    mw = Descriptors.MolWt(mol)
                else:
                    return {"status": "error", "error": f"Invalid SMILES string provided: '{smiles}'"}

            params = {"c1": c1, "v1": v1, "c2": c2, "v2": v2}
            missing = [k for k, v in params.items() if v is None]

            if len(missing) != 1:
                return {
                    "status": "error",
                    "error": f"Exactly one parameter (c1, v1, c2, or v2) must be missing to solve C1V1=C2V2. Provided parameters: {params}"
                }

            target = missing[0]

            c1_std = self._to_standard_unit(c1, u1, mw, d1) if c1 is not None else None
            v1_std = self._vol_to_ml(v1, uv1) if v1 is not None else None
            c2_std = self._to_standard_unit(c2, u2, mw, d2) if c2 is not None else None
            v2_std = self._vol_to_ml(v2, uv2) if v2 is not None else None

            if target == "v1":
                v1_std = (c2_std * v2_std) / c1_std
                v1 = self._vol_from_ml(v1_std, uv1)
                result = {"v1": round(v1, 4), "unit": uv1}
            elif target == "c1":
                c1_std = (c2_std * v2_std) / v1_std
                c1 = self._from_standard_unit(c1_std, u1, mw, d1)
                result = {"c1": round(c1, 4), "unit": u1}
            elif target == "v2":
                v2_std = (c1_std * v1_std) / c2_std
                v2 = self._vol_from_ml(v2_std, uv2)
                result = {"v2": round(v2, 4), "unit": uv2}
            elif target == "c2":
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
            return {"status": "error", "error": f"Dilution calculation failed: {str(e)}"}


class CalculateDensityConversionTool(BaseTool):
    """
    Converts between Mass, Volume, and Density (m = V * d).
    """
    @property
    def name(self) -> str:
        return "calculate_density_conversion"

    @property
    def description(self) -> str:
        return "Converts between Mass, Volume, and Density using the formula Mass = Volume * Density. Never calculate mass/volume/density conversions mentally — always use this tool."

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

            params = {"mass": mass, "volume": volume, "density": density}
            missing = [k for k, v in params.items() if v is None]

            if len(missing) != 1:
                return {"status": "error", "error": f"Exactly one parameter (mass, volume, or density) must be missing. Got missing: {missing}"}

            target = missing[0]

            m_g = mass
            if mass is not None:
                if m_unit == "mg": m_g = mass / 1000.0
                elif m_unit == "kg": m_g = mass * 1000.0
                elif m_unit == "g": m_g = mass
                else: return {"status": "error", "error": f"Unsupported mass_unit: '{m_unit}'"}

            v_ml = volume
            if volume is not None:
                if v_unit == "L": v_ml = volume * 1000.0
                elif v_unit == "uL": v_ml = volume / 1000.0
                elif v_unit == "mL": v_ml = volume
                else: return {"status": "error", "error": f"Unsupported volume_unit: '{v_unit}'"}

            if target == "mass":
                if density <= 0: return {"status": "error", "error": f"Invalid density: {density}"}
                m_g = v_ml * density
                res = m_g
                if m_unit == "mg": res = m_g * 1000.0
                if m_unit == "kg": res = m_g / 1000.0
                return {"status": "success", "calculated": "mass", "result": round(res, 4), "unit": m_unit}
            
            if target == "volume":
                if density <= 0: return {"status": "error", "error": f"Invalid density: {density}"}
                v_ml = m_g / density
                res = v_ml
                if v_unit == "L": res = v_ml / 1000.0
                if v_unit == "uL": res = v_ml * 1000.0
                return {"status": "success", "calculated": "volume", "result": round(res, 4), "unit": v_unit}

            if target == "density":
                if v_ml <= 0: return {"status": "error", "error": f"Invalid volume: {v_ml}"}
                density = m_g / v_ml
                return {"status": "success", "calculated": "density", "result": round(density, 4), "unit": "g/mL"}

        except Exception as e:
            return {"status": "error", "error": f"Density conversion failed: {str(e)}"}


class CalculateMixtureCompositionTool(BaseTool):
    """
    Calculates the final composition of a mixture when multiple sources are combined.
    Requires strict schema matching and fails fast on missing ingredient details.
    """
    @property
    def name(self) -> str:
        return "calculate_mixture_composition"

    @property
    def description(self) -> str:
        return "Calculates total mass, volume, and final concentration of a mixture from multiple ingredients. Never calculate mixture compositions mentally — always use this tool."

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

    def execute(self, **kwargs) -> Dict[str, Any]:
        try:
            ingredients = kwargs.get("ingredients")
            if not ingredients or not isinstance(ingredients, list):
                return {"status": "error", "error": "Missing or invalid required 'ingredients' list."}

            total_mass_g = 0.0
            total_volume_ml = 0.0
            total_solute_mass_mg = 0.0

            for idx, ing in enumerate(ingredients):
                amt = ing.get("amount")
                unit = ing.get("unit")
                conc = ing.get("concentration", 0.0)
                c_unit = ing.get("conc_unit", "%")
                density = ing.get("density", 1.0)

                if amt is None or unit is None:
                    return {"status": "error", "error": f"Ingredient at index {idx} is missing 'amount' or 'unit'."}

                if density <= 0:
                    return {"status": "error", "error": f"Ingredient at index {idx} has invalid density: {density}"}

                if unit in ["g", "mg", "kg"]:
                    m_g = amt
                    if unit == "mg": m_g = amt / 1000.0
                    elif unit == "kg": m_g = amt * 1000.0
                    v_ml = m_g / density
                elif unit in ["L", "mL", "uL"]:
                    v_ml = amt
                    if unit == "L": v_ml = amt * 1000.0
                    elif unit == "uL": v_ml = amt / 1000.0
                    m_g = v_ml * density
                else:
                    return {"status": "error", "error": f"Unsupported unit '{unit}' for ingredient at index {idx}."}

                if c_unit == "%":
                    solute_mg = (conc / 100.0) * m_g * 1000.0
                elif c_unit == "mg/L":
                    solute_mg = conc * (v_ml / 1000.0)
                elif c_unit == "g/L":
                    solute_mg = conc * v_ml
                else:
                    return {"status": "error", "error": f"Unsupported conc_unit '{c_unit}' for ingredient at index {idx}."}

                total_mass_g += m_g
                total_volume_ml += v_ml
                total_solute_mass_mg += solute_mg

            final_conc_pct = (total_solute_mass_mg / (total_mass_g * 1000.0)) * 100.0 if total_mass_g > 0 else 0.0
            final_conc_mg_l = (total_solute_mass_mg / (total_volume_ml / 1000.0)) if total_volume_ml > 0 else 0.0

            return {
                "status": "success",
                "total_mass_g": round(total_mass_g, 2),
                "total_volume_ml": round(total_volume_ml, 2),
                "final_concentration_pct": round(final_conc_pct, 4),
                "final_concentration_mg_l": round(final_conc_mg_l, 2),
                "summary": f"Mixture total: {round(total_mass_g, 2)}g ({round(total_volume_ml, 2)}mL) at {round(final_conc_pct, 4)}%."
            }
        except Exception as e:
            return {"status": "error", "error": f"Mixture calculation failed: {str(e)}"}


class CalculateDosageTool(BaseTool):
    """
    Calculates the amount of a substance to add to a batch based on target dosage.
    Strictly validates batch_size and target_dosage.
    """

    @property
    def name(self) -> str:
        return "calculate_dosage"

    @property
    def description(self) -> str:
        return "Calculates mass/volume required for a target dosage in a batch. Never calculate production dosages mentally."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "batch_size": {"type": "number", "description": "Size of the total batch."},
                "batch_unit": {"type": "string", "enum": ["kg", "g", "L", "mL", "mg"], "default": "kg"},
                "target_dosage": {"type": "number", "description": "Target dosage percentage (%)."},
                "ingredient_density": {"type": "number", "description": "Density of the ingredient to add (g/mL). Default 1.0."}
            },
            "required": ["batch_size", "target_dosage"]
        }

    def execute(self, **kwargs) -> Dict[str, Any]:
        try:
            batch_size = kwargs.get("batch_size")
            dosage = kwargs.get("target_dosage")
            unit = kwargs.get("batch_unit", "kg")
            density = kwargs.get("ingredient_density", 1.0)

            # FAIL FAST: Parametre kontrolleri
            if batch_size is None or dosage is None:
                return {
                    "status": "error",
                    "error": "Missing required arguments. Both 'batch_size' and 'target_dosage' must be provided."
                }

            if batch_size <= 0 or dosage <= 0:
                return {
                    "status": "error",
                    "error": f"Invalid input values. 'batch_size' ({batch_size}) and 'target_dosage' ({dosage}) must be strictly positive."
                }

            if density <= 0:
                return {"status": "error", "error": f"Invalid ingredient_density: {density}. Must be > 0."}

            # Birim Dönüşümü (Kanonik Birim: Gram)
            if unit == "kg":
                m_g = batch_size * 1000.0
            elif unit in ["g", "mL"]:
                m_g = batch_size
            elif unit == "L":
                m_g = batch_size * 1000.0
            elif unit == "mg":
                m_g = batch_size / 1000.0
            else:
                return {"status": "error", "error": f"Unsupported batch_unit: '{unit}'."}

            ing_mass_g = (dosage / 100.0) * m_g
            ing_vol_ml = ing_mass_g / density

            return {
                "status": "success",
                "required_mass_g": round(ing_mass_g, 2),
                "required_volume_ml": round(ing_vol_ml, 2),
                "summary": f"To reach {dosage}% dosage in a {batch_size} {unit} batch, add {round(ing_mass_g, 2)}g ({round(ing_vol_ml, 2)}mL) of the ingredient."
            }
        except Exception as e:
            return {"status": "error", "error": f"Dosage calculation failed: {str(e)}"}


class CalculateStoichiometryTool(BaseTool):
    """
    Converts between mass, moles, and number of molecules.
    Strictly follows schema and fails fast on errors.
    """

    @property
    def name(self) -> str:
        return "calculate_stoichiometry"

    @property
    def description(self) -> str:
        return "Converts between mass (g, mg), moles (mol, mmol), and molecular weight using n = m/MW. Never perform stoichiometry or molar calculations mentally — always use this tool."

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

            if not smiles:
                return {"status": "error", "error": "Missing required 'smiles' argument."}

            mol = Chem.MolFromSmiles(smiles)
            if not mol:
                return {"status": "error", "error": f"Invalid SMILES string provided: '{smiles}'"}
            
            mw = Descriptors.MolWt(mol)

            if mass is not None and moles is not None:
                return {"status": "error", "error": "Provide either mass or moles, not both, to calculate the other."}
            
            if mass is not None:
                m_g = mass
                if m_unit == "mg": m_g = mass / 1000.0
                elif m_unit == "kg": m_g = mass * 1000.0
                elif m_unit == "g": m_g = mass
                else: return {"status": "error", "error": f"Unsupported mass_unit: '{m_unit}'"}
                
                n_mol = m_g / mw
                
                res_n = n_mol
                if n_unit == "mmol": res_n = n_mol * 1000.0
                elif n_unit == "umol": res_n = n_mol * 1000000.0
                elif n_unit == "mol": res_n = n_mol
                else: return {"status": "error", "error": f"Unsupported moles_unit: '{n_unit}'"}
                
                return {
                    "status": "success",
                    "input": {"mass": mass, "unit": m_unit},
                    "calculated": {"moles": round(res_n, 6), "unit": n_unit},
                    "molecular_weight": round(mw, 2),
                    "summary": f"{mass} {m_unit} of substance (MW: {round(mw,2)}) is {round(res_n, 6)} {n_unit}."
                }

            if moles is not None:
                n_mol = moles
                if n_unit == "mmol": n_mol = moles / 1000.0
                elif n_unit == "umol": n_mol = moles / 1000000.0
                elif n_unit == "mol": n_mol = moles
                else: return {"status": "error", "error": f"Unsupported moles_unit: '{n_unit}'"}
                
                m_g = n_mol * mw
                
                res_m = m_g
                if m_unit == "mg": res_m = m_g * 1000.0
                elif m_unit == "kg": res_m = m_g / 1000.0
                elif m_unit == "g": res_m = m_g
                else: return {"status": "error", "error": f"Unsupported mass_unit: '{m_unit}'"}

                return {
                    "status": "success",
                    "input": {"moles": moles, "unit": n_unit},
                    "calculated": {"mass": round(res_m, 4), "unit": m_unit},
                    "molecular_weight": round(mw, 2),
                    "summary": f"{moles} {n_unit} of substance (MW: {round(mw,2)}) weighs {round(res_m, 4)} {m_unit}."
                }

            return {"status": "error", "error": "Provide either mass or moles to calculate the other."}

        except Exception as e:
            return {"status": "error", "error": f"Stoichiometry calculation failed: {str(e)}"}


class CalculateVocContentTool(BaseTool):
    """
    Calculates the total VOC content (g/L and %) of a mixture under regional standards.
    Requires SMILES for every organic component to prevent false non-VOC outputs.
    """

    _US_EPA_EXEMPT_SMILES = [
        "CC(=O)C",     # Acetone
        "CC",          # Ethane
        "C",           # Methane
        "COC(=O)C",    # Methyl Acetate
        "C(Cl)(F)(F)F",
    ]

    @property
    def name(self) -> str:
        return "calculate_voc_content"

    @property
    def description(self) -> str:
        return (
            "Calculates total VOC content (g/L and %) of a mixture under EU, US_EPA, or US_CARB standards. "
            "Requires SMILES for each component."
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
                            "density_g_ml": {"type": "number", "description": "Density of component in g/mL. Default 1.0."}
                        },
                        "required": ["smiles", "mass_g"]
                    }
                },
                "region": {
                    "type": "string",
                    "enum": ["EU", "US_EPA", "US_CARB"],
                    "default": "EU",
                    "description": "Regulatory region: EU (BP <= 250°C), US_EPA (250°C + exemptions), US_CARB (BP <= 216°C)."
                }
            },
            "required": ["components"]
        }

    def execute(self, **kwargs) -> Dict[str, Any]:
        try:
            region = kwargs.get("region", "EU")
            components = kwargs.get("components")

            if not components or not isinstance(components, list):
                return {"status": "error", "error": "Missing or invalid 'components' list."}

            volatility_tool = EstimateVolatilityAndNoteTool()
            total_mass = 0.0
            total_volume = 0.0
            voc_mass = 0.0
            component_details = []

            bp_threshold = 216.0 if region == "US_CARB" else 250.0

            for idx, comp in enumerate(components):
                smiles = comp.get("smiles")
                mass = comp.get("mass_g")
                density = comp.get("density_g_ml", 1.0)

                # FAIL FAST: Bileşen verileri eksikse hata dön!
                if not smiles or not isinstance(smiles, str) or not smiles.strip():
                    return {
                        "status": "error",
                        "error": f"Component at index {idx} is missing a valid 'smiles' string. Cannot determine VOC status without chemical structure."
                    }

                if mass is None or mass < 0:
                    return {"status": "error", "error": f"Component at index {idx} ({smiles}) has invalid mass_g: {mass}"}

                if density <= 0:
                    return {"status": "error", "error": f"Component at index {idx} ({smiles}) has invalid density_g_ml: {density}"}

                total_mass += mass
                total_volume += (mass / density)

                with rdBase.BlockLogs():
                    mol = Chem.MolFromSmiles(smiles)

                if not mol:
                    return {"status": "error", "error": f"RDKit failed to parse SMILES string '{smiles}' at component index {idx}."}

                is_organic = any(atom.GetAtomicNum() == 6 for atom in mol.GetAtoms())

                if not is_organic:
                    is_voc = False
                    bp = 0.0
                    reason = "Inorganic"
                else:
                    vol_res = volatility_tool.execute(smiles=smiles)
                    if "error" in vol_res or vol_res.get("status") == "error":
                        return {"status": "error", "error": f"Volatility estimation failed for SMILES '{smiles}': {vol_res.get('error')}"}

                    bp = vol_res.get("estimated_boiling_point_c", 0.0)
                    is_voc = bp <= bp_threshold
                    reason = f"BP ({round(bp,1)}°C) <= {bp_threshold}°C" if is_voc else f"BP ({round(bp,1)}°C) > {bp_threshold}°C"

                    if region == "US_EPA" and is_voc:
                        can_smiles = Chem.MolToSmiles(mol, isomericSmiles=True)
                        exempt_can = [Chem.MolToSmiles(Chem.MolFromSmiles(s), isomericSmiles=True) for s in self._US_EPA_EXEMPT_SMILES if Chem.MolFromSmiles(s)]

                        if can_smiles in exempt_can:
                            is_voc = False
                            reason = "US EPA Exempt (Negligibly Reactive)"

                if is_voc:
                    voc_mass += mass

                component_details.append({
                    "smiles": smiles,
                    "boiling_point_c": round(bp, 1) if is_organic else "N/A",
                    "is_voc": is_voc,
                    "mass_g": mass,
                    "is_organic": is_organic,
                    "classification_reason": reason
                })

            voc_pct = (voc_mass / total_mass * 100.0) if total_mass > 0 else 0.0
            voc_g_l = (voc_mass / (total_volume / 1000.0)) if total_volume > 0 else 0.0

            return {
                "status": "success",
                "region_applied": region,
                "bp_threshold_used": bp_threshold,
                "total_mass_g": round(total_mass, 2),
                "total_volume_ml": round(total_volume, 2),
                "voc_mass_g": round(voc_mass, 2),
                "voc_percentage": round(voc_pct, 2),
                "voc_g_l": round(voc_g_l, 2),
                "component_audit": component_details,
                "summary": f"[{region}] Mixture contains {round(voc_pct, 2)}% VOCs ({round(voc_g_l, 2)} g/L)."
            }
        except Exception as e:
            return {"status": "error", "error": f"VOC calculation failed: {str(e)}"}


# Register tools
ToolRegistry.register(CalculateDilutionTool())
ToolRegistry.register(CalculateStoichiometryTool())
ToolRegistry.register(CalculateDensityConversionTool())
ToolRegistry.register(CalculateMixtureCompositionTool())
ToolRegistry.register(CalculateDosageTool())
ToolRegistry.register(CalculateVocContentTool())