# Methodology

## Analytical scope

The project focuses on retrospective analysis of historical open data and educational demonstrations of machine-learning methods.

## Analysis levels

### Descriptive
What happened in the historical dataset?

Examples:
- event counts over time;
- regional distributions;
- category distributions;
- rolling averages.

### Diagnostic
What historical patterns are visible?

Examples:
- weekday/time-window differences;
- changes between periods;
- regional concentration;
- temporal autocorrelation.

### Predictive demonstration
Can historical features provide a statistically useful estimate of an aggregated future event label?

The initial target is intentionally aggregated and educational. The project does not aim to forecast exact strike targets, exact routes, or operationally actionable locations.

## Validation principles

- split data chronologically where appropriate;
- avoid leakage from future observations;
- compare against a naive baseline;
- report class imbalance;
- use Precision, Recall, F1, ROC-AUC and PR-AUC;
- record feature definitions;
- document model limitations.

## Reproducibility

Raw data stays unchanged. Cleaning and feature engineering must be implemented in code and rerunnable from source snapshots.
