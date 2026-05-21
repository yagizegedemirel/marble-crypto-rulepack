# Scenario 01 - High-Velocity Structuring Detection

V1 Live in Marble. Triggers on transactions, fires when a customer accumulates 5+ sub-EUR1000 transactions. Scenario ID `019e4a2c-7b4a-7db4-b692-302452610fcc`. Last batch run 2026-05-21 14:28, 1367 decisions on 10277 transactions.

## What it catches

Structuring: breaking one large payment into many small ones, each under the reporting threshold. Same aggregate value, half a day, no single transaction big enough to trip the manual SAR queue. In retail it's called smurfing, in CASPs it's automated and faster.

Detection target: customers whose sub-EUR1000 activity hits 5+ within a short window. Anchored to:

- FATF Recommendation 10 (CDD and ongoing transaction monitoring)
- MiCA Articles 67-68 (CASP transaction monitoring obligations)
- AMLD6 Article 13 (suspicious activity detection and reporting)
- MASAK Law No. 5549 Article 4 (TR equivalent reporting threshold)
- EU AI Act Article 12 (record-keeping for high-risk financial crime AI)

## How it's built in Marble

Four components.

**Trigger condition**: `transactions where amount_eur < 1000`. This is the pre-filter. 8910 transactions out of 10277 skip evaluation entirely because they're over the threshold. Compute optimization, not detection logic.

**Aggregate variable**: `tx_count_24h_under_1000`. Counts `transaction_id` from the transactions table, filtered by `customer_id` equal to the trigger object's customer_id, and `amount_eur < 1000`.

**Rule**: `tx_count_24h_under_1000 >= 5`. Score modifier +50 when true. Named "5+ sub-EUR1000 transactions in 24h window".

**Decision thresholds:**

| Score | Outcome |
|---|---|
| < 30 | Approve |
| 30 - 70 | Review |
| 70 - 100 | Block and Review |
| ≥ 100 | Decline |

A single firing of this rule produces score 50, which lands in Review. Thresholds are calibrated for a one-rule-at-a-time scenario; in a multi-rule pack the same firing wouldn't bias outcomes.

## Why the immutability matters

Marble enforces commit and activate as two steps. V1 is locked once activated; you can't edit it, only ship V2 as a new draft. This is what gets a fintech through an AMLD6 Article 23 audit: every alert traces back to an exact rule version, with timestamp, and no one can rewrite history.

For EU AI Act Article 12 the same property doubles as the record-keeping mechanism for a high-risk system.

## Results

| | |
|---|---|
| Input transactions | 10277 |
| Trigger-matched (sub-EUR1000) | 1367 |
| Rule firings | 1367 |
| Outcome | 1367 × Review |
| Batch status | Success |
| Batch wallclock | < 1min |

## Known gaps

**Time window not implemented in V1.** The rule name says "24h window" but the variable doesn't filter on timestamp. Marble's UI exposes `Now()` and date operators, but the exact pattern for "timestamp within 24h relative to the trigger" didn't resolve in the build window I gave V1. I shipped without it rather than block on UI discovery.

Net effect: the variable counts lifetime sub-EUR1000 transactions instead of trailing-24h. The rule fires on long-tail customers who happen to have 5+ small transactions across months. That's not structuring, that's a regular customer with low-ticket activity.

**False positive cost.** Synthetic ground truth had 72 expected firings (12 STRUCTURING-seeded customers × 6 transactions each). Actual firings: 1367. ~1800% over design. 1295 alerts are noise.

At 30 minutes per alert investigation (standard L1 estimate), the noise costs roughly 648 analyst hours. For a 5-person L1 team working 160h/month, that's most of a month consumed by one miscalibrated rule.

**Cross-typology contamination.** Designed for STRUCTURING. Without the time window it also catches SMURFING - the seeded pattern of 15 customers × 3 transactions sending to a funnel wallet. Two AML typologies, one rule, no way for the L1 analyst to know which typology the alert represents from the decision detail alone. Triaging without typology context burns time before any investigation work starts.

## Sample firing

One of the 1367 decisions, drilled down:

- Decision ID: `019e4a4b-c0b0-71...`
- Transaction: `TX-S6-CUST-0495-2` (`S6` prefix is the synthetic seed marker for SMURFING)
- Customer: `CUST-0495`
- Amount: EUR 369.58, `fiat_deposit` channel, EUR currency
- Counterparty country: Austria
- Travel rule fields: originator complete, beneficiary complete
- Timestamp: 2026-05-17 14:30
- Rule hit: "5+ sub-EUR1000 transactions in 24h window", +50
- Outcome: Review

Worth flagging: this is a true positive against the synthetic ground truth (the seed says SMURFING), but the rule was designed for STRUCTURING. Right answer, wrong reason. In production the analyst wouldn't have the seed marker, which is what makes typology contamination a real operational cost.

## V2 plan

1. Add `transactions.timestamp >= Now() - 24h` to the variable's filter set. Restores temporal velocity, kills the long-tail false positives.
2. Split this into two scenarios. Structuring stays on velocity. Smurfing moves to scenario 06 with a different signal (counterparty graph rather than customer-level count).
3. Drop the threshold to `≥ 3` and the amount filter to `< EUR 500`. The seeded structuring pattern uses smaller transactions than EUR 1000; 5+ catches stragglers but misses the tight bursts.
4. Add a parallel aggregate: `sum(amount_eur)` over the 24h window. Fire only when count ≥ 5 AND sum > EUR 4000. Filters out genuine high-frequency low-ticket retail.

## Screenshots

- [scenario-01-batch-execution-success.png](../../demo/screenshots/scenario-01-batch-execution-success.png): the 1367 / 1367 / 1367 Success batch row
- [scenario-01-decisions-list.png](../../demo/screenshots/scenario-01-decisions-list.png): decisions list filtered to this scenario, V1 Live, all Review
- [scenario-01-decision-detail-smurfing.png](../../demo/screenshots/scenario-01-decision-detail-smurfing.png): single decision with trigger object panel and rule hit

## Data files

- Customer master: [01-synthetic-data/customers_marble.csv](../../01-synthetic-data/customers_marble.csv) - 500 rows, pre-formatted for Marble ingestion
- Transactions: [01-synthetic-data/transactions_marble.csv](../../01-synthetic-data/transactions_marble.csv) - 10277 rows, includes synthetic seed markers in `suspicious_seed`
