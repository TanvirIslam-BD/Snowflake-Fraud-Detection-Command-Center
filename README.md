# Snowflake Fraud Detection Command Center

An AI-driven intelligent workflow automation agent that autonomously monitors financial transactions, detects anomalies, scores risk with AI reasoning, and executes graduated response actions — all powered by Snowflake CoCo CLI.

## Business Problem

Financial fraud costs institutions over $30B annually. Traditional rule-based systems generate excessive false positives and require manual review queues that take hours. This agent reduces fraud response time from hours to seconds while maintaining full explainability for compliance.

**Measurable Impact:** $46,615 in value protected per pipeline run, with autonomous detection-to-action in under 60 seconds.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              CoCo CLI Orchestration Layer                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Skill 1    │  │   Skill 2    │  │   Skill 3    │  │
│  │  Anomaly     │→ │  Risk Score  │→ │  Escalation  │  │
│  │  Detector    │  │  & Reasoner  │  │  & Actions   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│         ↑                  ↑                  ↓         │
├─────────────────────────────────────────────────────────┤
│                   Snowflake Data Layer                   │
│  TRANSACTIONS | CUSTOMERS | MERCHANTS | FRAUD_ALERTS    │
└─────────────────────────────────────────────────────────┘
```

## Skills Overview

### Skill 1: Transaction Anomaly Detector
Scans 10,000+ transactions using 5 detection signals:
- **Velocity attacks** — >5 transactions in 30-minute rolling window
- **Geo-impossible travel** — Different countries within 60 minutes
- **Amount deviation** — >3x customer average AND >$1,000
- **High-risk merchant** — First contact at gambling/crypto/wire transfer
- **Channel switching** — In-store customer suddenly online

### Skill 2: Fraud Risk Scorer & Reasoner
Enriches flagged transactions with customer history and merchant context, then produces:
- Risk score (0-100) using additive scoring rubric
- Risk level classification (CLEAR / MONITOR / ALERT / CRITICAL)
- Natural-language reasoning explaining the assessment

### Skill 3: Escalation & Action Orchestrator
Executes graduated responses based on risk level:
- **CLEAR (0-30):** Log and dismiss
- **MONITOR (31-60):** 24-hour watch, insert monitoring alert
- **ALERT (61-85):** HOLD transaction, escalate to fraud team
- **CRITICAL (86-100):** BLOCK transaction, FREEZE all pending, full audit log

## Demo Results

From a single pipeline run against 10,022 transactions:

| Metric | Value |
|--------|-------|
| Transactions Scanned | 10,022 |
| Anomalies Detected | 15 |
| Auto-Blocked | 15 txns ($8,215) |
| Held for Review | 5 txns ($38,400) |
| Total Value Protected | $46,615 |
| Critical Alerts | 4 |

## Project Structure

```
├── setup/
│   └── create_tables.sql              # Database DDL + synthetic data
├── plugin/
│   └── fraud-agent/
│       ├── plugin.json                # CoCo CLI plugin manifest
│       └── skills/
│           ├── detect-fraud.md        # Master orchestrator skill
│           ├── anomaly-detector.md    # Skill 1: Multi-signal detection
│           ├── risk-scorer.md         # Skill 2: Context-enriched scoring
│           └── escalation-handler.md  # Skill 3: Graduated actions
├── streamlit_app/
│   ├── streamlit_app.py              # Fraud Detection Dashboard (deployed to SiS)
│   ├── snowflake.yml                 # Deployment manifest
│   └── .streamlit/config.toml        # Dark theme config
└── demo/
    └── run_demo.md                   # End-to-end demo walkthrough
```

## Quick Start

### 1. Setup Data
Run `setup/create_tables.sql` in Snowsight to create the database with 10K+ synthetic transactions including injected fraud patterns.

### 2. Install Plugin
```bash
cp -r plugin/fraud-agent ~/.snowflake/cortex/plugins/fraud-agent
```

### 3. Run the Pipeline
In CoCo CLI:
```
Run fraud detection
```

### 4. View Dashboard
The Streamlit dashboard is deployed at:
`FRAUD_DETECTION_DEMO.ANALYTICS.FRAUD_DETECTION_DASHBOARD`

## Key Differentiators

1. **Multi-step orchestration** — 3 skills chained with conditional branching (not sequential)
2. **AI reasoning** — Every action includes natural-language explanation for compliance
3. **Error handling** — Each skill handles failures independently with retry/degrade logic
4. **Minimal intervention** — Fully autonomous; humans only needed for ALERT-level review
5. **Real-world relevance** — Fraud detection is a $30B+ problem with clear measurable ROI
6. **Complete audit trail** — All decisions logged with reasoning, timestamps, and action metadata

## Technology Stack

- **Snowflake** — Data warehouse, compute, Streamlit hosting
- **CoCo CLI** — Agent orchestration and skill execution
- **Cortex AI** — Risk reasoning and natural-language explanations
- **Streamlit-in-Snowflake** — Real-time monitoring dashboard

## Author

Tanvirul Islam
