from store_chunks import store_chunks
from store_summaries import summaries_to_faiss  

def main():
    # Step 1: Preprocess, chunk, and store chunks in FAISS
    store_chunks(
        json_path="storage/data/sections/Catalogue_ESIB_2022-2023_chunks_contextual_headers.json",
        faiss_index_path="storage/vectorstores/faiss_chunks_contextual"
    )

    # Step 2: Summarize (Header 1, Header 2) sections and store in FAISS
    summaries_to_faiss(
        summaries_json_path="storage/data/summaries/Catalogue_ESIB_2022-2023_summaries_h2.json",
        faiss_index_path="storage/vectorstores/faiss_h2_summaries"
    )

if __name__ == "__main__":
    main()
