import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# 1. Get Connection String
MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    raise ValueError("MONGODB_URI not found in .env file")

# 2. Initialize Client
# We use a single client instance to benefit from connection pooling
client = MongoClient(
    MONGODB_URI,
    # Best practice for serverless/long-running scripts
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=5000
)

# 3. Access Database
db = client["et_concierge"]

# 4. Access Collections
# This is the collection your state_updater_node uses
sessions_collection = db["sessions"]

# Optional: Indexing for performance
# We ensure session_id is indexed so lookups are instant
sessions_collection.create_index("session_id", unique=True)

# 5. Helper to get or create a state (Useful for your main.py entry point)
def get_session_state(session_id: str):
    """
    Fetches the existing state from DB or returns None if new user.
    """
    return sessions_collection.find_one({"session_id": session_id})

print("🗄️ MongoDB Session Collection initialized.")