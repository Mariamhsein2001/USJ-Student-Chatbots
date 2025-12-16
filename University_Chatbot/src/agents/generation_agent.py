from langchain_core.messages import AIMessage
from rag.generation.generation import generate_answer
import time
def generate(state):
    """
    Stream answer chunk by chunk in a format compatible with LangGraph.
    """
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
    s = time.time()
    answer_text = ""
    for chunk in generate_answer(question, context, chat_history):
        if chunk.strip():
            answer_text += chunk
            # Yield a **dict** for LangGraph
            yield {
                "messages": [{"role": "assistant", "content": chunk}],
                "metadata": {"langgraph_node": "generate"}
            }

    e = time.time()
    print(f"Generation took {e - s:.2f} seconds.")
    # Append the final message to the state
    state["messages"].append(AIMessage(content=answer_text))
