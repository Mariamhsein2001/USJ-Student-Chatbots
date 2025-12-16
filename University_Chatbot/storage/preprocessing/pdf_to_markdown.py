
# DEPRECATED
import fitz  # PyMuPDF
import os

def extract_structured_markdown(pdf_path: str, output_path: str = None) -> None:
    """
    Extracts text from a PDF file and converts it into structured Markdown,
    attempting to preserve headings based on font size.

    Parameters:
        pdf_path (str): Path to the input PDF file.
        output_path (str, optional): Path to save the generated Markdown file.
                                     If not provided, saves alongside the PDF with `.md` extension.

    Output:
        Saves a Markdown (.md) file containing the extracted text.
    """
    if not os.path.exists(pdf_path):
        print(f"Error: File not found - {pdf_path}")
        return

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF file: {e}")
        return

    text_blocks = []
    try:
        for page_num, page in enumerate(doc, start=1):
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if "lines" not in block:
                    continue
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if not text:
                            continue
                        text_blocks.append({
                            "text": text,
                            "size": span["size"],
                            "font": span["font"],
                            "flags": span["flags"],
                        })
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return

    if not text_blocks:
        print("Warning: No text extracted from PDF.")
        return

    try:
        # Identify unique font sizes and assign heading levels
        unique_sizes = sorted(set(round(b["size"]) for b in text_blocks), reverse=True)
        size_to_heading = {
            size: "#" * (i + 1) for i, size in enumerate(unique_sizes[:6])  # H1 to H6
        }

        # Build Markdown content
        md_lines = []
        for block in text_blocks:
            size = round(block["size"])
            heading_prefix = size_to_heading.get(size, "")
            if heading_prefix:
                md_lines.append(f"{heading_prefix} {block['text']}")
            else:
                md_lines.append(block["text"])

        markdown_text = "\n\n".join(md_lines)

        # Determine output file path
        if output_path is None:
            output_path = os.path.splitext(pdf_path)[0] + ".md"

        # Save the Markdown content
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_text)

        print(f"Markdown saved to: {output_path}")
    except Exception as e:
        print(f"Error generating or saving Markdown: {e}")


if __name__ == "__main__":
    # Example usage
    pdf_path = "storage/data/raw/Catalogue_ESIB_2022-2023.pdf"
    extract_structured_markdown(pdf_path)
