import streamlit as st

def kpi_cards(summary_dict):
    cols = st.columns(len(summary_dict))
    for idx, (k,v) in enumerate(summary_dict.items()):
        cols[idx].metric(label=k, value=f"{v:,.0f}")
