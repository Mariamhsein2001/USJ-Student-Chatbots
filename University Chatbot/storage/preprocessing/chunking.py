import re
import json
from typing import List
from langchain.schema import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter


def split_sections(markdown_file_path: str) -> List[Document]:
    """
    Split the markdown file into sections based on headers.

    Args:
        markdown_file_path (str): Path to the markdown file.

    Returns:
        List[Document]: A list of LangChain Document objects with metadata.
    """
    # Load the Markdown file
    with open(markdown_file_path, "r", encoding="utf-8") as f:
        markdown_text = f.read()

    # Define headers for splitting
    headers_to_split_on = [
        ("##", "Header 1"),
        ("###", "Header 2"),
        ("#####", "Header 3"),
    ]

    # Create the Markdown splitter
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on)

    # Split the Markdown content
    md_header_splits = markdown_splitter.split_text(markdown_text)

    # Clean the headers (remove leading #) but retain structure
    cleaned_sections = [
        Document(
            page_content=re.sub(r"^#+\s*", "", split.page_content, flags=re.MULTILINE),
            metadata=split.metadata
        )
        for split in md_header_splits
    ]

    return cleaned_sections


def split_chunks(documents: List[Document], chunk_size: int = 1500, chunk_overlap: int = 150) -> List[Document]:
    """
    Further split the documents into smaller character-level chunks.

    Args:
        documents (List[Document]): The documents to split.
        chunk_size (int): Maximum size of each chunk.
        chunk_overlap (int): Number of overlapping characters between chunks.

    Returns:
        List[Document]: The resulting list of chunked documents.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    chunks = text_splitter.split_documents(documents)

    # Normalize headers and assign chunk index
    for idx, doc in enumerate(chunks):
        for header in ["Header 1", "Header 2", "Header 3"]:
            doc.metadata[header] = doc.metadata.get(header) or "None"
        doc.metadata["chunk_index"] = idx



    return chunks


def main() -> None:
    markdown_file_path =  'storage/data/raw/Catalogue_ESIB_2022-2023.md'
    output_path = 'storage/data/sections/Catalogue_ESIB_2022-2023_chunks.json'

    # Step 1: Split into sections
    section_docs = split_sections(markdown_file_path)
    
    # Step 2: Further split into character-level chunks
    final_chunks= split_chunks(section_docs)
    
    # Step 3: Save to JSON
    chunks_data= [{"page_content": doc.page_content, "metadata": doc.metadata} for doc in final_chunks]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks_data, f, ensure_ascii=False, indent=2)
    
    # Example: print the 51st chunk
    print(final_chunks[50])


if __name__ == "__main__":
    main()
