"""
Standalone proof-of-concept for the Razorpay Payment Links integration
described in the README's "Production Roadmap" section.

This script does NOT touch the main recovery pipeline. It does not
import from, call, or modify rules.py, policy.py, simulate_outcomes.py,
classify_transactions.py, audit.py, validators.py, state_machine.py,
probabilities.py, or dashboard.py. It exists only to prove that a real
Razorpay Test Mode payment link can be created outside the pipeline,
before any of this is wired into simulate_outcomes.py.

Run directly: python src/razorpay_poc.py
"""

import os
import time
from typing import Final

import requests
from dotenv import load_dotenv

RAZORPAY_PAYMENT_LINKS_URL: Final[str] = "https://api.razorpay.com/v1/payment_links"
TEST_KEY_PREFIX: Final[str] = "rzp_test_"

DEMO_AMOUNT_PAISE: Final[int] = 49900
DEMO_CURRENCY: Final[str] = "INR"
DEMO_DESCRIPTION: Final[str] = "RecoverAI test recovery link"
DEMO_REFERENCE_ID: Final[str] = f"POC-DEMO-{int(time.time())}"

REQUEST_TIMEOUT_SECONDS: Final[int] = 15


def load_credentials() -> tuple[str, str]:
    """Load RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET from .env."""
    load_dotenv()

    key_id = os.getenv("RAZORPAY_KEY_ID", "")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "")

    if not key_id or not key_secret:
        raise ValueError(
            "RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must both be set in .env"
        )

    return key_id, key_secret


def validate_test_mode(key_id: str) -> None:
    """Raise if key_id is not a Razorpay test-mode key."""
    if not key_id.startswith(TEST_KEY_PREFIX):
        raise ValueError(
            f"RAZORPAY_KEY_ID does not start with '{TEST_KEY_PREFIX}' - "
            "refusing to run this PoC against what looks like a live key."
        )


def _extract_razorpay_error_description(exc: Exception) -> str | None:
    """Pull Razorpay's own error description out of a failed HTTP response, if present."""
    response = getattr(exc, "response", None)
    if response is None:
        return None

    try:
        return response.json()["error"]["description"]
    except (ValueError, KeyError, TypeError):
        return None


def create_demo_payment_link(key_id: str, key_secret: str) -> str:
    """Create one test-mode Razorpay Payment Link and return its short_url."""
    payload = {
        "amount": DEMO_AMOUNT_PAISE,
        "currency": DEMO_CURRENCY,
        "description": DEMO_DESCRIPTION,
        "reference_id": DEMO_REFERENCE_ID,
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
    except Exception as exc:
        raise RuntimeError(
            f"Unexpected error while creating the Razorpay payment link: {exc}"
        ) from exc

    return response.json()["short_url"]


if __name__ == "__main__":
    key_id, key_secret = load_credentials()
    validate_test_mode(key_id)
    short_url = create_demo_payment_link(key_id, key_secret)

    print("Razorpay Test Mode Payment Link PoC")
    print("=" * 40)
    print(f"Reference ID: {DEMO_REFERENCE_ID}")
    print(f"Amount:       {DEMO_AMOUNT_PAISE / 100:.2f} {DEMO_CURRENCY}")
    print(f"Payment link: {short_url}")
