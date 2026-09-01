import pandas as pd
from rules import classify, apply_policy_gateway

df = pd.read_csv("failed_transactions.csv")

# Step 1: base classification, per transaction, in isolation
classified = df["failure_reason"].apply(classify).apply(pd.Series)
df["action"] = classified["action"]
df["channel"] = classified["channel"]

# Step 2: policy gateway — customer-aware overrides (do-not-contact, retry cap)
df = apply_policy_gateway(df)

# Anything the gateway suppressed sends on no channel
df.loc[df["policy_note"] != "", "channel"] = "none"

df.to_csv("classified_transactions.csv", index=False)

print("Action breakdown:")
print(df["action"].value_counts())
print("\nPolicy overrides:")
print(df[df["policy_note"] != ""]["policy_note"].value_counts())
print("\nChannel breakdown:")
print(df["channel"].value_counts())
print("\nSample:")
print(df[["transaction_id", "failure_reason", "action", "channel", "policy_note"]].head(10))