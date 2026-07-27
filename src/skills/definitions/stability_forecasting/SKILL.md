---
name: stability_forecasting
description: Predict product shelf life and degradation kinetics using Arrhenius modeling.
---

# Stability & Shelf Life Forecasting Skill

This skill allows you to estimate how long a product (flavor, beverage, or chemical mixture) will remain stable under different storage conditions based on accelerated testing data.

## Core Tool
- `predict_shelf_life_arrhenius`: Uses the Arrhenius equation to extrapolate degradation data from high temperatures (e.g., 40°C, 50°C) to target temperatures (e.g., 25°C).

## Workflow

### 1. Data Preparation
- Collect stability data containing at least two (ideally three or more) different temperatures.
- Each temperature should have multiple time points showing the degradation of a key quality attribute (e.g., aroma concentration, sensory score, or color).

### 2. Kinetic Modeling
- Call `predict_shelf_life_arrhenius` with your data.
- **Failure Threshold**: Define the point at which the product is no longer acceptable (e.g., if starting at 100%, a failure threshold of 90 means 10% loss).

### 3. Result Interpretation
- **Reaction Order**: The tool automatically detects if the degradation is Linear (0th order) or Logarithmic (1st order).
- **Activation Energy (Ea)**: Look at the Ea value. 
  - Standard food/flavor reactions: **40 - 125 kJ/mol**.
  - If Ea is outside this range, be cautious; the degradation mechanism might have changed at high temperatures.
- **Extrapolation**: The tool provides the predicted shelf life at your target temperature (usually 25°C or 4°C).

### 4. Risk Assessment
- Check the **Arrhenius R²**. A value > 0.9 indicates a reliable model.
- If the tool provides warnings about low correlation, recommend more testing or use a shorter safety margin.

## Guidelines
- **Units**: Ensure time units are consistent (always days, or always weeks).
- **Temperature**: Input temperatures in Celsius; the tool handles Kelvin conversion internally.
- **Matrix Effects**: Remind the user that changes in pH or packaging can significantly alter $Ea$ and shelf life.
