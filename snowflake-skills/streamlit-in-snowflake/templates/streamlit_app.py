"""
Streamlit in Snowflake — Starter App
=====================================
A basic dashboard showing data from a Snowflake table.
Replace the sample query with your actual data.

This works in both warehouse and container runtimes.
"""

import streamlit as st
from snowflake.snowpark.context import get_active_session

# -- Page config (must be first Streamlit call) --
st.set_page_config(
    page_title="{{APP_TITLE}}",
    page_icon="❄️",
    layout="wide",
)

# -- Snowflake session --
session = get_active_session()

# Tip: For warehouse runtime, switch to a larger warehouse for heavy queries:
# session.sql("USE WAREHOUSE analytics_wh").collect()


# -- Helper: cached data loading --
@st.cache_data(ttl=600)  # Cache for 10 minutes
def load_data():
    """Load data from Snowflake. Replace with your actual query."""
    return session.sql("""
        SELECT
            CURRENT_DATE() AS report_date,
            SEQ4() AS id,
            UNIFORM(1, 100, RANDOM()) AS metric_a,
            UNIFORM(200, 500, RANDOM()) AS metric_b,
            CASE MOD(SEQ4(), 4)
                WHEN 0 THEN 'Category A'
                WHEN 1 THEN 'Category B'
                WHEN 2 THEN 'Category C'
                ELSE 'Category D'
            END AS category
        FROM TABLE(GENERATOR(ROWCOUNT => 200))
    """).to_pandas()


# -- Main app --
st.title("{{APP_TITLE}}")
st.caption("Powered by Streamlit in Snowflake")

df = load_data()

# -- KPI cards --
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Rows", f"{len(df):,}")
col2.metric("Avg Metric A", f"{df['METRIC_A'].mean():.1f}")
col3.metric("Avg Metric B", f"{df['METRIC_B'].mean():.1f}")
col4.metric("Categories", df["CATEGORY"].nunique())

st.divider()

# -- Filters --
categories = st.multiselect(
    "Filter by category",
    options=df["CATEGORY"].unique(),
    default=df["CATEGORY"].unique(),
)
filtered = df[df["CATEGORY"].isin(categories)]

# -- Charts --
left, right = st.columns(2)

with left:
    st.subheader("Metric A by Category")
    st.bar_chart(
        filtered.groupby("CATEGORY")["METRIC_A"].mean(),
    )

with right:
    st.subheader("Metric B Distribution")
    st.bar_chart(
        filtered.groupby("CATEGORY")["METRIC_B"].sum(),
    )

# -- Data table --
st.subheader("Raw Data")
st.dataframe(filtered, use_container_width=True)

# -- Footer --
st.caption(f"Showing {len(filtered):,} of {len(df):,} rows")
