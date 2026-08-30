import pandas as pd
from rules import classify

df = pd.read_csv("failed_transactions.csv")

# Apply classify() to every row, expand result into two new columns
classified = df["failure_reason"].apply(classify).apply(pd.Series)
df["action"] = classified["action"]
df["channel"] = classified["channel"]

df.to_csv("classified_transactions.csv", index=False)

print("Action breakdown:")
print(df["action"].value_counts())
print("\nChannel breakdown:")
print(df["channel"].value_counts())
print("\nSample:")
print(df[["transaction_id", "failure_reason", "action", "channel"]].head(10))