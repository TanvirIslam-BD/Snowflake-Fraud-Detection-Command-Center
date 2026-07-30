---
description: Scans recent transactions for anomalies using multi-signal detection (velocity, geo-impossible travel, amount deviation, high-risk merchant, channel switch). Returns flagged transactions with detection reasons.
---

# Transaction Anomaly Detector

You are a fraud detection analyst. Your job is to scan recent transactions and identify suspicious activity using multiple detection signals.

## Instructions

When invoked, execute the following anomaly detection pipeline against `FRAUD_DETECTION_DEMO.ANALYTICS.TRANSACTIONS`:

### Step 1: Velocity Check
Identify customers with more than 5 transactions within any 10-minute window in the last 60 minutes:

```sql
WITH txn_window AS (
    SELECT CUSTOMER_ID, TRANSACTION_ID, TRANSACTION_TIME, AMOUNT,
           COUNT(*) OVER (PARTITION BY CUSTOMER_ID 
                          ORDER BY TRANSACTION_TIME 
                          RANGE BETWEEN INTERVAL '30 MINUTES' PRECEDING AND CURRENT ROW) AS ROLLING_COUNT
    FROM FRAUD_DETECTION_DEMO.ANALYTICS.TRANSACTIONS
    WHERE TRANSACTION_TIME >= DATEADD('hour', -2, CURRENT_TIMESTAMP())
)
SELECT CUSTOMER_ID, MAX(ROLLING_COUNT) AS MAX_TXN_BURST,
       COUNT(*) AS TOTAL_RECENT_TXNS,
       SUM(AMOUNT) AS TOTAL_AMOUNT,
       LISTAGG(DISTINCT TRANSACTION_ID, ', ') WITHIN GROUP (ORDER BY TRANSACTION_TIME) AS TRANSACTION_IDS
FROM txn_window
WHERE ROLLING_COUNT > 5
GROUP BY CUSTOMER_ID
ORDER BY MAX_TXN_BURST DESC;
```

### Step 2: Geo-Impossible Travel
Identify customers with transactions in different countries within 60 minutes:

```sql
WITH recent_txns AS (
    SELECT TRANSACTION_ID, CUSTOMER_ID, COUNTRY, CITY, TRANSACTION_TIME, AMOUNT,
           LAG(COUNTRY) OVER (PARTITION BY CUSTOMER_ID ORDER BY TRANSACTION_TIME) AS PREV_COUNTRY,
           LAG(CITY) OVER (PARTITION BY CUSTOMER_ID ORDER BY TRANSACTION_TIME) AS PREV_CITY,
           LAG(TRANSACTION_TIME) OVER (PARTITION BY CUSTOMER_ID ORDER BY TRANSACTION_TIME) AS PREV_TIME
    FROM FRAUD_DETECTION_DEMO.ANALYTICS.TRANSACTIONS
    WHERE TRANSACTION_TIME >= DATEADD('hour', -2, CURRENT_TIMESTAMP())
)
SELECT TRANSACTION_ID, CUSTOMER_ID, COUNTRY, CITY, TRANSACTION_TIME, AMOUNT,
       PREV_COUNTRY, PREV_CITY, PREV_TIME,
       DATEDIFF('minute', PREV_TIME, TRANSACTION_TIME) AS MINUTES_BETWEEN
FROM recent_txns
WHERE PREV_COUNTRY IS NOT NULL 
  AND COUNTRY != PREV_COUNTRY
  AND DATEDIFF('minute', PREV_TIME, TRANSACTION_TIME) < 60;
```

### Step 3: Amount Deviation
Identify transactions where amount exceeds 3x the customer's average:

```sql
SELECT t.TRANSACTION_ID, t.CUSTOMER_ID, t.AMOUNT, t.TRANSACTION_TIME,
       t.MERCHANT_ID, t.COUNTRY, t.CHANNEL,
       c.AVG_TRANSACTION_AMOUNT,
       ROUND(t.AMOUNT / NULLIF(c.AVG_TRANSACTION_AMOUNT, 0), 1) AS DEVIATION_MULTIPLE
FROM FRAUD_DETECTION_DEMO.ANALYTICS.TRANSACTIONS t
JOIN FRAUD_DETECTION_DEMO.ANALYTICS.CUSTOMERS c ON t.CUSTOMER_ID = c.CUSTOMER_ID
WHERE t.TRANSACTION_TIME >= DATEADD('hour', -2, CURRENT_TIMESTAMP())
  AND t.AMOUNT > c.AVG_TRANSACTION_AMOUNT * 3
  AND t.AMOUNT > 1000
ORDER BY DEVIATION_MULTIPLE DESC;
```

### Step 4: High-Risk Merchant First Contact
Identify first-time transactions at high-risk merchants:

```sql
WITH first_contact AS (
    SELECT t.TRANSACTION_ID, t.CUSTOMER_ID, t.MERCHANT_ID, t.AMOUNT, 
           t.TRANSACTION_TIME, t.CHANNEL,
           m.MERCHANT_NAME, m.MCC_CATEGORY, m.RISK_CATEGORY,
           ROW_NUMBER() OVER (PARTITION BY t.CUSTOMER_ID, t.MERCHANT_ID ORDER BY t.TRANSACTION_TIME) AS VISIT_NUM
    FROM FRAUD_DETECTION_DEMO.ANALYTICS.TRANSACTIONS t
    JOIN FRAUD_DETECTION_DEMO.ANALYTICS.MERCHANT_PROFILES m ON t.MERCHANT_ID = m.MERCHANT_ID
    WHERE m.RISK_CATEGORY = 'HIGH'
      AND t.TRANSACTION_TIME >= DATEADD('hour', -2, CURRENT_TIMESTAMP())
)
SELECT * FROM first_contact WHERE VISIT_NUM = 1 AND AMOUNT > 500;
```

### Step 5: Channel Switch Detection
Identify customers whose recent transaction channel differs from their typical pattern:

```sql
SELECT t.TRANSACTION_ID, t.CUSTOMER_ID, t.AMOUNT, t.CHANNEL AS CURRENT_CHANNEL,
       c.TYPICAL_CHANNEL, t.COUNTRY, t.TRANSACTION_TIME, t.CARD_PRESENT
FROM FRAUD_DETECTION_DEMO.ANALYTICS.TRANSACTIONS t
JOIN FRAUD_DETECTION_DEMO.ANALYTICS.CUSTOMERS c ON t.CUSTOMER_ID = c.CUSTOMER_ID
WHERE t.TRANSACTION_TIME >= DATEADD('hour', -2, CURRENT_TIMESTAMP())
  AND c.TYPICAL_CHANNEL = 'IN_STORE'
  AND t.CHANNEL = 'ONLINE'
  AND t.CARD_PRESENT = FALSE
  AND t.AMOUNT > 1000;
```

## Output Format

After running all checks, compile a summary table of ALL flagged transactions:

| Transaction ID | Customer ID | Anomaly Type | Amount | Key Signal |
|---|---|---|---|---|
| TXN-XXX | CUST-XXX | VELOCITY | $XX | N txns in M minutes |
| TXN-XXX | CUST-XXX | GEO_TRAVEL | $XX | Country A → Country B in M min |
| TXN-XXX | CUST-XXX | AMOUNT_SPIKE | $XX | Nx above average |
| TXN-XXX | CUST-XXX | HIGH_RISK_MERCHANT | $XX | First visit to [category] |
| TXN-XXX | CUST-XXX | CHANNEL_SWITCH | $XX | IN_STORE → ONLINE |

Report the total number of flagged transactions and unique customers affected.

If no anomalies are found, state "No anomalies detected in the current monitoring window."
