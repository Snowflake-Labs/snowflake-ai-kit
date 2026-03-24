# ============================================================
# ML Model Registry — Train and Register
# Train a sklearn model, log to registry, run inference
# ============================================================
#
# Prerequisites:
#   pip install snowflake-ml-python snowflake-snowpark-python
#
# This script can run in:
#   - Snowflake Notebook (recommended)
#   - Local Python environment with Snowflake connection
# ============================================================

from snowflake.snowpark import Session
from snowflake.ml.registry import Registry
import pandas as pd

# ── Connect to Snowflake ─────────────────────────────────────
# In a Snowflake Notebook, session is already available.
# For local execution, create a session:

# connection_params = {
#     "account": "{{ACCOUNT}}",
#     "user": "{{USER}}",
#     "password": os.environ["SNOWFLAKE_PASSWORD"],
#     "warehouse": "{{WAREHOUSE}}",
#     "database": "{{DATABASE}}",
#     "schema": "DATA",
#     "role": "{{ROLE}}"
# }
# session = Session.builder.configs(connection_params).create()

# ── Load training data ───────────────────────────────────────

df = session.table("{{DATABASE}}.DATA.CUSTOMER_CHURN").to_pandas()

print(f"Dataset: {len(df)} rows, churn rate: {df['CHURNED'].mean():.1%}")

# ── Feature engineering ──────────────────────────────────────

# Encode categoricals
df["CONTRACT_ENCODED"] = df["CONTRACT_TYPE"].map({
    "month-to-month": 0, "one-year": 1, "two-year": 2
})
df["PAYMENT_ENCODED"] = df["PAYMENT_METHOD"].map({
    "electronic_check": 0, "mailed_check": 1,
    "bank_transfer": 2, "credit_card": 3
})
df["HAS_PREMIUM_SUPPORT"] = df["HAS_PREMIUM_SUPPORT"].astype(int)

FEATURE_COLS = [
    "TENURE_MONTHS", "MONTHLY_CHARGES", "TOTAL_CHARGES",
    "CONTRACT_ENCODED", "PAYMENT_ENCODED",
    "NUM_SUPPORT_TICKETS", "HAS_PREMIUM_SUPPORT", "NUM_PRODUCTS"
]
TARGET_COL = "CHURNED"

X = df[FEATURE_COLS]
y = df[TARGET_COL]

# ── Train/test split ────────────────────────────────────────

from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"Train: {len(X_train)}, Test: {len(X_test)}")

# ── Train model ──────────────────────────────────────────────

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, classification_report

clf = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    random_state=42
)
clf.fit(X_train, y_train)

# Evaluate
y_pred = clf.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
f1 = f1_score(y_test, y_pred)

print(f"\nModel Performance:")
print(f"  Accuracy: {accuracy:.3f}")
print(f"  F1 Score: {f1:.3f}")
print(f"\n{classification_report(y_test, y_pred)}")

# ── Register model in Snowflake ──────────────────────────────

reg = Registry(
    session=session,
    database_name="{{DATABASE}}",
    schema_name="REGISTRY"
)

mv = reg.log_model(
    model=clf,
    model_name="customer_churn_model",
    version_name="v1",
    conda_dependencies=["scikit-learn"],
    comment="Random Forest churn classifier — 8 features, 100 trees",
    metrics={"accuracy": round(accuracy, 4), "f1_score": round(f1, 4)},
    sample_input_data=X_test
)

print(f"\nModel registered: customer_churn_model v1")
print(f"Functions: {mv.show_functions()}")

# ── Run inference ────────────────────────────────────────────

# Inference on test set
predictions = mv.run(X_test)
print(f"\nInference results (first 5 rows):")
print(predictions.head())

# ── Verify metrics ───────────────────────────────────────────

print(f"\nStored metrics:")
print(f"  accuracy: {mv.get_metric('accuracy')}")
print(f"  f1_score: {mv.get_metric('f1_score')}")

# ── List registered models ───────────────────────────────────

print(f"\nAll models in registry:")
print(reg.show_models())
