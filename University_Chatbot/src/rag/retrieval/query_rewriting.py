import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

import re
import json
import os
import logging
from core.llm import get_llm

# === Setup Logging ===
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# === Load Environment Variables and Initialize Gemini Client ===
llm = get_llm()

def rewrite_query(original_query, chat_history=None):
    """
    Rewrite the original query using Gemini API with context from previous chat history.
    
    Parameters:
        original_query (str): The user's current question.
        chat_history (list[tuple]): Optional list of (user, bot) messages.

    Returns:
        str: The rewritten query for improved retrieval.
    """
    chat_context = ""
    if chat_history:
        for i, (user_msg, bot_msg) in enumerate(chat_history[-4:]):
            chat_context += f"\nUser: {user_msg}\nBot: {bot_msg}"

    # === Construct Prompt ===
    prompt = f"""You are a University Chatbot for the Engineering Department at USJ.
Your task is to reformulate user queries to improve document retrieval in a RAG system.

Consider the following recent chat history and the new question from the user. Rewrite the query to make it more precise and complete based on context.

Chat History:{chat_context}

User Question: {original_query}

Some reference:
 - if the query is about prerequisites for a specific course only make sure to mention that it is in course content/Description des Cours/course description.
 - if the user is asking about the courses in the first year (semester 1 and 2), second year (semester 3 and 4), third year (semester 5 and 6), make sure to mention the semester.
 - if the question is not related to the chat history do not use the chat history.
 - Do not assume what the user is asking about
 - if the question is in french or any other language translate to english after rewriting the question and return the translated only.
 - If the user mentions CCE: Computer and Communication Engineering.
Respond ONLY in this exact JSON format:
{{
  "rewritten_query": "..."
}}"""

    try:
        response = llm.generate_content(prompt)
        content = response.text.strip()
        logger.debug(f"Gemini raw response: {content}")

        try:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                json_str = match.group(0)
                json_str = json_str.encode("utf-8").decode("unicode_escape")
                result = json.loads(json_str)
                rewritten_query = result.get("rewritten_query", "").strip()
                logger.info(f"Rewritten Query: {rewritten_query}")
                return rewritten_query
            else:
                logger.warning("No JSON object found in Gemini response.")

        except Exception as parse_err:
            logger.error(f"Error parsing Gemini response: {parse_err}")

    except Exception as api_err:
        logger.error(f"Error during Gemini API call: {api_err}")

    return ""

# === Example Usage ===
if __name__ == "__main__":
    # chat_history should be a list of (user, bot) tuples
    chat_history = [
        ("I’m planning to apply to USJ Engineering", "Great! Let me know if you’re interested in a specific department."),
        ("Yes, I want to know about the first year", "Sure, I can help with the first-year courses.")
    ]
    original_query = "what do I take in the first year"
    rewritten = rewrite_query(original_query, chat_history)
    print("Rewritten Query:", rewritten)
