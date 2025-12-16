# app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os

# Add parent directory to access src/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.agentic_rag import graph  # adjust path if needed

app = FastAPI()

# Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all origins for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    config = {"configurable": {"thread_id": req.thread_id or "default"}}

    final_state = None
    tool_called = False

    for event in graph.stream(
        {"messages": [{"role": "user", "content": req.message}]},
        stream_mode="values",
        config=config,
    ):
        final_state = event
        # check if any tool message exists
        tool_called = any(getattr(m, "type", None) == "tool" for m in final_state["messages"])

    answer_text = final_state["messages"][-1].content
    return {"response": answer_text, "tool_called": tool_called}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
