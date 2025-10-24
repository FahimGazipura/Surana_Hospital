from dateutil.relativedelta import relativedelta
import os
import sys
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
)

# Add parent folder to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Local module imports
from scripts.merge_data import merge_data
from dashboard.filters import filter_ip_data, ip_filter_ui
from dashboard.reports import (
    display_ip_metrics,
    display_filtered_ip_data,
    display_yearly_revenue_report,
    display_yearly_ip_count_report,
    display_monthly_revenue_report,
    display_monthly_ip_count_report,
    export_nabl_report_to_pdf
)

def get_age_group(age):
    """Categorize age into groups."""
    try:
        age = float(age)
        if age < 18:
            return "Less than 18 years"
        elif age < 65:
            return "Less than 65 years"
        else:
            return "Greater than equal 65 years"
    except:
        return "Unknown"

def generate_agewise_report(df, date_col, month, year, expired_filter=None):
    """Generate age-wise summary (Male/Female/Total) for a given month and year."""
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df["month"] = df[date_col].dt.month
    df["year"] = df[date_col].dt.year
    df = df[(df["month"] == month) & (df["year"] == year)]
    if expired_filter == "Yes":
        df = df[df["patient_expired"].astype(str).str.lower() == "yes"]
    df["Age Group"] = df["Age"].apply(get_age_group)
    df["Sex"] = df["sex"].fillna("Unknown").str.title()
    summary = (
        df.groupby(["Age Group", "Sex"])
        .size()
        .unstack(fill_value=0)
        .reindex(
            ["Less than 18 years", "Less than 65 years", "Greater than equal 65 years"],
            fill_value=0
        )
    )
    summary["Total"] = summary.sum(axis=1)
    total_row = pd.DataFrame(summary.sum()).T
    total_row.index = ["Total"]
    summary = pd.concat([summary, total_row])
    for sex in ["Male", "Female"]:
        if sex not in summary.columns:
            summary[sex] = 0
    return summary[["Male", "Female", "Total"]]

def load_css():
    """Load custom CSS styling with scrollable fixed sidebar, optimized metric cards, and table header wrapping."""
    try:
        with open("dashboard/styles.css") as f:
            css = f.read()
        card_css = """
        .metric-card {
            background-color: #f0f2f6;
            border-radius: 8px;
            padding: 12px;
            margin: 8px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
            min-height: 100px;
        }
        .metric-card h3 {
            margin: 0;
            font-size: 1.1em;
            color: #333;
        }
        .metric-card .metric-value {
            font-size: 1.8em;
            font-weight: bold;
            color: #007bff;
            margin: 8px 0;
        }
        /* Scrollable fixed sidebar */
        [data-testid="stSidebar"] {
            width: 15% !important;
            position: fixed !important;
            top: 0;
            left: 0;
            max-height: 100vh !important;
            overflow-y: auto !important;
            z-index: 100;
            padding: 10px;
            box-sizing: border-box;
        }
        [data-testid="stAppViewContainer"] {
            margin-left: 15% !important;
            width: 85% !important;
        }
        /* Table header wrapping and auto-width */
        [data-testid="stTable"] th {
            white-space: normal !important;
            word-wrap: break-word !important;
            max-width: 200px !important;
            min-width: 100px !important;
            width: auto !important;
            padding: 8px !important;
            line-height: 1.2em !important;
        }
        [data-testid="stTable"] td {
            max-width: 200px !important;
            min-width: 100px !important;
            width: auto !important;
            padding: 8px !important;
        }
        [data-testid="stTable"] {
            width: 100% !important;
        }
        /* Filter UI spacing */
        .filter-container select {
            margin-bottom: 5px;
            font-size: 0.85em;
            padding: 4px;
        }
        """
        st.markdown(f"<style>{css}\n{card_css}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error("Error: 'styles.css' not found.")

def export_nabl_pdf(month, year, adm_report, dsch_report, death_report):
    """Generate NABL PDF report for admissions, discharges, and deaths."""
    buffer = BytesIO()
    pdf = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []
    title = f"Age Wise IPD Report for the month of {datetime(year, month, 1).strftime('%B-%Y')}"
    elements.append(Paragraph(title, styles['Title']))
    elements.append(Spacer(1, 12))

    def add_table(title, df):
        elements.append(Paragraph(title, styles['Heading2']))
        data = [df.reset_index().columns.to_list()] + df.reset_index().values.tolist()
        t = Table(data)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 18))

    add_table("📅 Age Wise IPD Admission Report", adm_report)
    add_table("🏥 Age Wise IPD Discharge Report", dsch_report)
    add_table("⚰️ Age Wise IPD Death Report", death_report)
    pdf.build(elements)
    buffer.seek(0)
    return buffer

def main():
    st.set_page_config(layout="wide")
    st.title("🏥 Hospital Dashboard")

    load_css()

    # Initialize session state
    if 'ip_data' not in st.session_state:
        st.session_state.ip_data = None
    if 'op_data' not in st.session_state:
        st.session_state.op_data = None

    # Load saved data (if available)
    if st.session_state.ip_data is None and os.path.exists("ip_data.csv"):
        st.session_state.ip_data = pd.read_csv("ip_data.csv")
    if st.session_state.op_data is None and os.path.exists("op_data.csv"):
        st.session_state.op_data = pd.read_csv("op_data.csv")

    # Tabs
    tabs = st.tabs(["🔄 Refresh Data", "📋 IP Details", "📑 NABL Report", "📊 Dashboard"])

    # TAB 1: Refresh Data
    with tabs[0]:
        st.header("🔄 Refresh Data")
        if st.button("Refresh Data"):
            with st.spinner("Refreshing data..."):
                try:
                    ip_merge_df, op_merge_df = merge_data()
                    st.session_state.ip_data = ip_merge_df
                    st.session_state.op_data = op_merge_df
                    ip_merge_df.to_csv("ip_data.csv", index=False)
                    op_merge_df.to_csv("op_data.csv", index=False)
                    st.success(f"✅ Data refreshed successfully! IP data: {ip_merge_df.shape[0]} rows, "
                               f"unique ip_no: {ip_merge_df['ip_no'].nunique()}")
                    if ip_merge_df['ip_no'].duplicated().any():
                        st.warning(f"Warning: Found {ip_merge_df['ip_no'].duplicated().sum()} duplicate ip_no values")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
        
        if st.session_state.ip_data is not None:
            st.subheader("IP Data Preview")
            st.dataframe(st.session_state.ip_data.tail(100))
        if st.session_state.op_data is not None:
            st.subheader("OP Data Preview")
            st.dataframe(st.session_state.op_data.tail(100))

    # TAB 2: IP Details
    with tabs[1]:
        st.header("📋 IP Details - Filter IP Data")
        if st.session_state.ip_data is not None:
            filters = ip_filter_ui(st.session_state.ip_data, tab_key="ip_details")
            st.markdown("---")
            try:
                filter_args = {
                    'date_filter': filters['date_filter'],
                    'consultant_specialty': filters['consultant_specialty'],
                    'doc_name': filters['doc_name'],
                    'referral_specialty': filters['referral_specialty'],
                    'ref_name': filters['ref_name'],
                    'group': filters['group'],
                    'credit_company': filters['credit_company'],
                    'tpa_corporate': filters['tpa_corporate'],
                    'patient_expired': filters['patient_expired'],
                    'case_type': filters['case_type']
                }
                filtered_ip_data = filter_ip_data(st.session_state.ip_data, **filter_args)
                partial_data = filter_ip_data(st.session_state.ip_data)
                display_ip_metrics(filtered_ip_data)
                st.markdown("---")
                display_yearly_revenue_report(partial_data)
                st.markdown("---")
                display_yearly_ip_count_report(partial_data)
                st.markdown("---")
                display_monthly_revenue_report(partial_data)
                st.markdown("---")
                display_monthly_ip_count_report(partial_data)
                st.markdown("---")
                display_filtered_ip_data(filtered_ip_data)
            except Exception as e:
                st.error(f"Error filtering data: {e}")

    # TAB 3: NABL Report
    with tabs[2]:
        st.header("📑 NABL Age-Wise IPD Report")
        if st.session_state.ip_data is None:
            st.warning("Please refresh IP data first.")
        else:
            ip_df = st.session_state.ip_data.copy()
            ip_df["adm_dt"] = pd.to_datetime(ip_df["adm_dt"], errors="coerce")
            ip_df["dschg_dt"] = pd.to_datetime(ip_df["dschg_dt"], errors="coerce")
            current_month = datetime.now().month
            current_year = datetime.now().year
            col1, col2 = st.columns(2)
            with col1:
                month = st.selectbox(
                    "Select Month",
                    range(1, 13),
                    index=current_month - 1,
                    format_func=lambda x: datetime(1900, x, 1).strftime("%B")
                )
            with col2:
                available_years = sorted(ip_df["adm_dt"].dt.year.dropna().unique())
                if current_year not in available_years:
                    available_years.append(current_year)
                    available_years = sorted(available_years)
                year_index = available_years.index(current_year)
                year = st.selectbox("Select Year", available_years, index=year_index)
            st.markdown("### 📅 Age Wise IPD Admission Report")
            adm_report = generate_agewise_report(ip_df, "adm_dt", month, year)
            st.dataframe(adm_report)
            st.markdown("### 🏥 Age Wise IPD Discharge Report")
            dsch_report = generate_agewise_report(ip_df, "dschg_dt", month, year)
            st.dataframe(dsch_report)
            st.markdown("### ⚰️ Age Wise IPD Death Report")
            death_report = generate_agewise_report(ip_df, "dschg_dt", month, year, expired_filter="Yes")
            st.dataframe(death_report)
            if st.button("📤 Export NABL Report to PDF"):
                try:
                    pdf_buffer = export_nabl_pdf(month, year, adm_report, dsch_report, death_report)
                    st.download_button(
                        label="⬇️ Download NABL Report PDF",
                        data=pdf_buffer,
                        file_name=f"NABL_Report_{datetime(year, month, 1).strftime('%B_%Y')}.pdf",
                        mime="application/pdf"
                    )
                    st.success("✅ PDF generated successfully!")
                except Exception as e:
                    st.error(f"Error generating PDF: {e}")

    # TAB 4: Dashboard Overview
    with tabs[3]:
        st.header("📊 Dashboard Overview")
        if st.session_state.ip_data is not None:
            filters = ip_filter_ui(st.session_state.ip_data, tab_key="dashboard")
            st.markdown("---")
            try:
                # Extract filtered DataFrames
                filtered_ip_data = filters['filtered_df']  # Current period
                filtered_df_admissions = filters['filtered_df_admissions']  # Current period
                filtered_df_discharges = filters['filtered_df_discharges']  # Current period
                filtered_ip_data_full = filters['filtered_df_full']  # Full data with non-date filters
                filtered_df_admissions_full = filters['filtered_df_admissions_full']  # Full data with non-date filters
                filtered_df_discharges_full = filters['filtered_df_discharges_full']  # Full data with non-date filters
                date_filter = filters['date_filter']

                # Handle current and previous period ranges
                if date_filter:
                    start_date = pd.to_datetime(date_filter[0])
                    end_date = pd.to_datetime(date_filter[1])
                else:
                    today = datetime.today()
                    start_date = today.replace(day=1)
                    end_date = today

                date_span = (end_date - start_date).days + 1
                prev_end_date = end_date - relativedelta(months=1)
                prev_start_date = prev_end_date - relativedelta(days=date_span - 1)
                prev_start_date = max(prev_start_date, prev_end_date.replace(day=1))
                prev_prev_end_date = end_date - relativedelta(months=2)
                prev_prev_start_date = prev_prev_end_date - relativedelta(days=date_span - 1)
                prev_prev_start_date = max(prev_prev_start_date, prev_prev_end_date.replace(day=1))

                # Current Period Metrics
                current_discharges = filtered_df_discharges[
                    (pd.to_datetime(filtered_df_discharges['dschg_dt'], errors='coerce') >= start_date) &
                    (pd.to_datetime(filtered_df_discharges['dschg_dt'], errors='coerce') <= end_date)
                ]
                total_admissions = filtered_df_admissions[
                    (pd.to_datetime(filtered_df_admissions['adm_dt'], errors='coerce') >= start_date) &
                    (pd.to_datetime(filtered_df_admissions['adm_dt'], errors='coerce') <= end_date)
                ]['ip_no'].nunique()
                total_discharges = current_discharges['ip_no'].nunique()
                total_revenue = current_discharges['line_revenue'].apply(pd.to_numeric, errors='coerce').sum()

                # Previous Period Metrics
                prev_dschg_data = filtered_df_discharges_full[
                    (pd.to_datetime(filtered_df_discharges_full['dschg_dt'], errors='coerce') >= prev_start_date) &
                    (pd.to_datetime(filtered_df_discharges_full['dschg_dt'], errors='coerce') <= prev_end_date)
                ]
                prev_adm_data = filtered_df_admissions_full[
                    (pd.to_datetime(filtered_df_admissions_full['adm_dt'], errors='coerce') >= prev_start_date) &
                    (pd.to_datetime(filtered_df_admissions_full['adm_dt'], errors='coerce') <= prev_end_date)
                ]
                prev_admissions = prev_adm_data['ip_no'].nunique()
                prev_discharges = prev_dschg_data['ip_no'].nunique()
                prev_revenue = prev_dschg_data['line_revenue'].apply(pd.to_numeric, errors='coerce').sum()

                # Previous to Previous Period Metrics
                prev_prev_dschg_data = filtered_df_discharges_full[
                    (pd.to_datetime(filtered_df_discharges_full['dschg_dt'], errors='coerce') >= prev_prev_start_date) &
                    (pd.to_datetime(filtered_df_discharges_full['dschg_dt'], errors='coerce') <= prev_prev_end_date)
                ]
                prev_prev_discharges = prev_prev_dschg_data['ip_no'].nunique()

                # Average of Previous and Previous to Previous Month Discharges
                avg_prev_discharges = (prev_discharges + prev_prev_discharges) / 2

                # Occupancy (Current 3 months)
                end_date_occ = end_date
                start_date_3m = end_date_occ - timedelta(days=90)
                occupancy_data = filtered_ip_data_full[
                    (filtered_ip_data_full['adm_dt'].notnull()) &
                    (filtered_ip_data_full['dschg_dt'].isnull()) &
                    (pd.to_datetime(filtered_ip_data_full['adm_dt'], errors='coerce') >= start_date_3m) &
                    (pd.to_datetime(filtered_ip_data_full['adm_dt'], errors='coerce') <= end_date_occ)
                ]
                occupancy = occupancy_data['ip_no'].nunique()

                # Previous Occupancy
                prev_start_3m = start_date_3m - timedelta(days=90)
                prev_end_3m = end_date_occ - timedelta(days=90)
                prev_occupancy_data = filtered_ip_data_full[
                    (filtered_ip_data_full['adm_dt'].notnull()) &
                    (filtered_ip_data_full['dschg_dt'].isnull()) &
                    (pd.to_datetime(filtered_ip_data_full['adm_dt'], errors='coerce') >= prev_start_3m) &
                    (pd.to_datetime(filtered_ip_data_full['adm_dt'], errors='coerce') <= prev_end_3m)
                ]
                prev_occupancy = prev_occupancy_data['ip_no'].nunique()

                # Display Metrics in Sidebar
                def metric_card(title, current, previous, period="month"):
                    if title == "Occupancy (Last 3M)":
                        if current == 0 and previous == 0:
                            return f"""
                            <div class="metric-card">
                                <h3>{title}</h3>
                                <div class="metric-value">{current}</div>
                                <div style="color:gray; font-size:0.9em;">No data for prior period</div>
                            </div>
                            """
                        return f"""
                        <div class="metric-card">
                            <h3>{title}</h3>
                            <div class="metric-value">{current}</div>
                            <div style="color:gray; font-size:0.9em;">{previous} vs prior 3M</div>
                        </div>
                        """
                    else:
                        if current == 0 and previous == 0:
                            return f"""
                            <div class="metric-card">
                                <h3>{title}</h3>
                                <div class="metric-value">{int(current)}</div>
                                <div style="color:gray; font-size:0.9em;">No data for prior {period}</div>
                            </div>
                            """
                        diff = current - previous
                        arrow = "⬆️" if diff > 0 else "⬇️" if diff < 0 else "➡️"
                        color = "green" if diff > 0 else "red" if diff < 0 else "gray"
                        return f"""
                        <div class="metric-card">
                            <h3>{title}</h3>
                            <div class="metric-value">{int(current)}</div>
                            <div style="color:{color}; font-size:0.9em;">{int(previous)} ({arrow} {abs(int(diff))} vs prev {period})</div>
                        </div>
                        """

                with st.sidebar:
                    st.markdown(metric_card("Total Admissions", total_admissions, prev_admissions, "month"), unsafe_allow_html=True)
                    st.markdown(metric_card("Total Discharges", total_discharges, prev_discharges, "month"), unsafe_allow_html=True)
                    st.markdown(metric_card("Total Revenue", total_revenue, prev_revenue, "month"), unsafe_allow_html=True)
                    st.markdown(metric_card("Occupancy (Last 3M)", occupancy, prev_occupancy, "3M"), unsafe_allow_html=True)

                st.markdown("---")

                # Doctor-Wise, Referral Name-Wise, Specialty-Wise, TPA/Corporate-Wise, and Credit Company-Wise Metrics
                col_left, col_right = st.columns([1, 1])

                # Doctor-Wise
                with col_left:
                    with st.container(height=400):
                        st.subheader("Doctor-Wise Discharge Metrics (Current Period)")
                        doctor_metrics = current_discharges.groupby('DocName').agg({
                            'ip_no': 'nunique',
                            'line_revenue': lambda x: pd.to_numeric(x, errors='coerce').sum()
                        }).reset_index().rename(columns={
                            'ip_no': 'Count',
                            'line_revenue': 'Total Revenue'
                        })
                        doctor_metrics['ATS'] = doctor_metrics['Total Revenue'] / doctor_metrics['Count']
                        doctor_metrics = doctor_metrics.sort_values('Total Revenue', ascending=False)
                        total_row = pd.DataFrame({
                            'DocName': ['Total'],
                            'Count': [current_discharges['ip_no'].nunique()],
                            'Total Revenue': [current_discharges['line_revenue'].apply(pd.to_numeric, errors='coerce').sum()],
                            'ATS': [current_discharges['line_revenue'].apply(pd.to_numeric, errors='coerce').sum() / current_discharges['ip_no'].nunique() if current_discharges['ip_no'].nunique() > 0 else 0]
                        })
                        doctor_metrics = pd.concat([doctor_metrics, total_row], ignore_index=True)
                        doctor_metrics['Total Revenue'] = doctor_metrics['Total Revenue'].apply(lambda x: f"{int(x)}")
                        doctor_metrics['ATS'] = doctor_metrics['ATS'].apply(lambda x: f"{int(x)}")
                        st.dataframe(
                            doctor_metrics,
                            column_config={
                                "DocName": "Doctor Name",
                                "Count": st.column_config.NumberColumn("Count", format="%d"),
                                "Total Revenue": st.column_config.NumberColumn("Revenue", format="%d"),
                                "ATS": st.column_config.NumberColumn("ATS", format="%d")
                            },
                            hide_index=True,
                            use_container_width=True
                        )

                with col_right:
                    if total_discharges < avg_prev_discharges:
                        with st.container(height=400):
                            st.subheader("Doctor-Wise Discharge Analysis (Current vs Avg of Prev 2 Months)")
                            current_dschg_doctor = current_discharges.groupby('DocName')['ip_no'].nunique().reset_index().rename(columns={'ip_no': 'Current Month Count'})
                            prev_dschg_doctor = prev_dschg_data.groupby('DocName')['ip_no'].nunique().reset_index().rename(columns={'ip_no': 'Previous Month Count'})
                            prev_prev_dschg_doctor = prev_prev_dschg_data.groupby('DocName')['ip_no'].nunique().reset_index().rename(columns={'ip_no': 'Previous to Previous Month Count'})
                            dschg_doctor_comparison = pd.merge(current_dschg_doctor, prev_dschg_doctor, on='DocName', how='outer')
                            dschg_doctor_comparison = pd.merge(dschg_doctor_comparison, prev_prev_dschg_doctor, on='DocName', how='outer').fillna(0)
                            dschg_doctor_comparison['Difference'] = dschg_doctor_comparison['Current Month Count'] - (dschg_doctor_comparison['Previous Month Count'] + dschg_doctor_comparison['Previous to Previous Month Count']) / 2
                            dschg_doctor_comparison = dschg_doctor_comparison.sort_values('Difference', ascending=True)
                            total_row = pd.DataFrame({
                                'DocName': ['Total'],
                                'Current Month Count': [total_discharges],
                                'Previous Month Count': [prev_discharges],
                                'Previous to Previous Month Count': [prev_prev_discharges],
                                'Difference': [total_discharges - avg_prev_discharges]
                            })
                            dschg_doctor_comparison = pd.concat([dschg_doctor_comparison, total_row], ignore_index=True)
                            dschg_doctor_comparison[['Current Month Count', 'Previous Month Count', 'Previous to Previous Month Count', 'Difference']] = dschg_doctor_comparison[['Current Month Count', 'Previous Month Count', 'Previous to Previous Month Count', 'Difference']].apply(lambda x: x.round().astype(int))
                            st.dataframe(
                                dschg_doctor_comparison,
                                column_config={
                                    "DocName": "Doctor Name",
                                    "Current Month Count": st.column_config.NumberColumn("Current Month Discharges", format="%d"),
                                    "Previous Month Count": st.column_config.NumberColumn("Previous Month Discharges", format="%d"),
                                    "Previous to Previous Month Count": st.column_config.NumberColumn("Prev to Prev Month Discharges", format="%d"),
                                    "Difference": st.column_config.NumberColumn("Difference (vs Avg)", format="%d")
                                },
                                hide_index=True,
                                use_container_width=True
                            )

                # Referral Name-Wise
                with col_left:
                    with st.container(height=400):
                        st.subheader("Referring Name-Wise Discharge Metrics (Current Period)")
                        refname_metrics = current_discharges.groupby('refname').agg({
                            'ip_no': 'nunique',
                            'line_revenue': lambda x: pd.to_numeric(x, errors='coerce').sum()
                        }).reset_index().rename(columns={
                            'ip_no': 'Count',
                            'line_revenue': 'Total Revenue'
                        })
                        refname_metrics['ATS'] = refname_metrics['Total Revenue'] / refname_metrics['Count']
                        refname_metrics = refname_metrics.sort_values('Total Revenue', ascending=False)
                        total_row = pd.DataFrame({
                            'refname': ['Total'],
                            'Count': [current_discharges['ip_no'].nunique()],
                            'Total Revenue': [current_discharges['line_revenue'].apply(pd.to_numeric, errors='coerce').sum()],
                            'ATS': [current_discharges['line_revenue'].apply(pd.to_numeric, errors='coerce').sum() / current_discharges['ip_no'].nunique() if current_discharges['ip_no'].nunique() > 0 else 0]
                        })
                        refname_metrics = pd.concat([refname_metrics, total_row], ignore_index=True)
                        refname_metrics['Total Revenue'] = refname_metrics['Total Revenue'].apply(lambda x: f"{int(x)}")
                        refname_metrics['ATS'] = refname_metrics['ATS'].apply(lambda x: f"{int(x)}")
                        st.dataframe(
                            refname_metrics,
                            column_config={
                                "refname": "Referring Name",
                                "Count": st.column_config.NumberColumn("Count", format="%d"),
                                "Total Revenue": st.column_config.NumberColumn("Revenue", format="%d"),
                                "ATS": st.column_config.NumberColumn("ATS", format="%d")
                            },
                            hide_index=True,
                            use_container_width=True
                        )

                with col_right:
                    if total_discharges < avg_prev_discharges:
                        with st.container(height=400):
                            st.subheader("Referring Name-Wise Discharge Analysis (Current vs Avg of Prev 2 Months)")
                            current_dschg_refname = current_discharges.groupby('refname')['ip_no'].nunique().reset_index().rename(columns={'ip_no': 'Current Month Count'})
                            prev_dschg_refname = prev_dschg_data.groupby('refname')['ip_no'].nunique().reset_index().rename(columns={'ip_no': 'Previous Month Count'})
                            prev_prev_dschg_refname = prev_prev_dschg_data.groupby('refname')['ip_no'].nunique().reset_index().rename(columns={'ip_no': 'Previous to Previous Month Count'})
                            dschg_refname_comparison = pd.merge(current_dschg_refname, prev_dschg_refname, on='refname', how='outer')
                            dschg_refname_comparison = pd.merge(dschg_refname_comparison, prev_prev_dschg_refname, on='refname', how='outer').fillna(0)
                            dschg_refname_comparison['Difference'] = dschg_refname_comparison['Current Month Count'] - (dschg_refname_comparison['Previous Month Count'] + dschg_refname_comparison['Previous to Previous Month Count']) / 2
                            dschg_refname_comparison = dschg_refname_comparison.sort_values('Difference', ascending=True)
                            total_row = pd.DataFrame({
                                'refname': ['Total'],
                                'Current Month Count': [total_discharges],
                                'Previous Month Count': [prev_discharges],
                                'Previous to Previous Month Count': [prev_prev_discharges],
                                'Difference': [total_discharges - avg_prev_discharges]
                            })
                            dschg_refname_comparison = pd.concat([dschg_refname_comparison, total_row], ignore_index=True)
                            dschg_refname_comparison[['Current Month Count', 'Previous Month Count', 'Previous to Previous Month Count', 'Difference']] = dschg_refname_comparison[['Current Month Count', 'Previous Month Count', 'Previous to Previous Month Count', 'Difference']].apply(lambda x: x.round().astype(int))
                            st.dataframe(
                                dschg_refname_comparison,
                                column_config={
                                    "refname": "Referring Name",
                                    "Current Month Count": st.column_config.NumberColumn("Current Month Discharges", format="%d"),
                                    "Previous Month Count": st.column_config.NumberColumn("Previous Month Discharges", format="%d"),
                                    "Previous to Previous Month Count": st.column_config.NumberColumn("Prev to Prev Month Discharges", format="%d"),
                                    "Difference": st.column_config.NumberColumn("Difference (vs Avg)", format="%d")
                                },
                                hide_index=True,
                                use_container_width=True
                            )

                # Specialty-Wise
                with col_left:
                    with st.container(height=400):
                        st.subheader("Specialty-Wise Discharge Metrics (Current Period)")
                        specialty_metrics = current_discharges.groupby('consultant_specialty').agg({
                            'ip_no': 'nunique',
                            'line_revenue': lambda x: pd.to_numeric(x, errors='coerce').sum()
                        }).reset_index().rename(columns={
                            'ip_no': 'Count',
                            'line_revenue': 'Total Revenue'
                        })
                        specialty_metrics['ATS'] = specialty_metrics['Total Revenue'] / specialty_metrics['Count']
                        specialty_metrics = specialty_metrics.sort_values('Total Revenue', ascending=False)
                        total_row = pd.DataFrame({
                            'consultant_specialty': ['Total'],
                            'Count': [current_discharges['ip_no'].nunique()],
                            'Total Revenue': [current_discharges['line_revenue'].apply(pd.to_numeric, errors='coerce').sum()],
                            'ATS': [current_discharges['line_revenue'].apply(pd.to_numeric, errors='coerce').sum() / current_discharges['ip_no'].nunique() if current_discharges['ip_no'].nunique() > 0 else 0]
                        })
                        specialty_metrics = pd.concat([specialty_metrics, total_row], ignore_index=True)
                        specialty_metrics['Total Revenue'] = specialty_metrics['Total Revenue'].apply(lambda x: f"{int(x)}")
                        specialty_metrics['ATS'] = specialty_metrics['ATS'].apply(lambda x: f"{int(x)}")
                        st.dataframe(
                            specialty_metrics,
                            column_config={
                                "consultant_specialty": "Consultant Specialty",
                                "Count": st.column_config.NumberColumn("Count", format="%d"),
                                "Total Revenue": st.column_config.NumberColumn("Revenue", format="%d"),
                                "ATS": st.column_config.NumberColumn("ATS", format="%d")
                            },
                            hide_index=True,
                            use_container_width=True
                        )

                with col_right:
                    if total_discharges < avg_prev_discharges:
                        with st.container(height=400):
                            st.subheader("Specialty-Wise Discharge Analysis (Current vs Avg of Prev 2 Months)")
                            current_dschg_specialty = current_discharges.groupby('consultant_specialty')['ip_no'].nunique().reset_index().rename(columns={'ip_no': 'Current Month Count'})
                            prev_dschg_specialty = prev_dschg_data.groupby('consultant_specialty')['ip_no'].nunique().reset_index().rename(columns={'ip_no': 'Previous Month Count'})
                            prev_prev_dschg_specialty = prev_prev_dschg_data.groupby('consultant_specialty')['ip_no'].nunique().reset_index().rename(columns={'ip_no': 'Previous to Previous Month Count'})
                            dschg_specialty_comparison = pd.merge(current_dschg_specialty, prev_dschg_specialty, on='consultant_specialty', how='outer')
                            dschg_specialty_comparison = pd.merge(dschg_specialty_comparison, prev_prev_dschg_specialty, on='consultant_specialty', how='outer').fillna(0)
                            dschg_specialty_comparison['Difference'] = dschg_specialty_comparison['Current Month Count'] - (dschg_specialty_comparison['Previous Month Count'] + dschg_specialty_comparison['Previous to Previous Month Count']) / 2
                            dschg_specialty_comparison = dschg_specialty_comparison.sort_values('Difference', ascending=True)
                            total_row = pd.DataFrame({
                                'consultant_specialty': ['Total'],
                                'Current Month Count': [total_discharges],
                                'Previous Month Count': [prev_discharges],
                                'Previous to Previous Month Count': [prev_prev_discharges],
                                'Difference': [total_discharges - avg_prev_discharges]
                            })
                            dschg_specialty_comparison = pd.concat([dschg_specialty_comparison, total_row], ignore_index=True)
                            dschg_specialty_comparison[['Current Month Count', 'Previous Month Count', 'Previous to Previous Month Count', 'Difference']] = dschg_specialty_comparison[['Current Month Count', 'Previous Month Count', 'Previous to Previous Month Count', 'Difference']].apply(lambda x: x.round().astype(int))
                            st.dataframe(
                                dschg_specialty_comparison,
                                column_config={
                                    "consultant_specialty": "Consultant Specialty",
                                    "Current Month Count": st.column_config.NumberColumn("Current Month Discharges", format="%d"),
                                    "Previous Month Count": st.column_config.NumberColumn("Previous Month Discharges", format="%d"),
                                    "Previous to Previous Month Count": st.column_config.NumberColumn("Prev to Prev Month Discharges", format="%d"),
                                    "Difference": st.column_config.NumberColumn("Difference (vs Avg)", format="%d")
                                },
                                hide_index=True,
                                use_container_width=True
                            )

                # TPA/Corporate-Wise
                with col_left:
                    with st.container(height=400):
                        st.subheader("TPA/Corporate-Wise Discharge Metrics (Current Period)")
                        tpa_corporate_metrics = current_discharges.groupby('TPA/CORPORATE').agg({
                            'ip_no': 'nunique',
                            'line_revenue': lambda x: pd.to_numeric(x, errors='coerce').sum()
                        }).reset_index().rename(columns={
                            'ip_no': 'Count',
                            'line_revenue': 'Total Revenue'
                        })
                        tpa_corporate_metrics['ATS'] = tpa_corporate_metrics['Total Revenue'] / tpa_corporate_metrics['Count']
                        tpa_corporate_metrics = tpa_corporate_metrics.sort_values('Total Revenue', ascending=False)
                        total_row = pd.DataFrame({
                            'TPA/CORPORATE': ['Total'],
                            'Count': [current_discharges['ip_no'].nunique()],
                            'Total Revenue': [current_discharges['line_revenue'].apply(pd.to_numeric, errors='coerce').sum()],
                            'ATS': [current_discharges['line_revenue'].apply(pd.to_numeric, errors='coerce').sum() / current_discharges['ip_no'].nunique() if current_discharges['ip_no'].nunique() > 0 else 0]
                        })
                        tpa_corporate_metrics = pd.concat([tpa_corporate_metrics, total_row], ignore_index=True)
                        tpa_corporate_metrics['Total Revenue'] = tpa_corporate_metrics['Total Revenue'].apply(lambda x: f"{int(x)}")
                        tpa_corporate_metrics['ATS'] = tpa_corporate_metrics['ATS'].apply(lambda x: f"{int(x)}")
                        st.dataframe(
                            tpa_corporate_metrics,
                            column_config={
                                "TPA/CORPORATE": "TPA/Corporate",
                                "Count": st.column_config.NumberColumn("Count", format="%d"),
                                "Total Revenue": st.column_config.NumberColumn("Revenue", format="%d"),
                                "ATS": st.column_config.NumberColumn("ATS", format="%d")
                            },
                            hide_index=True,
                            use_container_width=True
                        )

                with col_right:
                    if total_discharges < avg_prev_discharges:
                        with st.container(height=400):
                            st.subheader("TPA/Corporate-Wise Discharge Analysis (Current vs Avg of Prev 2 Months)")
                            current_dschg_tpa = current_discharges.groupby('TPA/CORPORATE')['ip_no'].nunique().reset_index().rename(columns={'ip_no': 'Current Month Count'})
                            prev_dschg_tpa = prev_dschg_data.groupby('TPA/CORPORATE')['ip_no'].nunique().reset_index().rename(columns={'ip_no': 'Previous Month Count'})
                            prev_prev_dschg_tpa = prev_prev_dschg_data.groupby('TPA/CORPORATE')['ip_no'].nunique().reset_index().rename(columns={'ip_no': 'Previous to Previous Month Count'})
                            dschg_tpa_comparison = pd.merge(current_dschg_tpa, prev_dschg_tpa, on='TPA/CORPORATE', how='outer')
                            dschg_tpa_comparison = pd.merge(dschg_tpa_comparison, prev_prev_dschg_tpa, on='TPA/CORPORATE', how='outer').fillna(0)
                            dschg_tpa_comparison['Difference'] = dschg_tpa_comparison['Current Month Count'] - (dschg_tpa_comparison['Previous Month Count'] + dschg_tpa_comparison['Previous to Previous Month Count']) / 2
                            dschg_tpa_comparison = dschg_tpa_comparison.sort_values('Difference', ascending=True)
                            total_row = pd.DataFrame({
                                'TPA/CORPORATE': ['Total'],
                                'Current Month Count': [total_discharges],
                                'Previous Month Count': [prev_discharges],
                                'Previous to Previous Month Count': [prev_prev_discharges],
                                'Difference': [total_discharges - avg_prev_discharges]
                            })
                            dschg_tpa_comparison = pd.concat([dschg_tpa_comparison, total_row], ignore_index=True)
                            dschg_tpa_comparison[['Current Month Count', 'Previous Month Count', 'Previous to Previous Month Count', 'Difference']] = dschg_tpa_comparison[['Current Month Count', 'Previous Month Count', 'Previous to Previous Month Count', 'Difference']].apply(lambda x: x.round().astype(int))
                            st.dataframe(
                                dschg_tpa_comparison,
                                column_config={
                                    "TPA/CORPORATE": "TPA/Corporate",
                                    "Current Month Count": st.column_config.NumberColumn("Current Month Discharges", format="%d"),
                                    "Previous Month Count": st.column_config.NumberColumn("Previous Month Discharges", format="%d"),
                                    "Previous to Previous Month Count": st.column_config.NumberColumn("Prev to Prev Month Discharges", format="%d"),
                                    "Difference": st.column_config.NumberColumn("Difference (vs Avg)", format="%d")
                                },
                                hide_index=True,
                                use_container_width=True
                            )

                # Credit Company-Wise
                with col_left:
                    with st.container(height=400):
                        st.subheader("Credit Company-Wise Discharge Metrics (Current Period)")
                        credit_company_metrics = current_discharges.groupby('CREDIT COMPANY').agg({
                            'ip_no': 'nunique',
                            'line_revenue': lambda x: pd.to_numeric(x, errors='coerce').sum()
                        }).reset_index().rename(columns={
                            'ip_no': 'Count',
                            'line_revenue': 'Total Revenue'
                        })
                        credit_company_metrics['ATS'] = credit_company_metrics['Total Revenue'] / credit_company_metrics['Count']
                        credit_company_metrics = credit_company_metrics.sort_values('Total Revenue', ascending=False)
                        total_row = pd.DataFrame({
                            'CREDIT COMPANY': ['Total'],
                            'Count': [current_discharges['ip_no'].nunique()],
                            'Total Revenue': [current_discharges['line_revenue'].apply(pd.to_numeric, errors='coerce').sum()],
                            'ATS': [current_discharges['line_revenue'].apply(pd.to_numeric, errors='coerce').sum() / current_discharges['ip_no'].nunique() if current_discharges['ip_no'].nunique() > 0 else 0]
                        })
                        credit_company_metrics = pd.concat([credit_company_metrics, total_row], ignore_index=True)
                        credit_company_metrics['Total Revenue'] = credit_company_metrics['Total Revenue'].apply(lambda x: f"{int(x)}")
                        credit_company_metrics['ATS'] = credit_company_metrics['ATS'].apply(lambda x: f"{int(x)}")
                        st.dataframe(
                            credit_company_metrics,
                            column_config={
                                "CREDIT COMPANY": "Credit Company",
                                "Count": st.column_config.NumberColumn("Count", format="%d"),
                                "Total Revenue": st.column_config.NumberColumn("Revenue", format="%d"),
                                "ATS": st.column_config.NumberColumn("ATS", format="%d")
                            },
                            hide_index=True,
                            use_container_width=True
                        )

                with col_right:
                    if total_discharges < avg_prev_discharges:
                        with st.container(height=400):
                            st.subheader("Credit Company-Wise Discharge Analysis (Current vs Avg of Prev 2 Months)")
                            current_dschg_credit = current_discharges.groupby('CREDIT COMPANY')['ip_no'].nunique().reset_index().rename(columns={'ip_no': 'Current Month Count'})
                            prev_dschg_credit = prev_dschg_data.groupby('CREDIT COMPANY')['ip_no'].nunique().reset_index().rename(columns={'ip_no': 'Previous Month Count'})
                            prev_prev_dschg_credit = prev_prev_dschg_data.groupby('CREDIT COMPANY')['ip_no'].nunique().reset_index().rename(columns={'ip_no': 'Previous to Previous Month Count'})
                            dschg_credit_comparison = pd.merge(current_dschg_credit, prev_dschg_credit, on='CREDIT COMPANY', how='outer')
                            dschg_credit_comparison = pd.merge(dschg_credit_comparison, prev_prev_dschg_credit, on='CREDIT COMPANY', how='outer').fillna(0)
                            dschg_credit_comparison['Difference'] = dschg_credit_comparison['Current Month Count'] - (dschg_credit_comparison['Previous Month Count'] + dschg_credit_comparison['Previous to Previous Month Count']) / 2
                            dschg_credit_comparison = dschg_credit_comparison.sort_values('Difference', ascending=True)
                            total_row = pd.DataFrame({
                                'CREDIT COMPANY': ['Total'],
                                'Current Month Count': [total_discharges],
                                'Previous Month Count': [prev_discharges],
                                'Previous to Previous Month Count': [prev_prev_discharges],
                                'Difference': [total_discharges - avg_prev_discharges]
                            })
                            dschg_credit_comparison = pd.concat([dschg_credit_comparison, total_row], ignore_index=True)
                            dschg_credit_comparison[['Current Month Count', 'Previous Month Count', 'Previous to Previous Month Count', 'Difference']] = dschg_credit_comparison[['Current Month Count', 'Previous Month Count', 'Previous to Previous Month Count', 'Difference']].apply(lambda x: x.round().astype(int))
                            st.dataframe(
                                dschg_credit_comparison,
                                column_config={
                                    "CREDIT COMPANY": "Credit Company",
                                    "Current Month Count": st.column_config.NumberColumn("Current Month Discharges", format="%d"),
                                    "Previous Month Count": st.column_config.NumberColumn("Previous Month Discharges", format="%d"),
                                    "Previous to Previous Month Count": st.column_config.NumberColumn("Prev to Prev Month Discharges", format="%d"),
                                    "Difference": st.column_config.NumberColumn("Difference (vs Avg)", format="%d")
                                },
                                hide_index=True,
                                use_container_width=True
                            )

                st.markdown("---")
                display_filtered_ip_data(filtered_ip_data)

            except Exception as e:
                st.error(f"❌ Dashboard error: {e}")

if __name__ == "__main__":
    main()