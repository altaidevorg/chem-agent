import os
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agent.core import ChemistryAgent

def test_compaction():
    agent = ChemistryAgent()
    
    # Query 1: Read a large-ish file to fill context
    print("\n--- Query 1: Reading history file ---")
    query1 = "Read 'data/history_of_chem_eng.md' and tell me who George E. Davis was."
    response1 = agent.run(query1)
    print(f"Agent Response: {response1[:100]}...")

    # Query 2: Ask another question to trigger compaction (since threshold is very low: 500 tokens)
    print("\n--- Query 2: Triggering Compaction ---")
    query2 = "What was the main concept introduced by Arthur D. Little?"
    response2 = agent.run(query2)
    print(f"Agent Response: {response2[:100]}...")

if __name__ == "__main__":
    test_compaction()
