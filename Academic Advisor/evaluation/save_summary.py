import pandas as pd
import os

# === Configuration ===
results_file = "evaluation/Evaluation_Results_New.xlsx"
summary_file = "evaluation/Evaluation_Summary.xlsx"
correctness_threshold = 0.6  # threshold for answer correctness

# === Load results ===
df = pd.read_excel(results_file)

# Ensure 'Category' column exists
if "Category" not in df.columns:
    raise ValueError("The dataset must include a 'Category' column for grouped summaries.")

# --- Hallucination Accuracy (PASS / Total) ---
hallucination_pass = (df["Hallucination_Status"] == "PASS").sum()
total_cases = len(df)
hallucination_score = hallucination_pass / total_cases if total_cases > 0 else None

# --- Tool Correctness ---
if "ToolCorrectness_Score" in df.columns:
    df["ToolCorrectness_Status"] = df["ToolCorrectness_Score"].apply(
        lambda x: "PASS" if pd.notna(x) and x == 1 else "FAIL"
    )
else:
    df["ToolCorrectness_Status"] = None

# --- Answer Correctness ---
if "Correctness_Score" in df.columns:
    df["Correctness_Status"] = df["Correctness_Score"].apply(
        lambda x: "PASS" if pd.notna(x) and x >= correctness_threshold else "FAIL"
    )
else:
    df["Correctness_Status"] = None

# === Overall summary ===
summary = {
    "Metric": [
        "Hallucination Accuracy (PASS / Total)",
        "Tool Correctness (Binary 1 = PASS)",
        f"Answer Correctness (≥ {correctness_threshold} → PASS)",
    ],
    "Total": [
        total_cases,
        total_cases,
        total_cases,
    ],
    "Passed": [
        hallucination_pass,
        (df["ToolCorrectness_Status"] == "PASS").sum(),
        (df["Correctness_Status"] == "PASS").sum(),
    ],
    "Failed": [
        (df["Hallucination_Status"] == "FAIL").sum(),
        (df["ToolCorrectness_Status"] == "FAIL").sum(),
        (df["Correctness_Status"] == "FAIL").sum(),
    ],
    "Pass Rate (%)": [
        round((hallucination_pass / total_cases) * 100, 2) if total_cases > 0 else None,
        round(((df["ToolCorrectness_Status"] == "PASS").sum() / total_cases) * 100, 2)
        if total_cases > 0 else None,
        round(((df["Correctness_Status"] == "PASS").sum() / total_cases) * 100, 2)
        if total_cases > 0 else None,
    ],
}

summary_df = pd.DataFrame(summary)

# === Category-level summary ===
category_summary = (
    df.groupby("Category")
    .apply(
        lambda g: pd.Series({
            "Total": len(g),
            "Hallucination_PASS": (g["Hallucination_Status"] == "PASS").sum(),
            "ToolCorrect_PASS": (g["ToolCorrectness_Status"] == "PASS").sum(),
            "Correctness_PASS": (g["Correctness_Status"] == "PASS").sum(),
            "Hallucination_Rate(%)": round((g["Hallucination_Status"] == "PASS").mean() * 100, 2),
            "ToolCorrect_Rate(%)": round((g["ToolCorrectness_Status"] == "PASS").mean() * 100, 2),
            "Correctness_Rate(%)": round((g["Correctness_Status"] == "PASS").mean() * 100, 2),
        })
    )
    .reset_index()
)

# === Save updated results + both summaries ===
os.makedirs(os.path.dirname(summary_file), exist_ok=True)

with pd.ExcelWriter(summary_file) as writer:
    df.to_excel(writer, sheet_name="Detailed_Results", index=False)
    summary_df.to_excel(writer, sheet_name="Overall_Summary", index=False)
    category_summary.to_excel(writer, sheet_name="Category_Summary", index=False)

print("===  FINAL SUMMARY ===")
print(summary_df.to_string(index=False))
print("\n=== CATEGORY SUMMARY ===")
print(category_summary.to_string(index=False))
print(f"\n Saved summary to {summary_file}")
