-- ============================================================
-- Cortex MCP Server — Setup
-- Creates prerequisite UDFs and demo tools for MCP exposure
-- ============================================================

USE ROLE {{ROLE}};
USE WAREHOUSE {{WAREHOUSE}};

CREATE DATABASE IF NOT EXISTS {{DATABASE}};
CREATE SCHEMA IF NOT EXISTS {{DATABASE}}.{{SCHEMA}};
USE SCHEMA {{DATABASE}}.{{SCHEMA}};

-- ────────────────────────────────────────────────────────────
-- Example UDFs for custom MCP tools
-- ────────────────────────────────────────────────────────────

-- Simple scalar UDF
CREATE OR REPLACE FUNCTION MULTIPLY_BY_TEN(x FLOAT)
  RETURNS FLOAT
  LANGUAGE PYTHON
  RUNTIME_VERSION = '3.8'
  HANDLER = 'multiply_by_ten'
  AS $$
def multiply_by_ten(x: float) -> float:
    return x * 10
$$;

-- UDF returning structured data (VARIANT)
CREATE OR REPLACE FUNCTION CALCULATE_METRICS(revenue FLOAT, cost FLOAT)
  RETURNS VARIANT
  LANGUAGE PYTHON
  RUNTIME_VERSION = '3.8'
  HANDLER = 'calculate_metrics'
  AS $$
import json
def calculate_metrics(revenue: float, cost: float) -> dict:
    profit = revenue - cost
    margin = (profit / revenue * 100) if revenue > 0 else 0
    return {
        "revenue": revenue,
        "cost": cost,
        "profit": round(profit, 2),
        "margin_pct": round(margin, 1)
    }
$$;

-- Example stored procedure
CREATE OR REPLACE PROCEDURE GENERATE_REPORT(region VARCHAR)
  RETURNS VARCHAR
  LANGUAGE PYTHON
  RUNTIME_VERSION = '3.8'
  PACKAGES = ('snowflake-snowpark-python')
  HANDLER = 'generate_report'
  AS $$
def generate_report(session, region: str) -> str:
    df = session.sql(f"""
        SELECT
            COUNT(*) AS order_count,
            ROUND(SUM(TOTAL_AMOUNT), 2) AS total_revenue
        FROM SALES
        WHERE REGION = '{region}'
    """).collect()
    if df:
        row = df[0]
        return f"Report for {region}: {row['ORDER_COUNT']} orders, ${row['TOTAL_REVENUE']:,.2f} revenue"
    return f"No data found for region: {region}"
$$;

-- Test the UDFs
SELECT MULTIPLY_BY_TEN(42);
SELECT CALCULATE_METRICS(100000, 65000);
