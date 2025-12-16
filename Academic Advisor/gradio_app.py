import gradio as gr
import sqlite3
import sys, os, base64
from langchain_core.messages import HumanMessage,AIMessage

# --- Path setup ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.agents.agentic_advisor import create_agent_for_user
from src.core.context import fetch_user_context
from src.core.cache import GLOBAL_CACHE_STORE


# --- User Auth ---
def validate_user(username: str, password: str) -> bool:
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


# --- Globals ---
current_user = None
global_advisor = None


# --- Login Logic ---
def login_user(username, password):
    global current_user, global_advisor

    if not validate_user(username, password):
        return gr.update(visible=True), gr.update(visible=False), "❌ Invalid login. Try again."

    cached_context_data = GLOBAL_CACHE_STORE.get(("user_context",), username)
    user_context = cached_context_data.value if cached_context_data else None

    if not user_context:
        user_context = fetch_user_context(username)
        if "error" in user_context:
            return gr.update(visible=True), gr.update(visible=False), f"❌ Context fetching error: {user_context['error']}"
        GLOBAL_CACHE_STORE.put(("user_context",), username, user_context)

    agent_instance, error = create_agent_for_user(username)
    if error:
        return gr.update(visible=True), gr.update(visible=False), f" Agent creation failed: {error}"

    current_user = username
    global_advisor = agent_instance

    return gr.update(visible=False), gr.update(visible=True), f"✅ Welcome {username}! You can start chatting."

def extract_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return ""


# --- Chat Logic ---
def chat_with_agent(message, history):
    if not current_user or not global_advisor:
        yield "🔒 Please log in first."
        return

    final_answer = ""

    for msg, meta in global_advisor.stream(
        {"messages": [HumanMessage(content=message)]},
        config={"configurable": {"thread_id": current_user, "user_id": current_user}},
        stream_mode="messages",
    ):
        # Debug (optional – remove later)
        # msg.pretty_print()

        # Only stream AI responses
        if meta.get("langgraph_node") == "model" and isinstance(msg, AIMessage):
            text = extract_text(msg.content)
            if text:
                final_answer += text
                yield final_answer

    if not final_answer:
        yield "⚠️ The advisor could not generate a response. Please rephrase your question."

# --- Assets ---
logo_path = "assets/logo.png"
bg_image_path = "assets/background.jpg"

with open(bg_image_path, "rb") as f:
    bg_image = base64.b64encode(f.read()).decode()

with open(logo_path, "rb") as f:
    logo_image = base64.b64encode(f.read()).decode()


# --- CSS ---
custom_css = f"""
<style>
/* Background */
body, .gradio-container, .gradio-container > div {{
    background: transparent !important;
    position: relative !important;
    z-index: 0;
}}
.bg-image {{
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-image: url("data:image/jpeg;base64,{bg_image}");
    background-size: cover;
    background-position: center;
    filter: blur(6px);
    z-index: -1;
}}

/* Login section */
#login-section {{
    background: rgba(255, 255, 255, 0.88);
    border-radius: 16px;
    padding: 25px;
    max-width: 600px;
    margin: 80px auto;
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3);
}}
#logo {{
    display: block;
    margin: 0 auto 10px auto;
    height: 60px;
}}

/* Chatbot container background */
#chat-section {{
    background: rgba(255, 255, 255, 0.85);
    border-radius: 16px;
    padding: 25px;
    max-width: 900px;
    margin: 40px auto;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}}

/* Make only the chatbot area itself white */
#chat-section .gr-chatbot {{
    background-color: white !important;
    border-radius: 12px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}}
</style>
<div class="bg-image"></div>
"""


# --- UI ---
with gr.Blocks(title="ESIB University Advisor Chatbot") as app:
    gr.HTML(custom_css)

    # LOGIN PAGE
    with gr.Column(visible=True, elem_id="login-section") as login_col:
        gr.HTML(f"""
        <div style="text-align:center;">
            <img id="logo" src="data:image/png;base64,{logo_image}">
            <h2> ESIB Academic Advisor</h2>
            <p>Please log in to continue chatting with your advisor.</p>
        </div>
        """)
        user_input = gr.Textbox(label="👤 Username", placeholder="Enter your student username", interactive=True)
        pass_input = gr.Textbox(label="🔒 Password", type="password", placeholder="Enter your password", interactive=True)
        login_btn = gr.Button("🔑 Login", variant="primary")
        login_status = gr.Markdown(value="", elem_id="login-status", visible=True)

    # CHAT PAGE
    with gr.Column(visible=False, elem_id="chat-section") as chat_col:
        gr.HTML(f"""
         <!-- Subtitle centered below everything -->
        <h2 style="margin:5px 0 0 0; color:black; text-align:center;">Chat with Your Academic Advisor</h2>
        <p style="margin-top:10px; font-size:16px; color:black; text-align:center;">
            Receive personalized guidance, course advice, and all the program information you need to plan your studies.
        </p>""")

        chat_iface = gr.ChatInterface(
            fn=chat_with_agent,
            chatbot=gr.Chatbot(height=500, show_copy_button=True, type="messages"),
        )

    # Button connection
    login_btn.click(
        fn=login_user,
        inputs=[user_input, pass_input],
        outputs=[login_col, chat_col, login_status]
    )

if __name__ == "__main__":
    app.launch(share=True)
