# embeddings/embedding_model.py

from langchain_huggingface import HuggingFaceEmbeddings

def get_embedding_function():
    """Returns a multilingual E5-large embedding function."""
    return HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-large")

def test_embedding():
    embedding_func = get_embedding_function()
    sample_text = "This is a test sentence for embeddings."
    result = embedding_func.embed_query(sample_text)
    print("Embedding generated. Length:", len(result))
    print("First 5 dimensions:", result[:5])

if __name__ == "__main__":
    test_embedding()

