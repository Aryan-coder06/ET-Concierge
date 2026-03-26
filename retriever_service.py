import os
from dotenv import load_dotenv
from pymongo import MongoClient
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()

# --- Setup ---
MONGODB_URI = os.getenv("MONGODB_URI")
client = MongoClient(MONGODB_URI)
db = client["et_concierge"]

embeddings = GoogleGenerativeAIEmbeddings( 
    model="gemini-embedding-001", 
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

# Vector Store for Knowledge Base (Product Cards)
product_store = MongoDBAtlasVectorSearch(
    collection=db["knowledge_base"],
    embedding=embeddings,
    index_name="vector_index",
    embedding_key="embedding",
    text_key="text"
)

# Vector Store for Persona Journeys
persona_store = MongoDBAtlasVectorSearch(
    collection=db["persona_base"],
    embedding=embeddings,
    index_name="vector_index",
    embedding_key="embedding",
    text_key="text" # Based on your previous persona storage code
)

def get_product_chunks(query: str, profile: dict, k=3):
    """Searches the Knowledge Base with a persona filter."""
    # Pre-filter: Only search products relevant to this user's persona
    search_filter = {"metadata.personas": {"$in": [profile.get("persona", "retail_investor")]}}
    
    try:
        return product_store.similarity_search(query, k=k, pre_filter=search_filter)
    except Exception as e:
        print(f"❌ Product Search Error: {e}")
        return []

def get_persona_chunks(query: str, k=1):
    """Searches for the specific journey matching the user's situation."""
    try:
        return persona_store.similarity_search(query, k=k)
    except Exception as e:
        print(f"❌ Persona Search Error: {e}")
        return []