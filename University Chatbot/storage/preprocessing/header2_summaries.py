import os
import json
import time
import logging
from typing import List
from langchain.schema import Document
from langchain.chains.summarize import load_summarize_chain
from langchain_core.language_models import BaseLanguageModel
from langchain_google_genai import ChatGoogleGenerativeAI

from storage.preprocessing.utils import load_chunks,group_by_header_2

# --- Inline Configuration ---
LLM_MODEL = "gemini-2.0-flash-lite"
TEMPERATURE = 0.3

# --- Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# --- Summarization ---
def summarize_doc(documents: List[Document], llm: BaseLanguageModel) -> str:
    if not documents:
        return "[No documents to summarize.]"
    try:
        h1 = documents[0].metadata.get("Header 1", "")
        h2 = documents[0].metadata.get("Header 2", "")
        intro = (
            f"You are summarizing content from the section titled:\n"
            f"- Header 1: \"{h1}\"\n"
            f"- Header 2: \"{h2}\"\n\n"
            f"Make sure the summary clearly reflects the main ideas of this section, "
            f"and refer to the topic in the summary itself.\n\n"
            f"Add the headers in the summary (Example: This document is about {h2} of {h1})"
        )
        documents[0] = Document(page_content=intro + documents[0].page_content, metadata=documents[0].metadata)
        chain = load_summarize_chain(llm, chain_type="map_reduce", verbose=False)
        result = chain.invoke({"input_documents": documents})
        summary = result.get("output_text", "").strip()
        return summary if summary else "[No summary generated.]"
    except Exception as e:
        logging.error(f"Summarization error: {e}")
        return "[Summarization failed.]"

def summarize_chunks(chunks_path: str , output_summary_path: str) -> List[Document]:
    docs = load_chunks(chunks_path)
    grouped = group_by_header_2(docs)
    llm = ChatGoogleGenerativeAI(model=LLM_MODEL, temperature=TEMPERATURE)

    os.makedirs(os.path.dirname(output_summary_path), exist_ok=True)
    summarized_docs = []

    with open(output_summary_path, "w", encoding="utf-8") as f:
        f.write("[\n")
        for idx, ((h1, h2), doc_list) in enumerate(grouped.items()):
            logging.info(f"Summarizing [{idx + 1}/{len(grouped)}]: {h1} > {h2}")
            summary = summarize_doc(doc_list, llm)
            metadata = {"Header 1": h1, "Header 2": h2, "chunk_index": idx}
            summarized_docs.append(Document(page_content=summary, metadata=metadata))
            json.dump({"page_content": summary, "metadata": metadata}, f, ensure_ascii=False, indent=2)
            f.write(",\n" if idx < len(grouped) - 1 else "\n")
            f.flush()
            time.sleep(10)
        f.write("]")

    logging.info(f"Saved {len(summarized_docs)} summaries to {output_summary_path}")
    return summarized_docs

# --- Run ---
if __name__ == "__main__":
    CHUNKS_JSON_PATH = "storage/data/sections/Catalogue_ESIB_2022-2023_chunks.json"
    SUMMARIES_JSON_PATH = "storage/data/summaries/Catalogue_ESIB_2022-2023_summaries_h2.json"
    summarize_chunks(CHUNKS_JSON_PATH, SUMMARIES_JSON_PATH)
