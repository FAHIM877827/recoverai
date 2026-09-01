# RecoverAI Policy Matrix

## Purpose

This document defines the deterministic recovery policies used by
RecoverAI. Safety-critical recovery decisions are made by rules and
policy controls, not by the LLM.

| Failure Reason | Proposed Action | Customer Contact | Retry Cap | Terminal Condition |
|---|---|---|---:|---|
| `network_timeout` | `RETRY_NOW` | No, by default | 2 | Mark unresolved after 2 failed recovery retries |
| `bank_unavailable` | `RETRY_NOW` | No, by default | 2 | Mark unresolved after 2 failed recovery retries |
| `insufficient_funds` | `RETRY_LATER` | One optional nudge if consent exists | 1 | Mark unresolved if delayed retry fails |
| `card_expired` | `SEND_NUDGE` | Yes, if consent exists | 0 direct retries | Mark unresolved if no response or recovery link expires |
| `invalid_card` | `SEND_NUDGE` | Yes, if consent exists | 0 direct retries | Mark unresolved if no response or recovery link expires |
| `fraud_blocked` | `MANUAL_REVIEW` | No | 0 | Requires a human decision |
| `customer_cancelled` | `MARK_LOST` | No | 0 | Immediate terminal state |

> A customer nudge may include a fresh payment link, but it is not a direct retry of the failed payment method. The customer voluntarily initiates a new payment attempt.

## Global Safety Limits

- **Retry cap:** A transaction may never exceed 2 recovery retry attempts. Failure-specific policies may apply a lower cap; for example, `insufficient_funds` allows only 1 delayed retry.
- **Nudge cap:** Maximum 1 nudge per failed transaction.
- **Customer contact cap:** Maximum 3 recovery messages per customer in 30 days.
- **Cooldown:** No second recovery action within 24 simulated hours.
- **Opt-out:** Blocks all LLM generation, recovery-link creation, and customer contact.
- **Fraud/risk failure:** Blocks all automatic recovery actions and routes the transaction to `MANUAL_REVIEW`.
- **Idempotency:** A source event ID can be processed only once. Duplicate ingestion or webhook events are recorded as `DUPLICATE_EVENT_IGNORED` and cannot create another retry, nudge, payment link, or recovery entry.

## Design Principle

The LLM is responsible only for generating customer-facing wording after
the recovery policy has approved a nudge.

The LLM does **not** decide:

- Whether a payment should be retried.
- Whether a customer should be contacted.
- Whether a transaction is safe to recover.
- Whether an opt-out should be ignored.
- Whether retry or contact limits can be exceeded.
- Whether a payment should be marked recovered.

These decisions are controlled deterministically by RecoverAI's policy layer.