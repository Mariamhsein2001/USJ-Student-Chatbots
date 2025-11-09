import json
import sys
import os
import time
import pandas as pd
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.agents.agentic_rag import graph



def run_rag_query(user_input: str, thread_id: str = "def234"):
    """
    Run a RAG query through the compiled LangGraph and return both
    the final answer and any retrieved documents.

    Args:
        graph: The compiled LangGraph object.
        user_input (str): User query.
        thread_id (str): Unique thread/session ID.

    Returns:
        tuple: (final_answer: str, retrieved_docs: list[str])
    """
    config = {"configurable": {"thread_id": thread_id}}
    final_state = None

    # Stream through the graph
    for event in graph.stream(
        {"messages": [{"role": "user", "content": user_input}]},
        stream_mode="values",
        config=config,
    ):
        final_state = event  # capture latest state

    # --- Extract final AI answer ---
    answer = final_state["messages"][-1].content

    # --- Extract retrieved docs from tool messages ---
    retrieved_docs = [
        m.content for m in final_state["messages"] if getattr(m, "type", None) == "tool"
    ]

    return answer, retrieved_docs
# --- Load your QA Excel ---
qa_df = pd.read_excel("evaluation/QA_Evaluation.xlsx")  

# Prepare output Excel
output_file = "evaluation/Retrieval_Results.xlsx"
if os.path.exists(output_file):
    results_df = pd.read_excel(output_file)
else:
    results_df = pd.DataFrame(columns=["Question", "ActualOutput", "ExpectedOutput", "RetrievedContext"])

# --- Run RAG queries and append results immediately ---
for idx, row in qa_df.iterrows():
    query = row["Questions"]
    expected_answer = row["Answers"]
    
    print(f"\n===== USER QUERY {idx+1} =====\n{query}")
    time.sleep(10)  # optional: prevent rapid queries
    
    # Get RAG answer + retrieved documents
    answer, retrieved_docs = run_rag_query(query)
    
    # --- Clean retrieved docs ---
    cleaned_docs = [doc.strip() for doc in retrieved_docs if doc.strip()]  
    
    print("\n=== RAG Answer ===")
    print(answer)
    
    print("\n=== Retrieved Docs ===")
    for doc in cleaned_docs:
        print(doc)
    
    # Append to DataFrame as JSON string (preserves list)
    new_row = {
        "Question": query,
        "ActualOutput": answer,
        "ExpectedOutput": expected_answer,
        "RetrievedContext": json.dumps(cleaned_docs, ensure_ascii=False)
    }
    results_df = pd.concat([results_df, pd.DataFrame([new_row])], ignore_index=True)
    
    # Save after each query
    results_df.to_excel(output_file, index=False)
    print(f"Logged result {idx+1} to {output_file}")
