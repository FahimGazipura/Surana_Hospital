import streamlit as st
import locale
import plotly.express as px
# reports/pdf_reports.py
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import pandas as pd


def export_nabl_report_to_pdf(df, file_path="NABL_Report.pdf"):
    """
    Generate Age-wise IPD NABL report PDF from cleaned IPD DataFrame.
    df must have columns: adm_dt, dsch_dt, Age, Sex, patient_expired (Yes/No)
    """
    try:
        # Ensure numeric values are Python int
        df = df.copy()
        df['Age'] = df['Age'].apply(lambda x: int(x) if pd.notna(x) else 0)

        # Categorize Age groups
        def age_group(age):
            if age < 18:
                return "Less than 18 years"
            elif age < 65:
                return "Less than 65 years"
            else:
                return "Greater than equal 65 years"

        df['Age Group'] = df['Age'].apply(age_group)

        # Admission Report
        adm_df = df.groupby(['Age Group', 'Sex']).size().unstack(fill_value=0)
        adm_df['Total'] = adm_df.sum(axis=1)
        adm_df.loc['Total'] = adm_df.sum(numeric_only=True)

        # Discharge Report
        dsch_df = df[df['dsch_dt'].notna()].groupby(['Age Group', 'Sex']).size().unstack(fill_value=0)
        dsch_df['Total'] = dsch_df.sum(axis=1)
        dsch_df.loc['Total'] = dsch_df.sum(numeric_only=True)

        # Death Report
        death_df = df[df['patient_expired'].str.upper() == 'YES'].groupby(['Age Group', 'Sex']).size().unstack(
            fill_value=0)
        death_df['Total'] = death_df.sum(axis=1)
        death_df.loc['Total'] = death_df.sum(numeric_only=True)

        # PDF setup
        doc = SimpleDocTemplate(file_path, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        # Title
        elements.append(Paragraph("Age Wise IPD NABL Report", styles['Title']))
        elements.append(Spacer(1, 12))

        # Function to add table
        def add_table(df_table, title):
            elements.append(Paragraph(title, styles['Heading2']))
            data = [df_table.columns.tolist()] + df_table.reset_index().values.tolist()
            # Convert all elements to str to avoid float issues
            data = [[str(cell) for cell in row] for row in data]
            table = Table(data, hAlign='LEFT')
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)
            elements.append(Spacer(1, 12))

        add_table(adm_df, "Age Wise IPD Admission Report")
        add_table(dsch_df, "Age Wise IPD Discharge Report")
        add_table(death_df, "Age Wise IPD Death Report")

        # Build PDF
        doc.build(elements)
        print(f"✅ NABL Report exported successfully: {file_path}")

    except Exception as e:
        print(f"❌ Error generating PDF: {e}")


# Ensure locale is set for Indian Rupees
try:
    locale.setlocale(locale.LC_MONETARY, 'en_IN')
except locale.Error:
    locale.setlocale(locale.LC_MONETARY, '')

def display_ip_metrics(filtered_ip_data):
    """
    Display metrics cards for filtered IP data.
    
    Parameters:
    - filtered_ip_data: Filtered DataFrame from ip_data
    """
    with st.container():
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        col_metrics1, col_metrics2, col_metrics3 = st.columns(3)
        with col_metrics1:
            total_ip_count = filtered_ip_data['ip_no'].nunique()
            st.metric(label="Total IP Count", value=total_ip_count)
        with col_metrics2:
            total_revenue = filtered_ip_data['line_revenue'].sum()
            st.metric(label="Total Revenue", value=locale.currency(total_revenue, grouping=True, symbol=True))
        with col_metrics3:
            if total_ip_count > 0:
                ats = total_revenue / total_ip_count
                ats_value = locale.currency(ats, grouping=True, symbol=True)
            else:
                ats_value = "N/A"
            st.metric(label="ATS (Revenue/IP)", value=ats_value)
        st.markdown('</div>', unsafe_allow_html=True)

def display_filtered_ip_data(filtered_ip_data):
    """
    Display filtered IP data table with total record count.
    
    Parameters:
    - filtered_ip_data: Filtered DataFrame from ip_data
    """
    st.subheader("Filtered IP Data")
    st.dataframe(filtered_ip_data, use_container_width=True)
    st.write(f"Total Records: {len(filtered_ip_data)}")

def display_yearly_revenue_report(ip_data):
    """
    Display year-wise revenue report with a table on the left and a line chart on the right
    for filtered ip_data (all filters except dschg_dt) using existing dis_year column.
    
    Parameters:
    - ip_data: Filtered DataFrame (ip_data)
    """
    if ip_data is None or ip_data.empty or 'dis_year' not in ip_data.columns:
        st.warning("No data available for year-wise revenue report or dis_year column missing.")
        return

    # Group by dis_year and sum line_revenue
    yearly_revenue = ip_data.groupby('dis_year')['line_revenue'].sum().reset_index()

    # Ensure dis_year is string for display
    yearly_revenue['dis_year'] = yearly_revenue['dis_year'].astype(str)

    # Create two columns for table and chart
    col_table, col_chart = st.columns(2)

    # Table on the left
    with col_table:
        st.subheader("Year-Wise Revenue Report")
        # Format line_revenue as Indian Rupees for the table
        table_data = yearly_revenue.copy()
        table_data['line_revenue'] = table_data['line_revenue'].apply(
            lambda x: locale.currency(x, grouping=True, symbol=True)
        )
        st.dataframe(table_data, use_container_width=True, height=200)

    # Line chart on the right
    with col_chart:
        st.subheader("Year-Wise Revenue Trend")
        fig = px.line(
            yearly_revenue,
            x='dis_year',
            y='line_revenue',
            markers=True,
            labels={'dis_year': 'Year', 'line_revenue': 'Revenue (₹)'},
            title=""
        )
        fig.update_layout(
            xaxis_title="Year",
            yaxis_title="Revenue (₹)",
            showlegend=False,
            margin=dict(l=0, r=0, t=30, b=0),
            height=200
        )
        fig.update_traces(line_color='#007bff', marker=dict(size=8))
        st.plotly_chart(fig, use_container_width=True)

def display_yearly_ip_count_report(ip_data):
    """
    Display year-wise unique IP count report with a table on the left and a line chart on the right
    for filtered ip_data (all filters except dschg_dt) using existing dis_year column.
    
    Parameters:
    - ip_data: Filtered DataFrame (ip_data)
    """
    if ip_data is None or ip_data.empty or 'dis_year' not in ip_data.columns or 'ip_no' not in ip_data.columns:
        st.warning("No data available for year-wise IP count report or required columns missing.")
        return

    # Group by dis_year and count unique ip_no
    yearly_ip_count = ip_data.groupby('dis_year')['ip_no'].nunique().reset_index()
    yearly_ip_count.columns = ['dis_year', 'ip_count']

    # Ensure dis_year is string for display
    yearly_ip_count['dis_year'] = yearly_ip_count['dis_year'].astype(str)

    # Create two columns for table and chart
    col_table, col_chart = st.columns(2)

    # Table on the left
    with col_table:
        st.subheader("Year-Wise IP Count Report")
        st.dataframe(yearly_ip_count, use_container_width=True, height=200)

    # Line chart on the right
    with col_chart:
        st.subheader("Year-Wise IP Count Trend")
        fig = px.line(
            yearly_ip_count,
            x='dis_year',
            y='ip_count',
            markers=True,
            labels={'dis_year': 'Year', 'ip_count': 'Unique IP Count'},
            title=""
        )
        fig.update_layout(
            xaxis_title="Year",
            yaxis_title="Unique IP Count",
            showlegend=False,
            margin=dict(l=0, r=0, t=30, b=0),
            height=200
        )
        fig.update_traces(line_color='#28a745', marker=dict(size=8))
        st.plotly_chart(fig, use_container_width=True)

def display_monthly_revenue_report(ip_data):
    """
    Display month-wise revenue report with a table on the left and a line chart on the right
    for filtered ip_data (all filters except dschg_dt) using dis_year and dis_month_name,
    showing last 5 unique years (numeric) and months ordered January to December.
    
    Parameters:
    - ip_data: Filtered DataFrame (ip_data)
    """
    if ip_data is None or ip_data.empty or 'dis_year' not in ip_data.columns or 'dis_month_name' not in ip_data.columns:
        st.warning("No data available for month-wise revenue report or required columns missing.")
        return

    # Define month order (January to December)
    month_order = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]

    # Get last 5 unique years from ip_data (numeric)
    unique_years = sorted(ip_data['dis_year'].dropna().astype(int).unique(), reverse=True)
    last_5_years = unique_years[:5] if len(unique_years) >= 5 else unique_years
    if not last_5_years:
        st.warning("No valid dis_year values found in the data.")
        return

    # Filter for last 5 years
    ip_data = ip_data[ip_data['dis_year'].isin(last_5_years)]

    if ip_data.empty:
        st.warning(f"No data available for years: {', '.join(map(str, last_5_years))}")
        return

    # Group by dis_month_name and dis_year, sum line_revenue
    monthly_revenue = ip_data.groupby(['dis_month_name', 'dis_year'])['line_revenue'].sum().reset_index()

    if monthly_revenue.empty:
        st.warning("No data after grouping by dis_month_name and dis_year. Check dis_month_name values.")
        return

    # Convert dis_year to string for display
    monthly_revenue['dis_year'] = monthly_revenue['dis_year'].astype(str)

    # Pivot to get dis_year as columns and dis_month_name as rows
    pivot_table = monthly_revenue.pivot(index='dis_month_name', columns='dis_year', values='line_revenue').fillna(0)

    # Reindex to ensure all months in order, fill missing months with 0
    pivot_table = pivot_table.reindex(month_order, fill_value=0)

    # Create two columns for table and chart
    col_table, col_chart = st.columns(2)

    # Table on the left
    with col_table:
        st.subheader("Month-Wise Revenue Report")
        # Format revenue as Indian Rupees
        formatted_table = pivot_table.copy()
        for col in formatted_table.columns:
            formatted_table[col] = formatted_table[col].apply(
                lambda x: locale.currency(x, grouping=True, symbol=True) if x > 0 else "₹0"
            )
        st.dataframe(formatted_table, use_container_width=True, height=450)

    # Line chart on the right
    with col_chart:
        st.subheader("Month-Wise Revenue Trend")
        # Prepare data for line chart (melt pivot table back to long format)
        chart_data = monthly_revenue.pivot(index='dis_month_name', columns='dis_year', values='line_revenue').reset_index()
        chart_data = chart_data.melt(id_vars='dis_month_name', var_name='dis_year', value_name='line_revenue')
        chart_data = chart_data[chart_data['line_revenue'].notnull()]
        # Ensure month order
        chart_data['dis_month_name'] = pd.Categorical(chart_data['dis_month_name'], categories=month_order, ordered=True)
        chart_data = chart_data.sort_values('dis_month_name')
        fig = px.line(
            chart_data,
            x='dis_month_name',
            y='line_revenue',
            color='dis_year',
            markers=True,
            labels={'dis_month_name': 'Month', 'line_revenue': 'Revenue (₹)', 'dis_year': 'Year'},
            title=""
        )
        fig.update_layout(
            xaxis_title="Month",
            yaxis_title="Revenue (₹)",
            legend_title="Year",
            margin=dict(l=0, r=0, t=30, b=0),
            height=450
        )
        fig.update_traces(marker=dict(size=8))
        st.plotly_chart(fig, use_container_width=True)

def display_monthly_ip_count_report(ip_data):
    """
    Display month-wise unique IP count report with a table on the left and a line chart on the right
    for filtered ip_data (all filters except dschg_dt) using dis_year and dis_month_name,
    showing last 5 unique years (numeric) and months ordered January to December.
    
    Parameters:
    - ip_data: Filtered DataFrame (ip_data)
    """
    if ip_data is None or ip_data.empty or 'dis_year' not in ip_data.columns or 'dis_month_name' not in ip_data.columns or 'ip_no' not in ip_data.columns:
        st.warning("No data available for month-wise IP count report or required columns missing.")
        return

    # Define month order (January to December)
    month_order = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December'
    ]

    # Get last 5 unique years from ip_data (numeric)
    unique_years = sorted(ip_data['dis_year'].dropna().astype(int).unique(), reverse=True)
    last_5_years = unique_years[:5] if len(unique_years) >= 5 else unique_years
    if not last_5_years:
        st.warning("No valid dis_year values found in the data.")
        return

    # Filter for last 5 years
    ip_data = ip_data[ip_data['dis_year'].isin(last_5_years)]

    if ip_data.empty:
        st.warning(f"No data available for years: {', '.join(map(str, last_5_years))}")
        return

    # Group by dis_month_name and dis_year, count unique ip_no
    monthly_ip_count = ip_data.groupby(['dis_month_name', 'dis_year'])['ip_no'].nunique().reset_index()
    monthly_ip_count.columns = ['dis_month_name', 'dis_year', 'ip_count']

    if monthly_ip_count.empty:
        st.warning("No data after grouping by dis_month_name and dis_year. Check dis_month_name values.")
        return

    # Convert dis_year to string for display
    monthly_ip_count['dis_year'] = monthly_ip_count['dis_year'].astype(str)

    # Pivot to get dis_year as columns and dis_month_name as rows
    pivot_table = monthly_ip_count.pivot(index='dis_month_name', columns='dis_year', values='ip_count').fillna(0)

    # Reindex to ensure all months in order, fill missing months with 0
    pivot_table = pivot_table.reindex(month_order, fill_value=0)

    # Create two columns for table and chart
    col_table, col_chart = st.columns(2)

    # Table on the left
    with col_table:
        st.subheader("Month-Wise IP Count Report")
        # Format counts as integers
        formatted_table = pivot_table.copy()
        for col in formatted_table.columns:
            formatted_table[col] = formatted_table[col].astype(int)
        st.dataframe(formatted_table, use_container_width=True, height=450)

    # Line chart on the right
    with col_chart:
        st.subheader("Month-Wise IP Count Trend")
        # Prepare data for line chart (melt pivot table back to long format)
        chart_data = monthly_ip_count.pivot(index='dis_month_name', columns='dis_year', values='ip_count').reset_index()
        chart_data = chart_data.melt(id_vars='dis_month_name', var_name='dis_year', value_name='ip_count')
        chart_data = chart_data[chart_data['ip_count'].notnull()]
        # Ensure month order
        chart_data['dis_month_name'] = pd.Categorical(chart_data['dis_month_name'], categories=month_order, ordered=True)
        chart_data = chart_data.sort_values('dis_month_name')
        fig = px.line(
            chart_data,
            x='dis_month_name',
            y='ip_count',
            color='dis_year',
            markers=True,
            labels={'dis_month_name': 'Month', 'ip_count': 'Unique IP Count', 'dis_year': 'Year'},
            title=""
        )
        fig.update_layout(
            xaxis_title="Month",
            yaxis_title="Unique IP Count",
            legend_title="Year",
            margin=dict(l=0, r=0, t=30, b=0),
            height=450
        )
        fig.update_traces(marker=dict(size=8))
        st.plotly_chart(fig, use_container_width=True)