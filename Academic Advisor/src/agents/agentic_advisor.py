

import sys , os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from langchain_core.messages import  SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model

from src.core.prompts import SYSTEM_MESSAGE

from src.agents.tools.tools import detect_schedule_conflicts, build_timetable, course_distribution_advisor ,course_context_lookup,calculate_total_credits_tool
from dotenv import load_dotenv
import os
# === Initialize Gemini Flash LLM ===
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

llm = init_chat_model(
    "gemini-2.0-flash",
    model_provider="google_genai",
    google_api_key= api_key
)


def create_agent_for_user(username: str):

    # === System message with detailed instructions (Context is simplified and structured) ===
    prompt = SYSTEM_MESSAGE.format(username = username)
    sys_msg = SystemMessage(content=prompt)

    tools = [detect_schedule_conflicts, build_timetable, course_distribution_advisor,course_context_lookup,calculate_total_credits_tool]

    agent_instance = create_react_agent(
        model=llm,
        tools=tools,
        prompt=sys_msg,
        checkpointer=MemorySaver(),
        name=f"academic_advisor_agent_{username}"
    )
    # with open("graph.png", "wb") as f:
    #     f.write(agent_instance.get_graph().draw_mermaid_png())
    # print("Saved graph structure as graph.png")

    # Return the agent instance, no error, and the user ID
    return agent_instance, None

if __name__ == "__main__":
    # Example student
    username = "Leila"
    agent, error= create_agent_for_user(username) 
    if error:
        print("Error:", error)
    else:
        print(f"Agent created for {username}")

        # Start a conversation with the agent
        result = agent.invoke(
            {
                "messages": [
                    {"role": "user", "content": "Hi, can you help me plan my courses for next semester?"}
                ]
            },
            config={"configurable": {"thread_id": "Leila-session-1"}}
        )


        print("\n=== Agent Response ===")
    
        # Assuming `result` is what you got
        for msg in result["messages"]:
            msg.pretty_print()
            
            
    