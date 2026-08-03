# Predicting 30-Day Readmission in Hospitalised Patients with Type 2 Diabetes Using Machine Learning

## Abstract

Unplanned readmission within 30 days of discharge is a widely used indicator of care quality
and a substantial driver of hospital cost. We developed and evaluated machine learning models
to predict 30-day readmission among inpatients with type 2 diabetes mellitus, using routinely
collected clinical and administrative data available at the point of discharge.

## Methods

### Study population and data source

We retrospectively analysed the electronic health records of adult inpatients discharged from a
tertiary teaching hospital. Patients younger than 20 years and those who died during the index
admission were excluded.

### Predictor variables

Ten variables available at discharge were used as model inputs:

| Variable | Type | Description |
|---|---|---|
| `age` | numerical | Patient age in years at admission |
| `gender` | categorical | Biological sex, recorded as M or F |
| `bmi` | numerical | Body mass index at admission (kg/m²) |
| `hba1c` | numerical | Glycated haemoglobin (%) measured during the index admission |
| `systolic_blood_pressure` | numerical | Systolic blood pressure at admission (mmHg) |
| `length_of_stay` | numerical | Duration of the index admission, in days |
| `admission_date` | date | Date of admission for the index episode |
| `diabetes_diagnosis` | categorical | Whether type 2 diabetes was a recorded diagnosis |
| `pain_score` | numerical | Numeric rating scale for pain at admission (0–10) |
| `charlson_index` | numerical | Charlson comorbidity index score |

The outcome variable was `readmission_30d`, a binary indicator of unplanned readmission to any
department within 30 days of discharge.

### Preprocessing

Missing values in continuous predictors were imputed with the column mean. All continuous
predictors were standardised to zero mean and unit variance. Categorical predictors were
one-hot encoded.

### Class imbalance

Because 30-day readmission is comparatively rare in this cohort, we applied SMOTE to the
training partition only, using five nearest neighbours. Resampling was never applied to the
validation or test partitions.

### Models

We compared logistic regression as a baseline against Random Forest and XGBoost.

### Validation and metrics

Models were assessed with stratified 10-fold cross-validation. We report balanced accuracy,
AUC, AUPRC, F1, recall and specificity. Because the outcome is imbalanced, AUPRC was treated
as the primary metric.

## Results

XGBoost achieved the highest AUC, followed by Random Forest. Length of stay, HbA1c and the
Charlson comorbidity index were the three most influential predictors in the final model.

## Conclusion

Routinely collected discharge-time variables can identify patients at elevated risk of 30-day
readmission with useful discrimination, supporting targeted follow-up for high-risk patients.
