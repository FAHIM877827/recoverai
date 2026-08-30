# src/simulate_outcomes.py
import random

SUCCESS_PROBABILITY = {
    "retry_now": 0.70,      # network timeouts often self-resolve
    "retry_later": 0.45,    # insufficient funds — decent odds after a wait
    "send_nudge": 0.40,     # depends on customer responding
    "mark_lost": 0.0,       # never recovered
}

def simulate_outcome(action: str) -> bool:
    prob = SUCCESS_PROBABILITY.get(action, 0.0)
    return random.random() < prob

REASONING = {
    "retry_now": (
        "Network timeouts are often temporary, so an immediate retry "
        "can recover the payment without customer intervention."
    ),

    "retry_later": (
        "Insufficient funds may resolve after 24-48 hours, so waiting "
        "before retrying gives the customer time to add funds."
    ),

    "send_nudge": (
        "This payment requires customer action, so sending a personalized "
        "message is more effective than automatically retrying."
    ),

    "mark_lost": (
        "This transaction is blocked for security reasons, so RecoverAI "
        "does not retry or contact the customer automatically."
    ),
}
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def build_prompt(customer_name, amount, failure_reason, channel):
    if channel == "sms":
        return (
            f"Write an SMS under 150 characters for a failed payment recovery. "
            f"Customer: {customer_name}, Amount: ₹{amount}, Reason: {failure_reason}. "
            f"Tone: friendly, urgent but not pushy. Include a retry link placeholder [LINK]. "
            f"Return ONLY the message text, nothing else."
        )
    else:
        return (
            f"Write a short recovery email (under 80 words) for a failed payment. "
            f"Customer: {customer_name}, Amount: ₹{amount}, Reason: {failure_reason}. "
            f"Include: greeting, what happened, one clear action, a retry link placeholder [LINK]. "
            f"Tone: professional, helpful, non-pushy. "
            f"Return ONLY the email body text, nothing else."
        )

def generate_nudge(customer_name, amount, failure_reason, channel):
    try:
        prompt = build_prompt(customer_name, amount, failure_reason, channel)
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.7,
            reasoning_effort="low",
        )
        message = response.choices[0].message.content.strip()
        return message, "llm_generated"
    except Exception as e:
        fallback = f"Hi {customer_name}, your payment of ₹{amount} didn't go through. Please retry: [LINK]"
        return fallback, "template_fallback"


