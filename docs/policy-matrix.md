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

> **Enforcement status:** The `Proposed Action` column is enforced today (see below). The `Retry Cap` and `Customer Contact` columns describe intended per-failure-reason design values (`policy.py`'s `max_retries`/`max_nudges`/`contact_allowed` fields) — see "Planned / Not Yet Enforced" below for which of these are not actually consulted by any code yet.

## Enforcement Status

This section reflects what `apply_policy_gateway()` (`rules.py`) and the
rest of the classification pipeline actually do today, verified line by
line against the code — not what the design intends.

### Enforced Today

- **Failure-reason -> action/channel routing.** Each `failure_reason` maps to a fixed `action` and `channel`. Implemented in `policy.py:16-93` (`POLICIES` dict) and consumed by `classify()` at `rules.py:8-28`.
- **Fraud/risk failures never auto-retried or messaged; routed to `MANUAL_REVIEW`.** Implemented via the `fraud_blocked` entry at `policy.py:72-81`, consumed by `classify()` at `rules.py:8-28`.
- **Opt-out (`do_not_contact`) blocks customer-facing actions.** A `do_not_contact` customer who would otherwise get `send_nudge`/`retry_later` is forced to `mark_lost` instead. Implemented at `rules.py:71-73`, inside `apply_policy_gateway()`.
- **Customer contact cap of 3.** A customer cannot receive more than `MAX_CONTACT_ATTEMPTS = 3` customer-facing actions (`send_nudge`/`retry_later`) before being forced to `mark_lost`. Implemented at `rules.py:37` (constant) and `rules.py:75-82` (enforcement) inside `apply_policy_gateway()`. **Caveat:** this is a whole-run/whole-dataset cap, not a rolling 30-day window — see below.
- **Idempotency / duplicate event suppression.** A given `(transaction_id, event_type)` pair is processed at most once; duplicates are logged as `DUPLICATE_EVENT_IGNORED` and skip all further processing. Implemented in `audit.py:29-43` (`event_exists()`) and consumed in `classify_transactions.py:28-36` — **note this lives outside `policy.py`/`rules.py` entirely**, not inside `apply_policy_gateway()`.

### Planned / Not Yet Enforced

- **Per-failure-reason retry cap (`max_retries`).** `policy.py` defines `max_retries` for every failure reason (e.g. `2` for `network_timeout`/`bank_unavailable` at `policy.py:19,30`, `1` for `insufficient_funds` at `policy.py:41`). This value is never read: `classify()` (`rules.py:8-28`) does not include it in its returned dict, and `apply_policy_gateway()` has no retry-counting or retry-loop logic. No code anywhere executes or limits repeated retry attempts — the pipeline gives every transaction exactly one simulated outcome.
- **Per-failure-reason nudge cap (`max_nudges`).** Same story as retry cap: defined per failure reason in `policy.py` (e.g. `policy.py:42,53,64`) but dropped by `classify()` and never consulted by `apply_policy_gateway()`.
- **`contact_allowed` flag.** Defined per failure reason in `policy.py` (e.g. `policy.py:21,43,54,65`) but never read anywhere. `apply_policy_gateway()` derives whether an action is customer-facing purely from the action string (`rules.py:69`), not from this flag.
- **30-day contact window.** The contact cap enforced at `rules.py:75-82` has no time dimension — `contact_counts` accumulates for the lifetime of a single pipeline run with no date/window check. There is no rolling-30-day enforcement anywhere in `policy.py` or `rules.py`.
- **24-hour cooldown between recovery actions.** No cooldown or timestamp-diff logic exists in either file.
- **"Mark unresolved after N failed recovery retries."** Since no retry loop exists (see retry cap above), this terminal condition is not literally implemented — outcomes come from a single probability draw per transaction, not from counting failed attempts.

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
