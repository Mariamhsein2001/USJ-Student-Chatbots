from langchain_core.messages import AIMessage
from langchain.chat_models import init_chat_model
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.agents.tools import retrieve_university_info,find_course_tool
from src.core.prompts import QUERY_OR_RESPOND

def get_query_or_respond_node(api_key):
    """Return query_or_respond node with LLM bound to tools."""
    llm = init_chat_model(
        "gemini-2.0-flash",
        model_provider="google_genai",
        google_api_key=api_key
    )
    available_tools = [retrieve_university_info, find_course_tool]
    llm_with_tools = llm.bind_tools(available_tools)

    def query_or_respond(state):
        system_prompt = QUERY_OR_RESPOND
        messages = [{"role": "system", "content": system_prompt}] + state["messages"]
        response = llm_with_tools.invoke(messages)
        state["messages"].append(response)
        return state

    return query_or_respond
