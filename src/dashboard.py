import streamlit as st
import pandas as pd

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------

st.set_page_config(
    page_title="RecoverAI",
    page_icon="💳",
    layout="wide"
)

# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

df = pd.read_csv("final_transactions_with_baseline.csv")

# --------------------------------------------------
# METRICS
# --------------------------------------------------

total_at_risk = df["amount"].sum()

recoverai_recovered = df["recovered_amount"].sum()
recoverai_rate = df["recovered"].mean() * 100

baseline_recovered = df["naive_recovered_amount"].sum()
baseline_rate = df["naive_recovered"].mean() * 100

additional_revenue = recoverai_recovered - baseline_recovered
lift = recoverai_rate - baseline_rate

# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.markdown(
    """
    <div style="padding: 10px 0 20px 0;">
        <h1 style="margin-bottom: 0;">💳 RecoverAI</h1>
        <p style="font-size: 18px; color: #666;">
            Intelligent failed-payment recovery engine
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

st.divider()

# --------------------------------------------------
# KPI CARDS
# --------------------------------------------------

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Amount at Risk",
        f"₹{total_at_risk:,.0f}"
    )

with col2:
    st.metric(
        "Recovered Revenue",
        f"₹{recoverai_recovered:,.0f}"
    )

with col3:
    st.metric(
        "Recovery Rate",
        f"{recoverai_rate:.1f}%"
    )

with col4:
    st.metric(
        "Incremental Revenue",
        f"₹{additional_revenue:,.0f}",
        f"+{lift:.1f} pp"
    )

st.divider()

# --------------------------------------------------
# RECOVERY PERFORMANCE
# --------------------------------------------------

st.header("Recovery Performance")

chart_data = pd.DataFrame(
    {
        "Recovered Revenue": [
            baseline_recovered,
            recoverai_recovered
        ]
    },
    index=[
        "Naive Baseline",
        "RecoverAI"
    ]
)

st.bar_chart(chart_data)

col1, col2 = st.columns(2)

with col1:
    st.metric(
        "Naive Baseline Recovery",
        f"₹{baseline_recovered:,.0f}",
        f"{baseline_rate:.1f}%"
    )

with col2:
    st.metric(
        "RecoverAI Recovery",
        f"₹{recoverai_recovered:,.0f}",
        f"{recoverai_rate:.1f}%"
    )

st.divider()

# --------------------------------------------------
# HOW RECOVERAI WORKS
# --------------------------------------------------

st.header("How RecoverAI Makes Decisions")

step1, step2, step3, step4 = st.columns(4)

with step1:
    st.subheader("1. Failure")
    st.write("Payment fails and the failure reason is captured.")

with step2:
    st.subheader("2. Classify")
    st.write("Deterministic rules identify the failure type.")

with step3:
    st.subheader("3. Decide")
    st.write("Rules select retry, delayed retry, nudge, or loss.")

with step4:
    st.subheader("4. Recover")
    st.write("LLM generates a personalized customer message when needed.")

st.info(
    "AI boundary: deterministic rules control recovery decisions. "
    "The LLM is used only for personalized messaging."
)

st.divider()

# --------------------------------------------------
# TRANSACTION DECISIONS
# --------------------------------------------------

st.header("Transaction Recovery Decisions")

# Filters
filter_col1, filter_col2, filter_col3 = st.columns(3)

with filter_col1:
    actions = ["All"] + sorted(df["action"].dropna().unique().tolist())
    selected_action = st.selectbox("Recovery Action", actions)

with filter_col2:
    reasons = ["All"] + sorted(
        df["failure_reason"].dropna().unique().tolist()
    )
    selected_reason = st.selectbox("Failure Reason", reasons)

with filter_col3:
    result = st.selectbox(
        "Recovery Result",
        ["All", "Recovered", "Not Recovered"]
    )

filtered_df = df.copy()

if selected_action != "All":
    filtered_df = filtered_df[
        filtered_df["action"] == selected_action
    ]

if selected_reason != "All":
    filtered_df = filtered_df[
        filtered_df["failure_reason"] == selected_reason
    ]

if result == "Recovered":
    filtered_df = filtered_df[
        filtered_df["recovered"] == True
    ]

elif result == "Not Recovered":
    filtered_df = filtered_df[
        filtered_df["recovered"] == False
    ]

display_columns = [
    "customer_name",
    "amount",
    "failure_reason",
    "action",
    "recovered",
    "reasoning"
]

available_columns = [
    column for column in display_columns
    if column in filtered_df.columns
]

st.dataframe(
    filtered_df[available_columns],
    use_container_width=True,
    hide_index=True
)

st.caption(
    f"Showing {len(filtered_df)} of {len(df)} transactions"
)

st.divider()

# --------------------------------------------------
# AI GENERATED RECOVERY MESSAGES
# --------------------------------------------------

st.header("AI Recovery Messages")

messages = df[
    df["nudge_message"].notna()
].copy()

for _, row in messages.head(5).iterrows():

    with st.expander(
        f"{row['customer_name']}  •  ₹{row['amount']:,.2f}  •  {row['channel']}"
    ):

        st.write(
            f"**Failure reason:** {row['failure_reason']}"
        )

        st.write(
            f"**Message source:** {row['message_source']}"
        )

        st.write("**Generated message:**")

        st.info(row["nudge_message"])

st.divider()

# --------------------------------------------------
# ENGINEERING NOTES
# --------------------------------------------------

st.header("Engineering Design")

design_col1, design_col2 = st.columns(2)

with design_col1:

    st.subheader("Deterministic Decision Layer")

    st.write(
        """
        • Failure classification uses explicit rules
        • Recovery actions are deterministic
        • Security-blocked payments are not automatically retried
        • Recovery outcomes are measured against a naive baseline
        """
    )

with design_col2:

    st.subheader("LLM Layer")

    st.write(
        """
        • LLM generates customer-facing messages
        • LLM does not control money movement
        • LLM failures fall back to a template
        • Messages are generated only when customer communication is appropriate
        """
    )

st.divider()

st.caption(
    "RecoverAI • Failed Payment Recovery • Simulation + AI Messaging"
)
