import os
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

# LangChain & Google Imports
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document

# Import your configuration and raw data
from et_persona import PERSONA_JOURNEYS
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

# Initialize Vector Store
vector_store = MongoDBAtlasVectorSearch(
    collection=collection,
    embedding=embeddings,
    index_name="vector_index", 
    relevance_score_fn="cosine"
)

# ── 2. ID Generator ──────────────────────────────────────
def make_chunk_id(product_name: str, section: str) -> str:
    """Generates the unique _id for MongoDB"""
    clean = product_name.lower().replace(" ", "")
    return f"{clean}_{section}"

# ── 3. Main Ingestion Function ───────────────────────────
def ingest_product():

    documents = []
    ids = []

    for p in PERSONA_JOURNEYS:
        print(f"ingesting {p['id']} " )
        doc = Document(
            page_content=p["content"],
            metadata=p["metadata"]  
        )
        documents.append(doc)
        ids.append(p['id'])

    # add_documents generates the 'embedding' field and upserts into MongoDB
    vector_store.add_documents(documents=documents, ids=ids)
    print(f"  {len(documents)} chunks stored.\n")

# ── 4. Orchestration ─────────────────────────────────────
def main():
   

    ingest_product()


if __name__ == "__main__":
    main()