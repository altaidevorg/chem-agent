# src/database/schemas.py

# 1. Versioning & Audit
CREATE_AUDIT_LOG = """
CREATE TABLE IF NOT EXISTS regulatory_audit_log (
    id INTEGER PRIMARY KEY DEFAULT nextval('audit_id_seq'),
    source VARCHAR, -- e.g., 'DG_SANTE', 'IFRA'
    event_type VARCHAR, -- e.g., 'UPDATE', 'BOOTSTRAP'
    records_changed INTEGER,
    status VARCHAR, -- e.g., 'SUCCESS', 'FAILED'
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message VARCHAR
);
"""

CREATE_AUDIT_SEQ = "CREATE SEQUENCE IF NOT EXISTS audit_id_seq;"

CREATE_SCHEMA_VERSION = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description VARCHAR
);
"""

# 2. Cross-Reference Layer (The Connector)
CREATE_COMPOUND_XREF = """
CREATE TABLE IF NOT EXISTS compound_cross_reference (
    inchikey VARCHAR PRIMARY KEY, -- 27-char hash, the ultimate unique ID
    smiles VARCHAR,
    cas_no VARCHAR, -- Original CAS
    cas_no_clean VARCHAR, -- Standardized CAS (no dashes/spaces)
    fl_no VARCHAR, -- EU Flavouring Number
    pubchem_cid INTEGER,
    chemical_name VARCHAR,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# 3. Regulatory Layer (Normalized Long Format)
CREATE_EU_FLAVORINGS = """
CREATE TABLE IF NOT EXISTS eu_flavorings (
    fl_no VARCHAR PRIMARY KEY, -- FL numbers are unique IDs for the Union List
    inchikey VARCHAR, -- Optional, resolved later via CAS cross-reference
    restrictions VARCHAR,
    conditions_of_use VARCHAR,
    status VARCHAR,
    source VARCHAR DEFAULT 'Regulation (EC) No 1334/2008'
);
"""

CREATE_IFRA_STANDARDS = """
CREATE TABLE IF NOT EXISTS ifra_standards (
    inchikey VARCHAR, -- In IFRA, we usually have structures, but could be NULL during bootstrap
    category_code VARCHAR, -- e.g., '1', '5A', '7B', '11'
    max_concentration_pct DOUBLE,
    restriction_type VARCHAR, -- e.g., 'Restricted', 'Prohibited', 'Specified'
    source VARCHAR DEFAULT 'IFRA 51st Amendment',
    PRIMARY KEY (inchikey, category_code)
);
"""

# 4. Reactivity Layer (Many-to-Many)
CREATE_REACTIVITY_GROUPS = """
CREATE TABLE IF NOT EXISTS reactivity_groups (
    group_id INTEGER PRIMARY KEY,
    group_name VARCHAR,
    smarts_pattern VARCHAR,
    description VARCHAR
);
"""

CREATE_COMPOUND_REACTIVITY_GROUPS = """
CREATE TABLE IF NOT EXISTS compound_reactivity_groups (
    inchikey VARCHAR REFERENCES compound_cross_reference(inchikey),
    group_id INTEGER REFERENCES reactivity_groups(group_id),
    PRIMARY KEY (inchikey, group_id)
);
"""

CREATE_REACTIVITY_RULES = """
CREATE TABLE IF NOT EXISTS reactivity_rules (
    rule_id VARCHAR PRIMARY KEY,
    group_a INTEGER REFERENCES reactivity_groups(group_id),
    group_b INTEGER REFERENCES reactivity_groups(group_id),
    severity VARCHAR, -- e.g., 'CRITICAL', 'WARNING'
    consequence VARCHAR, -- e.g., 'Heat Generation', 'Toxic Gas'
    description VARCHAR
);
"""

# 5. Structural Alerts (Categorized SMARTS)
CREATE_STRUCTURAL_RESTRICTIONS = """
CREATE TABLE IF NOT EXISTS structural_restrictions (
    id INTEGER PRIMARY KEY,
    class_name VARCHAR, -- e.g., 'PAINS', 'Brenk', 'Genotoxic'
    severity VARCHAR, -- e.g., 'HIGH', 'CRITICAL'
    smarts_pattern VARCHAR,
    origin_source VARCHAR, -- e.g., 'ChEMBL', 'Internal'
    description VARCHAR
);
"""

# 6. Physicochemical Descriptors (For Ingredient Replacement)
CREATE_COMPOUND_DESCRIPTORS = """
CREATE TABLE IF NOT EXISTS compound_descriptors (
    inchikey VARCHAR PRIMARY KEY REFERENCES compound_cross_reference(inchikey),
    mw DOUBLE,
    logp DOUBLE,
    hansen_d DOUBLE, -- Dispersion
    hansen_p DOUBLE, -- Polar
    hansen_h DOUBLE, -- H-bonding
    boiling_point_c DOUBLE,
    odor_note VARCHAR, -- e.g., 'Top', 'Heart', 'Base'
    is_fragrance BOOLEAN DEFAULT TRUE,
    is_flavor BOOLEAN DEFAULT TRUE,
    cost_per_kg DOUBLE, -- Placeholder for commercial data
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Dictionary of all tables for easy initialization
INITIAL_SCHEMA = [
    CREATE_AUDIT_SEQ,
    CREATE_SCHEMA_VERSION,
    CREATE_AUDIT_LOG,
    CREATE_COMPOUND_XREF,
    CREATE_EU_FLAVORINGS,
    CREATE_IFRA_STANDARDS,
    CREATE_REACTIVITY_GROUPS,
    CREATE_COMPOUND_REACTIVITY_GROUPS,
    CREATE_REACTIVITY_RULES,
    CREATE_STRUCTURAL_RESTRICTIONS,
    CREATE_COMPOUND_DESCRIPTORS
]
