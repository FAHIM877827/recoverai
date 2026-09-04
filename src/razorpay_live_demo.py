"""
Minimal live-demo helper for the Razorpay Test Mode Payment Links flow
shown in the dashboard's "Live Razorpay Test Recovery" section.

This is a scaffold, not a webhook receiver: status updates only happen
when check_and_update_status() is called explicitly (e.g. from the
dashboard's "Refresh Payment Status" button), never automatically.

Reuses load_credentials()/validate_test_mode() from razorpay_poc.py
rather than duplicating them. Audit events are logged through the
existing audit.py API (create_audit_event) without modifying its
schema: the Razorpay payment_link_id is stored in the audit row's
"reason" field, the short_url in "final_action", and the current
Razorpay status in "to_state".

This file is independent of the 150-transaction simulation pipeline
(rules.py, policy.py, simulate_outcomes.py, classify_transactions.py,
state_machine.py, validators.py, probabilities.py). It is read by
dashboard.py only for the separate "Live Razorpay Test Recovery"
section; it does not feed into any simulated-batch metric.
"""

import os
import csv
import time
from typing import Final

import requests

from audit import AUDIT_FILE, create_audit_event
from razorpay_poc import (
    RAZORPAY_PAYMENT_LINKS_URL,
    REQUEST_TIMEOUT_SECONDS,
    load_credentials,
    validate_test_mode,
    _extract_razorpay_error_description,
)

LINK_CREATED_EVENT: Final[str] = "LIVE_RAZORPAY_DEMO_LINK_CREATED"
STATUS_CHECKED_EVENT: Final[str] = "LIVE_RAZORPAY_DEMO_STATUS_CHECKED"

LIVE_DEMO_AMOUNT_PAISE: Final[int] = 49900
LIVE_DEMO_CURRENCY: Final[str] = "INR"
LIVE_DEMO_DESCRIPTION: Final[str] = "RecoverAI live test recovery link"


def new_demo_transaction_id() -> str:
    """Generate a fresh, collision-free transaction_id for a live demo run."""
    return f"LIVE-DEMO-{int(time.time())}"


def get_latest_audit_event(transaction_id: str, event_type: str) -> dict | None:
    """Return the most recent audit row for this transaction_id/event_type, or None."""
    if not os.path.exists(AUDIT_FILE):
        return None

    latest = None
    with open(AUDIT_FILE, "r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row["transaction_id"] == transaction_id and row["event_type"] == event_type:
                latest = row

    return latest


def create_live_demo_link(transaction_id: str) -> tuple[str, str]:
    """Create one real Razorpay Test Mode payment link and audit-log it. Returns (payment_link_id, short_url)."""
    key_id, key_secret = load_credentials()
    validate_test_mode(key_id)

    payload = {
        "amount": LIVE_DEMO_AMOUNT_PAISE,
        "currency": LIVE_DEMO_CURRENCY,
        "description": LIVE_DEMO_DESCRIPTION,
        "reference_id": transaction_id,
    }

    try:
        response = requests.post(
            RAZORPAY_PAYMENT_LINKS_URL,
            auth=(key_id, key_secret),
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        detail = _extract_razorpay_error_description(exc)
        raise RuntimeError(
            f"Razorpay Payment Links API call failed: {detail or exc}"
        ) from exc

    body = response.json()
    payment_link_id = body["id"]
    short_url = body["short_url"]
    status = body["status"]

    create_audit_event(
        transaction_id=transaction_id,
        event_type=LINK_CREATED_EVENT,
        to_state=status,
        reason=payment_link_id,
        final_action=short_url,
        actor="razorpay_live_demo",
        correlation_id=f"LIVE_DEMO_{transaction_id}",
    )

    return payment_link_id, short_url


def check_and_update_status(transaction_id: str) -> str:
    """
    Re-check the live Razorpay status for transaction_id's payment link and
    log a fresh LIVE_RAZORPAY_DEMO_STATUS_CHECKED audit event. Returns the
    current status string (e.g. "created", "paid", "expired").

    No idempotency guard here on purpose: re-checking status is meant to be
    repeatable, unlike the batch pipeline's one-shot events.
    """
    key_id, key_secret = load_credentials()
    validate_test_mode(key_id)

    link_created_event = get_latest_audit_event(transaction_id, LINK_CREATED_EVENT)
    if link_created_event is None:
        raise ValueError(
            f"No {LINK_CREATED_EVENT} audit event found for transaction_id="
            f"{transaction_id!r}. Create a payment link first."
        )
    payment_link_id = link_created_event["reason"]

    try:
        response = requests.get(
            f"{RAZORPAY_PAYMENT_LINKS_URL}/{payment_link_id}",
            auth=(key_id, key_secret),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        detail = _extract_razorpay_error_description(exc)
        raise RuntimeError(
            f"Razorpay payment link status check failed: {detail or exc}"
        ) from exc

    status = response.json()["status"]

    create_audit_event(
        transaction_id=transaction_id,
        event_type=STATUS_CHECKED_EVENT,
        to_state=status,
        reason=payment_link_id,
        actor="razorpay_live_demo",
        correlation_id=f"LIVE_DEMO_{transaction_id}",
    )

    return status


if __name__ == "__main__":
    demo_transaction_id = new_demo_transaction_id()
    payment_link_id, short_url = create_live_demo_link(demo_transaction_id)
    initial_status = check_and_update_status(demo_transaction_id)

    print("Razorpay Live Test Recovery Demo")
    print("=" * 40)
    print(f"Transaction ID: {demo_transaction_id}")
    print(f"Payment link:   {short_url}")
    print(f"Status:         {initial_status}")
    print()
    print("Pay this link with a Razorpay test card, then re-check with:")
    print(
        f'  python -c "from razorpay_live_demo import check_and_update_status; '
        f'print(check_and_update_status({demo_transaction_id!r}))"'
    )
