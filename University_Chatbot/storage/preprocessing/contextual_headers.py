import json
import os
import time
from dotenv import load_dotenv
from langchain.schema import Document
from google import genai

# Load the environment variables from .env file
load_dotenv()

# Retrieve the Google API key from environment variables
api_key = os.getenv("GOOGLE_API_KEY")

# Initialize the Google Generative AI client
client = genai.Client(api_key=api_key)


def load_chunks(json_file_path):
    """
    Load document chunks from a JSON file and return them as LangChain Document objects.
    
    Parameters:
    - json_file_path (str): Path to the JSON file containing saved chunks.

    Returns:
    - List[Document]: List of Document objects with content and metadata.
    """
    with open(json_file_path, "r", encoding="utf-8") as f:
        chunks_data = json.load(f)
    docs = [Document(page_content=d["page_content"], metadata=d["metadata"]) for d in chunks_data]
    return docs


def save_chunks(updated_docs, output_json_path):
    """
    Save a list of Document objects to a JSON file.

    Parameters:
    - updated_docs (List[Document]): Updated Document objects with new headers.
    - output_json_path (str): Path to output JSON file.
    """
    chunks_data = [
        {"page_content": doc.page_content, "metadata": doc.metadata}
        for doc in updated_docs
    ]
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(chunks_data, f, ensure_ascii=False, indent=2)


def generate_header_with_gemini(chunk_content, metadata, model="gemini-2.0-flash-lite"):
    """
    Use Gemini to generate a concise header/title for a text chunk.

    Parameters:
    - chunk_content (str): The text content of the chunk.
    - metadata (dict): Metadata associated with the chunk.
    - model (str): Gemini model name (default: "gemini-2.0-flash-lite").

    Returns:
    - str: A generated title for the chunk.
    """
    # Convert metadata dictionary into a string
    metadata_str = "; ".join([f"{k}: {v}" for k, v in metadata.items()])

    # Create a prompt for Gemini
    prompt = f"""
Given the following text chunk and its metadata, generate a short contextualized, descriptive, and informative title (max 25 words) for the chunk to give more context.
Your response MUST be the title of the document, and nothing else. DO NOT include quotes or any explanations.

Metadata: {metadata_str}

Chunk:
{chunk_content}

Title:
"""

    try:
        # Send prompt to Gemini model
        response = client.models.generate_content(
            model=model,
            contents=prompt
        )

        # Extract title from the first line of the response
        header = response.text.strip().split('\n')[0]
        return header

    except Exception as e:
        print(f"Gemini error: {e}")
        return "Unknown Title"


def add_context(input_json_path, output_json_path, sleep_seconds=10):
    """
    Process all chunks by generating a title for each and prepending it to the content.

    Parameters:
    - input_json_path (str): Path to the input JSON file with original chunks.
    - output_json_path (str): Path where the new JSON with headers will be saved.
    - sleep_seconds (int): Time to sleep between API requests to avoid throttling (default: 10 seconds).
    """
    # Load the chunks
    docs = load_chunks(input_json_path)
    updated_docs = []

    for idx, doc in enumerate(docs):
        print(f"\nProcessing chunk {idx+1}/{len(docs)}")

        # Generate a header for the current chunk
        header = generate_header_with_gemini(doc.page_content, doc.metadata)
        print(f"Generated header: {header}")

        # Combine the header with the original content
        new_content = f"Header: {header}\n\n{doc.page_content}"
        updated_doc = Document(page_content=new_content, metadata=doc.metadata)
        updated_docs.append(updated_doc)

        # Pause before next API call
        time.sleep(sleep_seconds)

    # Save the updated chunks to a file
    save_chunks(updated_docs, output_json_path)
    print(f"\nSaved updated chunks to: {output_json_path}")


if __name__ == "__main__":
    # Input JSON path containing the initial split chunks
    input_json = r"C:\Users\user\Desktop\University Chatbot\storage\data\sections\test.json"
    
    # Output path to save the chunks with headers added
    output_json = r"C:\Users\user\Desktop\University Chatbot\storage\data\sections\test_cont.json"
    
    # Run the chunk processing pipeline
    add_context(input_json, output_json)
