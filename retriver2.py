import os
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

# LangChain & Google Imports
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document


load_dotenv()



# ── 1. Clients & Vector Store Setup ──────────────────────
MONGODB_URI = os.getenv("MONGODB_URI")
client = MongoClient(MONGODB_URI)
db = client["et_concierge"]
collection = db["persona_base"]


embeddings = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-001", 
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

# ── Update Vector Store Initialization ──────────────────
vector_store = MongoDBAtlasVectorSearch(
    collection=collection,
    embedding=embeddings,
    index_name="vector_index",      # Must match the Index Name in Atlas UI
    relevance_score_fn="cosine",
    embedding_key="embedding",      # CRITICAL: This is the name of the field in your DB
    text_key="text"              # CRITICAL: This is the name of the text field in your DB
)

def getContent(query: str): # Removed -> str as it returns a list of Documents
    """
    Performs a vector search and returns the most relevant documents.
    """
    # LangChain handles the embedding of the 'query' automatically
    # This calls the Atlas Vector Search index
    try:
        results = vector_store.similarity_search(query, k=1)
        return results
    except Exception as e:
        print(f"❌ Search Error: {e}")
        return []

if __name__ == "__main__":
    user_query = input("Enter your query: ")
    
    if user_query.strip():
        search_results = getContent(user_query)
        
        if not search_results:
            print("No relevant information found")
        else:
            print("\n--- Top matches found in ET Knowledge Base ---\n")
            for i, doc in enumerate(search_results):
                # Accessing metadata from the LangChain Document object
                # product = doc.metadata.get("type", "Unknown")
                # section = doc.metadata.get("category", "General")
                
                # print(f"Result {i+1} | Source: {product} ({section})")
                print(f"Content: {doc.page_content[:200]}...") 
                print("-" * 50)
    else:
        print("Please enter a valid query.")