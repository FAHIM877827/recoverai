# Recovery probability assumptions used by RecoverAI.
#
# These are simulation assumptions, NOT measured Razorpay production data.
# They are chosen conservatively based on published payment-recovery
# and soft-decline behavior benchmarks.

SUCCESS_PROBABILITY = {
    "retry_now": 0.65,
    "retry_later": 0.40,
    "send_nudge": 0.25,
    "mark_lost": 0.0,
}

# Naive baseline: retry every failed payment once immediately.
# It does not distinguish between failure types.

NAIVE_SUCCESS_PROBABILITY = {
    "network_timeout": 0.65,
    "insufficient_funds": 0.15,
    "card_expired": 0.00,
    "invalid_card": 0.00,
    "fraud_blocked": 0.00,
}