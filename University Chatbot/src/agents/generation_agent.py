from langchain_core.messages import AIMessage
from rag.generation.generation import generate_answer

def generate(state):
    """Generate final answer with context + history."""
    context = "\n\n".join(
        m.content for m in state["messages"] if getattr(m, "type", None) == "tool"
    )
    chat_history = "\n".join(
        m.content for m in state["messages"] if getattr(m, "type", None) in {"human", "ai"}
    )
    question = next(
        (m.content for m in reversed(state["messages"]) if getattr(m, "type", None) == "human"),
        ""
    )

    answer_text = ""
    for chunk in generate_answer(question, context, chat_history):
        # print(chunk, end="", flush=True)
        answer_text += chunk

    state["messages"].append(AIMessage(content=answer_text))
    return state
