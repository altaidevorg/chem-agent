import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from src.agent.core import ChemistryAgent

def run_test_query(agent, query, title):
    print(f"\n{'='*20} TEST: {title} {'='*20}")
    print(f"[User]: {query}")
    response = agent.run(query)
    print(f"\n[Agent]: {response}")
    print(f"{'='*60}\n")

def main():
    agent = ChemistryAgent()
    
    # 1. Test Skill Discovery and Loading
    run_test_query(agent, 
        "List all available skills and then load the full instructions for the 'molecule_analysis' skill.", 
        "Skill Discovery & Progressive Disclosure")

    # 2. Test RDKit Resolution, Properties, and Safety
    run_test_query(agent, 
        "Resolve 'Ibuprofen' to SMILES, calculate its molecular weight and LogP, and fetch its GHS safety data.", 
        "RDKit: Resolution, Properties, and Safety")

    # 3. Test File Operations
    run_test_query(agent, 
        "Read the file 'data/lab_results.csv' and write a brief summary of its contents to 'output/verification_summary.md'.", 
        "File System: Read and Write")

    # 4. Test Advanced RDKit (MCS and Functional Groups)
    run_test_query(agent, 
        "Find the maximum common substructure between Caffeine and Theobromine. Also, detect functional groups in Aspirin.", 
        "Advanced RDKit: MCS and Functional Groups")

    # 5. Test Visualization and Identifiers
    run_test_query(agent, 
        "Convert the SMILES 'CCO' to InChIKey and generate a 2D diagram image saved as 'output/ethanol_test.png'.", 
        "RDKit: Identifiers and Visualization")

if __name__ == "__main__":
    main()
