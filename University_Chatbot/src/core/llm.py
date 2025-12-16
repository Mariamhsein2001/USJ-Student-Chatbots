# src/core/llm.py

import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables from .env file
load_dotenv()  

def get_llm(

):
    """
    Initialize and return a Google Gemini LLM wrapper.

    Args:
        model_name (str): The Gemini model to use (e.g., "gemini-2.0-flash").
        temperature (float): Sampling temperature.

    Returns:
        ChatGoogleGenerativeAI: An initialized chat model.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Google API key not found. Ensure it is set in your .env file.")

    genai.configure(api_key=api_key)
    llm = genai.GenerativeModel("gemini-2.0-flash")
    return llm
