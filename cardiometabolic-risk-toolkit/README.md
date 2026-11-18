# Cardiometabolic Risk Toolkit

A reproducible research prototype for estimating the probability of a first recorded type 2 diabetes diagnosis within 365 days among adults with a recorded prediabetes diagnosis. The demo generates synthetic FHIR R4 records, constructs a longitudinal cohort, trains a logistic regression model, and evaluates it on a later period and an unseen simulated clinic.

This is an independent MedScope Analytics research project. All records and results in the demo are simulated. Intended use is software and methods evaluation.

## Quick start

Requires Python 3.11 or 3.12. From the repository directory:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python risk_study.py
python -m unittest discover -s tests -v
```

On Windows PowerShell, use `.venv\Scripts\Activate.ps1` for activation. Change the demo seed or output directory with `--seed 42 --out build/demo`.

| Generated file | Contents |
|---|---|
| `synthetic-fhir.json` | FHIR R4 collection with Patient, Condition, and Observation resources |
| `study-metadata.json` | Simulated clinic, prediction date, and observation end date |
| `evaluation-predictions.csv` | Held-out features, source ID for latest A1c, outcome, and synthetic risk score |
| `validation-report.json` | Sample sizes, event rates, AUROC, average precision, Brier score, calibration bins, and age subgroup summaries |

## Sample use cases

1. **Check what the model could know at baseline.** Trace a row's `latest_a1c_record` to its Observation. Compare the measurement and issue dates with the prediction date. The tests verify that future measurements and delayed results are excluded.
2. **Investigate performance at a new clinic.** Compare mean predicted risk with observed event rates for `later_period` and `held_out_site`. The simulated coastal clinic has a higher underlying event probability and more missing historical A1c values. Its results reflect a combined site and time shift.
3. **Assess whether the model adds information.** Compare average precision and Brier score against the constant training-prevalence baseline. Inspect subgroup event counts and calibration bins before interpreting differences.

See [study protocol](docs/study-protocol.md) for cohort rules, split design, and limitations. See [sample validation report](docs/sample-validation-report.json) for the default run.

## Scope

The first release demonstrates longitudinal FHIR feature extraction, fixed-horizon prediction, and reproducible temporal and simulated site evaluation. Real-world validation needs an independently defined cohort and appropriately authorized data. Federated evaluation, cloud deployment, and monitoring are future work. The scores have no established clinical validity and are unsuitable for patient care.
