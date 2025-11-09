import os
import json

from chunking import split_sections, split_chunks
from contextual_headers import add_context


def preprocessing_pipeline(
    md_path: str
) -> str:
    """
    Run the full preprocessing pipeline on a PDF file.
    
    Args:
        md_path (str): Path to the input PDF.

    Returns:
        str: Path to the final contextual chunk JSON file.
    """
    # Derive base name (without extension)
    base_name = os.path.splitext(os.path.basename(md_path))[0]

    # Define derived output paths
    output_dir = os.path.join(os.path.dirname(md_path), "sections")
    os.makedirs(output_dir, exist_ok=True)

    chunk_json_path = os.path.join(output_dir, f"{base_name}_chunks.json")
    contextual_json_path = os.path.join(output_dir, f"{base_name}_chunks_contextual_headers.json")

    print("Step 1: Splitting Markdown into sections and chunks...")
    section_docs = split_sections(md_path)
    chunked_docs = split_chunks(section_docs)

    chunks_data = [{"page_content": doc.page_content, "metadata": doc.metadata} for doc in chunked_docs]
    with open(chunk_json_path, "w", encoding="utf-8") as f:
        json.dump(chunks_data, f, ensure_ascii=False, indent=2)
    print(f"Chunks saved to {chunk_json_path}")

    print("Step 2: Generating contextual headers using Gemini...")
    add_context(chunk_json_path, contextual_json_path)

    print(f"Preprocessing pipeline completed successfully!\nFinal output: {contextual_json_path}")
    return contextual_json_path


if __name__ == "__main__":
    # Example: run from CLI or another script
    input_markdown = "storage/data/raw/Catalogue_ESIB_2022-2023.md"
    final_output_path = preprocessing_pipeline(input_markdown)
