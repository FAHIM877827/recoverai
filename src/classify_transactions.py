import pandas as pd

from rules import classify, apply_policy_gateway
from audit import create_audit_event


df = pd.read_csv("failed_transactions.csv")


# ============================================================
# STEP 1: FAILED_PAYMENT_RECEIVED
# ============================================================

for _, row in df.iterrows():
    create_audit_event(
        transaction_id=row["transaction_id"],
        event_type="FAILED_PAYMENT_RECEIVED",
        actor="RECOVERY_PIPELINE",
        correlation_id=f"RECOVERY_{row['transaction_id']}",
    )


# ============================================================
# STEP 2: FAILURE_CLASSIFIED + ACTION_PROPOSED
# ============================================================

classified = df["failure_reason"].apply(classify).apply(pd.Series)

df["action"] = classified["action"]
df["channel"] = classified["channel"]


for _, row in df.iterrows():

    # Failure classified
    create_audit_event(
        transaction_id=row["transaction_id"],
        event_type="FAILURE_CLASSIFIED",
        proposed_action=row["action"],
        reason=f"Failure classified as {row['failure_reason']}",
        actor="CLASSIFIER",
        correlation_id=f"RECOVERY_{row['transaction_id']}",
    )

    # Action proposed
    create_audit_event(
        transaction_id=row["transaction_id"],
        event_type="ACTION_PROPOSED",
        proposed_action=row["action"],
        reason=f"Proposed recovery action: {row['action']}",
        actor="CLASSIFIER",
        correlation_id=f"RECOVERY_{row['transaction_id']}",
    )


# ============================================================
# STEP 3: POLICY GATEWAY
# ============================================================

df = apply_policy_gateway(df)


# Suppressed transactions should not have a customer channel
df.loc[df["policy_note"] != "", "channel"] = "none"


# ============================================================
# STEP 4: POLICY_APPROVED / POLICY_SUPPRESSED
# ============================================================

for _, row in df.iterrows():

    correlation_id = f"RECOVERY_{row['transaction_id']}"

    if row["policy_note"] != "":
        # Policy blocked the proposed action
        create_audit_event(
            transaction_id=row["transaction_id"],
            event_type="POLICY_SUPPRESSED",
            proposed_action=classify(row["failure_reason"])["action"],
            final_action=row["action"],
            policy_note=row["policy_note"],
            reason=row["policy_note"],
            actor="POLICY_GATEWAY",
            correlation_id=correlation_id,
        )

    else:
        # Policy allowed the proposed action
        create_audit_event(
            transaction_id=row["transaction_id"],
            event_type="POLICY_APPROVED",
            proposed_action=row["action"],
            final_action=row["action"],
            reason="Recovery action passed policy checks.",
            actor="POLICY_GATEWAY",
            correlation_id=correlation_id,
        )


# ============================================================
# SAVE CLASSIFIED DATA
# ============================================================

df.to_csv("classified_transactions.csv", index=False)


# ============================================================
# OUTPUT
# ============================================================

print("Action breakdown:")
print(df["action"].value_counts())

print("\nPolicy overrides:")
print(df[df["policy_note"] != ""]["policy_note"].value_counts())

print("\nChannel breakdown:")
print(df["channel"].value_counts())

print("\nSample:")
print(
    df[
        [
            "transaction_id",
            "failure_reason",
            "action",
            "channel",
            "policy_note",
        ]
    ].head(10)
)