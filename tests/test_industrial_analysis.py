import os
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agent.core import ChemistryAgent

def test_industrial_analysis():
    agent = ChemistryAgent()
    
    # Query 1: Read and summarize the industrial process data
    query = "Please read the file 'data/industrial_process.csv' and give me a brief summary of what's in it. What is the average yield?"
    print(f"User: {query}")
    response = agent.run(query)
    print(f"Agent: {response}\n")
    
    # Query 2: Analyze the relationship between temperature and yield
    query = "Looking at the data in 'data/industrial_process.csv', is there any obvious relationship between temperature and yield? Which timestamp had the lowest yield?"
    print(f"User: {query}")
    response = agent.run(query)
    print(f"Agent: {response}\n")

if __name__ == "__main__":
    test_industrial_analysis()
