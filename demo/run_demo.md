# Intelligent Fraud Detection & Response Agent

## Demo Walkthrough

This guide demonstrates the full end-to-end workflow executed through CoCo CLI.

---

## Prerequisites

- Snowflake account with `FRAUD_DETECTION_DEMO` database (created by `setup/create_tables.sql`)
- CoCo CLI with the `fraud-agent` plugin installed at `~/.snowflake/cortex/plugins/fraud-agent/`

---

## Running the Full Pipeline

### Command

In CoCo CLI, invoke the master skill:

```
Run fraud detection
```

This triggers the full autonomous pipeline:

1. **Anomaly Detection** — Scans 10,000+ transactions across 5 detection signals
2. **Risk Scoring** — Enriches flagged transactions with context, scores 0-100
3. **Escalation** — Takes graduated actions (dismiss/monitor/hold/block)
4. **Audit** — Logs all decisions with reasoning to FRAUD_ALERTS table

---

## Demo Scenarios

### Scenario 1: Velocity Attack (Expected: CRITICAL → BLOCK)

Customer `CUST-00042` has 12 transactions in rapid succession (~2 min apart), small amounts, to multiple online merchants. Classic card testing pattern.

**Expected outcome:**
- Detected by velocity check (12 txns in 24 min)
- Risk score: 85-100 (velocity + multiple signals)
- Action: BLOCK all transactions, FREEZE pending

### Scenario 2: Geo-Impossible Travel (Expected: CRITICAL → BLOCK)

Customer `CUST-00100` has a transaction in New York followed by one in Lagos, Nigeria 20 minutes later. Physically impossible.

**Expected outcome:**
- Detected by geo-travel check (US → Nigeria in 20 min)
- Risk score: 90+ (geo-impossible + high amount + different continent)
- Action: BLOCK the Nigeria transaction, alert on the pair

### Scenario 3: Amount Anomaly (Expected: ALERT → HOLD)

Customer `CUST-00005` (avg transaction ~$50-200) suddenly makes $9,500 and $7,200 purchases online.

**Expected outcome:**
- Detected by amount deviation (>30x average)
- Risk score: 70-85 (large deviation but same country/device)
- Action: HOLD transactions pending verification

### Scenario 4: Channel Switch (Expected: MONITOR or ALERT)

Customer `CUST-00075` (typical IN_STORE) makes large ONLINE purchases from Moscow.

**Expected outcome:**
- Detected by channel switch + geo flag
- Risk score: 65-90 (depends on context enrichment)
- Action: HOLD or MONITOR with fraud team notification

---

## Verifying Results

After pipeline execution, query the audit trail:

```sql
SELECT ALERT_ID, TRANSACTION_ID, CUSTOMER_ID, RISK_SCORE, RISK_LEVEL, 
       ACTION_TAKEN, REASONING, STATUS
FROM FRAUD_DETECTION_DEMO.ANALYTICS.FRAUD_ALERTS
ORDER BY DETECTION_TIME DESC
LIMIT 20;
```

Check blocked transactions:

```sql
SELECT TRANSACTION_ID, CUSTOMER_ID, AMOUNT, STATUS, TRANSACTION_TIME
FROM FRAUD_DETECTION_DEMO.ANALYTICS.TRANSACTIONS
WHERE STATUS IN ('BLOCKED', 'HELD', 'FROZEN')
ORDER BY TRANSACTION_TIME DESC;
```

---

## Individual Skill Invocations

You can also run each skill independently:

| Command | Skill | Purpose |
|---------|-------|---------|
| "Check for anomalies" | anomaly-detector | Scan only, no action |
| "Score these transactions: TXN-GEO-0001, TXN-AMT-0001" | risk-scorer | Score specific txns |
| "What's the fraud status?" | detect-fraud | Query existing alerts |

---

## Architecture Highlights

- **Multi-step orchestration:** 3 skills chained with conditional branching (not just sequential)
- **Decision branches:** Pipeline stops early if no anomalies; fast-tracks CLEAR scores
- **Error handling:** Each skill handles failures independently; orchestrator retries or degrades gracefully
- **Minimal manual intervention:** Fully autonomous from detection to action; humans only needed for ALERT-level review
- **Compliance-ready:** Every decision logged with AI-generated reasoning for auditors
- **Measurable impact:** Reduces fraud response time from hours (manual review queues) to seconds (autonomous detection + action)

---

## File Structure

```
d:\AI_AGENT\
├── setup/
│   └── create_tables.sql              # DDL + data setup
├── plugin/
│   └── fraud-agent/
│       ├── plugin.json                # CoCo plugin manifest
│       └── skills/
│           ├── detect-fraud.md        # Master orchestrator
│           ├── anomaly-detector.md    # Skill 1: Detection
│           ├── risk-scorer.md         # Skill 2: Scoring
│           └── escalation-handler.md  # Skill 3: Actions
└── demo/
    └── run_demo.md                    # This file
```
