import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# =======
# LAYOUT
# =======
st.set_page_config(layout="wide")

st.markdown('<div style="text-align: center;font-size:42px;font-weight:bold;line-height:1.5; color:#1D4ED8;">📊 HR DASHBOARD</div>', unsafe_allow_html=True)
st.markdown("")

# ================
# GLOBAL STYLING
# ================
st.markdown("""
<style>

.block-container {
    padding-top: 3rem; 
    padding-bottom: 5rem;
}

h1, h2, h3 {
    scroll-margin-top: 100px;
}

.stTabs [data-baseweb="tab-list"] {
    justify-content: center;
    gap: 1rem;
}
@media (prefers-color-scheme: dark) {
    .stTabs [data-baseweb="tab"] {
        background-color: var(--background-color);
        color: var(--text-color);
        border: 3px solid var(--text-color);
        border-radius: 10px;
        padding: 0.5rem 1rem;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: rgba(0,0,0,0.10);
    }
}
.stExpander {
    margin-top: 10px;
    margin-bottom: 20px;
}
.stDataFrame {
    margin-top: 10px;
}

</style>
""", unsafe_allow_html=True)


# LOAD DATA
csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTQyERWzY558YfSVl-9PpWL_EJszeOYxx-aqt2Maav1dQmyKXl3G7wy7SlSk2EMpg/pub?output=csv"
df = pd.read_csv(csv_url)

# year
df["DateofHire"] = pd.to_datetime(df["DateofHire"], errors="coerce")
df["DateofTermination"] = pd.to_datetime(df["DateofTermination"], errors="coerce")

df["HireYear"] = df["DateofHire"].dt.year
df["TermYear"] = df["DateofTermination"].dt.year
# masa kerja (tahun)
df["TenureYears"] = np.where(
    df["DateofTermination"].notna(),
    (df["DateofTermination"] - df["DateofHire"]).dt.days / 365,
    (pd.to_datetime("today") - df["DateofHire"]).dt.days / 365
)

# gaji bulanan 40jam/minggu = 160 jam/bulan 
df["PayRate"] = df["PayRate"].fillna(0)
df["MonthlyPay"] = df["PayRate"] * 160

# Sidebar Filter
st.sidebar.header("📅 Filter Data")
years = sorted(pd.concat([df["HireYear"], df["TermYear"]], ignore_index=True).dropna().astype(int).unique(),reverse=True)
selected_year = st.sidebar.selectbox("Select Year", years, index=0)
prev_year = selected_year - 1

# Karyawan aktif pada akhir tahun
active_curr = df[
    (df["HireYear"] <= selected_year) &
    ((df["TermYear"].isna()) | (df["TermYear"] >= selected_year)) &
    (df["EmploymentStatus"].str.lower() == "active")
]

# Karyawan aktif pada tahun sebelumnya
active_prev = df[
    (df["HireYear"] <= prev_year) &
    ((df["TermYear"].isna()) | (df["TermYear"] >= prev_year)) &
    (df["EmploymentStatus"].str.lower() == "active")
]

# Karyawan yang keluar pada tahun itu
term_curr = df[df["TermYear"] == selected_year]
term_prev = df[df["TermYear"] == prev_year]

st.sidebar.markdown(
    """
    <div style="display: flex; flex-direction: column; height: 55vh; justify-content: space-between; text-align: justify; margin: 10px 0px">
        <div style="font-size: 11px; font-style:italic; color: var(--text-color); opacity:0.65;">
            *This filter updates the dashboard based on the selected year, affecting KPI Scorecards, Employee Termination Reasons,
            Employee & Project Distribution by Department, Workforce Score & Satisfaction, and Workforce Demographics
        </div>
        <div style="text-align: center; font-size: 16px; font-weight: bold; color: #1D4ED8;">
            Dashboard by<br>BIRU TEAM
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# KPI 
# 1. Total tenaga kerja aktif
active_curr_count = len(active_curr)
active_prev_count = len(active_prev)
active_change = ((active_curr_count - active_prev_count) / active_prev_count * 100) if active_prev_count > 0 else 0

# 2. Jumlah karyawan keluar
term_curr_count = len(term_curr)
term_prev_count = len(term_prev)
term_change = ((term_curr_count - term_prev_count) / term_prev_count * 100) if term_prev_count > 0 else 0

# 3. Tingkat turnover
def calc_turnover(df, year):
    aktif_awal = df[(df["HireYear"] <= year) & ((df["TermYear"].isna()) | (df["TermYear"] >= year))]
    keluar = df[df["TermYear"] == year]
    rate = (len(keluar) / len(aktif_awal) * 100) if len(aktif_awal) > 0 else 0
    return len(keluar), len(aktif_awal), round(rate, 2)

term_curr_count, active_start_count, turnover_curr = calc_turnover(df, selected_year)
term_prev_count, active_start_prev_count, turnover_prev = calc_turnover(df, prev_year)
turnover_change = turnover_curr - turnover_prev

# 4. Rata-rata lama bekerja
def active_tenure(df, year):
    aktif = df[(df["HireYear"] <= year) & ((df["TermYear"].isna()) | (df["TermYear"] >= year))].copy()
    aktif["TenureYears"] = aktif.apply(
        lambda row: ((min(pd.Timestamp(year=year, month=12, day=31), row["DateofTermination"] if pd.notna(row["DateofTermination"]) else pd.Timestamp(year=year, month=12, day=31)) - row["DateofHire"]).days) / 365.25, axis=1)
    return aktif["TenureYears"].mean() if not aktif.empty else 0

avg_tenure_curr = active_tenure(df, selected_year)
avg_tenure_prev = active_tenure(df, prev_year)
tenure_change = ((avg_tenure_curr - avg_tenure_prev) / avg_tenure_prev * 100) if avg_tenure_prev > 0 else 0

# 5. Rata-rata gaji bulanan
def avg_monthly_pay(df, year):
    aktif = df[(df["HireYear"] <= year) & ((df["TermYear"].isna()) | (df["TermYear"] >= year))].copy()
    # monthly pay 
    return aktif["MonthlyPay"].mean() if not aktif.empty else 0

avg_salary_curr = avg_monthly_pay(df, selected_year)
avg_salary_prev = avg_monthly_pay(df, prev_year)
salary_change = ((avg_salary_curr - avg_salary_prev) / avg_salary_prev * 100) if avg_salary_prev > 0 else 0

# usia
if "Age" not in df.columns:
    df["Age"] = ((pd.to_datetime("today") - pd.to_datetime(df["DOB"], errors="coerce")).dt.days / 365.25).round(1)

# =====
# TAB
# =====
tab1, tab2 = st.tabs(["🧭 Executive Summary", "🗂️ Employee Details"])
st.markdown("""
<style>
.stTabs [role="tab"] {
    padding: 8px 18px;
    border-radius: 6px 6px 0 0;
    opacity: 0.9;
    transition: 0.2s;
}
</style>
""", unsafe_allow_html=True)


# ===============================
# A. TAB UTAMA (Executive Summary)
# ===============================

with tab1:
    # ==================
    # 0. KPI SCORECARDS
    # ==================
    st.markdown("<h4>🎯 KPI Scorecards</h4>", unsafe_allow_html=True)

    # list data KPI
    kpi_data = [
        {
            "title": "👥 Active Employee",
            "value": f"{active_curr_count:,}",
            "delta": active_change,
            "delta_text": f"{active_change:+.2f}% vs prev year"
        },
        {
            "title": "🚪 Employee Left",
            "value": f"{term_curr_count:,}",
            "delta": term_change,
            "delta_text": f"{term_change:+.2f}% vs prev year"
        },
        {
            "title": "🔄 Turnover Rate",
            "value": f"{turnover_curr:.2f}%",
            "delta": turnover_change,
            "delta_text": f"{turnover_change:+.2f}% change"
        },
        {
            "title": "⏳ Avg Tenure",
            "value": f"{avg_tenure_curr:.2f} years",
            "delta": tenure_change,
            "delta_text": f"{tenure_change:+.2f}% vs prev year"
        },
        {
            "title": "💰 Monthly Pay",
            "value": f"${avg_salary_curr:,.0f}",
            "delta": salary_change,
            "delta_text": f"{salary_change:+.2f}% vs prev year"
        }
    ]

    # Auto warna positif/negatif
    def get_delta_color(kpi):
        if kpi['title'] in ["🚪 Employee Left", "🔄 Turnover Rate"]:
            return "#e74c3c" if kpi["delta"] > 0 else "#2ecc71" if kpi["delta"] < 0 else "var(--text-color)"
        else:
            return "#2ecc71" if kpi["delta"] > 0 else "#e74c3c" if kpi["delta"] < 0 else "var(--text-color)"

    cols = st.columns(5, gap="small")

    st.markdown("""
    <style>
        .kpi-card {
            border-radius: 15px;
            padding: 16px;
            background-color: var(--background-color);
            color: var(--text-color);
            box-shadow: 0px 2px 8px rgba(0,0,0,0.15);
            text-align: center;
            height: 140px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            transition: 0.25s;
        }

        @media (prefers-color-scheme: light) {
            .kpi-card {
                border: 1px solid rgba(0,0,0,0.28);
            }
        }
        @media (prefers-color-scheme: dark) {
            .kpi-card {
                border: 1px solid rgba(255,255,255,0.22);
            }
        }

        .kpi-card:hover {
            transform: translateY(-2px);
            box-shadow: 0px 4px 12px rgba(0,0,0,0.12);
        }
    </style>
    """, unsafe_allow_html=True)

    for col, kpi in zip(cols, kpi_data):
        # Tooltip
        if kpi['title'] == "💰 Monthly Pay":
            tooltip_text = f"Monthly Pay currently: ${avg_salary_curr:,.0f} (2024) vs ${avg_salary_prev:,.0f} (2023)"
        elif kpi['title'] == "⏳ Avg Tenure":
            tooltip_text = f"Average Tenure currently: {avg_tenure_curr:.2f} years (2024) vs {avg_tenure_prev:.2f} years (2023)"
        elif kpi['title'] == "👥 Active Employee":
            tooltip_text = f"Active Employees currently: {active_curr_count:,} (2024) vs {active_prev_count:,} (2023)"
        elif kpi['title'] == "🚪 Employee Left":
            tooltip_text = f"Employees Left currently: {term_curr_count:,} (2024) vs {term_prev_count:,} (2023)"
        elif kpi['title'] == "🔄 Turnover Rate":
            tooltip_text = f"Turnover Rate currently: {turnover_curr:.2f}% (2024) vs {turnover_prev:.2f}% (2023)"
        else:
            tooltip_text = ""

        delta_color = get_delta_color(kpi)
        delta_value = f"{kpi['delta']:+.2f}%"
        delta_suffix = kpi['delta_text'].replace(delta_value, "")

        col.markdown(f"""
            <div class="kpi-card" title="{tooltip_text}">
                <h6 style="margin: 0;">{kpi['title']}</h6>
                <p style="font-size: 28px; font-weight: bold; margin: 0; padding-bottom:8px;">
                    {kpi['value']}
                </p>
                <span style="font-size: 14px; font-weight: 500;">
                    <span style="color:{delta_color};">{delta_value}</span>{delta_suffix}
                </span>
            </div>""", 
        unsafe_allow_html=True)
    st.markdown("---")

    # ===================
    # 1. Employee Trend
    # ===================
    st.markdown("<br>", unsafe_allow_html=True)
    col_note, col_filter = st.columns([3, 1])

    with col_note:
        st.markdown("<h4>📈 Employee Trend</h4>", unsafe_allow_html=True)
        st.markdown("This section visualizes employee trends over time.", unsafe_allow_html=True)

    with col_filter:
        col_period, col_metric = st.columns(2)
        with col_period:
            period_options = ["Monthly", "Quarterly", "Yearly"] 
            period_option = st.selectbox("Period", period_options, index=0)
        
        with col_metric:
            metric_options = ["All", "Hiring", "Turnover"]
            metric_selected = st.selectbox("Metric", metric_options, index=0)

    df["JoinDate"] = pd.to_datetime(df["DateofHire"], errors="coerce")
    df["TermDate"] = pd.to_datetime(df["DateofTermination"], errors="coerce")

    # Hiring
    hiring_df = df[df["JoinDate"].notna()].copy()
    hiring_df["EventDate"] = hiring_df["JoinDate"]
    hiring_df["Metric"] = "Hiring"

    # Termination
    term_df = df[df["TermDate"].notna()].copy()
    term_df["EventDate"] = term_df["TermDate"]
    term_df["Metric"] = "Turnover"
    
    combined_df = pd.concat([hiring_df, term_df], ignore_index=True)
    
    min_date = combined_df["EventDate"].min()
    max_date = combined_df["EventDate"].max()
    
    if period_option == "Monthly":
        date_range = pd.period_range(start=min_date, end=max_date, freq='M')
    elif period_option == "Quarterly":
        date_range = pd.period_range(start=min_date, end=max_date, freq='Q')
    else:
        date_range = pd.period_range(start=min_date, end=max_date, freq='Y')

    complete_periods = pd.DataFrame({"Period": date_range})
    
    if period_option == "Monthly":
        complete_periods["Period_Date"] = complete_periods["Period"].dt.to_timestamp()
    elif period_option == "Quarterly":
        complete_periods["Period_Date"] = complete_periods["Period"].dt.to_timestamp(how='start')
    else:
        complete_periods["Period_Date"] = pd.to_datetime(complete_periods["Period"].astype(str) + "-01-01")

    if period_option == "Monthly":
        combined_df["Period"] = combined_df["EventDate"].dt.to_period("M")
    elif period_option == "Quarterly":
        combined_df["Period"] = combined_df["EventDate"].dt.to_period("Q")
    else:
        combined_df["Period"] = combined_df["EventDate"].dt.to_period("Y")
    
    grouped = (combined_df.groupby(["Period", "Metric"]).size().reset_index(name="Count"))
    
    all_metrics = ["Hiring", "Turnover"]
    template_data = []

    for period in complete_periods["Period"]:
        for metric in all_metrics:
            template_data.append({
                "Period": period,
                "Metric": metric,
                "Count": 0
            })

    template_df = pd.DataFrame(template_data)
    
    combined_template = pd.concat([template_df, grouped]).reset_index(drop=True)
    merged_df = combined_template.groupby(["Period", "Metric"])["Count"].max().reset_index()
    merged_df = pd.merge(merged_df, complete_periods, on="Period", how="left")

    if metric_selected == "Hiring":
        filtered_data = merged_df[merged_df["Metric"] == "Hiring"]
        color_map = {"Hiring": "#27AE60"}
    elif metric_selected == "Turnover":
        filtered_data = merged_df[merged_df["Metric"] == "Turnover"]
        color_map = {"Turnover": "#C0392B"}
    else:
        filtered_data = merged_df
        color_map = {"Hiring": "#27AE60", "Turnover": "#C0392B"}

    if not filtered_data.empty:
        if not filtered_data.empty:
            fig = px.line(
                filtered_data,
                x="Period_Date",
                y="Count",
                color="Metric",
                color_discrete_map=color_map,
                markers=True,
                line_shape="linear"
            )

            if period_option == "Quarterly":
                fig.update_traces(
                    customdata=filtered_data["Period"].apply(lambda x: f"Q{x.quarter} {x.year}").to_numpy().reshape(-1, 1),
                    hovertemplate="Period: %{customdata[0]}<br>Count: %{y}<extra></extra>",
                    line=dict(width=3),
                    marker=dict(size=4)
                )
            else:
                fig.update_traces(
                    hovertemplate="Period: %{x|%b %Y}<br>Count: %{y}<extra></extra>" if period_option=="Monthly" else
                                "Period: %{x|%Y}<br>Count: %{y}<extra></extra>",
                    line=dict(width=3),
                    marker=dict(size=4)
                )
            
            fig.update_layout(
                title=f"{'Hiring vs Turnover' if metric_selected == 'All' else metric_selected} Trend ({period_option})",
                xaxis_title="Period",
                yaxis_title="Employee Count",
                height=400,
                margin=dict(t=40, b=20, l=60, r=20),
                hovermode='x unified',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    itemclick=False,
                    itemdoubleclick=False
                )
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Quick Insight Employee Trend
        with st.expander(f"⚡Quick Insight – {metric_selected if metric_selected != 'All' else 'Hiring & Turnover'} ({period_option})"):
            def format_period(row):
                if period_option == "Quarterly":
                    return f"Q{row.Period.quarter} {row.Period.year}"
                elif period_option == "Monthly":
                    return row.Period_Date.strftime("%b %Y")
                else: 
                    return row.Period_Date.strftime("%Y")
            
            if metric_selected == "All":
                hiring_data = merged_df[merged_df["Metric"] == "Hiring"]
                turnover_data = merged_df[merged_df["Metric"] == "Turnover"]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    avg_hiring = hiring_data["Count"].mean()
                    max_hiring = hiring_data.loc[hiring_data["Count"].idxmax()]
                    min_hiring = hiring_data.loc[hiring_data["Count"].idxmin()]
                    st.markdown("##### 🟢 Hiring")
                    st.write(f"📈 **Average hiring**: **{avg_hiring:.2f}** employees")
                    st.write(f"⬆️ **Highest:** **{max_hiring['Count']}** employees on **{format_period(max_hiring)}**")
                with col2:
                    avg_turnover = turnover_data["Count"].mean()
                    max_turnover = turnover_data.loc[turnover_data["Count"].idxmax()]
                    min_turnover = turnover_data.loc[turnover_data["Count"].idxmin()]
                    st.markdown("##### 🔴 Turnover")
                    st.write(f"📈 **Average turnover:** **{avg_turnover:.2f}** employees")
                    st.write(f"⬆️ **Highest:** **{max_turnover['Count']}** employees on **{format_period(max_turnover)}**")
            else:
                total = filtered_data["Count"].sum()
                avg_value = filtered_data["Count"].mean()
                max_row = filtered_data.loc[filtered_data["Count"].idxmax()]
                min_row = filtered_data.loc[filtered_data["Count"].idxmin()]
                
                st.write(f"📈 Average {metric_selected.lower()}: **{avg_value:.2f}** employees")
                st.write(f"⬆️ Highest: **{max_row['Count']}** employees on **{format_period(max_row)}**")

    else:
        st.warning("No data available for the selected metric and period.")
        
    # ===============================
    # 2. Term Reason
    # ===============================
    st.markdown("<br>", unsafe_allow_html=True)
    col_note, col_filter = st.columns([3, 1])

    with col_note:
        st.markdown("<h4>⚠️ Employee Termination Reasons</h4>", unsafe_allow_html=True)
        st.markdown("This section visualizes the distribution of employee termination reasons for the year.", unsafe_allow_html=True)
        
    term_reason_counts = (
        term_curr["TermReason"]
        .value_counts()
        .reset_index()
    )
    term_reason_counts.columns = ["Reason", "Count"]

    theme = st.get_option("theme.base")
    fig_tt = px.treemap(
        term_reason_counts,
        path=["Reason"],
        values="Count",
        color="Count",
        color_continuous_scale="Reds",
        title=""
    )

    fig_tt.update_layout(
        width=500, height=320,
        margin=dict(t=20, b=20, l=20, r=20)
    )

    st.plotly_chart(fig_tt, use_container_width=True)

    # Insight Utama Term Reason
    with st.expander(f"⚡Quick Insight Termination Reasons ({selected_year})"):
        if not term_reason_counts.empty:
            max_reason_row = term_reason_counts.loc[term_reason_counts["Count"].idxmax()]
            st.write(f"⬆️ Most common reason: **{max_reason_row['Reason']}** **({max_reason_row['Count']} employees)**")
        else:
            st.write("No termination data for this year.")
    
    # ================================================
    # 3. Employee & Project Distribution by Department
    # ================================================
    st.markdown("<h4>🏢 Employee & Project Distribution by Department</h4>", unsafe_allow_html=True)
    st.markdown("This section provides an overview of employee and project distribution across departments.")
    col1, col2 = st.columns(2, gap="medium")

    # 3.1 Employee Distribution
    with col1:
        st.markdown("<h6 style='text-align:left; font-weight:bold;'>👔 Employee Distribution</h6>", unsafe_allow_html=True)
        dept_counts = active_curr["Department"].value_counts().reset_index()
        dept_counts.columns = ["Department","Count"]
        dept_counts = dept_counts.sort_values("Count", ascending=True)

        fig_dept = px.bar(
            dept_counts,
            x="Count", y="Department",
            orientation="h",
            text="Count",
            color="Count",
            color_continuous_scale=px.colors.sequential.Blues
        )
        fig_dept.update_traces(textposition="outside")
        fig_dept.update_layout(
            xaxis_title="Number of Employees",
            yaxis_title=None,
            height=320,
            margin=dict(t=20,b=20,l=20,r=20),
            coloraxis_showscale=False,
            xaxis=dict(range=[0, dept_counts["Count"].max()*1.1])
        )
        st.plotly_chart(fig_dept, use_container_width=True)

    # 3.2 Project Distribution
    with col2:
        st.markdown("<h6 style='text-align:left; font-weight:bold;'>📁 Project Distribution</h6>", unsafe_allow_html=True)
        project_counts = active_curr.groupby("Department")["SpecialProjectsCount"].sum().reset_index()
        project_counts = project_counts.sort_values("SpecialProjectsCount", ascending=True)

        fig_project = px.bar(
            project_counts,
            x="SpecialProjectsCount", y="Department",
            orientation="h",
            text="SpecialProjectsCount",
            color="SpecialProjectsCount",
            color_continuous_scale=px.colors.sequential.Blues
        )
        fig_project.update_traces(textposition="outside")
        fig_project.update_layout(
            xaxis_title="Number of Projects",
            yaxis_title=None,
            height=320,
            margin=dict(t=20,b=20,l=20,r=20),
            coloraxis_showscale=False,
            xaxis=dict(range=[0, project_counts["SpecialProjectsCount"].max()*1.1])
        )
        st.plotly_chart(fig_project, use_container_width=True)
    
    # Insight utama Employee & Project Distribution by Department
    with st.expander(f"⚡Quick Insights Employee & Project Distribution by Department ({selected_year})"):
        col1, col2 = st.columns(2)
        with col1:
            emp_max = dept_counts.loc[dept_counts["Count"].idxmax()]
            emp_min = dept_counts.loc[dept_counts["Count"].idxmin()]
            st.markdown("##### 👔 Employee Distribution")
            st.write(f"⬆️ Highest: **{emp_max['Department']}** ({emp_max['Count']}) employees")
            st.write(f"⬇️ Lowest: **{emp_min['Department']}** ({emp_min['Count']}) employees")
        with col2:
            proj_max = project_counts.loc[project_counts["SpecialProjectsCount"].idxmax()]
            proj_min = project_counts.loc[project_counts["SpecialProjectsCount"].idxmin()]
            
            st.markdown("##### 📁 Project Distribution")
            st.write(f"⬆️ Most: **{proj_max['Department']}** ({proj_max['SpecialProjectsCount']}) projects")
            st.write(f"⬇️ Fewest: **{proj_min['Department']}** ({proj_min['SpecialProjectsCount']}) projects")

    # ==================================
    # 4. Workforce Score & Satisfaction
    # ==================================
    st.markdown("<h4>📑 Workforce Score & Satisfaction</h4>", unsafe_allow_html=True)
    st.markdown("This section shows the distribution of performance, engagement, and satisfaction scores for active employees.", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)

    # 4.1 Performance Score (1-4)
    with col1:
        st.markdown("<h6 style='text-align:left; font-weight:bold;'>🎯 Performance Score</h6>", unsafe_allow_html=True)
        perf_scores = np.round(active_curr['PerformanceScore']).astype(int)
        perf_scores = perf_scores[(perf_scores >= 1) & (perf_scores <= 4)]
        perf_counts = perf_scores.value_counts().sort_index()
        fig_perf = px.bar(
            x=perf_counts.index.astype(str),
            y=perf_counts.values,
            labels={'x': 'Performance Score', 'y': 'Number of Employees'},
            color_discrete_sequence=['#1E3A8A'],
            height=350
        )
        st.plotly_chart(fig_perf, use_container_width=True)
        
        max_idx = perf_counts.idxmax()
        max_val = perf_counts.max()
        fig_perf.add_annotation(
            x=str(max_idx), 
            y=max_val,
            text=str(max_val),
            showarrow=False,
            yshift=10,
            font=dict(size=12, color="black")
        )

    # 4.2 Engagement Survey (1-5)
    with col2:
        st.markdown("<h6 style='text-align:left; font-weight:bold;'>💬 Engagement Survey</h6>", unsafe_allow_html=True)
        eng_scores = np.round(active_curr['EngagementSurvey']).astype(int)
        eng_scores = eng_scores[(eng_scores >= 1) & (eng_scores <= 5)]
        eng_counts = eng_scores.value_counts().reindex([1, 2, 3, 4, 5], fill_value=0)

        fig_eng = px.bar(
            x=[str(i) for i in [1, 2, 3, 4, 5]],
            y=eng_counts.values,
            labels={'x': 'Engagement Survey', 'y': 'Number of Employees'},
            color_discrete_sequence=['#3B82F6'],
            height=350
        )
        
        fig_eng.update_xaxes(
            tickmode='array',
            tickvals=['1','2','3','4','5'],
            ticktext=['1','2','3','4','5']
        )
        st.plotly_chart(fig_eng, use_container_width=True)


    # 4.3 Employee Satisfaction (1-5)
    with col3:
        st.markdown("<h6 style='text-align:left; font-weight:bold;'>😃 Employee Satisfaction</h6>", unsafe_allow_html=True)
        satis_scores = np.round(active_curr['EmpSatisfaction']).astype(int)
        satis_scores = satis_scores[(satis_scores >= 1) & (satis_scores <= 5)]
        satis_counts = satis_scores.value_counts().sort_index()
        fig_satis = px.bar(
            x=satis_counts.index.astype(str),
            y=satis_counts.values,
            labels={'x': 'Employee Satisfaction', 'y': 'Number of Employees'},
            color_discrete_sequence=['#93C5FD'],
            height=350
        )
        fig_satis.update_xaxes(
            tickmode='array',
            tickvals=['1','2','3','4','5'],
            ticktext=['1','2','3','4','5']
        )
        st.plotly_chart(fig_satis, use_container_width=True)

    # Insight utama Workforce Score & Satisfaction
    with st.expander(f"⚡Quick Insight Workforce Score & Satisfaction ({selected_year})"):
        # performance score
        most_perf = perf_scores.mode()[0]
        avg_perf = active_curr['PerformanceScore'].mean()
        st.write(f"🎯 Average Performance Score is **{avg_perf:.2f}**, with the most common score being **{most_perf}**.")
        # engagement survey
        most_eng = eng_scores.mode()[0]
        avg_eng = active_curr['EngagementSurvey'].mean()
        st.write(f"💬 Average Engagement Survey score is **{avg_eng:.2f}**, with the most employees score being **{most_eng}**.")
        # employee satisfaction
        most_satis = satis_scores.mode()[0]
        avg_satis = active_curr['EmpSatisfaction'].mean()
        st.write(f"😃 Average Employee Satisfaction is **{avg_satis:.2f}**, with the most common score being **{most_satis}**.")
    
    # =======================
    # 5. DEMOGRAFI KARYAWAN
    # =======================
    col_filter_demo1, col_filter_demo2 = st.columns([3, 1])
    with col_filter_demo1:
        st.markdown("<h4>👨‍👩‍👧‍👦 Workforce Demographic</h4>", unsafe_allow_html=True)
        st.markdown("This section provides an overview of the demographic characteristics of the selected employee group.")
    with col_filter_demo2:
        demo_type = st.selectbox(
            "Metric",
            ["Active Employees", "Turnover Employees"],
            key="demo_type"
        )
        
    col1, col2, col3 = st.columns(3, gap="medium")

    if demo_type == "Active Employees":
        data_source = active_curr
        color_primary = "#1E3A8A"
        color_secondary = "#3B82F6"
        color_tertiary = "#60A5FA"
        title_suffix = "Active"
    else:
        data_source = term_curr
        color_primary = "#991B1B"
        color_secondary = "#DC2626"
        color_tertiary = "#EF4444"
        title_suffix = "Turnover"

    # 5.1 Gender
    with col1:
        st.markdown(f"<h6 style='text-align:left'>⚥ Gender Distribution ({title_suffix})</h6>", unsafe_allow_html=True)
        
        if not data_source.empty:
            gender_counts = data_source["Sex"].value_counts().reset_index()
            gender_counts.columns = ["Gender", "Count"]

            fig_gender = px.pie(
                gender_counts,
                names="Gender",
                values="Count",
                color="Gender",
                color_discrete_map={"Male": color_primary, "Female": color_secondary},
                hole=0.4
            )
            fig_gender.update_traces(textinfo="percent+label", hovertemplate="%{label}: %{value} employees")
            fig_gender.update_layout(height=280, margin=dict(t=20,b=20,l=20,r=20))
            st.plotly_chart(fig_gender, use_container_width=True)
        else:
            st.info("No data available")

    # 5.2 Age distribution
    with col2:
        st.markdown(f"<h6 style='text-align:left'>⏳ Age Distribution ({title_suffix})</h6>", unsafe_allow_html=True)
        
        if not data_source.empty:
            data_source_age = data_source.copy()
            data_source_age['Age'] = selected_year - pd.to_datetime(data_source_age['DOB']).dt.year
            
            # bins 
            age_bins = list(range(20, 66, 5))
            counts, edges = np.histogram(data_source_age['Age'], bins=age_bins)
            
            max_idx = np.argmax(counts)
            most_common_age_range = f"{int(edges[max_idx])}-{int(edges[max_idx+1]-1)}"
            most_common_age_count = counts[max_idx]

            # plot
            fig_age = px.histogram(
                data_source_age, x="Age", nbins=len(age_bins)-1, 
                color_discrete_sequence=[color_primary]
            )
            fig_age.update_layout(
                xaxis_title="Age (Years)",
                yaxis_title="Number of Employees",
                height=300,
                margin=dict(t=20,b=20,l=20,r=20)
            )
            st.plotly_chart(fig_age, use_container_width=True)
        else:
            st.info("No data available")

    # 5.3 Marital Status
    with col3:
        st.markdown(f"<h6 style='text-align:left'>💍 Marital Status ({title_suffix})</h6>", unsafe_allow_html=True)
        
        if not data_source.empty:
            marital_counts = data_source["MaritalDesc"].dropna().value_counts().reset_index()
            marital_counts.columns = ["Marital Status", "Count"]
            marital_counts = marital_counts.sort_values("Count", ascending=True)  # Urutkan dari terkecil ke terbesar
            total_emp = marital_counts["Count"].sum()

            # Generate color palette berdasarkan tipe data dan urutan
            if demo_type == "Active Employees":
                # Untuk active: berbagai variasi biru (terkecil = muda, terbesar = tua)
                blue_palette = ["#93C5FD", "#60A5FA", "#3B82F6", "#2563EB", "#1E40AF", "#1E3A8A"]
                palette = blue_palette[:len(marital_counts)]
            else:
                # Untuk turnover: berbagai variasi merah (terkecil = muda, terbesar = tua)
                red_palette = ["#FCA5A5", "#F87171", "#EF4444", "#DC2626", "#B91C1C", "#991B1B"]
                palette = red_palette[:len(marital_counts)]

            fig_marital = px.bar(
                marital_counts,
                y="Marital Status",
                x="Count",
                color="Count",
                color_continuous_scale=palette,
                text="Count",
                orientation='h'
            )
            fig_marital.update_traces(textposition="outside", width=0.6)
            fig_marital.update_layout(
                xaxis_title="Number of Employees",
                yaxis_title="Marital Status",
                height=300,
                margin=dict(t=20,b=40,l=120,r=20),
                showlegend=False,
                coloraxis_showscale=False, 
                xaxis=dict(range=[0, marital_counts["Count"].max()*1.2])
            )
            st.plotly_chart(fig_marital, use_container_width=True)
        else:
            st.info("No data available")

    # Insight utama Workforce Demographic
    with st.expander(f"⚡Quick Insights Workforce Demographic - {title_suffix} ({selected_year})"):
        if not data_source.empty:
            # Gender insights
            gender_counts = data_source["Sex"].value_counts()
            if not gender_counts.empty:
                gender_total = gender_counts.sum()
                male_count = gender_counts.get("Male", 0)
                female_count = gender_counts.get("Female", 0)
                most_gender = "Male" if male_count > female_count else "Female"
                most_gender_count = max(male_count, female_count)
                gender_ratio = (most_gender_count / gender_total * 100) if gender_total > 0 else 0
                
                st.write(f"⚥ Majority of {title_suffix.lower()} employees are **{most_gender}** ({most_gender_count} employees, {gender_ratio:.1f}%)")
            
            # Age insights
            st.write(f"⏳ Most {title_suffix.lower()} employees are in the **{most_common_age_range}** age range ({most_common_age_count} employees)")

            # Marital Status insights
            marital_counts = data_source["MaritalDesc"].value_counts()
            if not marital_counts.empty:
                most_marital_status = marital_counts.idxmax()
                most_marital_count = marital_counts.max()
                st.write(f"💍 Most {title_suffix.lower()} employees are **{most_marital_status}** ({most_marital_count} employees)")
        else:
            st.write("No data available for the selected filters")
    
# =====================
# B. EMPLOYEE DETAILS
# =====================
detail_df = df.copy()
with tab2:
    st.markdown("#### 🪪 Employee Directory")
    st.markdown("This section provides an overview of employee details to explore key information about employee profiles.")

    if "Age" not in df.columns:
        df["Age"] = ((pd.to_datetime("today") - pd.to_datetime(df["DOB"], errors="coerce")).dt.days / 365.25).round(1)

    col_filter1, col_filter2, col_filter3, col_filter4= st.columns([1, 1, 1, 1])
    # 1. Filter
    with col_filter1:
        employment_status_filter = st.selectbox("📊 Employment Status",["All"] + sorted(df["EmploymentStatus"].dropna().unique()))
    with col_filter2:
        dept_filter = st.selectbox("🏢 Department",["All"] + sorted(df["Department"].dropna().unique()))
    with col_filter3:
        pos_filter = st.selectbox("💼 Position",["All"] + sorted(df["Position"].dropna().unique()))
    with col_filter4:
        manager_filter = st.selectbox("👨‍💼 Manager",["All"] + sorted(df["ManagerName"].dropna().unique()))
    
    columns_to_show = [
        "EmpID", "Employee_Name", "Position", "Department", "Employee Status", "Age", "Sex", "MaritalDesc",
        "RaceDesc", "State", "TenureYears", "DateofHire", "DateofTermination",
        "MonthlyPay", "ManagerName", "PerformanceScore", "EngagementSurvey", "EmpSatisfaction"]
    columns_to_show = [col for col in columns_to_show if col in detail_df.columns]
    
    col_filter5, col_filter6, col_filter7 = st.columns([2, 1, 1])
    with col_filter5:
        search_name = st.text_input("🔍 Search Employee Name", placeholder="Enter employee name...")
    with col_filter6:
        sort_column = st.selectbox(
            "Sort By:",
            options=columns_to_show,
            index=0)
    with col_filter7:
        sort_order = st.selectbox(
            "Order:",
            options=["🔼 Ascending", "🔽 Descending"],
            index=0)

    if employment_status_filter != "All":
        detail_df = detail_df[detail_df["EmploymentStatus"] == employment_status_filter]
    if dept_filter != "All":
        detail_df = detail_df[detail_df["Department"] == dept_filter]
    if pos_filter != "All":
        detail_df = detail_df[detail_df["Position"] == pos_filter]
    if manager_filter != "All":
        detail_df = detail_df[detail_df["ManagerName"] == manager_filter]
    if search_name:
        detail_df = detail_df[
            detail_df["Employee_Name"].str.contains(search_name, case=False, na=False)]

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Card Employee
    status_colors = {
        "Active": "#2ecc71",
        "Leave of Absence": "#f6e05e",
        "Voluntarily Terminated": "#feb2b2",
        "Terminated for Cause": "#e53e3e",
        "Future Start": "#63b3ed"}
    st.markdown(f"**Total Employees Displayed:** {len(detail_df)}")
    
    detail_df = detail_df.sort_values(
        by=sort_column,
        ascending=True if sort_order == "⬆️ Ascending" else False)

    for i, row in detail_df.iterrows():
        status_color = status_colors.get(row["EmploymentStatus"], "#A0AEC0")

        st.markdown(f"""
        <div style="
            border: 1px solid #ddd;
            border-radius: 15px;
            padding: 16px;
            margin-bottom: 15px;
            background-color: var(--bacground-color);
            box-shadow: 0px 2px 4px rgba(0,0,0,0.05);
        ">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h4 style="margin: 0;">👤 {row['Employee_Name']}</h4>
                <span style="color: var(--text-color); background-color: {status_color};
                    padding: 5px 10px; border-radius: 8px; font-size: 12px;">
                    {row['EmploymentStatus']}
                </span>
            </div>
            <p style="color: var(--text-color); margin: 5px 0 10px 0; font-weight: 500;">{row['Position']} - {row['Department']}</p>
            <div style="color: var(--text-color); display: flex; flex-wrap: wrap; gap: 12px; font-size: 14px;">
                <div>📅 <b>Tenure:</b> {row['TenureYears']:.1f} Years</div>
                <div>💰 <b>Salary:</b> ${row['MonthlyPay']:,.0f}</div>
                <div>👨‍💼 <b>Manager:</b> {row['ManagerName']}</div>
                <div>🎯 <b>Performance:</b> {row['PerformanceScore']}</div>
            </div>
            <hr style="margin: 10px 0; border: none; border-top: 1px solid #eee;">
            <div style="color: var(--text-color); font-size: 13px;">
                🧠 <b>Gender:</b> {row['Sex']} &nbsp;&nbsp;|&nbsp;&nbsp;
                🎂 <b>Age:</b> {row['Age']} &nbsp;&nbsp;|&nbsp;&nbsp;
                💍 <b>Marital Status:</b> {row['MaritalDesc']} &nbsp;&nbsp;|&nbsp;&nbsp;
                🌏 <b>Race:</b> {row['RaceDesc']} &nbsp;&nbsp;|&nbsp;&nbsp;
                📍 <b>State:</b> {row['State']}
            </div>
        </div>
        """, unsafe_allow_html=True)
