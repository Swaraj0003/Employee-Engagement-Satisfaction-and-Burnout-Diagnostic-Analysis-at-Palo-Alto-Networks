
import pandas as pd
import numpy as np
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

BASE = Path(__file__).parent
DATA_PATH = BASE / "employee_data.csv"
OUTPUT_PATH = BASE / "analytics_report.docx"

if not DATA_PATH.exists():
    raise FileNotFoundError(
        f"Dataset not found: {DATA_PATH}\n"
        "Place employee_data.csv in the project folder."
    )

df = pd.read_csv(DATA_PATH)
df.columns = df.columns.str.strip()

doc = Document()

# Document styling
styles = doc.styles
styles["Normal"].font.name = "Arial"
styles["Normal"].font.size = Pt(10)

# Title page
title = doc.add_heading(
    "Employee Engagement, Satisfaction, and "
    "Burnout Diagnostic Analysis",
    level=0
)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER

p = doc.add_paragraph(
    "Project scenario: Palo Alto Networks"
)
p.alignment = WD_ALIGN_PARAGRAPH.CENTER

p = doc.add_paragraph(
    "Prepared as an employee analytics and business intelligence study"
)
p.alignment = WD_ALIGN_PARAGRAPH.CENTER

doc.add_page_break()

# 1. Executive summary
doc.add_heading("1. Executive Summary", level=1)

doc.add_paragraph(
    "This project examines employee engagement, satisfaction, "
    "workload indicators, work-life balance, career progression, "
    "and attrition using the supplied employee dataset. The goal "
    "is to identify group-level patterns that may help HR teams "
    "investigate employee experience concerns and develop "
    "preventive support measures."
)

doc.add_paragraph(
    "The analysis is descriptive. Associations between variables "
    "do not establish causation, and the workload indicators used "
    "in this report are not clinical burnout assessments."
)

# 2. Dataset overview
doc.add_heading("2. Dataset Overview", level=1)

overview = [
    ("Number of records", str(len(df))),
    ("Number of columns", str(len(df.columns))),
    ("Missing cells", str(int(df.isna().sum().sum()))),
    ("Duplicate rows", str(int(df.duplicated().sum())))
]

table = doc.add_table(rows=1, cols=2)
table.style = "Light Shading Accent 1"
table.rows[0].cells[0].text = "Metric"
table.rows[0].cells[1].text = "Value"

for label, value in overview:
    cells = table.add_row().cells
    cells[0].text = label
    cells[1].text = value

doc.add_paragraph(
    "The dataset's source, collection date, population coverage, "
    "and representativeness should be verified before drawing "
    "conclusions about any real organization."
)

# 3. Methodology
doc.add_heading("3. Analytical Methodology", level=1)

methodology = [
    "Data inspection: reviewed the dataset dimensions, column names, "
    "data types, missing values, and duplicate records.",
    "Univariate analysis: examined distributions of numerical and "
    "categorical employee variables.",
    "Group comparisons: compared engagement, satisfaction, and "
    "work-life balance across departments, roles, overtime groups, "
    "and career stages where the required fields were available.",
    "Engagement index: averaged Job Involvement, Job Satisfaction, "
    "Environment Satisfaction, and Relationship Satisfaction, then "
    "mapped the 1–4 average to a 0–100 scale.",
    "Workload warning: identified records with overtime and a "
    "WorkLifeBalance rating of 1 or 2.",
    "Attrition context: compared observed attrition and engagement "
    "patterns without interpreting them as causal effects."
]

for item in methodology:
    doc.add_paragraph(item, style="List Bullet")

# 4. KPI calculations
doc.add_heading("4. Key Performance Indicators", level=1)

kpis = []

if "JobInvolvement" in df.columns and all(
    c in df.columns for c in [
        "JobInvolvement",
        "JobSatisfaction",
        "EnvironmentSatisfaction",
        "RelationshipSatisfaction"
    ]
):
    cols = [
        "JobInvolvement",
        "JobSatisfaction",
        "EnvironmentSatisfaction",
        "RelationshipSatisfaction"
    ]
    ratings = df[cols].apply(pd.to_numeric, errors="coerce")
    valid = ratings.notna().all(axis=1)
    engagement = ((ratings.mean(axis=1) - 1) / 3 * 100).where(valid)

    kpis.append((
        "Mean Engagement Index",
        f"{engagement.mean():.2f}/100"
        if engagement.notna().any() else "Not available",
        "Custom composite of four 1–4 ratings."
    ))

if "WorkLifeBalance" in df.columns:
    wlb = pd.to_numeric(df["WorkLifeBalance"], errors="coerce")
    wlb_index = (wlb - 1) / 3 * 100

    kpis.append((
        "Mean Work-Life Balance Index",
        f"{wlb_index.mean():.2f}/100"
        if wlb_index.notna().any() else "Not available",
        "Rescaled WorkLifeBalance rating."
    ))

if "OverTime" in df.columns:
    overtime = (
        df["OverTime"].astype("string").str.strip().str.lower()
        .map({"yes": True, "no": False})
    )

    kpis.append((
        "Overtime Percentage",
        f"{overtime.mean() * 100:.2f}%"
        if overtime.notna().any() else "Not available",
        "Percentage of records with known overtime status marked Yes."
    ))

if {"OverTime", "WorkLifeBalance"}.issubset(df.columns):
    overtime_bool = (
        df["OverTime"].astype("string").str.strip().str.lower()
        .map({"yes": True, "no": False})
    )
    balance = pd.to_numeric(df["WorkLifeBalance"], errors="coerce")
    known = overtime_bool.notna() & balance.notna()
    combined = overtime_bool & balance.le(2)

    kpis.append((
        "Combined Workload Warning",
        f"{combined[known].mean() * 100:.2f}%"
        if known.any() else "Not available",
        "Percentage with both overtime and work-life balance rated 1 or 2."
    ))

if "Attrition" in df.columns:
    attrition = (
        df["Attrition"].astype("string").str.strip().str.lower()
        .map({
            "yes": True, "no": False,
            "1": True, "0": False,
            "true": True, "false": False
        })
    )

    kpis.append((
        "Observed Attrition Rate",
        f"{attrition.mean() * 100:.2f}%"
        if attrition.notna().any() else "Not available",
        "Percentage of records with known attrition status marked Yes."
    ))

table = doc.add_table(rows=1, cols=3)
table.style = "Light Shading Accent 1"

headers = ["KPI", "Observed Value", "Definition"]
for i, header in enumerate(headers):
    table.rows[0].cells[i].text = header

for name, value, definition in kpis:
    cells = table.add_row().cells
    cells[0].text = name
    cells[1].text = value
    cells[2].text = definition

# 5. Department analysis
doc.add_heading("5. Department-Level Analysis", level=1)

if "Department" in df.columns:
    dept = df.groupby("Department").size().rename("Employee Count").to_frame()

    if "Engagement_Index" not in df.columns and all(
        c in df.columns for c in [
            "JobInvolvement",
            "JobSatisfaction",
            "EnvironmentSatisfaction",
            "RelationshipSatisfaction"
        ]
    ):
        cols = [
            "JobInvolvement",
            "JobSatisfaction",
            "EnvironmentSatisfaction",
            "RelationshipSatisfaction"
        ]
        ratings = df[cols].apply(pd.to_numeric, errors="coerce")
        valid = ratings.notna().all(axis=1)
        df["Engagement_Index"] = (
            (ratings.mean(axis=1) - 1) / 3 * 100
        ).where(valid)

    if "Engagement_Index" in df.columns:
        dept["Mean Engagement"] = df.groupby(
            "Department"
        )["Engagement_Index"].mean()

    if "WorkLifeBalance" in df.columns:
        dept["Mean Work-Life Balance"] = df.groupby(
            "Department"
        )["WorkLifeBalance"].mean()

    table = doc.add_table(rows=1, cols=len(dept.columns) + 1)
    table.style = "Light Shading Accent 1"

    table.rows[0].cells[0].text = "Department"
    for i, col in enumerate(dept.columns, start=1):
        table.rows[0].cells[i].text = col

    for department, row in dept.iterrows():
        cells = table.add_row().cells
        cells[0].text = str(department)

        for i, value in enumerate(row, start=1):
            cells[i].text = (
                f"{value:.2f}" if pd.notna(value) else "Not available"
            )

    doc.add_paragraph(
        "Department averages should be interpreted alongside group "
        "sizes and missingness. Small groups may produce unstable estimates."
    )
else:
    doc.add_paragraph(
        "Department data were not available in the supplied dataset."
    )

# 6. Findings to investigate
doc.add_heading("6. Findings and Areas for Investigation", level=1)

doc.add_paragraph(
    "The following questions should be answered using the EDA charts "
    "and group summaries generated by the research notebook:"
)

for item in [
    "Which departments or job roles have comparatively lower engagement?",
    "Does work-life balance differ between overtime and non-overtime groups?",
    "Are employees with longer time since promotion reporting different engagement?",
    "How do engagement distributions differ between employees who stayed and left?",
    "Are the observed differences large enough to be operationally meaningful?"
]:
    doc.add_paragraph(item, style="List Bullet")

doc.add_paragraph(
    "Insert verified findings from the notebook before final submission. "
    "Do not present questions or hypotheses as confirmed results."
)

# 7. Recommendations
doc.add_heading("7. Recommended Actions", level=1)

for item in [
    "Review workload allocation and overtime patterns at the group level.",
    "Offer confidential employee feedback channels and manager check-ins.",
    "Examine career-development and promotion opportunities where "
    "engagement patterns warrant further investigation.",
    "Repeat the analysis over time to monitor changes after interventions.",
    "Evaluate the effectiveness of interventions using appropriate "
    "follow-up measures rather than relying on one-time scores."
]:
    doc.add_paragraph(item, style="List Bullet")

# 8. Limitations
doc.add_heading("8. Limitations and Responsible Use", level=1)

doc.add_paragraph(
    "The engagement index is a project-defined proxy and has not been "
    "validated as a psychological scale. The combined overtime and "
    "work-life balance flag is a workload warning indicator, not a "
    "burnout diagnosis. Observational data cannot establish causality. "
    "Data provenance and representativeness must be verified. Avoid "
    "individual-level employment decisions based on these indicators, "
    "and protect employee privacy when storing or sharing results."
)

# 9. Conclusion
doc.add_heading("9. Conclusion", level=1)

doc.add_paragraph(
    "This project demonstrates how descriptive analytics and KPI "
    "visualization can support a more proactive approach to employee "
    "experience. The findings should guide further investigation, "
    "employee consultation, and evaluation of targeted interventions."
)

doc.save(OUTPUT_PATH)

print(f"Report created: {OUTPUT_PATH}")
