import plotly.express as px

def admission_trend(ip_df):
    trend = ip_df.groupby('dschg_dt').size().reset_index(name="Count")
    return px.line(trend, x="dschg_dt", y="Count", title="IP Admissions Over Time")

def revenue_by_specialty(ip_df):
    spec = ip_df.groupby('consultant_specialty')['Settlement Gross'].sum().reset_index()
    return px.bar(spec, x="consultant_specialty", y="Settlement Gross", title="Revenue by Specialty")
