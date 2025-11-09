import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph, MessagesState, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver

from src.agents.query_or_respond import get_query_or_respond_node
from src.agents.generation_agent import generate
from src.agents.tools import retrieve_university_info,find_course_tool

from langchain_core.messages import HumanMessage,AIMessage

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

memory = MemorySaver()

class ToolNodeWithStatus(ToolNode):
    def __call__(self, state: MessagesState):
        # Step 1: Show "Searching..."
        yield {
            "messages": state["messages"] + [
                AIMessage(content="🔎 Searching for relevant information...")
            ]
        }

        # Step 2: Run the actual tool
        result_state = super().__call__(state)

        # Step 3: Replace "Searching..." with the real response
        final_messages = state["messages"] + result_state["messages"][-1:] 
        yield {"messages": final_messages}

# --- Build Graph ---
graph_builder = StateGraph(MessagesState)

graph_builder.add_node("query_or_respond", get_query_or_respond_node(api_key))
graph_builder.add_node("tools", ToolNodeWithStatus([
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

# --- Run example session ---
if __name__ == "__main__":
    config = {"configurable": {"thread_id": "session_001"}}

    inputs = {
        "messages": [
            HumanMessage(content="What is the prerequiste of statistics")
        ]
    }

    # Stream mode instead of invoke
    for event in graph.stream(inputs, config=config, stream_mode="values"):
        # Pretty print each message in the current event
        for msg in event["messages"]:
            msg.pretty_print()
        print("\n" + "-"*50 + "\n")  # optional separator for readability

    # # User message 2 (follow-up)
    # inputs_2 = {"messages": [HumanMessage(content="Tell me more about the AI program.")]}
    # output_2 = graph.invoke(inputs_2, config=config)

    # print("\n--- Step 2 ---")
    # for msg in output_2["messages"]:
    #     print(f"{getattr(msg, 'type', '').upper()}: {msg.content}")
 