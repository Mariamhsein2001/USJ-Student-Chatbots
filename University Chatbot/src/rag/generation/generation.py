# generation.py
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.prompts import ChatPromptTemplate

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from retrieval.retrieval_pipeline import hierarchical_retrieval

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

# --- Initialize LLM with streaming ---
llm = init_chat_model(
    "gemini-2.5-flash",
    model_provider="google_genai",
    google_api_key=api_key,
    streaming=True  # Enable streaming
)

def generate_answer(question: str, context: str, chat_history: str = ""):
    """
    Generate an answer using retrieved context and optional conversation history.
    Yields partial outputs as they are generated.
    """
    prompt_template = ChatPromptTemplate.from_template("""
You are a university chatbot for the **Engineering School (ESIB)** at **Saint Joseph University of Beirut (USJ)**.

Conversation History:
{chat_history}

Context:
{context}

Question: {question}

Instructions:
- Only use information in the context above.
- Do not repeat the same sentence or information.
- Respond in the same language as the question (English if question is in English, French if question is in French).
- Use a friendly, natural, and conversational tone.
- If context is incomplete, respond with the available information and suggest retrieving more details.
- Only say "I don't know" if truly no relevant information is present.
- If prerequiste is Rien -> no prerequistes
- Make sure the response is related to the question.
- Try to ask more clarification if couldn't find information.
- Make sure to keep the conversation going.
- CCE refers to Computer and Communication Engineering
Answer:
""")

    chain = prompt_template | llm
    # Stream the response
    for event in chain.stream({
        "chat_history": chat_history,
        "context": context,
        "question": question
    }):
        # event contains partial message(s)
        yield event.content  


# --- Test streaming with retrieval ---
if __name__ == "__main__":
    test_question = "What master's programs are available at USJ?"

    # Step 1: Retrieve context
    retrieved_docs = hierarchical_retrieval(test_question)
    test_context = "\n\n".join([doc.page_content for doc in retrieved_docs])

    # Optional: previous conversation history
    test_history = "User asked about ESIB Master's programs earlier."

    # Step 2: Stream generated answer
    print("=== Retrieved Context ===")
    print(test_context)
    print("\n=== Generated Answer (Streaming) ===")
    for chunk in generate_answer(test_question, test_context, test_history):
        print(chunk, end="", flush=True)
