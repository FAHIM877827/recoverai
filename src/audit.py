import csv
import os
from datetime import datetime, timezone


POLICY_VERSION = "v1.0"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
AUDIT_FILE = os.path.join(DATA_DIR, "audit_events.csv")

AUDIT_FIELDS = [
    "audit_id",
    "transaction_id",
    "event_type",
    "timestamp",
    "from_state",
    "to_state",
    "proposed_action",
    "final_action",
    "policy_note",
    "reason",
    "policy_version",
    "actor",
    "correlation_id",
]


def create_audit_event(
    transaction_id,
    event_type,
    from_state="",
    to_state="",
    proposed_action="",
    final_action="",
    policy_note="",
    reason="",
    actor="SYSTEM",
    correlation_id="",
):
    """
    Create one append-only audit event for a transaction.
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    now = datetime.now(timezone.utc)

    event = {
        "audit_id": f"AUD_{now.strftime('%Y%m%d%H%M%S%f')}",
        "transaction_id": transaction_id,
        "event_type": event_type,
        "timestamp": now.isoformat(),
        "from_state": from_state,
        "to_state": to_state,
        "proposed_action": proposed_action,
        "final_action": final_action,
        "policy_note": policy_note,
        "reason": reason,
        "policy_version": POLICY_VERSION,
        "actor": actor,
        "correlation_id": correlation_id or f"RECOVERY_{transaction_id}",
    }

    file_exists = os.path.exists(AUDIT_FILE)

    with open(AUDIT_FILE, "a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=AUDIT_FIELDS)

        if not file_exists:
            writer.writeheader()

        writer.writerow(event)

    return event
    