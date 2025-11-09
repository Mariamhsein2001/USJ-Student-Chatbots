

import json
import os
from typing import List,Dict,Tuple
from langchain.schema import Document
import logging
# --- Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def load_chunks(json_path: str) -> List[Document]:
    """
    Load document chunks with metadata from a JSON file.

    Args:
        json_path (str): Path to the JSON file containing preprocessed chunks.

    Returns:
        List[Document]: A list of LangChain Document objects.
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"JSON file not found at: {json_path}")
    
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        documents = [
            Document(page_content=entry["page_content"], metadata=entry["metadata"])
            for entry in data
        ]
        print(f"Loaded {len(documents)} chunks from JSON.")
        return documents
    except Exception as e:
        raise RuntimeError(f"Failed to load JSON data: {e}")

# --- Grouping by Headers ---
def group_by_header_2(docs: List[Document]) -> Dict[Tuple[str, str], List[Document]]:
    grouped = {}
    current_h1, current_h2 = None, None
    for doc in docs:
        h1 = doc.metadata.get("Header 1")
        h2 = doc.metadata.get("Header 2")
        if h1: current_h1 = h1
        if h2: current_h2 = h2
        if current_h1 and current_h2:
            grouped.setdefault((current_h1, current_h2), []).append(doc)
    logging.info(f"Grouped into {len(grouped)} sections.")
    return grouped