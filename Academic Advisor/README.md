# 🎓 Agent- Based Academic Advisor Agent

### **AI-powered academic advisor for course planning and student guidance**

This project is an **agent-based academic advisor chatbot** designed for **ESIB (École Supérieure des Ingénieurs de Beyrouth)**.
It provides **personalized academic guidance**, including:

* Planning courses for upcoming semesters
* Checking credit requirements and track alignment
* Identifying course conflicts
* Offering tailored recommendations based on past performance and student interests

All recommendations are grounded in **official ESIB course rules, catalog, and credit requirements**.

Built with:

* **Gemini API** for reasoning and generating final course plans
* **Agent-based workflow** to orchestrate multiple planning tools
* **Custom academic tools** for credit calculation, timetable building, and course selection
* **Gradio UI** for a fast, interactive, streaming experience

The result is an **accurate, reliable, and student-friendly AI academic advisor**.

---

# 🛠️ Installation Guide

Follow these steps to run the Academic Advisor locally.

---

## 1. Clone the Repository

```bash
git clone https://github.com/<your-repo>/USJ-Student-Chatbots.git
cd Academic Advisor
```

---

## 2. Create a Python Environment

Using **conda**:

```bash
conda create -n esib-advisor python=3.10
conda activate esib-advisor
```

Or using **venv**:

```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows
```

---

## 3. Install Requirements

```bash
pip install -r requirements.txt
```

---

## 4. Create Your API Keys

This project requires:

### **Gemini API**

Used for:

* Generating course recommendations
* Merging multiple planning strategies

Create a key here: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

---

## 5. Create a `.env` File

Inside the project root, create a `.env` file:

```
GOOGLE_API_KEY=your_google_gemini_key

```

---

## 6. Run the Gradio App

Start the academic advisor locally:

```bash
python gradio_app.py
```

You will see:

```
Running on http://127.0.0.1:7860
```

Open it in your browser.

You now have a **fully streaming, agent-based academic advisor chatbot** running!

---

## 7. Optional: Run as an API

To integrate the advisor into a frontend, mobile app, or other systems, use the FastAPI server:

```bash
python app.py
```

**API Endpoint:** `/chat`
**Request Body Example:**

```json
{
  "message": "Plan my courses for next semester based on AI and Data Science track",
  "thread_id": "optional_thread_id"
}
```

---

#  Final Notes

This **Academic Advisor Agent** is:

* **Fully extendable** – add new majors, rules, schedules, and tools
* **Scalable** – add more agents/tools or swap backend components
* **Deploy-ready** – via Gradio locally or Hugging Face Spaces


