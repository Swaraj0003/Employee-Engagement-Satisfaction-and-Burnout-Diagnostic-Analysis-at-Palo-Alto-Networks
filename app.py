
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

st.set_page_config(
    page_title="Employee Engagement Analytics",
    page_icon="📊",
    layout="wide"
)

st.title("Employee Engagement & Well-Being Analytics")
st.caption(
    "Employee experience diagnostics | HR decision-support dashboard"
)

sns.set_theme(style="whitegrid")


# -----------------------------
# 1. Load data
# -----------------------------
@st.cache_data
def load_data(file_bytes):
    import io

    data = pd.read_csv(io.BytesIO(file_bytes))
    data.columns = data.columns.str.strip()

    if "Attrition" in data.columns:
        data["Attrition"] = (
            data["Attrition"].astype("string").str.strip().str.lower()
            .map({
                "yes": "Yes", "no": "No",
                "1": "Yes", "0": "No",
                "true": "Yes", "false": "No"
            })
            .fillna(data["Attrition"])
        )

    if "OverTime" in data.columns:
        data["OverTime"] = (
            data["OverTime"].astype("string").str.strip().str.lower()
            .map({"yes": "Yes", "no": "No"})
            .fillna(data["OverTime"])
        )

    return data


uploaded_file = st.sidebar.file_uploader(
    "Upload employee CSV",
    type=["csv"]
)

default_path = Path(__file__).parent / "employee_data.csv"

if uploaded_file is not None:
    df = load_data(uploaded_file.getvalue())
elif default_path.exists():
    df = load_data(default_path.read_bytes())
else:
    st.info(
        "Upload your employee CSV in the sidebar to start the dashboard."
    )
    st.stop()


# -----------------------------
# 2. Validate required columns
# -----------------------------
engagement_cols = [
    "JobInvolvement",
    "JobSatisfaction",
    "EnvironmentSatisfaction",
    "RelationshipSatisfaction"
]

if all(c in df.columns for c in engagement_cols):
    ratings = df[engagement_cols].apply(
        pd.to_numeric, errors="coerce"
    )
    valid = ratings.notna().all(axis=1)
    mean_rating = ratings.mean(axis=1)

    df["Engagement_Index"] = np.nan
    df.loc[valid, "Engagement_Index"] = (
        (mean_rating[valid] - 1) / 3 * 100
    )

if "WorkLifeBalance" in df.columns:
    df["WorkLifeBalance"] = pd.to_numeric(
        df["WorkLifeBalance"], errors="coerce"
    )
    df["WLB_Index"] = (
        (df["WorkLifeBalance"] - 1) / 3 * 100
    )

if {"OverTime", "WorkLifeBalance"}.issubset(df.columns):
    df["Overtime_Flag"] = (
        df["OverTime"].astype("string").str.lower().eq("yes")
    )
    df["Low_WLB_Flag"] = df["WorkLifeBalance"].le(2)
    df["Combined_Warning_Flag"] = (
        df["Overtime_Flag"] & df["Low_WLB_Flag"]
    )


# -----------------------------
# 3. Sidebar filters
# -----------------------------
st.sidebar.header("Dashboard Filters")

filtered = df.copy()

for col in ["Department", "JobRole"]:
    if col in filtered.columns:
        options = sorted(
            filtered[col].dropna().astype(str).unique().tolist()
        )
        selected = st.sidebar.multiselect(
            f"Select {col}",
            options=options,
            default=options
        )
        filtered = filtered[
            filtered[col].astype(str).isin(selected)
        ]

if "OverTime" in filtered.columns:
    overtime_options = ["All"] + sorted(
        filtered["OverTime"].dropna().astype(str).unique().tolist()
    )
    overtime_choice = st.sidebar.selectbox(
        "Overtime status", overtime_options
    )
    if overtime_choice != "All":
        filtered = filtered[
            filtered["OverTime"].astype(str) == overtime_choice
        ]

if "YearsAtCompany" in filtered.columns:
    tenure = pd.to_numeric(
        filtered["YearsAtCompany"], errors="coerce"
    ).dropna()

    if not tenure.empty:
        min_year = int(tenure.min())
        max_year = int(tenure.max())

        if min_year < max_year:
            selected_range = st.sidebar.slider(
                "Years at company",
                min_value=min_year,
                max_value=max_year,
                value=(min_year, max_year)
            )

            tenure_values = pd.to_numeric(
                filtered["YearsAtCompany"], errors="coerce"
            )
            filtered = filtered[
                tenure_values.between(*selected_range)
            ]

if filtered.empty:
    st.warning("No records match the selected filters.")
    st.stop()


# -----------------------------
# 4. Overview KPI cards
# -----------------------------
st.header("1. Engagement Health Overview")

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

kpi1.metric("Employees", f"{len(filtered):,}")

if "Engagement_Index" in filtered.columns:
    kpi2.metric(
        "Mean Engagement",
        f"{filtered['Engagement_Index'].mean():.1f}/100"
        if filtered["Engagement_Index"].notna().any()
        else "N/A"
    )
else:
    kpi2.metric("Mean Engagement", "N/A")

if "WLB_Index" in filtered.columns:
    kpi3.metric(
        "Work-Life Balance",
        f"{filtered['WLB_Index'].mean():.1f}/100"
        if filtered["WLB_Index"].notna().any()
        else "N/A"
    )
else:
    kpi3.metric("Work-Life Balance", "N/A")

if "Overtime_Flag" in filtered.columns:
    kpi4.metric(
        "Overtime",
        f"{filtered['Overtime_Flag'].mean() * 100:.1f}%"
    )
else:
    kpi4.metric("Overtime", "N/A")

st.caption(
    "Engagement is a project-defined composite index, not a validated "
    "psychological measurement."
)


# -----------------------------
# 5. Engagement by department
# -----------------------------
st.header("2. Engagement Analysis")

if (
    "Department" in filtered.columns
    and "Engagement_Index" in filtered.columns
):
    summary = (
        filtered.groupby("Department")["Engagement_Index"]
        .mean()
        .dropna()
        .sort_values()
    )

    if not summary.empty:
        fig, ax = plt.subplots(figsize=(9, 4))
        summary.plot(kind="bar", ax=ax)
        ax.set_title("Mean Engagement by Department")
        ax.set_ylabel("Engagement Index (0–100)")
        ax.set_xlabel("Department")
        plt.xticks(rotation=25, ha="right")
        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

if "JobSatisfaction" in filtered.columns:
    fig, ax = plt.subplots(figsize=(8, 4))
    sns.countplot(
        data=filtered,
        x="JobSatisfaction",
        order=[1, 2, 3, 4],
        ax=ax
    )
    ax.set_title("Job Satisfaction Distribution")
    ax.set_xlabel("Rating (1 = Low, 4 = High)")
    ax.set_ylabel("Employee Count")
    st.pyplot(fig)
    plt.close(fig)


# -----------------------------
# 6. Workload warning analysis
# -----------------------------
st.header("3. Workload & Well-Being")

if "Combined_Warning_Flag" in filtered.columns:
    warning_pct = filtered["Combined_Warning_Flag"].mean() * 100

    st.metric(
        "Employees with Both Warning Signals",
        f"{warning_pct:.1f}%"
    )

    warning_counts = (
        filtered["Combined_Warning_Flag"]
        .map({True: "Both signals", False: "Not both signals"})
        .value_counts()
    )

    fig, ax = plt.subplots(figsize=(7, 4))
    warning_counts.plot(kind="bar", ax=ax)
    ax.set_title("Overtime and Low Work-Life Balance")
    ax.set_ylabel("Employee Count")
    ax.set_xlabel("")
    plt.xticks(rotation=0)
    st.pyplot(fig)
    plt.close(fig)

    st.caption(
        "This flag indicates overtime combined with a work-life balance "
        "rating of 1 or 2. It is not a diagnosis of burnout."
    )

if (
    "OverTime" in filtered.columns
    and "WorkLifeBalance" in filtered.columns
):
    wlb_summary = (
        filtered.groupby("OverTime")["WorkLifeBalance"]
        .mean()
        .dropna()
    )

    if not wlb_summary.empty:
        fig, ax = plt.subplots(figsize=(7, 4))
        wlb_summary.plot(kind="bar", ax=ax)
        ax.set_title("Average Work-Life Balance by Overtime")
        ax.set_ylabel("Mean Rating (1–4)")
        ax.set_xlabel("Overtime")
        plt.xticks(rotation=0)
        st.pyplot(fig)
        plt.close(fig)


# -----------------------------
# 7. Career-stage analysis
# -----------------------------
st.header("4. Role & Career Stage")

career_col = st.selectbox(
    "Analyze engagement by career variable",
    [
        c for c in [
            "JobLevel",
            "YearsAtCompany",
            "YearsInCurrentRole",
            "YearsSinceLastPromotion"
        ]
        if c in filtered.columns
    ],
    index=0
) if any(
    c in filtered.columns for c in [
        "JobLevel",
        "YearsAtCompany",
        "YearsInCurrentRole",
        "YearsSinceLastPromotion"
    ]
) else None

if career_col and "Engagement_Index" in filtered.columns:
    career_summary = (
        filtered.groupby(career_col)["Engagement_Index"]
        .agg(["mean", "count"])
        .dropna()
        .reset_index()
    )

    if not career_summary.empty:
        fig, ax = plt.subplots(figsize=(9, 4))
        ax.plot(
            career_summary[career_col],
            career_summary["mean"],
            marker="o"
        )
        ax.set_title(f"Engagement by {career_col}")
        ax.set_xlabel(career_col)
        ax.set_ylabel("Mean Engagement Index")
        st.pyplot(fig)
        plt.close(fig)

        st.dataframe(career_summary, use_container_width=True)


# -----------------------------
# 8. Attrition comparison
# -----------------------------
st.header("5. Attrition — Contextual Analysis")

if "Attrition" in filtered.columns:
    known = filtered["Attrition"].isin(["Yes", "No"])
    attrition_rate = (
        filtered.loc[known, "Attrition"].eq("Yes").mean() * 100
        if known.any() else np.nan
    )

    st.metric(
        "Observed Attrition Rate",
        f"{attrition_rate:.1f}%"
        if pd.notna(attrition_rate) else "N/A"
    )

    if "Engagement_Index" in filtered.columns:
        attrition_summary = (
            filtered.groupby("Attrition")["Engagement_Index"]
            .agg(["mean", "count"])
            .dropna()
        )
        st.subheader("Engagement by Attrition Status")
        st.dataframe(attrition_summary, use_container_width=True)

        if not attrition_summary.empty:
            fig, ax = plt.subplots(figsize=(7, 4))
            attrition_summary["mean"].plot(kind="bar", ax=ax)
            ax.set_ylabel("Mean Engagement Index")
            ax.set_xlabel("Attrition")
            ax.set_title("Engagement Among Employees Who Stayed or Left")
            plt.xticks(rotation=0)
            st.pyplot(fig)
            plt.close(fig)

    st.caption(
        "These are descriptive associations, not evidence that engagement "
        "causes attrition."
    )


# -----------------------------
# 9. Detailed data and export
# -----------------------------
st.header("6. Filtered Data")

st.dataframe(filtered, use_container_width=True)

st.download_button(
    "Download filtered data as CSV",
    data=filtered.to_csv(index=False).encode("utf-8"),
    file_name="filtered_employee_analysis.csv",
    mime="text/csv"
)

st.success("Dashboard analysis completed.")
