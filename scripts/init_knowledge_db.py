import duckdb
import os
import json

def init_db():
    db_path = "data/chem_knowledge.db"
    os.makedirs("data", exist_ok=True)
    
    # Remove old DB if exists to start fresh
    if os.path.exists(db_path):
        os.remove(db_path)
        
    conn = duckdb.connect(db_path)
    
    print("--- 1. Initializing Regulatory Data ---")
    # 1.1 IFRA Standards
    conn.execute("""
    CREATE TABLE ifra_standards (
        cas_no VARCHAR,
        substance_name VARCHAR,
        restriction_type VARCHAR,
        max_limit VARCHAR,
        status VARCHAR,
        source VARCHAR DEFAULT 'IFRA 51st Amendment'
    )
    """)
    
    # 1.2 EU 1334/2008
    conn.execute("""
    CREATE TABLE eu_flavorings (
        fl_no VARCHAR,
        substance_name VARCHAR,
        cas_no VARCHAR,
        restrictions VARCHAR,
        conditions_of_use VARCHAR,
        status VARCHAR,
        source VARCHAR DEFAULT 'Regulation (EC) No 1334/2008'
    )
    """)
    
    # Seed Regulatory Data
    critical_substances = [
        ('91-64-5', 'Coumarin', 'Restricted', 'Depends on category (e.g., Cat 4: 1.5%)', 'Active', 'IFRA'),
        ('94-59-7', 'Safrole', 'Banned', '0%', 'Active', 'IFRA'),
        ('140-67-0', 'Estragole', 'Restricted', 'Depends on category', 'Active', 'IFRA'),
        ('106-24-1', 'Geraniol', 'Restricted', 'Allergen label required', 'Active', 'IFRA'),
        ('80-54-6', 'Butylphenyl Methylpropional (Lilial)', 'Banned', '0%', 'Active', 'IFRA'),
        ('31906-04-4', 'Hydroxyisohexyl 3-cyclohexene carboxaldehyde (Lyral)', 'Banned', '0%', 'Active', 'IFRA'),
        ('93-15-2', 'Methyleugenol', 'Restricted', 'Depends on category', 'Active', 'IFRA'),
        ('91-64-5', 'Coumarin', 'Restricted', '2 mg/kg in beverages', 'Active', 'EU'),
        ('94-59-7', 'Safrole', 'Banned', 'Prohibited in food', 'Active', 'EU'),
        ('89-82-7', 'Pulegone', 'Restricted', '20 mg/kg in beverages', 'Active', 'EU')
    ]
    
    for item in critical_substances:
        if item[5] == 'IFRA':
            conn.execute("INSERT INTO ifra_standards (cas_no, substance_name, restriction_type, max_limit, status) VALUES (?, ?, ?, ?, ?)", 
                         (item[0], item[1], item[2], item[3], item[4]))
        else:
            conn.execute("INSERT INTO eu_flavorings (cas_no, substance_name, restrictions, status) VALUES (?, ?, ?, ?)", 
                         (item[0], item[1], item[2], item[4]))

    print("--- 2. Initializing Reactivity Knowledge ---")
    # 2.1 Reactivity Groups (SMARTS)
    conn.execute("""
    CREATE TABLE reactivity_groups (
        group_name VARCHAR PRIMARY KEY,
        smarts_pattern VARCHAR,
        description TEXT
    )
    """)
    
    groups = [
        ("Aldehyde", "[CX3H1](=[OX1])", "Contains a terminal carbonyl group"),
        ("Primary Amine", "[NX3H2;!$(N-C=O)]", "Basic nitrogen with two hydrogens"),
        ("Alcohol", "[OX2H1;!$(O-C=O)]", "Hydroxyl group"),
        ("Carboxylic Acid", "[CX3](=[OX1])[OX2H1]", "Organic acid group"),
        ("Cyanide", "[C,c]#[N]", "Highly toxic cyanide/nitrile group"),
        ("Terpene/Alkene", "[CX3]=[CX3]", "Unsaturated carbon bonds, prone to oxidation"),
        ("Peroxide", "[OX2,OX1-][OX2,OX1-]", "Highly reactive O-O bond"),
        ("Strong Acid", "S(=O)(=O)[OH]", "Sulfonic or mineral acid type")
    ]
    conn.executemany("INSERT INTO reactivity_groups VALUES (?, ?, ?)", groups)
    
    # 2.2 Reactivity Rules
    conn.execute("""
    CREATE TABLE reactivity_rules (
        rule_id VARCHAR PRIMARY KEY,
        rule_name VARCHAR,
        group_a VARCHAR,
        group_b VARCHAR, -- Optional, NULL for individual group risks
        severity VARCHAR,
        consequence TEXT,
        description TEXT
    )
    """)
    
    rules = [
        ("R1_SCHIFF", "Schiff Base Formation", "Aldehyde", "Primary Amine", "High", "Aroma loss, discoloration", "Aldehyde + Primary Amine reaction"),
        ("R2_ACETAL", "Acetal Formation", "Aldehyde", "Alcohol", "Medium", "Odor profile change", "Common in acidic/alcoholic bases"),
        ("R4_OXIDATION", "Oxidation Risk", "Terpene/Alkene", None, "Medium", "Rancid off-notes", "Sensitivity to oxygen/light"),
        ("R6_HCN", "Toxic Gas Release", "Cyanide", "Carboxylic Acid", "Extreme", "Release of HCN gas", "Fatal risk in acidic mixtures"),
        ("R7_PEROXIDE", "Explosion Risk", "Peroxide", None, "Extreme", "Violent decomposition", "Inherent instability")
    ]
    conn.executemany("INSERT INTO reactivity_rules VALUES (?, ?, ?, ?, ?, ?, ?)", rules)
    
    print(f"Unified Chemical Knowledge Database initialized at {db_path}")
    conn.close()

if __name__ == "__main__":
    init_db()
