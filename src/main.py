# src/main.py
import sys
from src.agent.core import run_chemistry_agent

def main():
    print("=" * 60)
    print("🔬 Interactive Chemistry AI Agent Terminal 🔬")
    print("Type 'exit' or 'quit' to terminate the session.")
    print("=" * 60)
    
    while True:
        try:
            # Get persistent user input
            user_query = input("\n[User]: ").strip()
            
            # Check for exit conditions
            if not user_query:
                continue
            if user_query.lower() in ['exit', 'quit']:
                print("\n[System] Closing interactive session. Goodbye!")
                break
            
            # Trigger the agent core workflow
            agent_response = run_chemistry_agent(user_query)
            
            print("\n" + "=" * 22 + " AGENT REPORT " + "=" * 22)
            print(agent_response)
            print("=" * 58)
            
        except KeyboardInterrupt:
            print("\n\n[System] Session interrupted by user. Goodbye!")
            break
        except Exception as e:
            print(f"\n[Error] An error occurred during execution: {e}")

if __name__ == "__main__":
    # Ensure system path handles root execution
    main()