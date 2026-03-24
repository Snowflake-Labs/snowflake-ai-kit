# ============================================================
# ML Model Registry — Deploy as SPCS Service
# Creates a containerized inference endpoint
# ============================================================
#
# Prerequisites:
#   - Model already registered in Snowflake Model Registry
#   - SPCS compute pool available
#   - snowflake-ml-python >= 1.5.0
# ============================================================

from snowflake.snowpark import Session
from snowflake.ml.registry import Registry

# ── Connect to Snowflake ─────────────────────────────────────
# In a Snowflake Notebook, session is already available.
# For local execution, create a session (see train-and-register.py)

# ── Get the registered model ─────────────────────────────────

reg = Registry(
    session=session,
    database_name="{{DATABASE}}",
    schema_name="REGISTRY"
)

# Get the model version to deploy
mv = reg.get_model("customer_churn_model").version("v1")

print(f"Model: customer_churn_model v1")
print(f"Functions: {mv.show_functions()}")

# ── Deploy as SPCS inference service ─────────────────────────

mv.create_service(
    service_name="churn_prediction_service",
    service_compute_pool="{{COMPUTE_POOL}}",
    image_build_compute_pool="{{COMPUTE_POOL}}",
    max_instances=1,
    min_instances=0  # Scale to zero when idle
)

print("Service deployment initiated: churn_prediction_service")
print("Note: First deployment may take several minutes to build the container image.")

# ── Check service status ─────────────────────────────────────

# Via SQL:
# DESCRIBE SERVICE {{DATABASE}}.REGISTRY.CHURN_PREDICTION_SERVICE;
# SHOW SERVICES IN SCHEMA {{DATABASE}}.REGISTRY;

# ── Test the service ─────────────────────────────────────────

import pandas as pd

test_data = pd.DataFrame({
    "TENURE_MONTHS": [12, 36, 3],
    "MONTHLY_CHARGES": [85.50, 45.00, 110.00],
    "TOTAL_CHARGES": [1026.00, 1620.00, 330.00],
    "CONTRACT_ENCODED": [0, 2, 0],       # month-to-month, two-year, month-to-month
    "PAYMENT_ENCODED": [0, 3, 0],         # electronic_check, credit_card, electronic_check
    "NUM_SUPPORT_TICKETS": [5, 1, 8],
    "HAS_PREMIUM_SUPPORT": [0, 1, 0],
    "NUM_PRODUCTS": [1, 3, 1]
})

predictions = mv.run(test_data)
print("\nPredictions:")
print(predictions)

# ── HuggingFace model deployment (alternative) ───────────────
# For deploying a HuggingFace model with vLLM inference engine:

# from snowflake.ml.model import openai_signatures
# from snowflake.ml.model.inference_engine import InferenceEngine
# from snowflake.ml.model import huggingface
#
# model = huggingface.TransformersPipeline(
#     model="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
#     task="text-generation",
# )
#
# mv = reg.log_model(
#     model=model,
#     model_name="tinyllama_chat",
#     target_platforms=["SNOWPARK_CONTAINER_SERVICES"],
#     signatures=openai_signatures.OPENAI_CHAT_SIGNATURE,
# )
#
# mv.create_service(
#     service_name="llm_chat_service",
#     service_compute_pool="GPU_POOL",
#     image_build_compute_pool="GPU_POOL",
#     max_instances=1,
#     inference_engine_options={
#         "engine": InferenceEngine.VLLM,
#         "engine_args_override": [
#             "--max-model-len=2048",
#             "--gpu-memory-utilization=0.9"
#         ]
#     }
# )

# ── Cleanup (if needed) ─────────────────────────────────────

# Drop service:
# session.sql("DROP SERVICE IF EXISTS {{DATABASE}}.REGISTRY.CHURN_PREDICTION_SERVICE").collect()

# Delete model version:
# reg.get_model("customer_churn_model").delete_version("v1")

# Delete entire model:
# reg.delete_model("customer_churn_model")
