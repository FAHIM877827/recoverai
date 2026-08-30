import random
import pandas as pd
from datetime import datetime, timedelta

# Reproducibility — same data every run while we're building/debugging
random.seed(42)

# --- Config ---
NUM_RECORDS = 150

FAILURE_REASONS = ["insufficient_funds", "network_timeout", "card_expired", "fraud_blocked", "invalid_card"]
FAILURE_WEIGHTS = [0.35, 0.25, 0.15, 0.08, 0.17]  # must sum to 1.0

CUSTOMER_NAMES = [
    "Priya Sharma", "Rahul Verma", "Ananya Iyer", "Karthik Raj", "Sneha Patel",
    "Arjun Nair", "Divya Menon", "Vikram Singh", "Meera Pillai", "Rohan Gupta",
    "Kavya Reddy", "Aditya Kumar", "Lakshmi Rao", "Sanjay Mehta", "Pooja Desai",
    "Nikhil Joshi", "Anjali Bose", "Suresh Babu", "Deepa Krishnan", "Manoj Tiwari"
]

def generate_transaction(txn_id: int) -> dict:
    failure_reason = random.choices(FAILURE_REASONS, weights=FAILURE_WEIGHTS, k=1)[0]
    amount = round(random.uniform(99, 9999), 2)
    customer_name = random.choice(CUSTOMER_NAMES)

    # Random timestamp within the last 10 days
    days_ago = random.uniform(0, 10)
    timestamp = datetime.now() - timedelta(days=days_ago)

    return {
        "transaction_id": f"TXN{txn_id:04d}",
        "customer_name": customer_name,
        "amount": amount,
        "failure_reason": failure_reason,
        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
    }

def generate_dataset(num_records: int = NUM_RECORDS) -> pd.DataFrame:
    records = [generate_transaction(i + 1) for i in range(num_records)]
    df = pd.DataFrame(records)
    return df

if __name__ == "__main__":
    df = generate_dataset()
    df.to_csv("failed_transactions.csv", index=False)

    print(f"Generated {len(df)} records → failed_transactions.csv\n")
    print("Failure reason distribution:")
    print(df["failure_reason"].value_counts())
    print("\nSample rows:")
    print(df.head())
    print("\nAmount stats:")
    print(df["amount"].describe())