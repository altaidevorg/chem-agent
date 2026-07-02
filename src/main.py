# src/main.py
import sys
import os
from src.agent.core import ChemistryAgent

def main():
    # Initialize the persistent agent
    agent = ChemistryAgent()
    
    print("=" * 60)
    print("🔬 Professional Chemistry AI Agent (v2.1) 🔬")
    print("Commands: 'exit', 'clear' (reset memory), 'context' (show memory)")
    print("Logs: thoughts/ are saved in logs/thoughts/")
    print("=" * 60)
    
    while True:
        try:
            # Get persistent user input
            user_query = input("\n[User]: ").strip()
            
            # Check for special commands
            if not user_query:
                continue
            
            query_lower = user_query.lower()
            if query_lower in ['exit', 'quit']:
                print("\n[System] Saving session and closing. Goodbye!")
                agent.memory.save_to_file()
                break
            
            if query_lower == 'clear':
                agent.memory.clear()
                print("[System] Agent memory has been cleared.")
                continue
                
            if query_lower == 'context':
                print("\n" + "-" * 20 + " CURRENT CONTEXT " + "-" * 20)
                print(agent.memory.get_context_summary())
                print("-" * 57)
                continue
            
            # Trigger the agent core workflow
            agent_response = agent.run(user_query)
            
            print("\n" + "=" * 22 + " AGENT REPORT " + "=" * 22)
            print(agent_response)
            print("=" * 58)
            
        except KeyboardInterrupt:
            print("\n\n[System] Session interrupted by user. Goodbye!")
            agent.memory.save_to_file()
            break
        except Exception as e:
            print(f"\n[Error] An error occurred during execution: {e}")

if __name__ == "__main__":
    # Ensure system path handles root execution
    # Add project root to path if necessary
    sys.path.append(os.getcwd())
    main()
