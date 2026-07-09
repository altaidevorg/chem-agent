# 🏭 Industrial Data Analysis - 8 Challenge Questions (English)

These questions are designed to evaluate the ChemAgent's ability to perform multi-step reasoning, handle messy data, and cross-reference multiple files without specialized data analysis skills.

---

### 🧩 1. The "Incomplete Data" Puzzle
**Question:** "Look at `data/production_logs_messy.csv`. Batch B004 seems to be split across two rows. What is the total duration of Batch B004 from its initial start to its final end, and which operators were involved in the entire process?"

### 🧩 2. Multi-File Root Cause Analysis
**Question:** "We noticed a pressure fluctuation during Batch B002 (see `data/production_logs_messy.csv`). Check `data/sensor_calibrations.csv` to see if the pressure sensor (P-101) was in good standing at that time. What is its status, and who was the technician responsible for its last calibration?"

### 🧩 3. Financial & Operational Correlation
**Question:** "Calculate the potential cost of raw materials for Batch B001. We know it used 'Acetic Acid' from 'GlobalChem'. Based on `data/chemical_inventory.json`, Batch B001 has 50kg of material. Use the price from `data/material_inventory_detailed.json` to find the total cost for this batch's material."

### 🧩 4. Shift & Performance Analysis
**Question:** "John Doe was the operator for Batch B003. Based on `data/operator_shifts.jsonl`, which shift was he working on July 9th? According to the notes in `data/production_logs_messy.csv`, what happened during his shift that might explain the lower yield?"

### 🧩 5. Energy vs. Quality Correlation
**Question:** "Batch B003 (Ethanol) was produced on July 9th between 08:00 and 12:00. Check `data/energy_consumption.jsonl` for 'Reactor-A' during those hours. Was there a significant increase in steam usage compared to the midnight baseline (00:00-01:00), and does this correlate with the 'temperature spike' noted in the production logs?"

### 🧩 6. Supplier Reliability & Inventory Strategy
**Question:** "We need to restock 'Methanol' immediately. Compare the lead times in `data/raw_material_specs.csv` with the current stock levels in `data/material_inventory_detailed.json`. Which supplier should we order from to get the material fastest, and do we have any batches of Methanol that will expire before the end of 2026?"

### 🧩 7. Safety Incident Investigation
**Question:** "According to `data/safety_incidents.json`, there was a leak on valve V-102 (INC-2026-001). Cross-reference this with `data/operator_shifts.jsonl` for June 12th. Who was the operator on shift during that time? Also, check `data/maintenance_logs.txt`—was any work performed on a valve or reactor around that date?"

### 🧩 8. The "Ultimate" Quality Audit
**Question:** "Batch B003 had a purity drop. We've seen a temperature spike in `data/industrial_process.csv` at 03:00:00 and a note about a spike at 09:30 in `data/production_logs_messy.csv`. Is there any evidence in `data/sensor_calibrations.csv` that the temperature sensor (T-101) might be providing unreliable data? Based on all files, what is your final verdict on the root cause of the B003 quality issue?"
