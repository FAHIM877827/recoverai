# RecoverAI — AI-Powered Failed Payment Recovery Agent

**Razorpay AI Buildathon 2026 — Track 3: AI Revenue Recovery**

RecoverAI ingests a batch of failed payment transactions, classifies why each one failed, decides the right recovery action, executes it (simulated), and reports measurable ₹ recovered — compared against a naive baseline.

---

## 🎯 Problem Taste — Why This Matters

When a customer's payment fails — expired card, insufficient funds, a network timeout — that revenue is usually lost for good. Most merchants have no systematic way to win it back: failures go unretried, customers never get nudged, and money quietly disappears.

RecoverAI turns this into a measurable recovery pipeline instead of a silent loss.

**The headline result:**
> Out of ₹751,199.28 in failed payments, RecoverAI recovered ₹223,121.11 — a 31.3% recovery rate, compared to ₹180,282.49 (24.0%) from a naive retry-everything-once approach.

---

## 🏗️ Build Quality — Architecture & How to Run It

**Architecture:**

```
Synthetic Failed Transactions
        ↓
Rules-Based Classifier (failure reason → action + channel)
        ↓
Outcome Simulator (probability-based recovery outcome)
        ↓
Groq LLM (personalized nudge messages — only where needed)
        ↓
Streamlit Dashboard (metrics, comparison, live simulator)
```

**Tech stack:** Python, pandas, Groq API (`openai/gpt-oss-20b`), Streamlit

**Project structure:**
```
recoverai/
├── src/
│   ├── generate_data.py       # synthetic failed transaction generator
│   ├── rules.py                # failure reason → action/channel rules
│   ├── classify_transactions.py # applies rules to full dataset
│   ├── simulate_outcomes.py    # outcome simulation + LLM nudge generation
│   └── dashboard.py            # Streamlit app (Day 2-3)
├── .env                        # GROQ_API_KEY (not committed)
├── .gitignore
└── README.md
```

**How to run:**
```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install pandas groq python-dotenv streamlit
# Add your GROQ_API_KEY to a .env file
python src/generate_data.py
python src/classify_transactions.py
python src/simulate_outcomes.py
streamlit run src/dashboard.py
```

*(Update once dashboard.py exists — Day 2-3)*

---

## 🧠 AI Judgment — Where We Used AI, and Where We Deliberately Didn't

We split decisions between **deterministic rules** and **generative AI**, based on which each task actually needed:

- **Rules, not AI:** Deciding *which action* to take for a given failure reason (retry now / retry later / send nudge / mark lost) is deterministic and needs to be predictable and auditable — so it's plain if/else logic, not an LLM call. This also means `fraud_blocked` transactions are **never** auto-retried or messaged, by design — a hardcoded safety boundary, not something we'd trust an LLM to decide case-by-case.
- **LLM, not rules:** Writing a *personalized nudge message* is inherently generative — tone, phrasing, and content need to adapt per customer. This is the one place we used Groq's `openai/gpt-oss-20b` model.

Every classifier decision also comes with a plain-English **reasoning trace** (e.g., *"Network timeouts resolve automatically ~70% of the time — retrying immediately avoids unnecessary customer friction"*), so the agent's logic is inspectable, not a black box.

---

## 🛠️ Failure Recovery — What Broke, and What We Did About It

1. **Groq model deprecation mid-build:** `llama-3.1-8b-instant` (originally used) was deprecated by Groq on June 17, 2026. Diagnosed via the actual API error message, confirmed the replacement (`openai/gpt-oss-20b`) via Groq's documentation, and migrated without losing existing working code.

2. **Silent empty LLM responses:** After migrating models, nudge generation returned empty strings with no error. Root cause: `gpt-oss-20b` is a reasoning model that consumes part of its token budget on internal reasoning before producing output — the original `max_tokens=150` was too low. Fixed by raising `max_tokens=400` and setting `reasoning_effort="low"` to bias toward direct, fast output for this short-message use case.

3. **Built-in runtime fallback:** If the Groq API call fails for any reason (rate limit, network issue, timeout) during actual operation, the system falls back to a safe template message rather than failing the transaction:
```python
   f"Hi {customer_name}, your payment of ₹{amount} didn't go through. Please retry: [LINK]"
```
   This was tested and confirmed working before the LLM integration was finalized.

*(Add any Day 2-5 issues here as they happen)*

---

## 📊 Results

*(Fill in after baseline comparison — Day 2)*

| Metric                | Naive Baseline | RecoverAI   |
|-----------------------|----------------|-------------|
| Total failed payments | ₹751,199.28    | ₹751,199.28 |
| ₹ Recovered           | ₹180,282.49    | ₹223,121.11 |
| Recovery rate         | 24.0%          | 31.3%       |

**RecoverAI recovers ₹42,838.62 more than a naive retry-all approach — a 7.3 percentage point improvement.**

---

## 🚀 Live Demo

*(Add Streamlit dashboard link/screenshot + link to 5-min pitch video once ready)*

---

## 🗺️ Production Roadmap — Razorpay Payment Links Integration

The current pipeline simulates recovery outcomes with probability assumptions (see `probabilities.py`) rather than calling a real payment gateway. Wiring in real Razorpay **Test Mode** Payment Links is the next step post-submission, planned as a single, narrow integration rather than a rework of the existing decision logic:

- **One integration point, at the existing gate.** Razorpay Payment Link creation plugs into `simulate_outcomes.py` at the point where a message is already about to be generated — i.e., only when `action` is `send_nudge` or `retry_later` *and* `do_not_contact` is `False`. This is the same choke point `generate_nudge()` already uses; the integration does not add a second, parallel eligibility check.
- **Real outcome instead of a simulated probability.** Once a real payment link exists, whether a transaction is `recovered` should come from the Razorpay link's actual status (paid / expired / cancelled), not from `SUCCESS_PROBABILITY`'s random draw — a real link with a fabricated "recovered" result would make the audit trail dishonest.
- **Idempotent by construction.** Link creation reuses the same `event_exists()` guard pattern `audit.py` already uses for `FAILED_PAYMENT_RECEIVED` / `RECOVERY_OUTCOME`, so a re-run never creates a duplicate payment link for the same transaction. Razorpay's `reference_id` is set to `transaction_id` so it dedupes on their side too.
- **Test-mode enforced, not assumed.** The integration checks that `RAZORPAY_KEY_ID` starts with `rzp_test_` and refuses to run otherwise — this repo has no other safeguard against accidentally using live keys.
- **No changes to the decision logic.** `policy.py` and `rules.py` stay exactly as they are — they already own the eligibility/contact-cap rails, and Razorpay only needs to consume their output (`action`, `channel`), not duplicate it.
- **Secrets handling.** `RAZORPAY_KEY_ID`/`RAZORPAY_KEY_SECRET` load via `.env`, the same way `GROQ_API_KEY` does today; never logged to `audit_events.csv`.

This is documented here as a plan only — not implemented in this submission.