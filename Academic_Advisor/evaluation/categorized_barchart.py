import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# === Data ===
data = {
    "Category": [
        "Conflict detection", "Course information", "Credit-related",
        "Eligibility checks", "Other", "Schedule generation", "Timetable creation"
    ],
    "No Hallucination Rate (%)": [100, 92.31, 60, 80, 90, 100, 100],
    "Tool Correctness Rate (%)": [75, 100, 80, 80, 100, 100, 100],
    "Answer Correctness Rate (%)": [100, 100, 60, 80, 80, 100, 100],
}

df = pd.DataFrame(data)

# === Plot setup ===
categories = df["Category"]
x = np.arange(len(categories))
width = 0.25

plt.figure(figsize=(10, 6))
plt.bar(x - width, df["No Hallucination Rate (%)"], width, label="No Hallucination", color="#1f77b4")
plt.bar(x, df["Tool Correctness Rate (%)"], width, label="Tool Correctness", color="#ff7f0e")
plt.bar(x + width, df["Answer Correctness Rate (%)"], width, label="Answer Correctness", color="#2ca02c")

# === Labels and formatting ===
plt.xlabel("Category")
plt.ylabel("Performance Rate (%)")
plt.title("Category-wise Performance Metrics of the Academic Advisor Chatbot")
plt.xticks(x, categories, rotation=30, ha="right")
plt.ylim(0, 110)
plt.legend()
plt.grid(axis="y", linestyle="--", alpha=0.7)
plt.tight_layout()

# === Save chart ===
output_chart = "evaluation/category_performance_chart.png"
os.makedirs(os.path.dirname(output_chart), exist_ok=True)
plt.savefig(output_chart, dpi=300)
plt.show()

print(f" Chart saved to: {output_chart}")
