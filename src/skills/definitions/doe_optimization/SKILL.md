---
name: doe_optimization
description: Design and analyze experimental trials (DoE) to optimize formulations and processes using statistical modeling.
---

# Design of Experiments (DoE) & Optimization

This skill enables the agent to assist R&D chemists in designing smarter experiments and optimizing formulations using statistical modeling and Response Surface Methodology (RSM).

## Capabilities
- **ANOVA (Analysis of Variance):** Determine which factors (e.g., Temperature, Concentration, pH) have a statistically significant impact on the final result.
- **Main Effects Analysis:** Calculate how much each factor changes the response and in which direction (positive/negative).
- **Formulation Optimization:** Identify the "Optimal Point" to reach a target goal (e.g., maximum yield, best sensory score, minimum cost).
- **Reduced Trial Count:** Use statistical modeling to predict results for combinations that haven't been tested yet.

## When to Use
- When optimizing a flavor or fragrance formula with multiple ingredients.
- When searching for the best reaction conditions in a laboratory setting.
- When trying to understand complex interactions between process variables.

## Tools
- `analyze_doe_results`: Fits a response surface model, runs ANOVA, and finds the optimal factor settings.

## Workflow Example
1. The user provides a table of recent experiments (e.g., 3 variables, 8 trials).
2. The agent uses `analyze_doe_results` to fit a model.
3. The agent reports which variable is the "bottleneck" and proposes the exact settings for the next successful batch.
