# pages/03_Admin_Dashboard.py

import io

import pandas as pd
import streamlit as st

from advisors_theme import apply_advisors_theme

st.set_page_config(
    page_title="Pre UKVI Admin Dashboard",
    page_icon="📊",
    layout="wide",
)

apply_advisors_theme()

st.title("Pre UKVI Admin Dashboard")
st.caption("Aggregate view for advisors and centres across multiple interview sessions.")


# ------------ Upload reports ------------

st.subheader("Upload one or more interview reports")

uploaded_files = st.file_uploader(
    "Upload CSV reports (advisor or speaking mode)",
    type=["csv"],
    accept_multiple_files=True,
)

if not uploaded_files:
    st.info("Upload at least one CSV report to see aggregated insights.")
    st.stop()

dfs = []
for f in uploaded_files:
    try:
        df = pd.read_csv(f)
        # Try to infer applicant name if captured in a column, else use filename
        if "Applicant" not in df.columns:
            df["Applicant"] = f.name.split(".")[0]
        dfs.append(df)
    except Exception as e:
        st.warning(f"Could not read {f.name}: {e}")

if not dfs:
    st.error("No valid CSVs were loaded.")
    st.stop()

all_df = pd.concat(dfs, ignore_index=True)

st.success(f"Loaded {len(uploaded_files)} report(s), {len(all_df)} rows total.")


# ------------ Basic filters ------------

st.subheader("Filters")

col1, col2 = st.columns(2)
with col1:
    categories = sorted(all_df["Category"].dropna().unique())
    selected_categories = st.multiselect(
        "Filter by category",
        options=categories,
        default=categories,
    )
with col2:
    readiness_vals = sorted(all_df.get("Readiness", "").dropna().unique())
    selected_readiness = st.multiselect(
        "Filter by readiness level",
        options=readiness_vals,
        default=readiness_vals,
    )

filtered = all_df.copy()
if selected_categories:
    filtered = filtered[filtered["Category"].isin(selected_categories)]
if "Readiness" in filtered.columns and selected_readiness:
    filtered = filtered[filtered["Readiness"].isin(selected_readiness)]

st.caption(f"Filtered rows: {len(filtered)}")


# ------------ Aggregate metrics ------------

st.subheader("Centre-wide performance overview")

if filtered.empty:
    st.warning("No data after filtering. Adjust filters to see metrics.")
    st.stop()

# Category-level scores
cat_summary = (
    filtered.groupby("Category")["Score"]
    .agg(["count", "mean"])
    .reset_index()
    .rename(columns={"count": "Questions", "mean": "Average Score"})
)

c1, c2 = st.columns([1.6, 1.4])
with c1:
    st.markdown("**Average score by category**")
    st.dataframe(cat_summary, use_container_width=True, hide_index=True)

with c2:
    # Applicant-level averages
    app_summary = (
        filtered.groupby("Applicant")["Score"]
        .agg(["count", "mean"])
        .reset_index()
        .rename(columns={"count": "Questions", "mean": "Average Score"})
    )
    st.markdown("**Average score by applicant**")
    st.dataframe(app_summary, use_container_width=True, hide_index=True)

weak_cats = cat_summary[cat_summary["Average Score"] <= 3]["Category"].tolist()
if weak_cats:
    st.markdown(
        "**Weak categories across the centre:** " +
        ", ".join(f"`{c}`" for c in weak_cats)
    )

# Common risk flags and missing points
st.subheader("Common risk phrases and gaps")

risk_all, missing_all = [], []

if "Risk Flags" in filtered.columns:
    for val in filtered["Risk Flags"].dropna():
        for item in str(val).split(","):
            item = item.strip()
            if item:
                risk_all.append(item)

if "Missing Points" in filtered.columns:
    for val in filtered["Missing Points"].dropna():
        for item in str(val).split(","):
            item = item.strip()
            if item:
                missing_all.append(item)

risk_df = (
    pd.Series(risk_all)
    .value_counts()
    .reset_index()
    .rename(columns={"index": "Risk Flag", 0: "Count"})
)

missing_df = (
    pd.Series(missing_all)
    .value_counts()
    .reset_index()
    .rename(columns={"index": "Gap", 0: "Count"})
)

c3, c4 = st.columns(2)
with c3:
    st.markdown("**Top risk phrases to coach against**")
    st.dataframe(risk_df, use_container_width=True, hide_index=True)
with c4:
    st.markdown("**Most frequent missing points**")
    st.dataframe(missing_df, use_container_width=True, hide_index=True)


# ------------ Drill-down table ------------

st.subheader("Drill-down: individual answers")

cols = [
    "Applicant",
    "Question #",
    "Category",
    "Question",
    "Answer",
    "Score",
    "Feedback",
    "Student Tip",
    "Risk Flags",
    "Missing Points",
    "Readiness",
]
existing_cols = [c for c in cols if c in filtered.columns]

st.dataframe(
    filtered[existing_cols],
    use_container_width=True,
    hide_index=True,
)

# Export aggregated dataset
csv_bytes = filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇ Download filtered combined dataset (CSV)",
    csv_bytes,
    "pre_ukvi_combined_filtered.csv",
    "text/csv",
)