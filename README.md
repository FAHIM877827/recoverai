# RecoverAI

## AI-Powered Failed Payment Recovery Agent

**Razorpay AI Buildathon 2026 — Track 03: AI Revenue Recovery**

RecoverAI identifies why a payment failed, applies a deterministic recovery policy, validates safety before contacting a customer, personalizes communication only where generative AI adds value, and measures recovered revenue against a naive retry baseline. A real Razorpay Test Mode execution path proves the design works beyond simulation.

## Headline Result

| Metric | Naive Baseline | RecoverAI |
|---|---:|---:|
| Total at risk | ₹7,51,199.28 | ₹7,51,199.28 |
| Recovered | ₹1,80,282.49 (24.0%) | ₹2,23,121.11 (31.3%) |

**+₹42,838.62 recovered, +7.3 percentage points over blind retry-everything.**

Results are from a reproducible, fixed-seed simulation over 150 synthetic failed transactions — not production payment data.

## The Problem

Not every failed payment deserves the same response. A network timeout is worth an instant retry. Insufficient funds needs a later retry and a reminder. An expired card needs the customer to act. A fraud-blocked payment should never be retried blindly.

Treating every failure identically causes two losses: blind retries waste attempts and annoy customers, while no action at all leaves recoverable revenue on the table. RecoverAI replaces guesswork with a controlled, auditable recovery workflow.

## How It Works

- **Failure Classifier** — deterministic rules map each failure reason to a candidate action
- **Policy Gateway** — enforces do-not-contact, contact caps, and fraud restrictions before anything executes
- **Safety Validators** — checks generated messages for correctness and unsafe content before sending
- **Groq LLM** — writes the customer-facing message only; never decides the action or whether to contact
- **Execution** — simulated for the 150-transaction batch; a real Razorpay Test Mode path proves live execution
- **Audit Trail** — every decision, suppression, and outcome logged with idempotency, so reruns never duplicate events

## Where AI Is Used — and Where It Deliberately Isn't

| Decision Authority | Why |
|---|---|
| Which recovery action to take — **Deterministic policy** | Predictable and auditable |
| Whether to contact the customer — **Policy gateway** | Enforces opt-outs & fraud limits |
| Is the generated content safe — **Validators** | Blocks unsafe or invalid output |
| Wording of the message — **Groq LLM** | Personalization is generative |
| What happens if the LLM fails — **Deterministic fallback** | Recovery keeps running regardless |

**Policy decides. Validators enforce. The LLM communicates. Audit records.**

## Recovery Decision Model

| Failure Reason | Action | Customer Contact |
|---|---|---|
| network_timeout / bank_unavailable | Retry now | No |
| insufficient_funds | Retry later | SMS |
| card_expired / invalid_card | Send nudge | Email |
| fraud_blocked | Manual review | No |
| customer_cancelled | Mark lost | No |

## Live Razorpay Test Mode Proof

Beyond the simulated batch, RecoverAI includes a real, verified execution path — not just a plan.

- Dashboard creates a genuine Razorpay Test Mode Payment Link via the live API
- A real test payment was completed manually in a browser
- Refreshing the dashboard re-queried Razorpay and confirmed the transition: **created → paid**
- Enforces the `rzp_test_` key prefix — refuses to run against live credentials

This proves the integration point works end-to-end at single-transaction scale; extending it to the full batch is the next roadmap step.

## Failure Recovery — What Broke, and What We Did

- Groq deprecated the model mid-build (`llama-3.1-8b-instant`) — diagnosed from the live API error and migrated to `openai/gpt-oss-20b` without touching the surrounding architecture
- The new model then returned empty messages — a reasoning model was consuming its token budget internally; fixed with higher `max_tokens` and `reasoning_effort="low"`
- Built a deterministic template fallback so a Groq outage never blocks recovery processing
- Caught a stale-numbers discrepancy before submission — committed output files didn't match a fresh pipeline run — traced it and corrected the real, reproducible figures
- Found and fixed a Windows Unicode console crash, and a "shadow constant" bug where two files silently duplicated the same safety limit

## Production Roadmap

- Extend the verified single-transaction Razorpay path to the full batch pipeline
- Replace simulated outcome probabilities with real Razorpay payment statuses at scale
- Move from manual status refresh to Razorpay webhook events
- Add durable state, distributed idempotency, retry scheduling, and monitoring for production use

## Why This Approach

RecoverAI is not "send an LLM a failed payment and ask it what to do." Decisions, validation, communication, execution, and auditing are separated by design — so the system stays measurable, safe to rerun, and honest about what is simulated versus what is real.

**Don't blindly retry everything. Decide what is safe, recover what is recoverable, and know exactly why every action happened.**
