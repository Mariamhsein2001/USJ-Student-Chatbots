import gradio as gr
import uuid
import sys
import os
import base64

# Add parent directory to access src/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agentic_rag import graph  # your RAG agent

# Session handling
session_ids = {}

def chat_stream(message, history, request: gr.Request):
    client_id = f"{request.client.host}-{request.headers.get('user-agent', '')}"
    session_id = session_ids.setdefault(client_id, str(uuid.uuid4()))
    config = {"configurable": {"thread_id": session_id}}
    response_text = ""
    try:
        for event in graph.stream(
            {"messages": [{"role": "user", "content": message}]},
            stream_mode="values",
            config=config,
        ):
            chunk = event["messages"][-1].content
            response_text = chunk
        return response_text
    except Exception as e:
        return f"Agent error: {str(e)}"


# Load images
logo_path = "assets/logo.png"
bg_image_path = "assets/background.jpg"

with open(bg_image_path, "rb") as f:
    bg_image = base64.b64encode(f.read()).decode()

with open(logo_path, "rb") as f:
    logo_image = base64.b64encode(f.read()).decode()


# --- CSS + HTML background layer ---
custom_css = f"""
<style>

/* Make all Gradio containers fully transparent */
body, .gradio-container, .gradio-container > div, .chat-container {{
    background: transparent !important;
    position: relative !important;
    z-index: 0;
}}

/* Fullscreen blurred background */
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
    transform: scale(1.05);
}}

/* Foreground container */
#content {{
    position: relative;
    z-index: 10;
    background-color: rgba(255, 255, 255, 0.85);
    border-radius: 12px;
    padding: 20px;
    max-width: 900px;
    margin: 40px auto;
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
}}

/* User message */
.chat-message.user {{
    background-color: rgba(240, 240, 240, 0.9) !important;
    color: black !important;
    border-radius: 16px !important;
    padding: 8px 12px;
}}

/* Bot message */
.chat-message.bot {{
    background-color: rgba(255, 255, 255, 0.85) !important;
    color: black !important;
    border-radius: 16px !important;
    padding: 8px 12px;
}}
</style>

<div class="bg-image"></div>
"""


# --- UI Layout ---
with gr.Blocks(title="ESIB University Chatbot") as demo:
    gr.HTML(custom_css)

    with gr.Column(elem_id="content"):
        gr.HTML(f"""
        <div style="
            display: flex;
            align-items: center;
            justify-content: flex-end;
            margin-bottom: 5px;
        ">
            <!-- Logo on the right -->
            <div style="text-align: center;">
                <img src="data:image/png;base64,{logo_image}" style="height:50px; display:block; margin: 0 auto;">
                
            </div>
        </div>

        <!-- Subtitle centered below everything -->
        <h2 style="margin:5px 0 0 0; color:black; text-align:center;">ESIB Chatbot</h2>
        <p style="margin-top:10px; font-size:16px; color:black; text-align:center;">
            Get instant answers about ESIB programs, admissions, and everything you need to know to navigate your academic journey.
        </p>
        """)



        gr.ChatInterface(
            fn=chat_stream,
            examples=[
                "What master's degrees are offered at ESIB?",
                "What are the admission requirements?",
                "Tell me about the engineering programs."
            ],
            theme="soft",
            type="messages"
        )


# Launch app
if __name__ == "__main__":
    demo.launch(share=True)
