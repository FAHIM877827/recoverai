from enum import Enum


class TransactionState(Enum):
    FAILED = "FAILED"
    CLASSIFIED = "CLASSIFIED"
    ACTION_PROPOSED = "ACTION_PROPOSED"

    POLICY_APPROVED = "POLICY_APPROVED"
    POLICY_SUPPRESSED = "POLICY_SUPPRESSED"

    RETRY_PENDING = "RETRY_PENDING"
    RETRY_ATTEMPTED = "RETRY_ATTEMPTED"

    NUDGE_PENDING = "NUDGE_PENDING"
    LLM_MESSAGE_GENERATED = "LLM_MESSAGE_GENERATED"
    LLM_MESSAGE_VALIDATED = "LLM_MESSAGE_VALIDATED"
    LLM_FALLBACK_USED = "LLM_FALLBACK_USED"

    RECOVERY_LINK_CREATED = "RECOVERY_LINK_CREATED"
    RECOVERY_PAYMENT_PENDING = "RECOVERY_PAYMENT_PENDING"

    MANUAL_REVIEW = "MANUAL_REVIEW"
    MARKED_LOST = "MARKED_LOST"
    RECOVERED = "RECOVERED"
    UNRESOLVED = "UNRESOLVED"


ALLOWED_TRANSITIONS = {
    TransactionState.FAILED: {
        TransactionState.CLASSIFIED,
    },

    TransactionState.CLASSIFIED: {
        TransactionState.ACTION_PROPOSED,
    },

    TransactionState.ACTION_PROPOSED: {
        TransactionState.POLICY_APPROVED,
        TransactionState.POLICY_SUPPRESSED,
    },

    TransactionState.POLICY_APPROVED: {
        TransactionState.RETRY_PENDING,
        TransactionState.NUDGE_PENDING,
        TransactionState.MARKED_LOST,
        TransactionState.MANUAL_REVIEW,
    },

    TransactionState.POLICY_SUPPRESSED: {
        TransactionState.UNRESOLVED,
        TransactionState.MARKED_LOST,
        TransactionState.MANUAL_REVIEW,
    },

    TransactionState.RETRY_PENDING: {
        TransactionState.RETRY_ATTEMPTED,
    },

    TransactionState.RETRY_ATTEMPTED: {
        TransactionState.RECOVERED,
        TransactionState.UNRESOLVED,
        TransactionState.RETRY_PENDING,
    },

    TransactionState.NUDGE_PENDING: {
        TransactionState.LLM_MESSAGE_GENERATED,
        TransactionState.LLM_FALLBACK_USED,
        TransactionState.UNRESOLVED,
    },

    TransactionState.LLM_MESSAGE_GENERATED: {
        TransactionState.LLM_MESSAGE_VALIDATED,
        TransactionState.LLM_FALLBACK_USED,
        TransactionState.UNRESOLVED,
    },

    TransactionState.LLM_MESSAGE_VALIDATED: {
        TransactionState.RECOVERY_LINK_CREATED,
        TransactionState.UNRESOLVED,
    },

    TransactionState.LLM_FALLBACK_USED: {
        TransactionState.RECOVERY_LINK_CREATED,
        TransactionState.UNRESOLVED,
    },

    TransactionState.RECOVERY_LINK_CREATED: {
        TransactionState.RECOVERY_PAYMENT_PENDING,
        TransactionState.UNRESOLVED,
    },

    TransactionState.RECOVERY_PAYMENT_PENDING: {
        TransactionState.RECOVERED,
        TransactionState.UNRESOLVED,
    },

    TransactionState.MANUAL_REVIEW: {
        TransactionState.RECOVERED,
        TransactionState.MARKED_LOST,
        TransactionState.UNRESOLVED,
    },

    TransactionState.MARKED_LOST: set(),
    TransactionState.RECOVERED: set(),
    TransactionState.UNRESOLVED: set(),
}


def validate_transition(
    current_state: TransactionState,
    next_state: TransactionState,
) -> bool:
    """
    Return True only when the requested state transition is explicitly allowed.
    """
    return next_state in ALLOWED_TRANSITIONS.get(current_state, set())


def transition(
    current_state: TransactionState,
    next_state: TransactionState,
) -> TransactionState:
    """
    Return the next state if valid; otherwise raise a clear workflow error.
    """
    if not validate_transition(current_state, next_state):
        raise ValueError(
            f"Invalid state transition: "
            f"{current_state.value} -> {next_state.value}"
        )

    return next_state