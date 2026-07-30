import streamlit as st
import pandas as pd
import altair as alt
from snowflake.snowpark.context import get_active_session

st.set_page_config(
    page_title="Fraud Detection Command Center",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

session = get_active_session()


@st.cache_data(ttl=60)
def get_alert_summary():
    return session.sql("""
        SELECT RISK_LEVEL, COUNT(*) AS ALERT_COUNT, 
               SUM(CASE WHEN STATUS = 'CRITICAL' THEN 1 ELSE 0 END) AS CRITICAL_COUNT
        FROM FRAUD_DETECTION_DEMO.ANALYTICS.FRAUD_ALERTS
        GROUP BY RISK_LEVEL
        ORDER BY CASE RISK_LEVEL WHEN 'CRITICAL' THEN 1 WHEN 'ALERT' THEN 2 
                      WHEN 'MONITOR' THEN 3 ELSE 4 END
    """).to_pandas()


@st.cache_data(ttl=60)
def get_recent_alerts():
    return session.sql("""
        SELECT ALERT_ID, TRANSACTION_ID, CUSTOMER_ID, RISK_SCORE, RISK_LEVEL,
               ANOMALY_TYPE, ACTION_TAKEN, REASONING, STATUS, DETECTION_TIME
        FROM FRAUD_DETECTION_DEMO.ANALYTICS.FRAUD_ALERTS
        ORDER BY DETECTION_TIME DESC
        LIMIT 50
    """).to_pandas()


@st.cache_data(ttl=60)
def get_transaction_stats():
    return session.sql("""
        SELECT STATUS, COUNT(*) AS COUNT, SUM(AMOUNT) AS TOTAL_AMOUNT
        FROM FRAUD_DETECTION_DEMO.ANALYTICS.TRANSACTIONS
        GROUP BY STATUS
        ORDER BY COUNT DESC
    """).to_pandas()


@st.cache_data(ttl=60)
def get_fraud_by_type():
    return session.sql("""
        SELECT ANOMALY_TYPE, COUNT(*) AS COUNT, AVG(RISK_SCORE) AS AVG_SCORE
        FROM FRAUD_DETECTION_DEMO.ANALYTICS.FRAUD_ALERTS
        GROUP BY ANOMALY_TYPE
        ORDER BY COUNT DESC
    """).to_pandas()


@st.cache_data(ttl=60)
def get_hourly_transactions():
    return session.sql("""
        SELECT DATE_TRUNC('hour', TRANSACTION_TIME) AS HOUR,
               COUNT(*) AS TXN_COUNT,
               SUM(CASE WHEN IS_FRAUD_LABEL THEN 1 ELSE 0 END) AS FRAUD_COUNT,
               SUM(AMOUNT) AS TOTAL_VOLUME
        FROM FRAUD_DETECTION_DEMO.ANALYTICS.TRANSACTIONS
        WHERE TRANSACTION_TIME >= DATEADD('day', -1, CURRENT_TIMESTAMP())
        GROUP BY 1
        ORDER BY 1
    """).to_pandas()


@st.cache_data(ttl=60)
def get_top_risk_customers():
    return session.sql("""
        SELECT fa.CUSTOMER_ID, c.FULL_NAME, c.RISK_TIER, c.COUNTRY,
               COUNT(*) AS ALERT_COUNT, MAX(fa.RISK_SCORE) AS MAX_RISK_SCORE,
               SUM(t.AMOUNT) AS TOTAL_FLAGGED_AMOUNT
        FROM FRAUD_DETECTION_DEMO.ANALYTICS.FRAUD_ALERTS fa
        JOIN FRAUD_DETECTION_DEMO.ANALYTICS.CUSTOMERS c ON fa.CUSTOMER_ID = c.CUSTOMER_ID
        JOIN FRAUD_DETECTION_DEMO.ANALYTICS.TRANSACTIONS t ON fa.TRANSACTION_ID = t.TRANSACTION_ID
        GROUP BY fa.CUSTOMER_ID, c.FULL_NAME, c.RISK_TIER, c.COUNTRY
        ORDER BY MAX_RISK_SCORE DESC
        LIMIT 10
    """).to_pandas()


# --- HEADER ---
st.title("Fraud Detection Command Center")
st.caption("Autonomous AI-driven fraud monitoring, scoring, and response")

# --- KPI METRICS ---
alerts_df = get_alert_summary()
txn_stats = get_transaction_stats()

total_txns = int(txn_stats["COUNT"].sum()) if not txn_stats.empty else 0
blocked_count = int(txn_stats[txn_stats["STATUS"] == "BLOCKED"]["COUNT"].sum()) if not txn_stats.empty else 0
held_count = int(txn_stats[txn_stats["STATUS"] == "HELD"]["COUNT"].sum()) if not txn_stats.empty else 0
blocked_value = float(txn_stats[txn_stats["STATUS"] == "BLOCKED"]["TOTAL_AMOUNT"].sum()) if not txn_stats.empty else 0
held_value = float(txn_stats[txn_stats["STATUS"] == "HELD"]["TOTAL_AMOUNT"].sum()) if not txn_stats.empty else 0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Transactions", f"{total_txns:,}")
col2.metric("Blocked", f"{blocked_count}", delta=f"${blocked_value:,.0f} protected")
col3.metric("Held for Review", f"{held_count}", delta=f"${held_value:,.0f} pending")
col4.metric("Total Alerts", f"{int(alerts_df['ALERT_COUNT'].sum()) if not alerts_df.empty else 0}")
col5.metric("Critical Alerts", f"{int(alerts_df[alerts_df['RISK_LEVEL']=='CRITICAL']['ALERT_COUNT'].sum()) if not alerts_df.empty and 'CRITICAL' in alerts_df['RISK_LEVEL'].values else 0}")

st.divider()

# --- TWO COLUMN LAYOUT ---
left_col, right_col = st.columns([3, 2])

with left_col:
    st.subheader("Recent Fraud Alerts")
    recent_alerts = get_recent_alerts()
    if not recent_alerts.empty:
        for _, row in recent_alerts.iterrows():
            severity_color = {
                "CRITICAL": "🔴", "ALERT": "🟠", "MONITOR": "🟡", "CLEAR": "🟢"
            }.get(row["RISK_LEVEL"], "⚪")

            with st.expander(
                f"{severity_color} {row['RISK_LEVEL']} | {row['TRANSACTION_ID']} | "
                f"Score: {row['RISK_SCORE']} | {row['ACTION_TAKEN']}"
            ):
                st.markdown(f"**Customer:** {row['CUSTOMER_ID']}")
                st.markdown(f"**Anomaly Type:** {row['ANOMALY_TYPE']}")
                st.markdown(f"**Status:** {row['STATUS']}")
                st.markdown(f"**Detection Time:** {row['DETECTION_TIME']}")
                st.markdown("---")
                st.markdown(f"**AI Reasoning:**")
                st.info(row["REASONING"])
    else:
        st.info("No alerts detected yet. Run the fraud detection pipeline to populate.")

with right_col:
    st.subheader("Alerts by Anomaly Type")
    fraud_types = get_fraud_by_type()
    if not fraud_types.empty:
        chart = alt.Chart(fraud_types).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
            x=alt.X("COUNT:Q", title="Alert Count"),
            y=alt.Y("ANOMALY_TYPE:N", sort="-x", title=""),
            color=alt.Color("AVG_SCORE:Q", scale=alt.Scale(scheme="reds"), title="Avg Score"),
            tooltip=["ANOMALY_TYPE", "COUNT", "AVG_SCORE"]
        ).properties(height=250)
        st.altair_chart(chart, use_container_width=True)

    st.subheader("Transaction Status Breakdown")
    if not txn_stats.empty:
        chart2 = alt.Chart(txn_stats).mark_arc(innerRadius=50).encode(
            theta=alt.Theta("COUNT:Q"),
            color=alt.Color("STATUS:N", scale=alt.Scale(
                domain=["COMPLETED", "BLOCKED", "HELD", "FROZEN", "PENDING"],
                range=["#2ecc71", "#e74c3c", "#f39c12", "#9b59b6", "#95a5a6"]
            )),
            tooltip=["STATUS", "COUNT", "TOTAL_AMOUNT"]
        ).properties(height=250)
        st.altair_chart(chart2, use_container_width=True)

st.divider()

# --- BOTTOM SECTION ---
bottom_left, bottom_right = st.columns(2)

with bottom_left:
    st.subheader("Top Risk Customers")
    top_customers = get_top_risk_customers()
    if not top_customers.empty:
        st.dataframe(
            top_customers[["CUSTOMER_ID", "FULL_NAME", "RISK_TIER", "COUNTRY",
                          "ALERT_COUNT", "MAX_RISK_SCORE", "TOTAL_FLAGGED_AMOUNT"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "MAX_RISK_SCORE": st.column_config.ProgressColumn(
                    "Risk Score", min_value=0, max_value=100, format="%d"
                ),
                "TOTAL_FLAGGED_AMOUNT": st.column_config.NumberColumn(
                    "Flagged Amount", format="$%.2f"
                ),
            }
        )

with bottom_right:
    st.subheader("Transaction Volume (24h)")
    hourly = get_hourly_transactions()
    if not hourly.empty:
        chart3 = alt.Chart(hourly).mark_area(
            opacity=0.6, line=True, color="#29B5E8"
        ).encode(
            x=alt.X("HOUR:T", title="Time"),
            y=alt.Y("TXN_COUNT:Q", title="Transactions"),
            tooltip=["HOUR:T", "TXN_COUNT", "FRAUD_COUNT", "TOTAL_VOLUME"]
        ).properties(height=250)

        fraud_line = alt.Chart(hourly).mark_line(
            color="#e74c3c", strokeWidth=2
        ).encode(
            x="HOUR:T",
            y=alt.Y("FRAUD_COUNT:Q", title="Fraud Count")
        )

        st.altair_chart(chart3 + fraud_line, use_container_width=True)

# --- SIDEBAR ---
with st.sidebar:
    st.header("Pipeline Controls")
    st.markdown("---")
    st.markdown("**Agent Status:** Active")
    st.markdown("**Last Scan:** Just now")
    st.markdown("**Detection Window:** 2 hours")
    st.markdown("---")
    st.markdown("### Detection Signals")
    st.markdown("- Velocity attacks")
    st.markdown("- Geo-impossible travel")
    st.markdown("- Amount deviation")
    st.markdown("- High-risk merchants")
    st.markdown("- Channel switching")
    st.markdown("---")
    st.markdown("### Quick Stats")
    st.markdown(f"- **Protected:** ${blocked_value + held_value:,.0f}")
    st.markdown(f"- **Fraud rate:** {(blocked_count + held_count) / max(total_txns, 1) * 100:.2f}%")
