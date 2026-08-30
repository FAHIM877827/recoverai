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