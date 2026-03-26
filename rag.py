import os
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

# LangChain & Google Imports
from langchain_mongodb import MongoDBVectorSearch
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document

# Import your configuration and raw data
from ingestion_config import PRODUCTS_CONFIG
from et_prime_raw import ET_PRIME_SECTIONS
from et_prime_raw import ET_MARKETS_SECTIONS
from et_prime_raw import ET_MONEY_SECTIONS
from et_prime_raw import ET_NOW_SECTIONS
from et_prime_raw import ET_MASTERCLASS_SECTIONS
from et_prime_raw import ET_RISE_SECTIONS
from et_prime_raw import ET_BRANDEQUITY_SECTIONS
from et_prime_raw import ET_TRAVELWORLD_SECTIONS
from et_prime_raw import ET_GOVERNMENT_SECTIONS
from et_prime_raw import ET_EVENTS_SECTIONS

load_dotenv()

# ── 1. Clients & Vector Store Setup ──────────────────────
MONGODB_URI = os.getenv("MONGODB_URI")
client = MongoClient(MONGODB_URI)
db = client["et_concierge"]
collection = db["knowledge_base"]

# Google text-embedding-004 (768 dimensions)
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004", 
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

# Initialize Vector Store
vector_store = MongoDBVectorSearch(
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
def ingest_product(product_config: dict, sections: list[dict]):
    """
    Ingests product data strictly following the user's schema:
    _id, content, embedding, and metadata {collection, product_name, category, personas, intent_tags, priority}
    """
    print(f"🚀 Ingesting: {product_config['product_name']}...")
    
    documents = []
    ids = []

    for chunk in sections:
        chunk_id = make_chunk_id(product_config["product_name"], chunk["section"])
        
        # page_content maps to 'content'
        # metadata maps to the 'metadata' object
        doc = Document(
            page_content=chunk["content"],
            metadata={
                "collection":    "product_cards", # Fixed per your schema
                "product_name":  product_config["product_name"],
                "category":      product_config["category"],
                "personas":      product_config["personas"],
                "intent_tags":   product_config["intent_tags"],
                "priority":      product_config["priority"]
            }
        )
        documents.append(doc)
        ids.append(chunk_id)

    # add_documents generates the 'embedding' field and upserts into MongoDB
    vector_store.add_documents(documents=documents, ids=ids)
    print(f"   ✅ {len(documents)} chunks stored.\n")

# ── 4. Orchestration ─────────────────────────────────────
def main():
    RAW_DATA_MAP = {
        "etprime": ET_PRIME_SECTIONS,
        "etmarkets": ET_MARKETS_SECTIONS,
        "etmoney": ET_MONEY_SECTIONS,
        "etnow": ET_NOW_SECTIONS,
        "etmasterclass": ET_MASTERCLASS_SECTIONS,
        "etrise": ET_RISE_SECTIONS,
        "etbrandequity": ET_BRANDEQUITY_SECTIONS,
        "ettravelworld": ET_TRAVELWORLD_SECTIONS,
        "etgovernment": ET_GOVERNMENT_SECTIONS,
        "etevents": ET_EVENTS_SECTIONS
    }

    for p in PRODUCTS_CONFIG:
        product_id = p["id"]
        if product_id in RAW_DATA_MAP:
            ingest_product(
                product_config={
                    "product_id":   product_id,
                    "product_name": p["name"],
                    "category":     p.get("category", "subscription"),
                    "personas":     p.get("personas", []),
                    "intent_tags":  p.get("intents", []),
                    "priority":     p.get("priority", 1)
                },
                sections=RAW_DATA_MAP[product_id]
            )

if __name__ == "__main__":
    main()