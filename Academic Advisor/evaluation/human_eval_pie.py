import pandas as pd
import matplotlib.pyplot as plt
import os

# === Configuration ===
input_file = "evaluation/human_eval.xlsx"  # your Excel file
score_column = "Relevance"  # column name in the Excel file
output_chart = "evaluation/relevance_score_distribution_pie.png"

# === Load Excel ===
df = pd.read_excel(input_file)

# === Check if column exists ===
if score_column not in df.columns:
    raise ValueError(f"Column '{score_column}' not found in the file.")

# === Count occurrences of each score ===
score_counts = df[score_column].value_counts().sort_index()

print("📊 Relevance Score Distribution:")
print(score_counts)

# === Define custom colors for 1–5 ===
custom_colors = {
    1: "#1f77b4",  # blue
    2: "#ff7f0e",  # orange
    3: "#2ca02c",  # green
    4: "#d62728",  # red
    5: "#9467bd"   # purple
}

# Match colors with existing scores
colors = [custom_colors.get(int(score), "#cccccc") for score in score_counts.index]

# === Plot pie chart ===
plt.figure(figsize=(6, 6))
plt.pie(
    score_counts,
    labels=[f"{int(score)}" for score in score_counts.index],
    autopct='%1.1f%%',
    startangle=90,
    colors=colors,
    wedgeprops={'edgecolor': 'white'}
)
plt.title("Distribution of Human Relevance Scores (1–5)", fontsize=12)
plt.tight_layout()

# === Save chart ===
os.makedirs(os.path.dirname(output_chart), exist_ok=True)
plt.savefig(output_chart, dpi=300)
plt.show()

print(f"\n Pie chart saved to: {output_chart}")
