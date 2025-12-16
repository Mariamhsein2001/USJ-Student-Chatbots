from typing import List
from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from embedding_model import get_embedding_function
import os 
import json

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

def store_chunks(
    json_path: str,
    faiss_index_path: str
) -> None:
    """
    Complete pipeline: preprocess PDF -> chunk to JSON -> embed & store in FAISS.

    Args:
        json_path (str): Path where chunked JSON is saved and loaded from.
        faiss_index_path (str): Path to store FAISS index.
    """
    try:
        
        print(f"Step 1: Loading document chunks from: {json_path}")
        chunks  = load_chunks(json_path)

        print(f"Step 2: Getting embedding model and storing to FAISS at: {faiss_index_path}")
        embedding_model = get_embedding_function()
        vector_db = FAISS.from_documents(chunks, embedding_model)
        vector_db.save_local(faiss_index_path)

        print("Pipeline completed successfully.")
    except Exception as e:
        print(f"Pipeline failed: {e}")


def main():
    store_chunks(
        json_path="storage/data/sections/Catalogue_ESIB_2022-2023_chunks_contextual_headers.json",
        faiss_index_path="storage/vectorstores/faiss_chunks_contextual"
    )


if __name__ == "__main__":
    main()
