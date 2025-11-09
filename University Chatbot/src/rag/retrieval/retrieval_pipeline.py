import time
from langchain_community.vectorstores import FAISS
from rag.retrieval.embedding_model import get_embedding_function
from rag.retrieval.query_rewriting import rewrite_query
from rag.retrieval.classify_metadata import classify_query_header
from concurrent.futures import ThreadPoolExecutor, as_completed
from rag.retrieval.rerank import rerank_documents 
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Load embedding model and FAISS indices
embedding_model = get_embedding_function()
lvl2 = FAISS.load_local("storage/vectorstores/faiss_h2_summaries", embedding_model, allow_dangerous_deserialization=True)
lvl3 = FAISS.load_local("storage/vectorstores/faiss_index", embedding_model, allow_dangerous_deserialization=True)

def hierarchical_retrieval(query: str, chat_history: list[tuple[str, str]] = None):
    overall_start = time.time()

    # 1. Query Rewriting
    t0 = time.time()
    rewritten_query = rewrite_query(query, chat_history) or query
    t1 = time.time()
    logging.info(f"Query rewriting took {t1 - t0:.2f}s")

    # 2. Header Classification
    t0 = time.time()
    classification = classify_query_header(rewritten_query)
    predicted_header1 = classification.get("Header 1")
    t1 = time.time()
    logging.info(f"Header classification took {t1 - t0:.2f}s")

    # 3. Embedding
    t0 = time.time()
    query_embedding = embedding_model.embed_query(rewritten_query)
    t1 = time.time()
    logging.info(f"Query embedding took {t1 - t0:.2f}s")

    # 4. Retrieve Level 2 (summaries)
    lvl2_filter = {}
    if predicted_header1:
        if isinstance(predicted_header1, str):
            lvl2_filter["Header 1"] = {"$in": [predicted_header1.strip()]}
        elif isinstance(predicted_header1, list):
            lvl2_filter["Header 1"] = {"$in": [h.strip() for h in predicted_header1 if h]}

    lvl2_results = lvl2.similarity_search_by_vector(query_embedding, k=3, filter=lvl2_filter)
    header2_values = list({doc.metadata.get("Header 2", "").strip() for doc in lvl2_results})
    logging.info(f"Unique Header 2 values: {header2_values}")

    # 5. Level 3 Retrieval  
    t0 = time.time()
    final_results = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(
                lvl3.similarity_search_by_vector,
                query_embedding,
                k=5,
                filter={"Header 2": {"$in": [header2]}}
            )
            for header2 in header2_values
        ]
        for future in as_completed(futures):
            final_results.extend(future.result())
    t1 = time.time()
    logging.info(f"Level 3 retrieval took {t1 - t0:.2f}s, retrieved {len(final_results)} docs.")

    # 6. Reranking
    if final_results:
        t0 = time.time()
        final_results = rerank_documents(rewritten_query, final_results, top_n=5)
        t1 = time.time()
        logging.info(f"Reranking took {t1 - t0:.2f}s, top {len(final_results)} results kept.")
    else:
        logging.warning("No documents after Level 3 retrieval. Running fallback...")
        final_results = lvl3.similarity_search_by_vector(query_embedding, k=5)

    # Output
    print(f"\nRetrieved {len(final_results)} full documents from Level 3.\n")
    for i, doc in enumerate(final_results, 1):
        print(f"\n--- Document {i} ---")
        print(doc.page_content)
        print("Metadata:", doc.metadata)

    total_time = time.time() - overall_start
    print(f"\nTotal time: {total_time:.2f} seconds")
    logging.info(f"Total hierarchical retrieval time: {total_time:.2f}s")

    return final_results

if __name__ == "__main__":
    query = "What masters degrees are offered at ESIB?"
    hierarchical_retrieval(query)
