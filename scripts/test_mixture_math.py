import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from src.tools.chem_math_tools import (
    CalculateDilutionTool, 
    CalculateDensityConversionTool, 
    CalculateMixtureCompositionTool, 
    CalculateDosageTool
)

def test_math():
    # 1. Density-Aware Dilution
    # 50% w/w Citral (density 0.89) diluted to 100 mg/L in 1L
    dil_tool = CalculateDilutionTool()
    res_dil = dil_tool.execute(
        c1=50, u1="%", d1=0.89,
        c2=100, u2="mg/L",
        v2=1, uv2="L",
        uv1="mL"
    )
    print(f"\n1. Dilution Result: {res_dil['summary']}")
    
    # 2. Density Conversion
    # What is the volume of 500g of a flavor with density 1.05?
    dens_tool = CalculateDensityConversionTool()
    res_dens = dens_tool.execute(mass=500, mass_unit="g", density=1.05, volume_unit="mL")
    print(f"2. Density Result: {res_dens['result']} {res_dens['unit']}")
    
    # 3. Mixture Composition
    # Mix 100g of 10% solution + 200g of 5% solution
    mix_tool = CalculateMixtureCompositionTool()
    res_mix = mix_tool.execute(ingredients=[
        {"amount": 100, "unit": "g", "concentration": 10, "conc_unit": "%"},
        {"amount": 200, "unit": "g", "concentration": 5, "conc_unit": "%"}
    ])
    print(f"3. Mixture Result: {res_mix['summary']}")
    
    # 4. Dosage
    # Dose at 0.05% for a 250kg batch
    dose_tool = CalculateDosageTool()
    res_dose = dose_tool.execute(batch_size=250, batch_unit="kg", target_dosage=0.05)
    print(f"4. Dosage Result: {res_dose['summary']}")

if __name__ == "__main__":
    test_math()
