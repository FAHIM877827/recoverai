# src/simulate_outcomes.py
import pandas as pd
import random
from probabilities import SUCCESS_PROBABILITY

random.seed(42)


def simulate_outcome(action: str) -> bool:
    prob = SUCCESS_PROBABILITY.get(action, 0.0)
    return random.random() < prob

REASONING = {
    "retry_now": (
        "Network timeouts are often temporary, so an immediate retry "
        "can recover the payment without customer intervention."
    ),

    "retry_later": (
        "Insufficient funds may resolve after 24-48 hours, so waiting "
        "before retrying gives the customer time to add funds."
    ),

    "send_nudge": (
        "This payment requires customer action, so sending a personalized "
        "message is more effective than automatically retrying."
    ),

    "mark_lost": (
        "This transaction is blocked for security reasons, so RecoverAI "
        "does not retry or contact the customer automatically."
    ),
}
# Overrides the action-based reasoning above when the policy gateway fired.
POLICY_REASONING = {
    "suppressed_do_not_contact": (
        "This customer has opted out of contact, so RecoverAI marks the "
        "transaction as lost instead of reaching out."
    ),
    "suppressed_retry_cap": (
        "This customer has already reached the maximum number of automated "
        "contact attempts, so RecoverAI stops instead of retrying indefinitely."
    ),
}

import os
from dotenv import load_dotenv
from groq import Groq
from validators import validate_message

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def build_prompt(customer_name, amount, failure_reason, channel):
    if channel == "sms":
        return (
            f"Write an SMS under 150 characters for a failed payment recovery. "
            f"Customer: {customer_name}, Amount: ₹{amount}, Reason: {failure_reason}. "
            f"Tone: friendly, urgent but not pushy. Include a retry link placeholder [LINK]. "
            f"Return ONLY the message text, nothing else."
        )
    else:
        return (
            f"Write a short recovery email (under 80 words) for a failed payment. "
            f"Customer: {customer_name}, Amount: ₹{amount}, Reason: {failure_reason}. "
            f"Include: greeting, what happened, one clear action, a retry link placeholder [LINK]. "
            f"Tone: professional, helpful, non-pushy. "
            f"Return ONLY the email body text, nothing else."
        )

def generate_nudge(customer_name, amount, failure_reason, channel):
    fallback = f"Hi {customer_name}, your payment of ₹{amount} didn't go through. Please retry: [LINK]"

    try:
        prompt = build_prompt(customer_name, amount, failure_reason, channel)
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.7,
            reasoning_effort="low",
        )
        message = response.choices[0].message.content.strip()
    except Exception:
        return fallback, "template_fallback"

    # Guardrail: never let an unvalidated LLM message reach a customer.
    is_valid, reason = validate_message(message, channel)
    if not is_valid:
        return fallback, f"validator_rejected:{reason}"

    return message, "llm_generated"


if __name__ == "__main__":
    df = pd.read_csv("classified_transactions.csv")

    # Simulate outcome for every transaction
    df["recovered"] = df["action"].apply(simulate_outcome)
    df["recovered_amount"] = df.apply(
        lambda r: r["amount"] if r["recovered"] else 0, axis=1
    )

    # Attach reasoning trace
    df["reasoning"] = df.apply(
    lambda r: POLICY_REASONING.get(
        r.get("policy_note", ""),
        REASONING.get(r["action"], "")
    ),
    axis=1,
)

    # Generate nudge messages only for rows that need one
    def maybe_generate_nudge(row):
        if row["action"] in ["send_nudge", "retry_later"]:
            msg, source = generate_nudge(
                row["customer_name"], row["amount"], row["failure_reason"], row["channel"]
            )
            return pd.Series([msg, source])
        return pd.Series([None, None])

    df[["nudge_message", "message_source"]] = df.apply(maybe_generate_nudge, axis=1)

    df.to_csv("final_transactions.csv", index=False)

    total_failed = df["amount"].sum()
    total_recovered = df["recovered_amount"].sum()
    recovery_rate = df["recovered"].mean() * 100

    print(f"Total amount at risk: ₹{total_failed:,.2f}")
    print(f"Total recovered: ₹{total_recovered:,.2f}")
    print(f"Recovery rate: {recovery_rate:.1f}%")
    print(f"\nSample nudge messages generated:")
    sample = df[df["nudge_message"].notna()][["customer_name", "channel", "nudge_message", "message_source"]].head(3)
    print(sample.to_string())