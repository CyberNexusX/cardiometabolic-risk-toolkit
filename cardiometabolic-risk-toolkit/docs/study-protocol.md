# Study protocol

## Cohort and endpoint

The observation unit is one synthetic adult per prediction date. Eligibility requires an existing prediabetes record on or before the prediction date, no recorded type 2 diabetes by that date, and a full year of simulated follow-up. The outcome is the first type 2 diabetes record from day 1 through day 365 inclusive. The endpoint is a recorded diagnosis and can differ from biological onset.

The demo excludes everyone with incomplete follow-up, even when an event was recorded early. A real study would assess the selection bias from this rule and consider time-to-event methods and how enrollment and death are observed.

## Features and timing

- Age in completed years on the index date.
- Latest final A1c in UCUM percent from the preceding 365 days, using only results with an issue date on or before the index date.
- Difference between the latest A1c and the most recent A1c measured on a distinct earlier day. Missing prior measurements produce a missing change value.

The demo uses date-level availability and inclusive prediction-day cutoffs. Same-day measurement and availability ordering would need timestamp-level rules for a real deployment. The parser supports the generated FHIR resource subset and relative patient references. General FHIR profile validation, terminology expansion, time-zone normalization, and reconciliation of duplicate clinical records would be separate integration work.

## Evaluation

Train on north and south clinic patients indexed in 2022. Evaluate on different north and south patients indexed in 2024 and on coastal patients indexed in 2024. No coastal observations enter training. Fit imputation, missingness indicators, and scaling on the training population only. The model is logistic regression with default regularization and fixed iteration limit. The comparator predicts the training event prevalence for every patient.

AUROC and average precision describe discrimination. Brier score measures squared probability error. Report mean predicted probability, observed outcome frequency, and fixed-width calibration bins. Report age strata below 65 and at 65 or above with denominators and event counts. Subgroup metrics are illustrative and do not establish clinical fairness.

## What this experiment establishes

The generator deliberately relates future diagnosis to A1c and age. It also inserts an outcome-correlated future lab to make leakage detectable. The coastal clinic changes the outcome probability and missingness rate. Consequently, performance values measure behavior under the simulation design, and the held-out clinic cannot establish real external validity. No clinical data, treatment recommendations, or patient-facing decision workflow are included.
