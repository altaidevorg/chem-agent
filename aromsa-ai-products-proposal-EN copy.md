# AI Products Proposal for Aromsa

**Two Complementary AI Products for a Flavor Manufacturer:
(A) A Domain-Specialized Local Chemistry Model · (B) An Agent Platform for Factory Efficiency**

Prepared by: [Company] · Target Customer: Aromsa Food Flavors and Additives Industry and Trade Inc. · Date: July 2026 · Status: Draft v1.0

---

## Overview: Two Products, One Thesis

Both products in this document rest on the same observation: in a flavor company, the scarcest resources are **expert time** and **trustworthy information flow**, and the strictest constraint is **formula confidentiality**. Accordingly, both products (a) absorb computable and document-heavy work rather than promising speculative "AI magic," (b) keep humans in control of every consequential decision, and (c) run entirely on-premises so that no formula, customer brief or process record ever leaves the site.

| | Product A | Product B |
|---|---|---|
| What it is | 9B-parameter chemistry-specialist LLM with built-in RDKit and statistics agent skills | Platform of process-specialized LLM agents layered on ERP/SCADA/LIMS |
| Primary users | R&D chemists, quality lab, application teams | Production, planning, quality, maintenance, technical sales support |
| Core value | Researcher time reallocated from desk work to experiments (≈3–10 FTE-equiv./yr) | Documentation, release, deviation and changeover efficiency (≈5–10 FTE-equiv./yr at the conservative end, plus availability and energy gains) |
| Deployment | Single-GPU on-prem workstation/server | On-prem platform; can share Product A's hardware |
| Proof mechanism | 6–8 week pilot vs. pre-measured baseline | 8–10 week pilot with explicit stop-condition |

The products can be adopted independently, but they compound: Product B's quality-deviation agent gains chemical root-cause depth when backed by Product A, and both share one data-sovereignty infrastructure.

All quantitative bands in this document are benchmark-informed estimates quoted at the conservative end; they are targets to be validated against baselines measured on Aromsa's own data, not commitments.

---

# PART A — Domain-Specialized Local AI Model for Chemistry

**A Compact, On-Premises Language Model for Cheminformatics and Statistical Analysis**

---

## A.1 Executive Summary

This document describes a 9-billion-parameter language model, specialized in chemistry, that runs entirely on-premises, and the concrete value it can deliver to a flavor manufacturer such as Aromsa.

Three things distinguish the product:

1. **Domain specialization.** The model is not a general-purpose chatbot. It was trained on books and academic literature covering the industrial applications of chemistry — food, flavor, coatings, pharmaceuticals and adjacent fields — and additionally trained for code generation and agentic task execution.
2. **It computes, it doesn't just converse.** The model ships with two built-in agent skills: RDKit-based cheminformatics and statistical analysis. Given a task, it writes and executes code locally, then interprets and reports the results. Numerical outputs come from validated open-source libraries (RDKit, standard statistics stacks), not from the model "guessing" numbers — an important reliability distinction.
3. **Data sovereignty.** At 9B parameters, the model runs on a single workstation-class GPU with no internet connection. Formulations — the core trade secret of any flavor house — never leave the site.

The product can optionally be extended with customer-specific skills and additional fine-tuning on the customer's own documents and workflows.

**Honest framing of capability:** this is a productivity and decision-support tool for chemists, not a replacement for them. It accelerates screening, calculation, literature-grounded reasoning and data analysis. Novel discovery, final formulation decisions and regulatory sign-off remain human responsibilities, and the deployment model is designed around human verification of outputs.

---

## A.2 What the Product Is

### A.2.1 Technical Identity

| Attribute | Description |
|---|---|
| Model size | 9 billion parameters (compact class) |
| Training data | Books and papers on industrial chemistry applications (food, flavor, coatings, pharma, polymers, cosmetics, etc.) plus code and agent-behavior training |
| Deployment | Fully local / on-premises; no internet connection required |
| Hardware profile | Runs on a single-GPU workstation or server (quantized deployment options available) |
| Built-in agent skills | (a) RDKit-based cheminformatics, (b) statistical analysis |
| Extensibility | New skills can be added; the model can be further fine-tuned per use case |
| Interface | Chat interface + agentic task execution; optional integration with LIMS, ERP and laboratory data sources |

### A.2.2 What "Agent Skill" Means

A conventional language model answers questions with text. This model, given a task, **writes code, executes it locally, checks the result and reports back.** Example:

> User: "Compute logP and estimated volatility descriptors for these 40 molecules, group them statistically, and propose top/heart/base-note candidate classifications."
>
> Model: parses the SMILES inputs with RDKit → computes descriptors → performs the statistical grouping → returns a table with interpretation. Everything runs on the local machine.

Because the arithmetic is done by RDKit and statistical libraries rather than by the neural network itself, the numbers are reproducible and auditable.

### A.2.3 Built-in Skill 1: Cheminformatics (RDKit)

Task classes the model executes out of the box:

- **Molecular representation:** SMILES/InChI/MOL interconversion, structure validation, salt and tautomer standardization
- **Descriptor calculation:** molecular weight, logP, TPSA, rotatable bonds, H-bond donors/acceptors and 200+ physicochemical descriptors
- **Similarity and substructure search:** fingerprint-based screening, Tanimoto similarity, substructure matching — e.g. "which 20 molecules in our library are closest to this odorant?"
- **Interaction and reactivity flagging:** functional-group-based screening of potential incompatibilities (e.g. aldehyde–amine Schiff-base risk, acid–carbonate gas evolution, oxidation-prone terpene combinations). *These are rule-based flags for a chemist to review, not definitive predictions.*
- **Chemical calculations:** stoichiometry, dilution and concentration math, mixture composition, partition/solubility estimates (with the accuracy limits inherent to descriptor-based estimation)

### A.2.4 Built-in Skill 2: Statistical Analysis

- Descriptive statistics, hypothesis testing (t-test, ANOVA, chi-square), correlation and regression
- **Design of Experiments support:** analysis of factorial designs, response-surface interpretation
- **Quality-control statistics:** control charts (SPC), process capability (Cp/Cpk), batch-to-batch variance analysis
- **Sensory panel data:** panelist consistency checks, significance testing between products, preference mapping
- Time-series analysis: degradation-kinetics regression on shelf-life and stability data

### A.2.5 What the Model Is *Not* Good At (Deliberately Stated)

- It does not replace experimental measurement. Estimated properties (vapor pressure, solubility, thresholds) are screening-grade, not specification-grade.
- Literature-style answers can be incomplete or occasionally wrong; the deployment includes source-citation prompting and a "verify before acting" workflow convention.
- It does not invent commercially novel molecules; it screens, ranks and reasons over known chemical space.

Stating these limits up front is what makes the rest of this document credible.

### A.2.6 Customization Layer (Optional)

| Level | Content | Example |
|---|---|---|
| New skill development | Agent capabilities connected to the customer's tools and data | GC-MS output parsing; internal raw-material database queries |
| Fine-tuning | Adapting the model on customer documents and domain knowledge | Aromsa's formulation terminology, internal procedures, past project reports |
| Integration | Connections to LIMS, ERP, instrument software | Automatic retrieval and reporting of analytical results |

---

## A.3 Why a Local (On-Premises) Model

In the flavor industry, the formula *is* the company. Sending formulations to a cloud AI service is an unacceptable risk profile for most manufacturers. The product's design philosophy follows from this:

- **Zero data-exfiltration surface:** the model does not talk to the internet. Formulas, raw-material lists, customer briefs and pricing never leave the company network.
- **Regulatory and trade-secret compliance:** personal data (GDPR/Data Protection Law) and trade secrets remain fully under company control; no third-party data-processor agreements are needed.
- **Predictable cost:** no per-token billing; under heavy laboratory use, the hardware-plus-license model is significantly more economical than cloud APIs.
- **Compact is practical:** the 9B class makes serious chemistry capability possible on a single server — no data-center investment, unlike 100B+ models.

---

## A.4 Sector-by-Sector Use Cases

### A.4.1 Flavor and Fragrance Manufacturing (Primary Target Sector)

Flavor production is chemistry-intensive and generates dense experimental data. The model works directly on both.

**Formulation R&D**
- Library screening for molecules similar to a target flavor/odor profile
- Reformulation support: when an ingredient must be removed for regulatory or cost reasons, candidate replacements proposed via physicochemical profile matching — as a **shortlist for the flavorist**, who makes the sensory judgment
- Volatility-based (vapor pressure, logP) reasoning for top/heart/base-note balance
- Literature-grounded answers on odor thresholds, stability behavior and known applications of candidate molecules, with citations for verification

**Stability and application**
- Functional-group-based flagging of at-risk flavor components in acidic beverage matrices, heat-processed bakery, or high-fat systems
- HLB and phase-behavior calculation support for emulsion formulations
- Degradation-kinetics fitting on shelf-life data and shelf-life extrapolation

**Quality and analytics**
- Assistance interpreting GC-MS peak lists against reference batches and flagging deviating components (assistive — the analyst confirms)
- SPC analysis for batch-to-batch consistency
- Statistical evaluation of sensory panel results

**Regulatory support**
- Ingredient queries against IFRA, EFSA/FEMA GRAS and EU Flavor Regulation (1334/2008) frameworks; allergen and restricted-substance checklists — as a first-pass screen, with final compliance confirmed against official current sources

### A.4.2 Food Industry (Aromsa's Customer Base)

The model also strengthens the technical support Aromsa provides to its own customers (beverage, dairy, confectionery, bakery producers):

- **Matrix interaction analysis:** anticipated interactions between a flavor and the customer's product matrix (pH, fat content, proteins, heat-treatment profile); Maillard and flavor-binding risk assessment
- **Additive compatibility:** screening for incompatibilities with preservatives, sweeteners, colorants
- **Nutrition and labeling math:** formula-based nutrient calculations, E-number and label-compliance checks
- **Process-contaminant awareness:** literature-supported assessment of formation conditions for acrylamide, furan, 3-MCPD and similar compounds
- **Product-development statistics:** consumer test and sensory data processing

### A.4.3 Chemicals, Paints and Coatings

- **Formulation optimization:** solvent-system selection (Hansen solubility parameter logic), resin–pigment–additive compatibility assessment
- **VOC and regulatory calculations:** VOC content computation, REACH/CLP classification support, SDS content checking
- **Reaction and process chemistry:** polymerization stoichiometry, cure chemistry, viscosity–temperature regression
- **Color and performance data:** statistical root-cause analysis of batch color deviations (ΔE), modeling of accelerated-aging test data
- **Storage compatibility:** reactive-hazard and incompatibility screening

### A.4.4 Pharmaceutical Industry

- **Early discovery support:** Lipinski/Veber rules, ADMET-related descriptor calculation, similarity-based compound screening, scaffold analysis
- **Preformulation:** solubility, pKa, logD estimation; computational support for salt/polymorph selection workflows; excipient–API compatibility assessment
- **Analytical methods and stability:** kinetic analysis of ICH stability data, shelf-life extrapolation, degradation-product structure suggestions
- **Statistics and validation:** process-validation statistics, method-validation calculations (linearity, repeatability, LOD/LOQ), batch-release trend analysis
- **Data-integrity advantage:** on-premises operation eliminates cloud-related data-integrity debates in GxP environments from the outset

### A.4.5 Other Application Areas (Summary)

| Sector | Example use |
|---|---|
| Cosmetics and personal care | Fragrance formulation, IFRA compliance, emulsion stability, preservative-system evaluation |
| Agrochemicals | Active–adjuvant compatibility, formulation-type selection, environmental-persistence descriptors |
| Polymers and plastics | Additive-migration assessment (food-contact regulations), stabilizer selection |
| Home care | Surfactant systems, malodor counteraction, pH and buffer calculations |

---

## A.5 Value Delivered

### A.5.1 Where the Value Actually Comes From

In an R&D-heavy flavor company, a substantial share of a chemist's week goes to non-experimental work: literature lookup, descriptor and mixture calculations, data cleaning, statistical analysis, report and compliance-document drafting. The product is designed to absorb precisely this load. The value case therefore rests on **time reallocation**, not on speculative "AI discovers new flavors" claims.

### A.5.2 Value Available Today (Current Capabilities)

| Benefit | Mechanism | Realistic expected effect |
|---|---|---|
| Faster R&D iteration | Candidate screening and descriptor work drops from hours to minutes | 5–15% of researcher time reallocated from desk work to experimental and creative work — the realistic band for assistant-class tools, to be validated in pilot |
| Fewer dead-end experiments | Computational pre-screening plus proper DoE analysis reduces blind trial-and-error | Meaningful reduction in failed iterations; magnitude depends on current workflow maturity and is measured in the pilot |
| More objective quality decisions | Standardized SPC, Cp/Cpk and panel statistics | More consistent batch accept/reject decisions; fewer disputes and re-tests |
| Democratized expertise | Literature-trained model gives junior staff reference-grade support | Reduced dependency on a few senior experts; faster onboarding |
| Trade-secret-safe AI adoption | 100% local operation | The organization gets AI leverage without exposing a single formula |

With ~72 researchers and engineers in Aromsa's R&D organization, even the conservative end of the time-reallocation band (5%) corresponds to roughly **3–4 FTE-equivalents of capacity per year**; the 15% end corresponds to ~10 FTE-equivalents. This is the anchor number for the business case, and it is measurable within an 8-week pilot.

### A.5.3 Value Unlocked by Customization (Roadmap)

- **Institutional memory:** fine-tuned on Aromsa's past project reports and procedures, the model becomes an internal knowledge asset — "how did we solve the similar stability issue in the 2019 strawberry project?"
- **Instrument-integration skills:** custom skills that pull data from GC-MS, HPLC and sensory-panel software and generate reports automatically
- **Regulation-watch skill:** automated screening of IFRA amendments and EU regulatory changes against the company's formula library
- **Customer brief → formulation starting point:** structured translation of customer requests into candidate formulation baselines for the flavorist

### A.5.4 The Investment Argument in One Paragraph

The product's economics do not depend on any breakthrough claim. They depend on three well-established facts: (1) chemists spend a large fraction of their time on computable, searchable, formattable work; (2) a domain-trained model with real computational tools can absorb much of that work at assistant quality; (3) in this industry, the only acceptable way to get that leverage is on-premises. Everything beyond that — fewer failed experiments, faster compliance, institutional memory — is upside on top of an already-sufficient base case.

---

## A.6 Deployment and Rollout (Summary)

1. **Discovery workshop (1–2 days):** priority use-case selection with Aromsa R&D and quality teams
2. **Pilot installation (1–2 weeks):** local server setup, base skills enabled, pilot group of 5–10 users
3. **Pilot evaluation (6–8 weeks):** real R&D tasks, measured KPIs (task time, experiment counts, output accuracy spot-checks, user satisfaction) against a pre-pilot baseline
4. **Customization phase (optional):** scenario-specific skills and/or fine-tuning
5. **Rollout:** extension to all R&D, quality and application teams; integrations

The pilot is designed to **prove or disprove the 5–15% band with Aromsa's own data** before any wider commitment.

---

# PART B — Agent Platform for Factory Efficiency in Flavor Manufacturing

**How LLM-Based Agents Improve Production, Quality and Operations — Assessed for Aromsa**

---

## B.1 Executive Summary

This document analyzes the value that LLMs and autonomous agents can deliver to factory efficiency, specifically in flavor manufacturing, using Aromsa's operational profile as the reference case.

Flavor manufacturing differs fundamentally from classic high-volume, single-product process industries: **very high SKU variety, small-to-medium batch sizes, frequent changeovers, intensive recipe management and a heavy documentation and traceability burden.** This is exactly the profile where robotic automation has limited returns but **information-processing automation** — LLM agents — has the highest leverage.

The core thesis: in a plant of Aromsa's scale, a large share of efficiency loss comes not from slow machines but from the **human-intensive information flow between machines** — batch records, changeover planning, quality-deviation investigations, certification documentation, shift handovers, customer complaint handling. The agent platform targets precisely this layer.

**Honest framing:** the figures in this document are benchmark-informed estimates, not guarantees. The proposed methodology is deliberately measurement-first — every scenario starts by establishing a baseline on Aromsa's own data, and value claims are validated or discarded during the pilot. Agents operate under human approval for all consequential decisions; nothing in this proposal removes people from quality or release authority.

---

## B.2 Aromsa Operational Profile (Public Information + Estimates)

### B.2.1 What Is Known

- Multiple factory buildings in Gebze Organized Industrial Zone (5th factory in 2014, a 6th designed as a green building from 2017); total area above 37,000 m²
- Roughly 350–450 employees, a significant share of them researchers, specialists and engineers
- Ministry-certified R&D Center; additional R&D + production facility in Emmerich, Germany
- Product groups: liquid flavors (since 1982), spray-dried flavors and emulsions (since 1987), sauces and fruit preparations (since 1991)
- An Organic Synthesis Unit producing proprietary molecules since 2000
- Industrial automation (PLC/SCADA) projects have been executed on site by local integrators — suggesting at least partial data-collection infrastructure is in place

### B.2.2 Estimated Machinery and Process Park

The inventory below is an **estimate** derived from Aromsa's product groups and industry norms; it must be verified in the discovery phase.

| Process area | Estimated equipment | Efficiency-critical point |
|---|---|---|
| Liquid flavor production | Stainless mixing/blending tanks (likely staged from ~100 L to ~10,000 L), precision dosing, weighing stations | Recipe accuracy, weighing errors, batch-record workload |
| Spray-dried flavors | Spray dryers, feed-emulsion preparation, cyclone/bag-filter lines | **Largest energy consumer on site**; long cleaning at product changeover; temperature/flow parameter tuning |
| Emulsion production | High-pressure homogenizers, high-shear mixers, colloid mills | Droplet-size consistency, batch-to-batch stability |
| Sauces / fruit preparations | Cooking kettles (atmospheric/vacuum), pasteurizers, hot-fill or aseptic filling | Thermal-process records, microbiological risk, allergen changeovers |
| Organic synthesis unit | Glass/steel reactors, distillation/fractionation columns, vacuum systems, solvent recovery | Batch synthesis records, yield tracking, safety procedures |
| Filling and packaging | Drum/IBC/pail filling lines, labeling, casing/palletizing | Label–product matching, traceability |
| Utilities | Tank farm (raw materials/solvents), CIP systems, cold storage, steam/compressed air/chilling, HVAC and odor/emission control | CIP time-water-chemical consumption, energy, environmental compliance |
| Quality laboratories | GC-MS, GC-FID, HPLC, density/refractometry, microbiology lab, sensory panel rooms | Batch release lead time |

### B.2.3 Estimated Operational Load Profile

A flavor manufacturer serving hundreds of active customers typically manages **thousands of active SKUs/recipes.** The resulting load:

- Dozens of distinct batches per day; each generating a weighing list, production order, batch record, QC request and certificate documents
- Frequent changeovers → CIP cycles, allergen-sequencing rules, line-clearance checks
- Continuous documentation demand from FSSC 22000 / IFS / ISO 9001 plus halal and kosher certification regimes
- Customer-specific documentation (spec sheets, allergen declarations, GMO/vegan/naturalness statements) — each customer in its own format

This means white-collar and grey-collar information work is a genuinely large cost component of production. That is the agent platform's target.

---

## B.3 What the Product Is

### B.3.1 Definition

The Factory Efficiency Agent Platform is a software layer of **LLM-based agents**, each specialized in a specific business process, connecting to production, quality, maintenance and planning systems, and running on-premises (or in a private cloud). The agents:

- Read from existing systems (ERP, SCADA/PLC historian, LIMS, MES if present, and the informal layer of spreadsheets and e-mail)
- Answer natural-language queries, generate reports and flag anomalies
- Execute defined workflows end-to-end, with approval-gated steps remaining with humans

The platform can run alongside Product 1 (the chemistry-specialist local model) or independently; combined, quality and R&D scenarios gain chemical depth.

### B.3.2 Architectural Principles

1. **Human-approved autonomy:** agents draft, propose and execute routine steps; batch release, recipe changes and other critical decisions always pass through human approval.
2. **Layering, not replacement:** SCADA/PLC and ERP stay; the platform sits on top as a read-then-write layer, starting read-only.
3. **Data sovereignty:** formulas and customer data stay on site (same philosophy as Product 1).
4. **Staged autonomy:** first "read and report" (low risk), then "propose," and only then approval-gated "execute."

---

## B.4 Use Cases and Value Analysis

### B.4.1 Production Planning and Scheduling Agent

**Problem:** in a high-SKU environment, line/tank scheduling is a manual balancing act between allergen-sequencing rules, CIP durations, spray-dryer campaign logic and delivery dates.

**What the agent does:** reads open orders, tank/line availability, cleaning-matrix rules and raw-material stock to draft daily/weekly schedules; answers what-if questions ("if we pull order X forward, what CIP cost does it trigger?") in seconds.

**Value:** fewer changeovers and less total CIP time; an order-of-magnitude increase in the planner's scenario-analysis capacity. Industry benchmarks for intelligent sequencing in comparable multi-SKU plants support **roughly 5–10% line-availability gains**; the actual figure for Aromsa is established in the pilot.

### B.4.2 Electronic Batch Record and Production Order Agent

**Problem:** per-batch weighing lists, process records and deviation notes on paper or semi-digital forms — slow and error-prone.

**What the agent does:** auto-generates production orders and weighing lists from recipes; converts operator input from natural language into structured records; flags gaps and inconsistencies immediately ("theoretical yield 92%, entered 78% — explanation missing"); compiles the release dossier at batch closure.

**Value:** substantially less documentation time per batch — a realistic initial band of **30–50% reduction**, growing as adoption matures; audit preparation (FSSC/IFS/customer audits) shrinking from days to hours; fewer record-driven deviations. This is typically the fastest-payback scenario because it requires no new sensors and little integration depth.

### B.4.3 Quality Deviation and Root-Cause Agent

**Problem:** when a batch's GC profile drifts from reference or color/density is out of spec, the investigation data is scattered across LIMS, SCADA and operator notes.

**What the agent does:** automatically assembles all relevant data for the deviating batch (raw-material lots, process parameters, prior batches, similar historical deviations); runs statistical comparisons; presents ranked root-cause hypotheses with supporting evidence; drafts the CAPA. (Combined with Product 1, it also generates chemistry-level hypotheses — oxidation, esterification, etc.)

**Value:** deviation closure time shortened by a realistic **20–40%**, driven mostly by eliminating the data-gathering phase; recurring deviations caught as patterns; quality-engineer capacity freed. The agent proposes; the quality engineer concludes.

### B.4.4 Batch Release Acceleration Agent

**Problem:** finished batches wait for shipment on the slowest link of the results-plus-records-plus-certificates chain.

**What the agent does:** auto-checks lab results against specifications, chases missing analyses, drafts CoAs and customer-format spec documents for conforming batches, and presents everything to the quality manager for one-screen approval.

**Value:** release lead time reduced by roughly **20–30%** (the waiting and paperwork share of release time, not the analysis time itself — that is lab-capacity bound), improving finished-goods turns and on-time-in-full delivery.

### B.4.5 Maintenance and Downtime Analysis Agent

**Problem:** unplanned stops on spray dryers, homogenizers and filling lines; failure logs in free text; no pattern analysis.

**What the agent does:** reads SCADA/historian data together with maintenance logs; keeps a live downtime Pareto; classifies free-text failure notes and surfaces recurring failure patterns; drafts work orders; where trend data exists (temperature, pressure, current draw), proposes simple early-warning rules.

**Value:** this is **analysis-driven, not full predictive maintenance** — that would require additional sensor investment. On analysis alone, comparable plants achieve **5–15% reductions in unplanned downtime** on targeted equipment, primarily by eliminating repeat failures. It is also the cheapest credible first step on the road to condition-based maintenance.

### B.4.6 Energy and Utilities Agent

**Problem:** spray drying, steam and chilling dominate the energy bill, yet per-batch specific energy consumption (kWh/kg product) is rarely measured or reported.

**What the agent does:** joins energy-meter/SCADA data with production data to compute product- and batch-level specific consumption; flags abnormal batches; relates dryer campaign planning to tariff windows; compiles data for sustainability reporting.

**Value:** visibility plus behavioral optimization alone typically yields **2–5% energy savings** in comparable plants — modest in percentage but meaningful in absolute terms on a spray-drying-heavy energy bill, and achieved without capital expenditure. Larger savings require process changes and are out of this product's scope.

### B.4.7 Shift Handover and Operations Copilot

**Problem:** information loss at shift handover; slow access to SOPs; experienced-operator knowledge locked in individuals.

**What the agent does:** auto-generates handover reports from the shift's event/downtime/deviation records; answers operators' natural-language questions ("which CIP recipe after lemon emulsion in this tank?") with citations from the SOP corpus; accelerates new-operator onboarding.

**Value:** primarily qualitative but real — fewer handover-driven errors and rework, faster onboarding. In a 350–450-person continuous-production organization the compound effect is significant, and it is the single biggest driver of operator acceptance of the whole platform.

### B.4.8 Supply Chain and Raw Materials Agent

**Problem:** natural raw materials (essential oils, fruit concentrates) bring seasonality, price volatility and lot-to-lot quality variation; hundreds of supplier documents (specs, certificates, analyses) to track.

**What the agent does:** auto-checks incoming lot analyses against specifications; tracks supplier document gaps (including expiring halal/kosher/organic certificates); projects stock-versus-consumption for critical raw materials and raises risk alerts.

**Value:** fewer raw-material-driven production stops; a substantial reduction in supplier-document compliance workload. (Commodity price forecasting is deliberately excluded — it is not a credible LLM capability.)

### B.4.9 Customer Technical Request and Complaint Agent

**Problem:** customer spec requests, quality questionnaires running to hundreds of questions, complaints and sample requests consume technical teams' time.

**What the agent does:** pre-fills customer questionnaires and spec requests from company databases; classifies complaints, links them to the relevant batch records and drafts the initial technical assessment; produces consistent documents in TR/EN/DE (useful for shared processes with the Emmerich site).

**Value:** faster technical-sales response times; R&D and quality staff returned to value-adding work. Document pre-filling from verified internal data is among the most reliable LLM applications in production use today.

### B.4.10 Value Summary (Estimated Impact Matrix)

| Scenario | Impact area | Realistic gain band* | Confidence | Implementation difficulty |
|---|---|---|---|---|
| Batch records / production orders | Documentation labor | 30–50% less recording time per batch | High | Low–Medium |
| Batch release acceleration | Release lead time | 20–30% shorter | High | Low–Medium |
| Customer/supplier documents | White-collar workload | 40–60% of document tasks automated | High | Low–Medium |
| Quality deviation root cause | Deviation closure time | 20–40% shorter | Medium–High | Medium |
| Planning/scheduling | Line availability | 5–10% changeover/CIP gain | Medium | Medium |
| Shift/operations copilot | Errors and onboarding | Qualitative + shorter onboarding | Medium | Low |
| Energy visibility | Energy cost | 2–5% savings | Medium | Low |
| Downtime analysis | Unplanned downtime | 5–15% reduction on targeted equipment | Medium (data-quality dependent) | Medium |

\* Bands are drawn from industry benchmarks and comparable transformation projects, deliberately quoted at the conservative end. Every band is validated against a pre-pilot baseline measured on Aromsa's own data before being used in any business case. These are targets, not commitments.

### B.4.11 Translating the Bands into an Order of Magnitude

Without pricing anything, the value logic is straightforward. Assume conservatively that 40–60 people at the site touch batch records, planning, quality and compliance documentation for 20–30% of their time. The three high-confidence scenarios alone (batch records, release, documents) recover a meaningful fraction of that time — on the order of **5–10 FTE-equivalents of capacity per year** at the conservative end, before counting changeover, downtime or energy gains. The pilot's explicit job is to replace this assumption-based estimate with a measured one within roughly ten weeks.

---

## B.5 Why Now, and Why This Approach

1. **Flavor manufacturing is information-intensive manufacturing.** Robotic automation has low returns in low-batch/high-variety environments; LLM agents have their highest leverage exactly there — recipes, records, documents, deviations, certificates.
2. **The infrastructure appears ready.** PLC/SCADA projects already executed on site indicate the data-collection layer partially exists; the agent layer multiplies the return on that prior investment.
3. **Competitive dynamics.** The global flavor majors (Givaudan, IFF, Symrise, dsm-firmenich) are deploying AI aggressively in both formulation and operations. For Turkey's leading independent producer this is a window of opportunity: the same capabilities, adopted with more agility and at lower cost.
4. **Data sovereignty** is a decisive purchasing argument against cloud-first competitors in an industry where formula confidentiality is existential.

---

## B.6 Rollout Roadmap (Proposed)

| Phase | Duration | Scope | Output |
|---|---|---|---|
| 0 — Discovery | 2–3 weeks | Machine park, data sources (ERP/SCADA/LIMS), process walk-throughs, bottleneck map, **baseline KPI measurement** | Verified inventory + prioritized scenario list + baselines |
| 1 — Pilot | 8–10 weeks | 2 scenarios (recommended: batch-record agent + quality-deviation agent), single factory/line | Measured KPI impact vs. baseline, user feedback |
| 2 — Expansion | 3–6 months | Rollout of proven scenarios to other lines + 2–3 new agents | Plant-wide adoption |
| 3 — Deeper autonomy | Ongoing | Progression from "propose" to approval-gated "execute"; Product 1 integration | End-to-end flows |

**Pilot success criteria:** documentation time per batch, deviation closure time, release lead time, user adoption rate — all measured against the Phase-0 baseline. If the pilot does not beat baseline on at least two of the three primary KPIs, expansion does not proceed. Building that stop-condition into the proposal is itself a credibility asset.

---

## B.7 Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Poor data quality / paper records | Prioritize the record-digitization agent in Phase 1; agents are themselves the tool for structuring messy data |
| Operator resistance | Position agents as load-takers, not monitors; involve operators in pilot design; the shift copilot is the trust-builder |
| Hallucination / incorrect suggestions | Mandatory source citation, human approval on all consequential actions, full logging of agent outputs, staged autonomy |
| Integration complexity | Phase-0 system inventory; start read-only |
| Food-safety compliance | Validation of agents against FSSC 22000/IFS record requirements; formal change-management procedure |
| Overpromising | Conservative benchmark bands, baseline-first methodology, explicit pilot stop-condition |

---

# Joint Next Steps

1. **Single discovery engagement (2–3 weeks):** one combined Phase-0 covering R&D use-case prioritization (Product A) and plant/system inventory plus baseline KPI measurement (Product B) — cheaper and faster than two separate discoveries.
2. **Parallel pilots on shared infrastructure:** Product A pilot in R&D (6–8 weeks) and Product B pilot on one production line (8–10 weeks), both scored against pre-measured baselines.
3. **Go/no-go per product:** each pilot carries its own success criteria; adoption decisions are independent, so a weak result in one does not block the other.
4. **Open items to resolve with Aromsa:** lead scenario selection, ERP/MES/LIMS inventory and access, pilot line selection, available GPU hardware, fine-tuning document corpus, and whether the Emmerich (Germany) site is in scope.
