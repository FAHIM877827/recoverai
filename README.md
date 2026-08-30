# RecoverAI — AI-Powered Failed Payment Recovery Agent

**Razorpay AI Buildathon 2026 — Track 3: AI Revenue Recovery**

RecoverAI ingests a batch of failed payment transactions, classifies why each one failed, decides the right recovery action, executes it (simulated), and reports measurable ₹ recovered — compared against a naive baseline.

---

## 🎯 Problem Taste — Why This Matters

When a customer's payment fails — expired card, insufficient funds, a network timeout — that revenue is usually lost for good. Most merchants have no systematic way to win it back: failures go unretried, customers never get nudged, and money quietly disappears.

RecoverAI turns this into a measurable recovery pipeline instead of a silent loss.

**The headline result:**
> Out of ₹[X] in failed payments, RecoverAI recovered ₹[Y] — a [Z]% recovery rate, compared to ₹[baseline] ([baseline%]) from a naive retry-everything-once approach.

*(Fill in exact numbers once baseline comparison is done — Day 2)*

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

| Metric | Naive Baseline | RecoverAI |
|---|---|---|
| Total failed payments | | |
| ₹ Recovered | | |
| Recovery rate | | |

---

## 🚀 Live Demo

*(Add Streamlit dashboard link/screenshot + link to 5-min pitch video once ready)*