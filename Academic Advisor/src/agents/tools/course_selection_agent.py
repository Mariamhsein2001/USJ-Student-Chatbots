from functools import lru_cache
import sys, os
from pathlib import Path

# Add paths only once at the top
sys.path.append(str(Path(__file__).resolve().parents[2]))
sys.path.append(str(Path(__file__).resolve().parents[3]))

from core.prompts import COURSE_SELECTION_PROMPT
from utils.utilities import load_rules_from_file

@lru_cache(maxsize=32)
def get_gpa_rules():
    return load_rules_from_file("storage/data/rules/gpa_rules.txt")

# Load GPA rules once (avoid reloading file each call)
GPA_RULES = get_gpa_rules()


def generate_course_selection_plan(context: dict, llm, interests: str = "", stream_handler=None) -> dict:
    """
    Generate a course selection plan using a language model (Gemini or compatible).
    Supports token streaming if `stream_handler` is provided.
    Silent (no console printing).
    """
    if "error" in context:
        return context

    prompt = COURSE_SELECTION_PROMPT.format(
        username=context.get("username", "Student"),
        gpa=context.get("gpa", "N/A"),
        interests=interests,
        past_summary=context.get("past_summary", ""),
        formatted_courses=context.get("formatted_courses", ""),
        gpa_rules=GPA_RULES
    )

    streamed_text = ""

    try:
        # If the model supports streaming (Gemini / generativeai)
        if hasattr(llm, "generate_content"):
            for chunk in llm.generate_content(prompt, stream=True):
                if hasattr(chunk, "text") and chunk.text:
                    streamed_text += chunk.text
                    if stream_handler:
                        stream_handler(chunk.text)  # e.g., update UI
        else:
            # Fallback for LLMs without streaming support
            response = llm.generate_content(prompt)
            streamed_text = getattr(response, "text", str(response)).strip()

    except Exception as e:
        streamed_text = f"Gemini error: {str(e)}"

    return {"prompt": prompt, "recommendation": streamed_text.strip()}
