import streamlit as st
import locale
import plotly.express as px
import pandas as pd

# Set locale to Indian English (en_IN) for currency formatting
try:
    locale.setlocale(locale.LC_ALL, 'en_IN')  # Set to Indian locale for ₹ symbol
except locale.Error:
    # Fallback to a generic locale if en_IN is not available
    locale.setlocale(locale.LC_ALL, '')  # Use system's default locale
    st.warning("Locale set to system default. Currency might not display as ₹. Install 'en_IN' locale for full support.")

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