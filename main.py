import uuid
import json
from graph import et_graph
from db import get_session_state # Assuming you added the helper I suggested earlier

def run_concierge():
    print("--- 🚀 ET AI Concierge Terminal Test ---")
    
    # 1. Create a unique session ID for this test run
    session_id = str(uuid.uuid4())
    print(f"Session ID: {session_id}\n")

    # 2. Initialize the starting state
    # In a real app, you'd fetch this from MongoDB using get_session_state
    state = {
        "session_id": session_id,
        "current_message": "",
        "profile": {
            "intent": None,
            "sophistication": None,
            "goal": None,
            "profession": None,
            "interests": [],
            "existing_products": []
        },
        "onboarding_complete": False,
        "messages": [],
        "questions_asked": [],
        "retrieved_chunks": [],
        "intent": "profiling",
        "response": {}
    }

    # 3. Chat Loop
    while True:
        user_input = input("\n👤 You: ")
        
        if user_input.lower() in ["exit", "quit", "q"]:
            print("Goodbye!")
            break

        # Update state with the new message
        state["current_message"] = user_input

        # 4. Run the Graph
        print("🤖 Concierge is thinking...")
        try:
            # invoke() runs the entire logic from profile_extractor to state_updater
            final_state = et_graph.invoke(state)
            
            # Update local state so the next turn has the history
            state = final_state
            
            # 5. Display Result
            res = final_state["response"]
            print(f"\n🤖 ET Concierge: {res['message']}")
            
            # Debug: Show current profile status
            if not state["onboarding_complete"]:
                print(f"📊 [System] Profile Progress: {state['profile']}")
            else:
                print("✅ [System] Onboarding Complete!")

        except Exception as e:
            print(f"❌ Error during execution: {e}")
            # If it's a retrieval error, check if your MongoDB Index is 'Active'
            break

if __name__ == "__main__":
    run_concierge()