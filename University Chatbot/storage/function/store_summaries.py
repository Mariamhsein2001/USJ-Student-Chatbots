import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
import json
import logging
from langchain.schema import Document
from langchain_community.vectorstores import FAISS

from embedding_model import get_embedding_function

# --- Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def summaries_to_faiss(
    summaries_json_path: str,
    faiss_index_path: str
) -> None:
    """
    Load header2 summaries from JSON and store them in a FAISS index.

    Args:
        summaries_json_path (str): Path to the summary JSON file.
        faiss_index_path (str): Output path to save the FAISS index.
    """
    logging.info(f"Loading summaries from {summaries_json_path}...")
    with open(summaries_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    documents = [Document(page_content=entry["page_content"], metadata=entry["metadata"]) for entry in data]

    logging.info("Embedding and saving into FAISS...")
    embed_fn = get_embedding_function()
    db = FAISS.from_documents(documents, embed_fn)
    db.save_local(faiss_index_path)
    logging.info(f"FAISS index saved at: {faiss_index_path}")


# --- Optional direct script usage ---
if __name__ == "__main__":
    summaries_to_faiss(
        summaries_json_path="storage/data/summaries/Catalogue_ESIB_2022-2023_summaries_h2.json",
        faiss_index_path="storage/vectorstores/faiss_h2_summaries"
    )
