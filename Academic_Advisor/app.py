from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import sys, os
import uuid

# --- Import project modules ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from langchain_core.messages import HumanMessage
from src.agents.agentic_advisor import create_agent_for_user
from src.core.context import fetch_user_context
from src.core.cache import GLOBAL_CACHE_STORE

# --- Initialize FastAPI app ---
app = FastAPI(title="ESIB University Advisor API")

# --- CORS (for frontend integration) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- In-memory session store ---
USER_SESSIONS = {}  # {username: {"agent": <agent_instance>, "context": {...}}}


# ===============================
#         MODELS
# ===============================
class LoginRequest(BaseModel):
    username: str
    password: str


class ChatRequest(BaseModel):
    username: str
    message: str


# ===============================
#         HELPERS
# ===============================
def validate_user(username: str, password: str) -> bool:
    """Validate username/password from SQLite DB."""
    try:
        conn = sqlite3.connect("storage/data_store/advising.db")
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        return row and row[0] == password
    except sqlite3.Error as e:
        print(f"Database error during validation: {e}")
        return False


# ===============================
#         ROUTES
# ===============================

@app.post("/login")
async def login_user(req: LoginRequest):
    """
    Login endpoint: validates user, fetches cached context, creates advisor agent.
    """
    username, password = req.username, req.password

    # Step 1: Validate user
    if not validate_user(username, password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Step 2: Retrieve context (from cache or DB)
    cached_context_data = GLOBAL_CACHE_STORE.get(("user_context",), username)
    user_context = None

    if cached_context_data:
        user_context = cached_context_data.value
        print(f"[CACHE HIT] Context loaded for user: {username}")
    else:
        user_context = fetch_user_context(username)
        if "error" in user_context:
            raise HTTPException(status_code=500, detail=f"Context fetch error: {user_context['error']}")
        GLOBAL_CACHE_STORE.put(("user_context",), username, user_context)
        print(f"[CACHE MISS] Context fetched and cached for user: {username}")

    # Step 3: Create user-specific advisor agent
    agent_instance, error = create_agent_for_user(username)
    if error:
        raise HTTPException(status_code=500, detail=f"Agent creation failed: {error}")

    # Step 4: Store in memory session
    USER_SESSIONS[username] = {
        "agent": agent_instance,
        "context": user_context,
    }

    return {
        "message": f"Welcome {username}! Advisor initialized.",
        "context_cached": bool(cached_context_data),
    }


@app.post("/chat")
async def chat_with_agent(req: ChatRequest):
    """
    Chat endpoint: handles message passing with user’s advisor agent.
    """
    username, message = req.username, req.message

    # --- Check if user is logged in ---
    if username not in USER_SESSIONS:
        raise HTTPException(status_code=403, detail="User not logged in or session expired")

    advisor_agent = USER_SESSIONS[username]["agent"]

    # --- Invoke the advisor agent ---
    try:
        result = advisor_agent.invoke(
            {"messages": [HumanMessage(content=message)]},
            config={"configurable": {"thread_id": username, "user_id": username}},
        )

        # Extract final message
        response_text = result["messages"][-1].content
        return {"response": response_text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")


# ===============================
#         STREAMING (optional)
# ===============================

@app.post("/chat/stream")
async def chat_with_agent_stream(req: ChatRequest):
    """
    Optional: stream response chunks for real-time UI updates.
    """
    from fastapi.responses import StreamingResponse

    username, message = req.username, req.message

    if username not in USER_SESSIONS:
        raise HTTPException(status_code=403, detail="User not logged in or session expired")

    advisor_agent = USER_SESSIONS[username]["agent"]

    def stream_generator():
        full_response = ""
        stream = advisor_agent.stream(
            {"messages": [HumanMessage(content=message)]},
            config={"configurable": {"thread_id": username, "user_id": username}},
            stream_mode="messages",
        )
        for msg_chunk, metadata in stream:
            if msg_chunk.type == "ai" and msg_chunk.content:
                full_response += msg_chunk.content
                yield full_response + "\n"

    return StreamingResponse(stream_generator(), media_type="text/plain")


# ===============================
#         SERVER START
# ===============================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
