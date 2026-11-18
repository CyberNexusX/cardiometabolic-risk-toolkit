"""Reproducible cardiometabolic risk study using generated FHIR R4 records."""
import argparse
import csv
from datetime import date, timedelta
import json
from pathlib import Path

import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SNOMED = "http://snomed.info/sct"
LOINC = "http://loinc.org"
A1C = "4548-4"
PREDIABETES = "714628002"
DIABETES = "44054006"
FEATURES = ("age_years", "latest_a1c", "a1c_change")
HORIZON = 365


def coding(system, code):
    return {"coding": [{"system": system, "code": code}]}


def has_code(concept, system, code):
    return any(
        item.get("system") == system and item.get("code") == code
        for item in concept.get("coding", [])
    )


def generate(seed):
    """Produce a collection Bundle and separate synthetic study metadata."""
    rng = np.random.default_rng(seed)
    entries, metadata = [], {}
    design = (
        ("north", date(2022, 1, 1), 1000),
        ("south", date(2022, 1, 1), 1000),
        ("north", date(2024, 1, 1), 450),
        ("south", date(2024, 1, 1), 450),
        ("coastal", date(2024, 1, 1), 900),
    )

    def add(resource):
        entries.append({"resource": resource})

    for site, period, size in design:
        for _ in range(size):
            patient_id = f"synthetic-{len(metadata) + 1:05d}"
            index = period + timedelta(days=int(rng.integers(0, 90)))
            age = int(rng.integers(30, 81))
            subject = {"reference": f"Patient/{patient_id}"}
            observed_days = 180 if rng.random() < 0.07 else HORIZON
            metadata[patient_id] = {
                "site": site,
                "index_date": index.isoformat(),
                "observed_through": (index + timedelta(days=observed_days)).isoformat(),
            }
            add({
                "resourceType": "Patient", "id": patient_id,
                "birthDate": date(index.year - age, 1, 1).isoformat(),
            })
            add({
                "resourceType": "Condition", "id": f"{patient_id}-baseline",
                "subject": subject, "code": coding(SNOMED, PREDIABETES),
                "recordedDate": index.isoformat(),
            })
            latest = float(np.clip(rng.normal(6.0, 0.24), 5.7, 6.4))
            change = float(rng.normal(0.12, 0.20))
            log_odds = -2.2 + 3.0 * (latest - 6) + 1.8 * change + 0.022 * (age - 55)
            if site == "coastal":
                log_odds += 0.65
            has_outcome = rng.random() < 1 / (1 + np.exp(-log_odds))
            outcome_day = int(rng.integers(1, HORIZON + 1))
            if has_outcome and outcome_day <= observed_days:
                add({
                    "resourceType": "Condition", "id": f"{patient_id}-outcome",
                    "subject": subject, "code": coding(SNOMED, DIABETES),
                    "recordedDate": (index + timedelta(days=outcome_day)).isoformat(),
                })
            for suffix, days, value in (
                ("prior", -180, latest - change),
                ("latest", -10, latest),
                ("future", 30, 7.2 if has_outcome else 5.8),
            ):
                missing_rate = 0.22 if site == "coastal" else 0.10
                if suffix == "prior" and rng.random() < missing_rate:
                    continue
                add({
                    "resourceType": "Observation", "id": f"{patient_id}-{suffix}",
                    "status": "final", "subject": subject, "code": coding(LOINC, A1C),
                    "effectiveDateTime": (index + timedelta(days=days)).isoformat(),
                    "issued": (index + timedelta(days=days + 1)).isoformat() + "T12:00:00Z",
                    "valueQuantity": {
                        "value": round(value, 2), "unit": "%",
                        "system": "http://unitsofmeasure.org", "code": "%",
                    },
                })
    return {"resourceType": "Bundle", "type": "collection", "entry": entries}, metadata


def partition(site, index):
    if site == "coastal":
        return "held_out_site"
    return "train" if index.year == 2022 else "later_period"


def build_cohort(bundle, metadata):
    """Extract features available at the prediction date and fixed-horizon labels."""
    patients = {}
    records = {patient_id: [] for patient_id in metadata}
    for entry in bundle["entry"]:
        resource = entry["resource"]
        if resource["resourceType"] == "Patient":
            patients[resource["id"]] = resource
        else:
            reference = resource.get("subject", {}).get("reference", "")
            patient_id = reference.removeprefix("Patient/")
            if reference.startswith("Patient/") and patient_id in records:
                records[patient_id].append(resource)

    rows = []
    for patient_id, study in metadata.items():
        index = date.fromisoformat(study["index_date"])
        birth = date.fromisoformat(patients[patient_id]["birthDate"])
        age = index.year - birth.year - ((index.month, index.day) < (birth.month, birth.day))
        follow_up = date.fromisoformat(study["observed_through"])
        horizon = index + timedelta(days=HORIZON)
        if age < 18 or follow_up < horizon:
            continue
        baseline, diabetes_dates, labs = False, [], []
        for record in records[patient_id]:
            concept = record.get("code", {})
            if record["resourceType"] == "Condition":
                recorded = date.fromisoformat(record["recordedDate"][:10])
                if has_code(concept, SNOMED, PREDIABETES) and recorded <= index:
                    baseline = True
                if has_code(concept, SNOMED, DIABETES):
                    diabetes_dates.append(recorded)
            elif record["resourceType"] == "Observation" and has_code(concept, LOINC, A1C):
                quantity = record.get("valueQuantity", {})
                if (
                    record.get("status") != "final"
                    or quantity.get("system") != "http://unitsofmeasure.org"
                    or quantity.get("code") != "%"
                    or not record.get("effectiveDateTime")
                    or not record.get("issued")
                ):
                    continue
                effective = date.fromisoformat(record["effectiveDateTime"][:10])
                available = date.fromisoformat(record["issued"][:10])
                if index - timedelta(days=365) <= effective <= available <= index:
                    labs.append((effective, available, record["id"], float(quantity["value"])))
        if not baseline or any(recorded <= index for recorded in diabetes_dates):
            continue
        labs.sort(reverse=True)
        latest = labs[0][3] if labs else None
        prior = next((lab[3] for lab in labs if lab[0] < labs[0][0]), None) if labs else None
        rows.append({
            "patient_id": patient_id, "site": study["site"],
            "index_date": study["index_date"], "split": partition(study["site"], index),
            "age_years": age, "latest_a1c": latest,
            "a1c_change": round(latest - prior, 2) if prior is not None else None,
            "latest_a1c_record": labs[0][2] if labs else None,
            "outcome": int(any(index < recorded <= horizon for recorded in diabetes_dates)),
        })
    return rows


def matrix(rows):
    return np.array([[row[feature] for feature in FEATURES] for row in rows], dtype=float)


def metrics(rows, probabilities):
    labels = np.array([row["outcome"] for row in rows])
    sample_size = len(rows)
    if not sample_size:
        return {"n": 0}
    has_both_classes = len(np.unique(labels)) == 2
    bins = []
    bin_indices = np.minimum((probabilities * 5).astype(int), 4)
    for index in range(5):
        included = bin_indices == index
        if included.any():
            bins.append({
                "range": [index / 5, (index + 1) / 5],
                "n": int(included.sum()),
                "observed_rate": float(labels[included].mean()),
                "mean_score": float(probabilities[included].mean()),
            })
    return {
        "n": sample_size, "events": int(labels.sum()),
        "observed_rate": float(labels.mean()), "mean_score": float(probabilities.mean()),
        "auroc": float(roc_auc_score(labels, probabilities)) if has_both_classes else None,
        "average_precision": float(average_precision_score(labels, probabilities))
        if has_both_classes else None,
        "brier": float(brier_score_loss(labels, probabilities)),
        "calibration_bins": bins,
    }


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def run(seed, output):
    output.mkdir(parents=True, exist_ok=True)
    bundle, metadata = generate(seed)
    rows = build_cohort(bundle, metadata)
    train = [row for row in rows if row["split"] == "train"]
    model = make_pipeline(SimpleImputer(strategy="median", add_indicator=True),
                          StandardScaler(), LogisticRegression(max_iter=1000))
    model.fit(matrix(train), [row["outcome"] for row in train])
    prevalence = float(np.mean([row["outcome"] for row in train]))
    report = {
        "synthetic_only": True, "seed": seed, "horizon_days": HORIZON,
        "patients_generated": len(metadata), "patients_included": len(rows),
        "training_patients": len(train), "training_event_rate": prevalence,
        "evaluation": {},
    }
    predictions = []
    for split in ("later_period", "held_out_site"):
        subset = [row for row in rows if row["split"] == split]
        scores = model.predict_proba(matrix(subset))[:, 1]
        baseline = np.full(len(subset), prevalence)
        report["evaluation"][split] = {
            "logistic_regression": metrics(subset, scores),
            "constant_baseline": metrics(subset, baseline),
            "age_subgroups": {},
        }
        for group, mask in (("age_under_65", [r["age_years"] < 65 for r in subset]),
                            ("age_65_plus", [r["age_years"] >= 65 for r in subset])):
            group_rows = [row for row, included in zip(subset, mask) if included]
            report["evaluation"][split]["age_subgroups"][group] = metrics(group_rows, scores[mask])
        predictions.extend({**row, "synthetic_risk_score": float(score)}
                           for row, score in zip(subset, scores))
    write_json(output / "synthetic-fhir.json", bundle)
    write_json(output / "study-metadata.json", metadata)
    write_json(output / "validation-report.json", report)
    with (output / "evaluation-predictions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(predictions[0]))
        writer.writeheader()
        writer.writerows(predictions)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path("build/demo"))
    args = parser.parse_args()
    result = run(args.seed, args.out)
    print(f"Included {result['patients_included']:,} synthetic patients.")
    print(f"Validation report: {args.out / 'validation-report.json'}")
