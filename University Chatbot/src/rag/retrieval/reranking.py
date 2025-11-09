import os
import requests
import logging
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from retrieval.embedding_model import get_embedding_function
from typing import List
from langchain.schema.document import Document

# === Setup Logging ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# === Load environment variables and API key ===
load_dotenv()
JINA_API_KEY = os.getenv("JINA_API_KEY")
if not JINA_API_KEY:
    logger.error("JINA_API_KEY not found in environment.")
    raise ValueError("Missing JINA_API_KEY in .env file.")

# === Constants ===
JINA_API_URL = "https://api.jina.ai/v1/rerank"
JINA_MODEL_NAME = "jina-reranker-v2-base-multilingual"

# === Initialize FAISS vector store and embedding model ===



def query_faiss(query: str, top_k: int = 10) -> List[Document]:
    """
    Search the FAISS index using a query string and return top_k matching documents.

    Args:
        query (str): Natural language query.
        top_k (int): Number of top results to retrieve.

    Returns:
        List[Document]: List of documents retrieved from FAISS.
    """
    try:
        embedding_model = get_embedding_function()
        vector_db = FAISS.load_local(
            "storage/vectorstores/faiss_index",
            embeddings=embedding_model,
            allow_dangerous_deserialization=True
        )
        logger.info("FAISS index and embedding model loaded successfully.")
    except Exception as e:
        logger.error(f"Error initializing vector store: {e}")
        raise
    try:
        query_embedding = embedding_model.embed_query(query)
        results = vector_db.similarity_search_by_vector(query_embedding, k=top_k)
        return results
    except Exception as e:
        logger.error(f"Error during FAISS search: {e}")
        return []


def rerank_documents(query: str, docs: List[Document], top_n: int = 5) -> List[Document]:
    """
    Use the Jina API to rerank a list of documents based on relevance to a query.

    Args:
        query (str): Natural language query.
        docs (List[Document]): List of documents retrieved from FAISS.
        top_n (int): Number of top documents to return after reranking.

    Returns:
        List[Document]: Top-n reranked documents.
    """
    if not docs:
        logger.warning("No documents to rerank.")
        return []

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {JINA_API_KEY}"
    }

    payload = {
        "model": JINA_MODEL_NAME,
        "query": query,
        "top_n": top_n,
        "documents": [doc.page_content for doc in docs],
        "return_documents": False
    }

    try:
        response = requests.post(JINA_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        result_json = response.json()
        top_indices = result_json.get("indices", list(range(min(top_n, len(docs)))))
        return [docs[i] for i in top_indices]
    except requests.exceptions.RequestException as e:
        logger.error(f"Jina API request failed: {e}")
    except Exception as e:
        logger.error(f"Error processing Jina API response: {e}")

    return []


def main():
    """
    Run a sample query through FAISS retrieval and rerank the results using Jina.
    Prints both the raw FAISS results and the reranked results.
    """
    query = "master's programs offered by Esib"

    # === FAISS Search ===
    search_results = query_faiss(query, top_k=10)
    logger.info(f"Retrieved {len(search_results)} documents from FAISS.")

    print("\n===== BEFORE RERANKING (FAISS Top 10) =====")
    for i, result in enumerate(search_results, 1):
        print(f"\n######## {i} ########")
        print(result.page_content)
        print(f"Metadata: {result.metadata}")

    # === Jina Reranking ===
    reranked_results = rerank_documents(query, search_results, top_n=5)
    logger.info(f"Reranked down to {len(reranked_results)} documents using Jina API.")

    print("\n===== AFTER RERANKING (Top 5 by Jina API) =====")
    for i, result in enumerate(reranked_results, 1):
        print(f"\n######## {i} ########")
        print(result.page_content)
        print(f"Metadata: {result.metadata}")


if __name__ == "__main__":
    main()
