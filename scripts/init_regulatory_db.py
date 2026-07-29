import duckdb
import os

def init_db():
    db_path = "data/regulatory.db"
    os.makedirs("data", exist_ok=True)
    
    # Connect to (or create) the database
    conn = duckdb.connect(db_path)
    
    # 1. Create IFRA Standards Table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS ifra_standards (
        cas_no VARCHAR,
        substance_name VARCHAR,
        restriction_type VARCHAR,
        max_limit VARCHAR,
        status VARCHAR,
        source VARCHAR DEFAULT 'IFRA 51st Amendment'
    )
    """)
    
    # 2. Create EU 1334/2008 (Annex I) Table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS eu_flavorings (
        fl_no VARCHAR,
        substance_name VARCHAR,
        cas_no VARCHAR,
        restrictions VARCHAR,
        conditions_of_use VARCHAR,
        status VARCHAR,
        source VARCHAR DEFAULT 'Regulation (EC) No 1334/2008'
    )
    """)
    
    # 3. Seed data: Expanded list of critical substances for Aromsa
    critical_substances = [
        # IFRA (Fragrance)
        ('91-64-5', 'Coumarin', 'Restricted', 'Depends on category (e.g., Cat 4: 1.5%)', 'Active', 'IFRA'),
        ('94-59-7', 'Safrole', 'Banned', '0%', 'Active', 'IFRA'),
        ('140-67-0', 'Estragole', 'Restricted', 'Depends on category', 'Active', 'IFRA'),
        ('106-24-1', 'Geraniol', 'Restricted', 'Allergen label required', 'Active', 'IFRA'),
        ('80-54-6', 'Butylphenyl Methylpropional (Lilial)', 'Banned', '0%', 'Active', 'IFRA'),
        ('31906-04-4', 'Hydroxyisohexyl 3-cyclohexene carboxaldehyde (Lyral)', 'Banned', '0%', 'Active', 'IFRA'),
        ('93-15-2', 'Methyleugenol', 'Restricted', 'Depends on category', 'Active', 'IFRA'),
        ('107-75-5', 'Hydroxycitronellal', 'Restricted', 'Depends on category', 'Active', 'IFRA'),
        ('104-55-2', 'Cinnamaldehyde', 'Restricted', 'Dermal sensitizer', 'Active', 'IFRA'),
        ('5392-40-5', 'Citral', 'Restricted', 'Sensitizer', 'Active', 'IFRA'),
        ('118-58-1', 'Benzyl Salicylate', 'Restricted', 'Sensitizer', 'Active', 'IFRA'),
        ('89-82-7', 'Pulegone', 'Restricted', 'Toxicological limit', 'Active', 'IFRA'),
        
        # EU 1334/2008 (Food/Flavorings)
        ('91-64-5', 'Coumarin', 'Restricted', '2 mg/kg in beverages, 15 mg/kg in bakery', 'Active', 'EU 1334/2008'),
        ('94-59-7', 'Safrole', 'Banned', 'Prohibited in food', 'Active', 'EU 1334/2008'),
        ('484-20-8', '5-Methoxypsoralen', 'Restricted', 'Prohibited in flavorings', 'Active', 'EU 1334/2008'),
        ('130-95-0', 'Quinine', 'Restricted', '75 mg/l in beverages', 'Active', 'EU 1334/2008'),
        ('57-06-7', 'Allyl isothiocyanate', 'Restricted', 'Max 50 mg/kg in food', 'Active', 'EU 1334/2008'),
        ('93-15-2', 'Methyleugenol', 'Restricted', '1 mg/kg in dairy', 'Active', 'EU 1334/2008'),
        ('89-82-7', 'Pulegone', 'Restricted', '20 mg/kg in beverages', 'Active', 'EU 1334/2008'),
        ('470-82-6', 'Eucalyptol', 'Restricted', 'Limits apply in certain foods', 'Active', 'EU 1334/2008')
    ]
    
    for item in critical_substances:
        if item[5] == 'IFRA':
            conn.execute("INSERT INTO ifra_standards (cas_no, substance_name, restriction_type, max_limit, status) VALUES (?, ?, ?, ?, ?)", 
                         (item[0], item[1], item[2], item[3], item[4]))
        else:
            conn.execute("INSERT INTO eu_flavorings (cas_no, substance_name, restrictions, status) VALUES (?, ?, ?, ?)", 
                         (item[0], item[1], item[2], item[4]))
    
    print(f"Regulatory database initialized at {db_path} with {len(critical_substances)} entries.")
    conn.close()

if __name__ == "__main__":
    init_db()
