import pandas as pd

from rules import classify, apply_policy_gateway
from audit import create_audit_event, event_exists
from state_machine import TransactionState, transition


df = pd.read_csv("failed_transactions.csv")

# Tracks each transaction's current state, enforced via state_machine.py.
# transition() raises ValueError if an illegal move is attempted, so a bug
# that tried to (say) mark a transaction RECOVERED before it was ever
# CLASSIFIED would crash loudly here instead of silently corrupting the
# audit trail.
current_state = {}


# ============================================================
# STEP 1: FAILED_PAYMENT_RECEIVED (idempotent — duplicates skip ALL
# downstream processing, not just this one event)
# ============================================================

new_rows = []

for _, row in df.iterrows():
    txn_id = row["transaction_id"]

    if event_exists(txn_id, "FAILED_PAYMENT_RECEIVED"):
        create_audit_event(
            transaction_id=txn_id,
            event_type="DUPLICATE_EVENT_IGNORED",
            reason="FAILED_PAYMENT_RECEIVED already recorded for this transaction — ignoring duplicate delivery, no further processing.",
            actor="RECOVERY_PIPELINE",
            correlation_id=f"RECOVERY_{txn_id}",
        )
        continue

    current_state[txn_id] = TransactionState.FAILED
    create_audit_event(
        transaction_id=txn_id,
        event_type="FAILED_PAYMENT_RECEIVED",
        to_state=TransactionState.FAILED.value,
        actor="RECOVERY_PIPELINE",
        correlation_id=f"RECOVERY_{txn_id}",
    )
    new_rows.append(row)

df = pd.DataFrame(new_rows).reset_index(drop=True) if new_rows else df.iloc[0:0]

if df.empty:
    print("No new transactions to process (all were duplicates).")
    import sys
    sys.exit(0)


# ============================================================
# STEP 2: FAILURE_CLASSIFIED + ACTION_PROPOSED
# ============================================================

classified = df["failure_reason"].apply(classify).apply(pd.Series)

df["action"] = classified["action"]
df["channel"] = classified["channel"]


for _, row in df.iterrows():
    txn_id = row["transaction_id"]

    # FAILED -> CLASSIFIED
    prev_state = current_state[txn_id]
    current_state[txn_id] = transition(prev_state, TransactionState.CLASSIFIED)
    create_audit_event(
        transaction_id=txn_id,
        event_type="FAILURE_CLASSIFIED",
        from_state=prev_state.value,
        to_state=current_state[txn_id].value,
        proposed_action=row["action"],
        reason=f"Failure classified as {row['failure_reason']}",
        actor="CLASSIFIER",
        correlation_id=f"RECOVERY_{txn_id}",
    )

    # CLASSIFIED -> ACTION_PROPOSED
    prev_state = current_state[txn_id]
    current_state[txn_id] = transition(prev_state, TransactionState.ACTION_PROPOSED)
    create_audit_event(
        transaction_id=txn_id,
        event_type="ACTION_PROPOSED",
        from_state=prev_state.value,
        to_state=current_state[txn_id].value,
        proposed_action=row["action"],
        reason=f"Proposed recovery action: {row['action']}",
        actor="CLASSIFIER",
        correlation_id=f"RECOVERY_{txn_id}",
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
    txn_id = row["transaction_id"]
    correlation_id = f"RECOVERY_{txn_id}"
    prev_state = current_state[txn_id]

    if row["policy_note"] != "":
        # ACTION_PROPOSED -> POLICY_SUPPRESSED
        current_state[txn_id] = transition(prev_state, TransactionState.POLICY_SUPPRESSED)
        create_audit_event(
            transaction_id=txn_id,
            event_type="POLICY_SUPPRESSED",
            from_state=prev_state.value,
            to_state=current_state[txn_id].value,
            proposed_action=classify(row["failure_reason"])["action"],
            final_action=row["action"],
            policy_note=row["policy_note"],
            reason=row["policy_note"],
            actor="POLICY_GATEWAY",
            correlation_id=correlation_id,
        )

    else:
        # ACTION_PROPOSED -> POLICY_APPROVED
        current_state[txn_id] = transition(prev_state, TransactionState.POLICY_APPROVED)
        create_audit_event(
            transaction_id=txn_id,
            event_type="POLICY_APPROVED",
            from_state=prev_state.value,
            to_state=current_state[txn_id].value,
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