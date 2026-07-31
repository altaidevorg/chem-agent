# src/database/seed_data.py
import logging
from src.database.manager import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 1. CAMEO Reactivity Groups (Selected 48 with SMARTS)
# Patterns are simplified for demonstration but follow chemical logic
REACTIVITY_GROUPS = [
    (1, "Acids, Strong Inorganic", "[OX2H][SX4](=[OX1])(=[OX1])[OX2H]|[OX2H][NX3](=[OX1])=[OX1]|Cl[H]|Br[H]|I[H]", "Strong mineral acids like H2SO4, HNO3, HCl"),
    (2, "Acids, Weak Inorganic", "[OX2H][PX4](=[OX1])([OX2H])[OX2H]|[CX3](=[OX1])([OX2H])[OX2H]", "Weak inorganic acids like H3PO4, H2CO3"),
    (3, "Acids, Carboxylic", "C(=O)[OH]", "Organic acids containing the carboxyl group"),
    (4, "Alcohols and Polyols", "[OX2H][CX4]", "Compounds with hydroxyl groups on saturated carbons"),
    (5, "Aldehydes", "[CX3H1](=O)", "Organic compounds with a terminal carbonyl group"),
    (6, "Amides", "C(=O)N", "Acid-derived nitrogen compounds"),
    (7, "Amines, Aliphatic", "[NX3;H2,H1,H0][CX4]", "Aliphatic nitrogen bases"),
    (8, "Amines, Aromatic", "[NX3;H2,H1,H0]c", "Aromatic nitrogen bases like aniline"),
    (9, "Azo, Diazo, Azido", "N=N|[N-]=[N+]=N", "Compounds containing N=N or azide groups"),
    (10, "Carbamates", "OC(=O)N", "Esters of carbamic acid"),
    (11, "Caustics (Bases)", "[OH-]|[NX3H2]C", "Strong bases and caustic materials"),
    (12, "Cyanides, Inorganic", "C#N|[C-]#[N]", "Inorganic cyanide salts"),
    (13, "Esters", "C(=O)OC", "Organic esters"),
    (14, "Ethers", "[OD2](C)C", "Organic ethers"),
    (15, "Fluorides, Inorganic", "[F-]", "Inorganic fluoride salts"),
    (16, "Hydrocarbons, Aliphatic Saturated", "[CX4;H4,H3,H2,H1]", "Alkanes"),
    (17, "Hydrocarbons, Aliphatic Unsaturated", "C=C|C#C", "Alkenes and Alkynes"),
    (18, "Hydrocarbons, Aromatic", "c1ccccc1", "Benzene and related aromatic systems"),
    (19, "Isocyanates", "N=C=O", "Highly reactive isocyanate groups"),
    (20, "Ketones", "CC(=O)C", "Internal carbonyl compounds"),
    (21, "Mercaptans (Thiols)", "[SX2H]", "Organic sulfur compounds"),
    (22, "Nitriles", "C#N", "Organic cyano compounds"),
    (23, "Nitro Compounds", "[N+](=O)[O-]", "Organic nitro groups"),
    (24, "Organophosphates", "P(=O)(OC)(OC)OC", "Phosphate esters"),
    (25, "Peroxides, Organic", "OO", "Organic peroxide linkage"),
    (26, "Phenols and Cresols", "[OX2H]c", "Hydroxyl group on aromatic ring"),
    (27, "Sulfides, Inorganic", "[S-2]", "Inorganic sulfide salts"),
    (28, "Epoxides", "C1OC1", "Cyclic ethers with three-membered rings"),
    (29, "Anhydrides", "C(=O)OC(=O)", "Acid anhydrides"),
    (30, "Acyl Halides", "C(=O)[Cl,Br,I,F]", "Acid halides"),
    (31, "Oxidizing Agents, Strong", "[O-][ClX4](=O)(=O)=O|[O-][NX3](=O)=O|[O-]Cl(=O)=O|[O-]N(=O)=O|Cl(=O)(=O)[O-]|N(=O)(=O)[O-]|Cl(=O)=O|N(=O)=O", "Strong oxidizers like chlorates, nitrates"),
    (32, "Reducing Agents, Strong", "[Li,Na,K,Mg,Al;+0]|[Li,Na,K,Mg,Al][H]", "Reactive metals and hydrides (neutral metallic form)"),
    (33, "Halogenated Organics", "C[Cl,Br,I,F]", "Organic compounds with halogens"),
    (34, "Carbonates", "OC(=O)O", "Carbonate salts and esters"),
    (35, "Sulfonates", "S(=O)(=O)O", "Sulfonic acid derivatives"),
    (36, "Nitrites, Inorganic", "[NX2](=O)[O-]", "Inorganic nitrites"),
    (37, "Silanes", "[SiH4,SiH3,SiH2,SiH1]", "Silicon hydrides"),
    (38, "Metal Carbonyls", "[CX1]#[OX1].[Fe,Ni,Co]", "Transition metal carbonyls"),
    (39, "Dithiocarbamates", "SC(=S)N", "Sulfur analogs of carbamates"),
    (40, "Hydrazines", "NN", "Hydrazine and its derivatives"),
    (41, "Perchlorates", "[OX1-][ClX4](=O)(=O)=O", "Perchlorate salts"),
    (42, "Chlorates", "[OX1-][ClX3](=O)=O", "Chlorate salts"),
    (43, "Nitrates, Inorganic", "[OX1-][NX3](=O)=O", "Inorganic nitrate salts"),
    (44, "Sulfates, Inorganic", "[OX1-][SX4](=O)(=O)[O-]", "Inorganic sulfate salts"),
    (45, "Thiosulfates", "S[S](=O)(=O)O", "Thiosulfate salts"),
    (46, "Boranes", "B[H]", "Boron hydrides"),
    (47, "Alkali Metals", "[Li,Na,K,Rb,Cs]", "Group 1 metals"),
    (48, "Alkaline Earth Metals", "[Mg,Ca,Sr,Ba]", "Group 2 metals")
]

# 2. Binary Reactivity Rules (Sample Matrix)
# Format: (G1_ID, G2_ID, Severity, Consequence, Description)
REACTIVITY_RULES = [
    (1, 11, "CRITICAL", "Violent Reaction / Heat", "Strong acid-base neutralization generates intense heat"),
    (31, 4, "CRITICAL", "Fire / Explosion", "Strong oxidizers can ignite alcohols"),
    (31, 21, "CRITICAL", "Explosion", "Strong oxidizers react violently with thiols"),
    (12, 1, "CRITICAL", "Toxic Gas (HCN)", "Cyanides release hydrogen cyanide gas in contact with acids"),
    (27, 1, "CRITICAL", "Toxic Gas (H2S)", "Sulfides release hydrogen sulfide gas in contact with acids"),
    (32, 4, "WARNING", "Flammable Gas (H2)", "Strong reducing agents (metals) release hydrogen from alcohols"),
    (1, 25, "CRITICAL", "Explosion", "Acids catalyze the decomposition of organic peroxides"),
    (11, 25, "WARNING", "Heat", "Bases can cause decomposition of peroxides"),
    (19, 7, "WARNING", "Heat / Polymerization", "Isocyanates react exothermically with amines"),
    (30, 4, "WARNING", "Heat / Corrosive Gas", "Acyl halides react with alcohols to form esters and HCl gas"),
    (31, 17, "WARNING", "Fire", "Strong oxidizers can react with unsaturated hydrocarbons"),
    (47, 33, "CRITICAL", "Explosion", "Alkali metals react violently with halogenated organics (Wurtz-like)"),
    (1, 36, "CRITICAL", "Toxic Gas (NOx)", "Nitrites release toxic nitrogen oxides with acids"),
    (12, 31, "CRITICAL", "Explosion", "Cyanides are highly incompatible with strong oxidizers")
]

# 3. Structural Restrictions (PAINS, Brenk, Genotox)
STRUCTURAL_RESTRICTIONS = [
    (1, "PAINS", "HIGH", "c1ccc2c(c1)C(=O)C=CC2=O", "ChEMBL PAINS alert: Aromatic quinone"),
    (2, "PAINS", "HIGH", "S=c1[nH]nc2ccccc2n1", "ChEMBL PAINS alert: 2-mercaptobenzimidazole variant"),
    (3, "Brenk", "MEDIUM", "[N;R0]=[N;R0]C", "Brenk alert: Aliphatic azo"),
    (4, "Brenk", "HIGH", "C=C=O", "Brenk alert: Ketene"),
    (5, "Genotoxic", "CRITICAL", "[N;!H0]C(=O)CN(C=O)N=O", "Structural alert for potential genotoxicity"),
    (6, "Genotoxic", "CRITICAL", "C1OC1", "Epoxide: Potential alkylating agent / genotoxic"),
    (7, "PAINS", "HIGH", "c1ccc(cc1)N=Nc2ccc(cc2)O", "Azophenol: Common PAINS alert")
]

# 4. Common Fragrance/Flavor Compounds (For Replacement Tool Testing)
SEED_COMPOUNDS = [
    {"name": "Phenylacetaldehyde", "smiles": "c1ccc(CC=O)cc1", "cas": "122-78-1"},
    {"name": "Phenethyl alcohol", "smiles": "c1ccc(CCO)cc1", "cas": "60-12-8"},
    {"name": "Hydrocinnamaldehyde", "smiles": "c1ccc(CCC=O)cc1", "cas": "104-53-0"},
    {"name": "Cinnamaldehyde", "smiles": "c1ccc(C=CC=O)cc1", "cas": "104-55-2"},
    {"name": "Linalool", "smiles": "CC(=CCCC(C)(C=C)O)C", "cas": "78-70-6"},
    {"name": "Limonene", "smiles": "CC1=CCC(CC1)C(=C)C", "cas": "138-86-3"},
    {"name": "Vanillin", "smiles": "COc1cc(C=O)ccc1O", "cas": "121-33-5"},
    {"name": "Ethyl vanillin", "smiles": "CCOc1cc(C=O)ccc1O", "cas": "121-32-4"},
    {"name": "Menthol", "smiles": "CC1CCC(C(C1)O)C(C)C", "cas": "89-78-1"},
    {"name": "Citral", "smiles": "CC(=CCCC(=CC=O)C)C", "cas": "5392-40-5"},
    {"name": "Benzyl acetate", "smiles": "CC(=O)OCc1ccccc1", "cas": "140-11-4"},
    {"name": "Methyl anthranilate", "smiles": "COC(=O)c1ccccc1N", "cas": "134-20-3"}
]

def seed_database():
    db = DatabaseManager()
    from src.database.standardizer import ChemicalStandardizer
    from src.tools.rdkit_tools import (
        CalculateMolecularPropertiesTool, 
        CalculateHansenParametersTool,
        EstimateVolatilityAndNoteTool
    )
    
    standardizer = ChemicalStandardizer()
    prop_tool = CalculateMolecularPropertiesTool()
    hsp_tool = CalculateHansenParametersTool()
    vol_tool = EstimateVolatilityAndNoteTool()
    
    with db.get_connection(read_only=False) as conn:
        logger.info("Seeding Reactivity Groups...")
        conn.executemany(
            "INSERT OR IGNORE INTO reactivity_groups (group_id, group_name, smarts_pattern, description) VALUES (?, ?, ?, ?)",
            REACTIVITY_GROUPS
        )
        
        logger.info("Seeding Reactivity Rules...")
        for i, rule in enumerate(REACTIVITY_RULES):
            rule_id = f"RULE_{i+1:03d}"
            conn.execute(
                "INSERT OR IGNORE INTO reactivity_rules (rule_id, group_a, group_b, severity, consequence, description) VALUES (?, ?, ?, ?, ?, ?)",
                (rule_id, *rule)
            )
            
        logger.info("Seeding Structural Restrictions...")
        conn.executemany(
            "INSERT OR IGNORE INTO structural_restrictions (id, class_name, severity, smarts_pattern, description) VALUES (?, ?, ?, ?, ?)",
            STRUCTURAL_RESTRICTIONS
        )
        
        logger.info("Seeding Compounds and Descriptors...")
        for comp in SEED_COMPOUNDS:
            ikey = standardizer.get_inchikey(comp["smiles"])
            cas_clean = standardizer.clean_cas(comp["cas"])
            
            # 1. Cross-Reference
            conn.execute("""
                INSERT OR IGNORE INTO compound_cross_reference (inchikey, smiles, cas_no, cas_no_clean, chemical_name)
                VALUES (?, ?, ?, ?, ?)
            """, (ikey, comp["smiles"], comp["cas"], cas_clean, comp["name"]))
            
            # 2. Calculate Descriptors
            props = prop_tool.execute(comp["smiles"])
            hsp = hsp_tool.execute(comp["smiles"])
            vol = vol_tool.execute(comp["smiles"])
            
            if "error" not in props and "error" not in hsp and "error" not in vol:
                conn.execute("""
                    INSERT OR IGNORE INTO compound_descriptors 
                    (inchikey, mw, logp, hansen_d, hansen_p, hansen_h, boiling_point_c, odor_note)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ikey, 
                    props["molecular_weight"], 
                    props["log_p"],
                    hsp["delta_d"],
                    hsp["delta_p"],
                    hsp["delta_h"],
                    vol["estimated_boiling_point_c"],
                    vol["odor_note_classification"].split(' ')[0] # 'Top', 'Heart', 'Base'
                ))
        
        logger.info("Seed data loaded successfully.")

if __name__ == "__main__":
    seed_database()
