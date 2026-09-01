# Maps each failure reason to an action and channel

RULES = {
    "network_timeout":    {"action": "retry_now",   "channel": "none"},
    "insufficient_funds": {"action": "retry_later",  "channel": "sms"},
    "card_expired":       {"action": "send_nudge",   "channel": "email"},
    "invalid_card":       {"action": "send_nudge",   "channel": "email"},
    "fraud_blocked":      {"action": "mark_lost",    "channel": "none"},
}

def classify(failure_reason: str) -> dict:
    """Returns the action + channel for a given failure reason."""
    return RULES.get(failure_reason, {"action": "mark_lost", "channel": "none"})

# --- Policy gateway: customer-aware safety rails, applied AFTER classify() ---
#
# classify() only looks at a single transaction in isolation. It has no idea
# whether this customer has already been contacted 5 times this week, or
# whether they've opted out entirely. This second pass adds that memory.

MAX_CONTACT_ATTEMPTS = 3  # per customer, across the whole dataset window


def apply_policy_gateway(df):
    """
    Sequential policy pass applied after base classify().

    Walks transactions in chronological order and enforces two rails per
    customer:
      1. do_not_contact suppression  — opted-out customers are never contacted
      2. retry/contact cap           — no customer gets unlimited automated
                                        attempts, even if every individual
                                        transaction looks recoverable

    Only actions that actually reach the customer (send_nudge, retry_later
    via SMS) count toward these rails. retry_now is a silent, no-channel
    system retry — it doesn't tire out or annoy a customer, so it's exempt.

    Returns a copy of df with 'action' overridden where a rail fires, plus a
    new 'policy_note' column explaining why (empty string if no override).
    """
    df = df.sort_values("timestamp").reset_index(drop=True).copy()
    contact_counts = {}
    actions = []
    policy_notes = []

    for _, row in df.iterrows():
        customer = row["customer_name"]
        action = row["action"]
        do_not_contact = bool(row.get("do_not_contact", False))
        note = ""

        customer_facing = action in ("send_nudge", "retry_later")

        if do_not_contact and customer_facing:
            action = "mark_lost"
            note = "suppressed_do_not_contact"

        elif customer_facing:
            count = contact_counts.get(customer, 0)
            if count >= MAX_CONTACT_ATTEMPTS:
                action = "mark_lost"
                note = "suppressed_retry_cap"
            else:
                contact_counts[customer] = count + 1

        actions.append(action)
        policy_notes.append(note)

    df["action"] = actions
    df["policy_note"] = policy_notes
    return df