
from dotenv import load_dotenv
from deepeval.models.base_model import DeepEvalBaseLLM
import google.generativeai as genai
import os 

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

 
# Define Gemini model for DeepEval
class GeminiModel(DeepEvalBaseLLM):
        def __init__(self):
            pass

        def load_model(self):
            genai.configure(api_key=api_key)
            return genai.GenerativeModel("gemini-2.0-flash-lite")

        def generate(self, prompt: str) -> str:
            model = self.load_model()
            response = model.generate_content(prompt)
            return response.text

        async def a_generate(self, prompt: str) -> str:
            return self.generate(prompt)

        def get_model_name(self):
            return "gemini-2.0-flash-lite"
