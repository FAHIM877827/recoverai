from copy import deepcopy

POLICY_VERSION = "v1.0"

DEFAULT_POLICY = {
    "action": "manual_review",
    "max_retries": 0,
    "max_nudges": 0,
    "contact_allowed": False,
    "reason": (
        "The failure reason is unknown or unsupported. "
        "RecoverAI will not take an automated recovery action."
    ),
}

POLICIES = {
    "network_timeout": {
        "action": "retry_now",
        "max_retries": 2,
        "max_nudges": 0,
        "contact_allowed": False,
        "reason": (
            "This appears to be a transient technical failure, so a bounded "
            "immediate retry may recover the payment without contacting the customer."
        ),
    },

    "bank_unavailable": {
        "action": "retry_now",
        "max_retries": 2,
        "max_nudges": 0,
        "contact_allowed": False,
        "reason": (
            "The bank appears temporarily unavailable, so a bounded retry may "
            "recover the payment without customer action."
        ),
    },

    "insufficient_funds": {
        "action": "retry_later",
        "max_retries": 1,
        "max_nudges": 1,
        "contact_allowed": True,
        "reason": (
            "A delayed retry may succeed after funds become available. "
            "One customer nudge is allowed only when consent and contact limits permit it."
        ),
    },

    "card_expired": {
        "action": "send_nudge",
        "max_retries": 0,
        "max_nudges": 1,
        "contact_allowed": True,
        "reason": (
            "The payment method requires customer action. Directly retrying the "
            "same expired card is not allowed; one recovery nudge may be sent."
        ),
    },

    "invalid_card": {
        "action": "send_nudge",
        "max_retries": 0,
        "max_nudges": 1,
        "contact_allowed": True,
        "reason": (
            "The payment method requires customer action. Direct retries are not "
            "allowed; one recovery nudge may be sent if contact is permitted."
        ),
    },

    "fraud_blocked": {
        "action": "manual_review",
        "max_retries": 0,
        "max_nudges": 0,
        "contact_allowed": False,
        "reason": (
            "Fraud or risk-related failures are never automatically retried "
            "or used for customer recovery messaging."
        ),
    },

    "customer_cancelled": {
        "action": "mark_lost",
        "max_retries": 0,
        "max_nudges": 0,
        "contact_allowed": False,
        "reason": (
            "The customer cancelled the payment. RecoverAI does not initiate "
            "automatic retries or customer contact for this failure type."
        ),
    },
}


def get_policy(failure_reason: str) -> dict:
    """
    Return a copy of the configured policy for a normalized failure reason.
    Unknown values always get the safest possible policy.
    """
    normalized_reason = (failure_reason or "").strip().lower()
    policy = POLICIES.get(normalized_reason, DEFAULT_POLICY)

    return {
        **deepcopy(policy),
        "failure_reason": normalized_reason or "unknown",
        "policy_version": POLICY_VERSION,
    }