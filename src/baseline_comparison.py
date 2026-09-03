import pandas as pd
from probabilities import NAIVE_SUCCESS_PROBABILITY
import random

random.seed(42)

# Naive baseline: retry everything once, immediately, no smart routing


def simulate_naive_outcome(failure_reason: str) -> bool:
    prob = NAIVE_SUCCESS_PROBABILITY.get(failure_reason, 0.0)
    return random.random() < prob

if __name__ == "__main__":
    df = pd.read_csv("final_transactions.csv")

    # Run naive simulation on the same transactions
    df["naive_recovered"] = df["failure_reason"].apply(simulate_naive_outcome)
    df["naive_recovered_amount"] = df.apply(
        lambda r: r["amount"] if r["naive_recovered"] else 0, axis=1
    )

    total_failed = df["amount"].sum()

    naive_recovered = df["naive_recovered_amount"].sum()
    naive_rate = df["naive_recovered"].mean() * 100

    agent_recovered = df["recovered_amount"].sum()
    agent_rate = df["recovered"].mean() * 100

    lift_amount = agent_recovered - naive_recovered
    lift_rate = agent_rate - naive_rate

    print("=" * 50)
    print("BASELINE vs RECOVERAI COMPARISON")
    print("=" * 50)
    print(f"Total amount at risk:       ₹{total_failed:,.2f}")
    print(f"\nNaive baseline (retry-all-once):")
    print(f"  Recovered:  ₹{naive_recovered:,.2f}  ({naive_rate:.1f}%)")
    print(f"\nRecoverAI (smart classification + nudges):")
    print(f"  Recovered:  ₹{agent_recovered:,.2f}  ({agent_rate:.1f}%)")
    print(f"\n>>> Additional revenue recovered: ₹{lift_amount:,.2f} (+{lift_rate:.1f} percentage points)")
    print("=" * 50)

    df.to_csv("final_transactions_with_baseline.csv", index=False)