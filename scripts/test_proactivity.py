from src.agent.core import ChemistryAgent
import sys

def run_test_query(query):
    agent = ChemistryAgent()
    print(f"Running query: {query}")
    response = agent.run(query)
    print("\n--- Agent Response ---")
    print(response)
    print("----------------------")

if __name__ == "__main__":
    query = "Analyze Ibuprofen."
    if len(sys.argv) > 1:
        query = sys.argv[1]
    run_test_query(query)
