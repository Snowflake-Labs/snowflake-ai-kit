# ML Model Registry

Train, register, and deploy ML models using Snowflake's Model Registry — from scikit-learn to HuggingFace Transformers.

## What It Does

This skill guides your AI coding agent through the full ML lifecycle on Snowflake:

1. **Setup** — Create a registry schema and prepare training data
2. **Train** — Build a model using scikit-learn (or XGBoost, LightGBM, etc.)
3. **Register** — Log the model to Snowflake Model Registry with `log_model()`
4. **Inference** — Run predictions with `mv.run()` in a warehouse
5. **Deploy** — (Optional) Deploy as a REST endpoint via SPCS with `mv.create_service()`

## Prerequisites

- Snowflake account with `snowflake-ml-python` package available
- A warehouse for training and inference
- (Optional) SPCS compute pool for service deployment

## Quick Start

Ask your AI coding agent:

> "Train a churn prediction model and register it in Snowflake's Model Registry"

Or for a demo:

> "Build a demo ML pipeline: train a model, register it, and run inference in Snowflake"

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Agent instructions and workflow |
| `templates/setup.sql` | Create ML.REGISTRY schema, seed CUSTOMER_CHURN data |
| `templates/train-and-register.py` | Train sklearn model, log to registry, run inference |
| `templates/deploy-service.py` | Deploy registered model as SPCS service |
