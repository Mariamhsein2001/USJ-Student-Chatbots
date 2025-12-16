from langchain_community.vectorstores import FAISS
from rag.retrieval.embedding_model import get_embedding_function
from sentence_transformers import CrossEncoder
# Load CrossEncoder reranker model
# reranker = CrossEncoder("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
reranker = CrossEncoder("Alibaba-NLP/gte-multilingual-reranker-base",trust_remote_code=True)
#reranker = CrossEncoder("jinaai/jina-reranker-v2-base-multilingual",automodel_args={"torch_dtype": "auto"},trust_remote_code=True,)

def query_faiss(query, top_k=10):
    """Retrieve top_k results from FAISS."""
    embedding_model = get_embedding_function()
    query_embedding = embedding_model.embed_query(query)

    # Load FAISS index
    vector_db = FAISS.load_local("faiss_level_2", embeddings=embedding_model, allow_dangerous_deserialization=True)

    # Perform similarity search
    search_results = vector_db.similarity_search_by_vector(query_embedding, k=top_k)

    return search_results


def rerank_documents(query, docs, top_n=3):
    """Rerank documents using Sentence-Transformers CrossEncoder."""
    if not docs:
        print("No documents to rerank.")
        return []

    scores = reranker.predict([(query, doc.page_content) for doc in docs])
    
    # Sort by highest score
    ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    reranked_docs = [docs[i] for i in ranked_indices[:top_n]]

    return reranked_docs

def main():
    query = "master's programs offered by Esib"
    
    # Retrieve from FAISS
    search_results = query_faiss(query)
    
    print("\n===== BEFORE RERANKING (FAISS Top 10) =====")
    for i, result in enumerate(search_results, 1):
        print(f'######## {i} ########')
        print(result.page_content)
        print(result.metadata)

    # Apply reranking
    reranked_results = rerank_documents(query, search_results, top_n=5)

    print("\n===== AFTER RERANKING (Top 5) =====")
    for i, result in enumerate(reranked_results, 1):
        print(f'######## {i} ########')
        print(result.page_content)
        print(result.metadata)

if __name__ == "__main__":
    main()
