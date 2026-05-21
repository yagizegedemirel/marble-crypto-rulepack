# Scenario 01 — High-Velocity Structuring Detection

**Status:** V1 Live · **Scenario ID:** `019e4a2c-7b4a-7db4-b692-302452610fcc` · **Trigger entity:** `transactions` · **Last batch:** 2026-05-21 14:28 (1,367 decisions on 10,277 transactions)

---

## 1. Regulatory Anchors

| Framework | Citation | Relevance |
|---|---|---|
| FATF | Recommendation 10 — Customer Due Diligence | Transaction monitoring obligation for designated non-financial businesses and professions, including VASPs |
| EU | MiCA Articles 67–68 | Crypto-Asset Service Provider transaction monitoring requirements |
| EU | AMLD6 Article 13 | Suspicious activity reporting and audit trail of detection systems |
| Türkiye | MASAK Law No. 5549, Article 4 | Suspicious transaction reporting threshold (TL equivalent of EUR thresholds) |
| EU AI Act | Article 12 | Record-keeping requirement for high-risk AI systems used in financial crime detection |

---

## 2. Business Problem

**Structuring** (also called smurfing in retail contexts) is the deliberate fragmentation of a single large transaction into multiple smaller transactions, each engineered to fall below the institution's reporting or enhanced due diligence threshold. The intent is to evade detection while moving the same aggregate value.

In crypto-asset service providers, structuring exploits the velocity gap between automated transaction monitoring (often batched hourly or daily) and the customer's ability to execute high-frequency small transactions through programmatic interfaces.

**Detection objective:** identify customers executing 5 or more sub-EUR 1,000 transactions, which collectively suggest deliberate threshold avoidance.

---

## 3. Detection Logic

### 3.1 Trigger Condition
Acts as the pre-filter that determines which records the scenario evaluates. Reduces compute on irrelevant data.

