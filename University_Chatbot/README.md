# 🎓 ESIB Bilingual Agentic RAG University Chatbot

### **AI-powered academic assistant for students, applicants, and staff**

This project is a **bilingual (English & French) Agentic RAG chatbot** designed for **ESIB (École Supérieure des Ingénieurs de Beyrouth)**.
It answers general questions about **programs, admissions, rules, degrees, courses**, and more — all grounded in the official **ESIB catalogue**.

Built with:

* **Gemini API** for advanced answer generation
* **LangGraph agentic workflow** (multi-node orchestration)
* **RAG pipeline** with retrieval and reasoning
* **Gradio UI** with full streaming

The result is an **accurate**, **fast**, and **student-friendly** AI assistant.
---

# 🛠️ Installation Guide

Follow these steps to run the chatbot locally.

---

## 1.Clone the Repository

```bash
git clone https://github.com/<your-repo>/USJ-Student-Chatbots.git
cd University Chatbot
```

---

## 2.Create a Python Environment

```bash
conda create -n esib-chatbot python=3.11
conda activate esib-chatbot
```

Or using venv:

```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows
```

---

## 3.Install Requirements

```bash
pip install -r requirements.txt
```
---

## 4.Create Your API Keys

This project requires:

### **Gemini API**

Used for:

* generation
* reasoning
* translation
* answer refinement

Create a key here:
[https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

---

### **Jina AI Reranker API**

Used for:

* Chunk reranking
Create a key here:
[https://jina.ai/reranker/](https://jina.ai/reranker/)

---

## 5.Create a `.env` File

Inside the project root, create:

```
.env
```

And add:

```
GOOGLE_API_KEY=your_google_gemini_key
JINA_API_KEY=your_jina_reader_key
```
---

## 6.Run the Gradio App

Start the chatbot locally:

```bash
python gradio_app.py
```

You will see:

```
Running on http://127.0.0.1:7860
```

Open it in your browser.

You now have a fully streaming, bilingual, agentic chatbot running!

---
## 7. Optional: Run as an API

To integrate the chatbot into a frontend, mobile app, or other systems, use the FastAPI server:

```bash
python app.py
```

**API Endpoint:** `/chat`
**Request Body Example:**

```json
{
  "message": "Tell me about master's in AI",
  "thread_id": "optional_thread_id"
}
```

---


# Final Notes

This University chatbot is:

* **fully extendable** (add majors, rules, schedules, forms)
* **scalable** (swap vector DBs, add tools/agents)
* **deploy-ready** (via Gradio or Hugging Face Spaces)

