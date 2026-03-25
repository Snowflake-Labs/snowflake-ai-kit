---
name: ml-model-registry
description: "Train, register, and deploy ML models using Snowflake Model Registry. Use for: training models, logging models, model versioning, warehouse inference, SPCS inference service, scikit-learn on Snowflake, XGBoost on Snowflake, model deployment. Triggers: model registry, train model, register model, log model, deploy model, ml pipeline, model inference, model versioning, snowflake ml, churn prediction, classification model, regression model."
---

# ML Model Registry

Train a model, register it in Snowflake's Model Registry, and run inference — all without moving data out of Snowflake.

## When to Use

- User wants to train and deploy an ML model on Snowflake
- User asks about Snowflake Model Registry or `snowflake-ml-python`
- User wants to log a trained model (sklearn, XGBoost, PyTorch, etc.)
- User needs model versioning and inference in a warehouse
- User wants to deploy a model as a REST service via SPCS

## Tools Used

- `snowflake_sql_execute` — Create schemas, tables, seed data, verify
- `notebook_actions` — Train model and register in Python (if in notebook)
- `ask_user_question` — Confirm targets, framework choices
- `read` / `write` / `edit` — Configure templates with user-specific values

## Bundled Files

```
ml-model-registry/
├── SKILL.md                    # This file (agent instructions)
├── README.md                   # Human-facing docs
└── templates/
    ├── setup.sql               # Create ML.REGISTRY schema, seed CUSTOMER_CHURN
    ├── train-and-register.py   # Train sklearn model, log_model(), run inference
    └── deploy-service.py       # Deploy as SPCS inference service
```

## Stopping Points

- Phase 0: User approves the workflow before any action
- Step 1: User confirms target objects and ML framework
- Step 3: User reviews model metrics before deployment
- Step 5: User decides on warehouse inference vs SPCS service

---

## Phase 0: Briefing and Consent

Present the following briefing to the user:

> ### ML Model Registry — What This Skill Does
>
> I'll build an end-to-end ML pipeline using Snowflake's Model Registry.
> Your data stays in Snowflake throughout training, registration, and inference.
>
> **What gets created:**
> 1. A registry schema (ML.REGISTRY) for storing models
> 2. Training data table (demo or yours)
> 3. A trained and registered model with version tracking
> 4. Inference results via warehouse or SPCS service
>
> **ML lifecycle:**
> ```
> Prepare Data → Train Model → log_model() → mv.run() (inference)
>                                           → mv.create_service() (optional REST API)
> ```
>
> **Supported frameworks:**
> scikit-learn, XGBoost, LightGBM, PyTorch, TensorFlow, HuggingFace Transformers, custom models
>
> **Two inference options:**
> - **Warehouse** — SQL-based batch inference, no extra infrastructure
> - **SPCS** — REST endpoint, GPU support, auto-scaling
>
> Ready to proceed?

**⚠️ MANDATORY STOPPING POINT**: Wait for user approval before continuing.

---

## Step 1: Gather Targets

Ask the user:

```
Let me set up the ML pipeline. A few questions:

- Database for registry: (e.g., ML)
- Schema for registry: (e.g., REGISTRY)
- Database/schema for training data: (e.g., ML.DATA)
- Warehouse: (e.g., COMPUTE_WH)
- ML framework: (sklearn, xgboost, lightgbm, pytorch, or other)
- Use demo data or your own dataset?
```

**⚠️ MANDATORY STOPPING POINT**: Wait for response.

If the user has their own data, ask about:
- Target column (what to predict)
- Feature columns (inputs)
- Task type (classification or regression)

---

## Step 2: Setup Environment

Read `templates/setup.sql` and substitute:
- `{{DATABASE}}` → user's registry database (e.g., ML)
- `{{SCHEMA}}` → user's registry schema (e.g., REGISTRY)
- `{{DATA_SCHEMA}}` → where training data lives (e.g., ML.DATA)
- `{{WAREHOUSE}}` → user's warehouse

Execute the setup SQL. This creates:
- `ML.REGISTRY` schema for model storage
- `ML.DATA.CUSTOMER_CHURN` table with 1000 synthetic customer records

Verify:

```sql
SELECT COUNT(*) AS total_rows,
       ROUND(AVG(CASE WHEN CHURNED = 1 THEN 1.0 ELSE 0.0 END), 2) AS churn_rate
FROM {{DATABASE}}.DATA.CUSTOMER_CHURN;
```

---

## Step 3: Train and Register Model

Read `templates/train-and-register.py` and substitute placeholders.

This script:
1. Connects to Snowflake and loads training data into a Snowpark DataFrame
2. Splits into train/test sets
3. Trains a model (default: sklearn RandomForestClassifier)
4. Evaluates accuracy, precision, recall
5. Logs the model to registry with `reg.log_model()`
6. Runs test inference with `mv.run()`

**Key code pattern:**

```python
from snowflake.ml.registry import Registry

reg = Registry(session=session, database_name="ML", schema_name="REGISTRY")

mv = reg.log_model(
    model=clf,
    model_name="customer_churn_model",
    version_name="v1",
    conda_dependencies=["scikit-learn"],
    comment="Random Forest churn classifier",
    metrics={"accuracy": accuracy, "f1": f1_score},
    sample_input_data=X_test
)

# Run inference
predictions = mv.run(X_test)
```

**⚠️ MANDATORY STOPPING POINT**: Show model metrics to user. Ask if they're satisfied or want to retrain with different parameters.

---

## Step 4: Model Management

After registration, useful operations:

```python
# List all models
reg.show_models()

# Get a specific model version
mv = reg.get_model("customer_churn_model").version("v1")

# Check model metadata
mv.show_functions()    # Available inference functions
mv.get_metric("accuracy")

# Add tags (after first version exists)
m = reg.get_model("customer_churn_model")
m.tags = {"team": "data-science", "use_case": "retention"}

# Log a new version
mv2 = reg.log_model(
    model=new_clf,
    model_name="customer_churn_model",
    version_name="v2",
    ...
)

# Set default version
m.default = mv2
```

---

## Step 5: Choose Inference Path

Ask the user:

```
Your model is registered. How would you like to run inference?

1. Warehouse — Run predictions via SQL (simpler, no extra infra)
2. SPCS Service — Deploy as a REST endpoint (GPU, auto-scaling)
3. Both — Register for warehouse now, deploy service later
```

**⚠️ MANDATORY STOPPING POINT**: Wait for response.

### Warehouse Inference

```python
# Python
predictions = mv.run(new_data_df)
```

```sql
-- SQL (after model is registered)
SELECT
    ML.REGISTRY.customer_churn_model!predict(
        TENURE_MONTHS, MONTHLY_CHARGES, TOTAL_CHARGES,
        CONTRACT_TYPE, PAYMENT_METHOD, NUM_SUPPORT_TICKETS
    ) AS prediction
FROM ML.DATA.NEW_CUSTOMERS;
```

### SPCS Service Deployment

Read `templates/deploy-service.py` and substitute placeholders. This creates a containerized inference endpoint:

```python
mv.create_service(
    service_name="churn_prediction_service",
    service_compute_pool="{{COMPUTE_POOL}}",
    image_build_compute_pool="{{COMPUTE_POOL}}",
    max_instances=1,
    min_instances=0  # scale to zero when idle
)
```

---

## Output

- A trained ML model registered in Snowflake Model Registry with version tracking and logged metrics
- Warehouse-based SQL inference or an SPCS REST endpoint for real-time predictions
- Access control grants so analysts can run inference without managing model artifacts

## Supported Frameworks

| Framework | log_model() Support | Notes |
|-----------|-------------------|-------|
| scikit-learn | Built-in | Auto-detects dependencies |
| XGBoost | Built-in | Supports Booster and XGBClassifier |
| LightGBM | Built-in | Supports Booster and LGBMClassifier |
| PyTorch | Built-in | Single tensor input by default |
| TensorFlow | Built-in | SavedModel format |
| HuggingFace | Built-in | TransformersPipeline wrapper |
| Custom | CustomModel class | Subclass `custom_model.CustomModel` |
| MLflow | Supported | Models from `mlflow.*.save_model()` |

## CustomModel Example

For models that don't fit built-in types:

```python
from snowflake.ml.model import custom_model

class MyModel(custom_model.CustomModel):
    @custom_model.inference_api
    def predict(self, input_df: pd.DataFrame) -> pd.DataFrame:
        # Your inference logic here
        results = self.context.model_ref.predict(input_df)
        return pd.DataFrame({"prediction": results})
```

## Dependencies

- **Warehouse inference**: Packages must be available in the Snowflake conda channel (or use `artifact_repository_map` with PyPI)
- **SPCS inference**: Any pip-installable package works
- **Best practice**: Match the Python version used for training with the inference environment

```python
# Use PyPI for packages not in Snowflake conda channel
mv = reg.log_model(
    model=clf,
    model_name="my_model",
    artifact_repository_map={"pip": "snowflake.snowpark.pypi_shared_repository"},
    pip_requirements=["scikit-learn==1.5.0"],
    sample_input_data=X_test
)
```

## Access Control

```sql
-- Grant model creation
GRANT CREATE MODEL ON SCHEMA ML.REGISTRY TO ROLE DATA_SCIENTIST;

-- Grant model usage (inference)
GRANT USAGE ON MODEL ML.REGISTRY.CUSTOMER_CHURN_MODEL TO ROLE ANALYST;
```
