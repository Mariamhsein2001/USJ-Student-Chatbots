import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph, MessagesState, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver

from src.agents.query_or_respond import get_query_or_respond_node
from src.agents.generation_agent import generate
from src.agents.tools import retrieve_university_info,find_course_tool

from langchain_core.messages import HumanMessage


memory = MemorySaver()

# --- Build Graph ---
graph_builder = StateGraph(MessagesState)

graph_builder.add_node("query_or_respond", get_query_or_respond_node())
graph_builder.add_node("tools", ToolNode([
    retrieve_university_info,
    find_course_tool
]))
graph_builder.add_node("generate", generate)

graph_builder.set_entry_point("query_or_respond")

graph_builder.add_conditional_edges(
    "query_or_respond",
    tools_condition,
    {END: END, "tools": "tools"},
)

graph_builder.add_edge("tools", "generate")
graph_builder.add_edge("generate", END)

graph = graph_builder.compile(checkpointer= memory)



# --- Optional: Save visualization ---
# with open("graph.png", "wb") as f:
#     f.write(graph.get_graph().draw_mermaid_png())
# print("Saved graph structure as graph.png")

def run_chatbot_stream():
    config = {"configurable": {"thread_id": "session_001"}}

    inputs = {
        "messages": [
            HumanMessage(content="tell me about master for AI ")
        ]
    }

    # Stream mode instead of invoke
    accumulated_text = ""

    for message_chunk, metadata in graph.stream(inputs, config=config, stream_mode="messages"):
        if not message_chunk.content:
            continue

        node_type = metadata.get("langgraph_node")

        if node_type == "generate":
            # Accumulate chunks for smooth streaming
            accumulated_text += message_chunk.content
            yield accumulated_text

        elif node_type == "query_or_respond":
            # For query_or_respond, just yield as-is (usually a complete message)
            accumulated_text += message_chunk.content
            yield accumulated_text       # for msg in event["messages"]:
        #     msg.pretty_print()
        # print("\n" + "-"*50 + "\n")  # optional separator for readability

    # # User message 2 (follow-up)
    # inputs_2 = {"messages": [HumanMessage(content="Tell me more about the AI program.")]}
    # output_2 = graph.invoke(inputs_2, config=config)

    # print("\n--- Step 2 ---")
    # for msg in output_2["messages"]:
    #     print(f"{getattr(msg, 'type', '').upper()}: {msg.content}")


if __name__ == "__main__":
    for response in run_chatbot_stream():
        print(response)
 