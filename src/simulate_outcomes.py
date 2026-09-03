# src/simulate_outcomes.py

import os
import random

import pandas as pd
from dotenv import load_dotenv
from groq import Groq

from probabilities import SUCCESS_PROBABILITY
from validators import validate_message
from audit import create_audit_event, event_exists


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

    "manual_review": (
        "Fraud or risk signals require human judgment, so RecoverAI flags "
        "this transaction for review instead of deciding automatically."
    ),
}


# Overrides the action-based reasoning when the policy gateway fired.
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


# Load environment variables.
load_dotenv()


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


def generate_nudge(
    customer_name,
    amount,
    failure_reason,
    channel,
    recovery_link,
    policy_action,
    do_not_contact,
):
    """
    Generate a customer recovery message using Groq.

    The LLM only writes the message.
    Policy decisions are already made before this function is called.
    """

    fallback = (
        f"Hi {customer_name}, your payment of ₹{amount} didn't go through. "
        f"Please retry: {recovery_link}"
    )

    # Safety: never contact customers who opted out.
    if do_not_contact:
        return None, "blocked_opt_out"

    # Safety: LLM is only allowed for customer-contact actions.
    if policy_action not in ("send_nudge", "retry_later"):
        return None, "blocked_policy"

    try:

        client = Groq(
            api_key=os.getenv("GROQ_API_KEY")
        )

        prompt = build_prompt(
            customer_name,
            amount,
            failure_reason,
            channel,
        )

        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            max_tokens=400,
            temperature=0.7,
            reasoning_effort="low",
        )

        message = response.choices[0].message.content.strip()

        # Replace placeholder with actual recovery link.
        message = message.replace("[LINK]", recovery_link)

    except Exception:

        # If the LLM fails, use deterministic fallback.
        return fallback, "template_fallback"

    # Deterministic validation before accepting the LLM message.
    is_valid, reason = validate_message(
        message,
        channel,
        customer_name,
        amount,
        recovery_link,
        policy_action,
        do_not_contact,
    )

    if not is_valid:
        return fallback, f"validator_rejected:{reason}"

    return message, "llm_generated"


if __name__ == "__main__":

    # ---------------------------------------------------------
    # Load classified transactions
    # ---------------------------------------------------------

    df = pd.read_csv("classified_transactions.csv")

    # ---------------------------------------------------------
    # 1. Simulate recovery outcome
    # ---------------------------------------------------------

    df["recovered"] = df["action"].apply(
        simulate_outcome
    )

    df["recovered_amount"] = df.apply(
        lambda r: r["amount"] if r["recovered"] else 0,
        axis=1,
    )

    # ---------------------------------------------------------
    # 2. Attach reasoning trace
    # ---------------------------------------------------------

    df["reasoning"] = df.apply(
        lambda r: POLICY_REASONING.get(
            r.get("policy_note", ""),
            REASONING.get(r["action"], ""),
        ),
        axis=1,
    )

    # ---------------------------------------------------------
    # 3. Generate recovery messages
    # ---------------------------------------------------------

    def maybe_generate_nudge(row):

        if row["action"] in ["send_nudge", "retry_later"]:

            recovery_link = (
                f"https://recoverai.test/pay/"
                f"{row['transaction_id']}"
            )

            msg, source = generate_nudge(
                row["customer_name"],
                row["amount"],
                row["failure_reason"],
                row["channel"],
                recovery_link,
                row["action"],
                bool(row.get("do_not_contact", False)),
            )

            return pd.Series(
                [msg, source]
            )

        return pd.Series(
            [None, None]
        )

    df[
        ["nudge_message", "message_source"]
    ] = df.apply(
        maybe_generate_nudge,
        axis=1,
    )

    # ---------------------------------------------------------
    # 4. Log recovery outcomes
    # ---------------------------------------------------------
    #
    # Every transaction gets exactly one RECOVERY_OUTCOME event.
    #
    # event_exists() prevents duplicate outcome events if the
    # simulator is run again.

    for _, row in df.iterrows():

        txn_id = row["transaction_id"]

        # Idempotency:
        # Do not create another outcome event for the same transaction.
        if event_exists(
            txn_id,
            "RECOVERY_OUTCOME",
        ):
            continue

        outcome_state = (
            "RECOVERED"
            if row["recovered"]
            else "UNRESOLVED"
        )

        create_audit_event(
            transaction_id=txn_id,
            event_type="RECOVERY_OUTCOME",
            to_state=outcome_state,
            proposed_action=row["action"],
            final_action=row["action"],
            reason=(
                "Payment recovered successfully."
                if row["recovered"]
                else "Recovery attempt did not recover the payment."
            ),
            actor="recoverai_simulator",
            correlation_id=f"RECOVERY_{txn_id}",
        )

    # ---------------------------------------------------------
    # 5. Save final results
    # ---------------------------------------------------------

    df.to_csv(
        "final_transactions.csv",
        index=False,
    )

    # ---------------------------------------------------------
    # 6. Print recovery metrics
    # ---------------------------------------------------------

    total_failed = df["amount"].sum()

    total_recovered = df["recovered_amount"].sum()

    recovery_rate = (
        df["recovered"].mean() * 100
    )

    print(
        f"Total amount at risk: ₹{total_failed:,.2f}"
    )

    print(
        f"Total recovered: ₹{total_recovered:,.2f}"
    )

    print(
        f"Recovery rate: {recovery_rate:.1f}%"
    )

    # ---------------------------------------------------------
    # 7. Print sample messages
    # ---------------------------------------------------------

    print(
        "\nSample nudge messages generated:"
    )

    sample = df[
        df["nudge_message"].notna()
    ][
        [
            "customer_name",
            "channel",
            "nudge_message",
            "message_source",
        ]
    ].head(3)

    print(
        sample.to_string(index=False)
    )