from dotenv import load_dotenv
import pandas as pd
from deepseek_LLM import DeepSeekOllamaLLM
from deepeval.test_case import LLMTestCase
from deepeval.metrics import (
    AnswerRelevancyMetric, FaithfulnessMetric,
    ContextualRelevancyMetric, ContextualPrecisionMetric, ContextualRecallMetric
)
from gemini_LLM import GeminiModel

# --- Load Excel file ---
excel_file = "evaluation/Retrieved_Eval_Results.xlsx"
df = pd.read_excel(excel_file)

# --- Initialize Gemini model ---
gemini_model = GeminiModel()

# --- Create test cases ---
test_cases = []
for _, row in df.iterrows():
    retrieved_docs = row['RetrievedContext']
    if isinstance(retrieved_docs, str):
        retrieved_docs = [doc.strip() for doc in retrieved_docs.split("\n\n") if doc.strip()]

    test_case = LLMTestCase(
        input=row['Question'],
        actual_output=row['ActualOutput'],
        expected_output=row['ExpectedOutput'],
        retrieval_context=retrieved_docs
    )
    test_cases.append(test_case)

# --- Define metrics with thresholds ---
all_metrics = [
    ContextualRelevancyMetric(threshold=0.6, model=gemini_model),
    ContextualPrecisionMetric(threshold=0.6, model=gemini_model),
    ContextualRecallMetric(threshold=0.6, model=gemini_model),
    AnswerRelevancyMetric(threshold=0.7, model=gemini_model),
    FaithfulnessMetric(threshold=0.8, model=gemini_model)
]

# --- Run evaluation and collect results ---
results_list = []
for test_case in test_cases:
    result_row = {
        "Question": test_case.input,
        "ActualOutput": test_case.actual_output,
        "ExpectedOutput": test_case.expected_output,
        "RetrievedContext": " | ".join(test_case.retrieval_context) if test_case.retrieval_context else ""
    }

    for metric in all_metrics:
        try:
            metric.measure(test_case)  # populates metric.score
            result_row[f"{metric.__class__.__name__}_score"] = metric.score
        except Exception as e:
            print(e)
            result_row[f"{metric.__class__.__name__}_score"] = 0.0

    results_list.append(result_row)
# --- Convert to DataFrame ---
results_df = pd.DataFrame(results_list)

# --- Print detailed per-row results ---
print("\n=== Detailed Results Per Row ===")
print(results_df.to_string(index=False))  # prints all rows neatly

# --- Save per-row results (only scores) ---
output_file = "evaluation/RAG_Eval_PerRow.xlsx"
results_df.to_excel(output_file, index=False)
print(f"\nSaved evaluation results per row to {output_file}")

# --- Final Summary (Pass/Fail counts based on thresholds) ---
summary = {}
for metric in all_metrics:
    metric_name = metric.__class__.__name__
    score_col = f"{metric_name}_score"
    total = len(results_df)
    passed = (results_df[score_col] >= metric.threshold).sum()
    failed = total - passed
    summary[metric_name] = {
        "Total": total,
        "Passed": passed,
        "Failed": failed,
        "Pass Rate (%)": round((passed / total) * 100, 2)
    }

summary_df = pd.DataFrame(summary).T  # transpose for readability

# --- Print summary results ---
print("\n=== Final Summary ===")
print(summary_df.to_string())

# --- Save summary results ---
summary_file = "evaluation/RAG_Eval_Summary.xlsx"
summary_df.to_excel(summary_file, index=True)
print(f"\nSaved summary results to {summary_file}")
