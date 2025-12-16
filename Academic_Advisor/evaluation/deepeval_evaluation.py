import os
import sys
import time
import pandas as pd
from deepeval.test_case import LLMTestCase, ToolCall, LLMTestCaseParams
from deepeval.metrics import HallucinationMetric, ToolCorrectnessMetric, GEval

# === Project imports ===
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from gemini_LLM import GeminiModel  # your existing Gemini wrapper

# === Configuration ===
input_excel = "evaluation/testing_with_output.xlsx"
output_file = "evaluation/Evaluation_Results_New.xlsx"

# === Initialize model & metrics ===
gemini_model = GeminiModel()

hallucination_metric = HallucinationMetric(threshold=0.5, model=gemini_model)
tool_metric = ToolCorrectnessMetric()

correctness_metric = GEval(
    name="Correctness",
    model=gemini_model,  # can replace with gemini-pro or ollama/llama3.2 if integrated
    evaluation_params=[
        LLMTestCaseParams.CONTEXT,
        LLMTestCaseParams.ACTUAL_OUTPUT,
        LLMTestCaseParams.EXPECTED_OUTPUT,
    ],
    evaluation_steps = [
    "Determine whether the actual output is factually correct based on the expected output.",
    "Check if all elements mentioned in the expected output are present and correctly represented in the actual output.",
    "Assess if there are any discrepancies in details, values, or information between the actual and expected outputs.",
    "We don't care if the structure or format or representation is different(such as different timetable structure); it is still correct as long as the content is accurate.",
    "Adding extra information is fine(such as course code and title), but missing information related to the main idea is penalized.",
    "We don't need exactly the same words; only the main idea matters and the question is answered.",
    "It is okay if unrrelated extra information is added as long as the question is correclty answered",
    "Scores should reflect **presence and accuracy of main ideas**, not wording.",
    "If the expected answer is present in the output then it is correct regardless of additional information (you give high scores regardless if additional info is relevant or not)",
    "Any schedule that fits the input requirements is acceptable."
    ]

)

# === Load Excel ===
df = pd.read_excel(input_excel)
print(f" Loaded {len(df)} test cases from {input_excel}")

# Normalize columns
df.columns = df.columns.str.strip().str.lower()
required_cols = ["student", "input", "output", "context","tools_called", "expected_tools", "expected_output"]
for col in required_cols:
    if col not in df.columns:
        raise ValueError(f"Missing required column in Excel: '{col}'")

results = []

# === Evaluate each test case ===
# === Evaluate each test case ===
for i, row in df.iterrows():
    print(f"\n=== Evaluating Test Case {i+1}/{len(df)} ===")
    print(f"Student: {row['student']} | Query: {str(row['input'])[:80]}...")
    print("-" * 80)

    # Prepare test case
    tools_called = [ToolCall(name=t.strip()) for t in str(row["tools_called"]).split(",") if t.strip()]
    expected_tools = [ToolCall(name=t.strip()) for t in str(row["expected_tools"]).split(",") if t.strip()]

    test_case = LLMTestCase(
        input=str(row["input"]),
        actual_output=str(row["output"]),
        context=[str(row["context"])],
        expected_output=str(row["expected_output"]),
        tools_called=tools_called,
        expected_tools=expected_tools,
    )

    result_row = {
        "TestID": i + 1,
        "Student": row["student"],
        "Input": row["input"],
        "Output": row["output"],
        "Expected_Output": row["expected_output"],
        "Context": row["context"],
        "Tools_Called": row["tools_called"],
        "Expected_Tools": row["expected_tools"],
    }

    # --- 1. Hallucination ---
    try:
        hallucination_metric.measure(test_case)
        result_row["Hallucination_Score"] = hallucination_metric.score
        result_row["Hallucination_Status"] = "PASS" if hallucination_metric.score <= hallucination_metric.threshold else "FAIL"
        print(f"Hallucination → Score: {hallucination_metric.score:.2f} | Status: {result_row['Hallucination_Status']}")
    except Exception as e:
        result_row["Hallucination_Score"] = None
        result_row["Hallucination_Status"] = f"Error: {e}"
        print(f"Hallucination → Error: {e}")

    # --- 2. Tool Correctness ---
    try:
        tool_metric.measure(test_case)
        result_row["ToolCorrectness_Score"] = tool_metric.score
        print(f"ToolCorrectness → Score: {tool_metric.score:.2f} ")
    except Exception as e:
        result_row["ToolCorrectness_Score"] = None
        print(f"ToolCorrectness → Error: {e}")

    # --- 3. Correctness (GEval) ---
    try:
        time.sleep(10)
        correctness_metric.measure(test_case)
        result_row["Correctness_Score"] = correctness_metric.score
        result_row["Correctness_Reason"] = correctness_metric.reason
        # <-- LOGGING ADDED
        print(f"Correctness → Score: {correctness_metric.score:.2f} | Reason: {correctness_metric.reason}")
    except Exception as e:
        result_row["Correctness_Score"] = None
        result_row["Correctness_Reason"] = f"Error: {e}"
        print(f"Correctness → Error: {e}")

    results.append(result_row)

    # Save after each iteration
    results_df = pd.DataFrame(results)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    results_df.to_excel(output_file, index=False)
    print(f"Progress saved → {output_file}")
    time.sleep(15)
