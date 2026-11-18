# GitHub publishing fields

**Repository name** `cardiometabolic-risk-toolkit`

**Description**  
Reproducible type 2 diabetes risk modeling with synthetic FHIR R4 records, leakage checks, and temporal and held-out clinic validation.

**Topics**  
`healthcare-ai` `fhir` `diabetes` `risk-prediction` `synthetic-data` `model-validation` `scikit-learn`

**Initial release title**  
v0.1.0 · Synthetic FHIR diabetes risk study

**Release summary**  
Initial research prototype for the 365-day recorded diabetes endpoint. Includes a seeded synthetic FHIR generator, an auditable cohort definition, logistic regression and prevalence baselines, validation reports, and regression tests for feature leakage.

## Upload

Extract the archive and open its `cardiometabolic-risk-toolkit` folder. Create an empty GitHub repository using the name above. Run these commands from the extracted folder, substituting your GitHub username for OWNER:

```sh
git init -b main
git add .
git commit -m "Release synthetic FHIR diabetes risk study"
git remote add origin https://github.com/OWNER/cardiometabolic-risk-toolkit.git
git push -u origin main
```

The package leaves the license choice to the repository owner. Add a LICENSE before inviting public reuse.
