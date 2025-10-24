import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

def safe_unique_list(df, col):
    """Return a safe list of unique values (handles NaN)."""
    return sorted(df[col].fillna('Unknown').astype(str).unique().tolist())

def filter_ip_data(
    df,
    date_filter=None,
    doc_name=None,
    ref_name=None,
    consultant_specialty=None,
    group=None,
    referral_specialty=None,
    credit_company=None,
    tpa_corporate=None,
    patient_expired=None,
    case_type=None
):
    """
    Filter ip_data DataFrame based on provided criteria.
    
    Parameters:
    - df: Input DataFrame (ip_data)
    - date_filter: Tuple of (start_date, end_date) in 'YYYY-MM-DD' format for filtering dschg_dt
    - doc_name: Filter for doctor's name (string or list of strings)
    - ref_name: Filter for referring name (string or list of strings)
    - consultant_specialty: Filter for consultant specialty (string or list of strings)
    - group: Filter for group (string or list of strings)
    - referral_specialty: Filter for referral specialty (string or list of strings)
    - credit_company: Filter for credit company (string or list of strings)
    - tpa_corporate: Filter for TPA/CORPORATE (string or list of strings)
    - patient_expired: Filter for patient expired status (string or list of strings, e.g., 'Yes', 'No')
    - case_type: Filter for case type (string or list of strings, e.g., 'Elective', 'Emergency')
    
    Returns:
    - Filtered DataFrame
    """
    filtered_df = df.copy()  # Avoid modifying the original DataFrame

    # Date filter (assuming date_filter is a tuple of start_date, end_date in 'YYYY-MM-DD')
    if date_filter:
        if isinstance(date_filter, tuple) and len(date_filter) == 2:
            start_date, end_date = pd.to_datetime(date_filter[0]), pd.to_datetime(date_filter[1])
            filtered_df = filtered_df[
                (pd.to_datetime(filtered_df['dschg_dt'], errors='coerce') >= start_date) & 
                (pd.to_datetime(filtered_df['dschg_dt'], errors='coerce') <= end_date)
            ]

    # String-based filters (case-insensitive)
    if doc_name:
        if isinstance(doc_name, list):
            filtered_df = filtered_df[filtered_df['DocName'].str.lower().isin([x.lower() for x in doc_name])]
        else:
            filtered_df = filtered_df[filtered_df['DocName'].str.lower() == doc_name.lower()]

    if ref_name:
        if isinstance(ref_name, list):
            filtered_df = filtered_df[filtered_df['refname'].str.lower().isin([x.lower() for x in ref_name])]
        else:
            filtered_df = filtered_df[filtered_df['refname'].str.lower() == ref_name.lower()]

    if consultant_specialty:
        if isinstance(consultant_specialty, list):
            filtered_df = filtered_df[filtered_df['consultant_specialty'].str.lower().isin(
                [x.lower() for x in consultant_specialty])]
        else:
            filtered_df = filtered_df[filtered_df['consultant_specialty'].str.lower() == consultant_specialty.lower()]

    if group:
        if isinstance(group, list):
            filtered_df = filtered_df[filtered_df['Group'].str.lower().isin([x.lower() for x in group])]
        else:
            filtered_df = filtered_df[filtered_df['Group'].str.lower() == group.lower()]

    if referral_specialty:
        if isinstance(referral_specialty, list):
            filtered_df = filtered_df[filtered_df['referral_specialty'].str.lower().isin(
                [x.lower() for x in referral_specialty])]
        else:
            filtered_df = filtered_df[filtered_df['referral_specialty'].str.lower() == referral_specialty.lower()]

    if credit_company:
        if isinstance(credit_company, list):
            filtered_df = filtered_df[filtered_df['CREDIT COMPANY'].str.lower().isin(
                [x.lower() for x in credit_company])]
        else:
            filtered_df = filtered_df[filtered_df['CREDIT COMPANY'].str.lower() == credit_company.lower()]

    if tpa_corporate:
        if isinstance(tpa_corporate, list):
            filtered_df = filtered_df[filtered_df['TPA/CORPORATE'].str.lower().isin(
                [x.lower() for x in tpa_corporate])]
        else:
            filtered_df = filtered_df[filtered_df['TPA/CORPORATE'].str.lower() == tpa_corporate.lower()]

    if patient_expired:
        if isinstance(patient_expired, list):
            filtered_df = filtered_df[filtered_df['patient_expired'].str.lower().isin(
                [x.lower() for x in patient_expired])]
        else:
            filtered_df = filtered_df[filtered_df['patient_expired'].str.lower() == patient_expired.lower()]

    if case_type:
        if isinstance(case_type, list):
            filtered_df = filtered_df[filtered_df['cse_typ_dcd'].str.lower().isin([x.lower() for x in case_type])]
        else:
            filtered_df = filtered_df[filtered_df['cse_typ_dcd'].str.lower() == case_type.lower()]

    return filtered_df

def ip_filter_ui(df, tab_key):
    """Reusable filter UI for IP Details and Dashboard tabs with fully cascading filters dependent on each other."""
    st.markdown('<div class="filter-container">', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Default date range: 1st day of current month to today
        today = datetime.today().date()
        first_day = today.replace(day=1)
        default_value = (first_day, today)

        date_range = st.date_input(
            "Date Range",
            value=default_value,
            format="YYYY-MM-DD",
            key=f"date_range_{tab_key}",
            help="Select the date range for discharge dates (dschg_dt)"
        )

        # Initialize filtered DataFrames
        filtered_df = df.copy()
        filtered_df_admissions = df.copy()
        filtered_df_discharges = df.copy()

        # Calculate previous period date range
        date_filter = None
        if len(date_range) == 2:
            date_filter = (date_range[0].strftime('%Y-%m-%d'), date_range[1].strftime('%Y-%m-%d'))
            start_date, end_date = pd.to_datetime(date_filter[0]), pd.to_datetime(date_filter[1])
            date_span = (end_date - start_date).days + 1
            prev_end_date = end_date - relativedelta(months=1)
            prev_start_date = prev_end_date - relativedelta(days=date_span - 1)
            prev_start_date = max(prev_start_date, prev_end_date.replace(day=1))

            # Apply date filter for current period only
            filtered_df_current = filtered_df[
                (pd.to_datetime(filtered_df['dschg_dt'], errors='coerce') >= start_date) &
                (pd.to_datetime(filtered_df['dschg_dt'], errors='coerce') <= end_date)
            ]
            filtered_df_discharges_current = filtered_df_discharges[
                (pd.to_datetime(filtered_df_discharges['dschg_dt'], errors='coerce') >= start_date) &
                (pd.to_datetime(filtered_df_discharges['dschg_dt'], errors='coerce') <= end_date)
            ]
            filtered_df_admissions_current = filtered_df_admissions[
                (pd.to_datetime(filtered_df_admissions['adm_dt'], errors='coerce') >= start_date) &
                (pd.to_datetime(filtered_df_admissions['adm_dt'], errors='coerce') <= end_date)
            ]
        else:
            filtered_df_current = filtered_df.copy()
            filtered_df_admissions_current = filtered_df_admissions.copy()
            filtered_df_discharges_current = filtered_df_discharges.copy()

        # Handle empty data after date filter for current period
        if filtered_df_current.empty:
            st.warning("No data available for the selected date range.")
            return {
                "date_filter": date_filter,
                "consultant_specialty": [],
                "doc_name": [],
                "referral_specialty": [],
                "ref_name": [],
                "group": [],
                "credit_company": [],
                "tpa_corporate": [],
                "patient_expired": [],
                "case_type": [],
                "filtered_df": filtered_df_current,
                "filtered_df_admissions": filtered_df_admissions_current,
                "filtered_df_discharges": filtered_df_discharges_current,
                "filtered_df_full": filtered_df,
                "filtered_df_admissions_full": filtered_df_admissions,
                "filtered_df_discharges_full": filtered_df_discharges
            }

    with col2:
        # Consultant Specialty (using current period data for options)
        consultant_specialty_list = safe_unique_list(filtered_df_current, 'consultant_specialty') or ["No values available"]
        consultant_specialty_filter = st.multiselect(
            "Consultant Specialty",
            consultant_specialty_list,
            key=f"consultant_specialty_{tab_key}",
            help="Select specialties available in the date range"
        )
        if consultant_specialty_filter and consultant_specialty_filter != ["No values available"]:
            filtered_df = filtered_df[filtered_df['consultant_specialty'].isin(consultant_specialty_filter)]
            filtered_df_discharges = filtered_df_discharges[filtered_df_discharges['consultant_specialty'].isin(consultant_specialty_filter)]
            filtered_df_admissions = filtered_df_admissions[filtered_df_admissions['consultant_specialty'].isin(consultant_specialty_filter)]
            filtered_df_current = filtered_df_current[filtered_df_current['consultant_specialty'].isin(consultant_specialty_filter)]
            filtered_df_discharges_current = filtered_df_discharges_current[filtered_df_discharges_current['consultant_specialty'].isin(consultant_specialty_filter)]
            filtered_df_admissions_current = filtered_df_admissions_current[filtered_df_admissions_current['consultant_specialty'].isin(consultant_specialty_filter)]

        # Doctor Name
        doc_name_list = safe_unique_list(filtered_df_current, 'DocName') or ["No values available"]
        doc_name_filter = st.multiselect(
            "Doctor Name",
            doc_name_list,
            key=f"doc_name_{tab_key}",
            help="Select doctor names for the selected specialty and date range"
        )
        if doc_name_filter and doc_name_filter != ["No values available"]:
            filtered_df = filtered_df[filtered_df['DocName'].isin(doc_name_filter)]
            filtered_df_discharges = filtered_df_discharges[filtered_df_discharges['DocName'].isin(doc_name_filter)]
            filtered_df_admissions = filtered_df_admissions[filtered_df_admissions['DocName'].isin(doc_name_filter)]
            filtered_df_current = filtered_df_current[filtered_df_current['DocName'].isin(doc_name_filter)]
            filtered_df_discharges_current = filtered_df_discharges_current[filtered_df_discharges_current['DocName'].isin(doc_name_filter)]
            filtered_df_admissions_current = filtered_df_admissions_current[filtered_df_admissions_current['DocName'].isin(doc_name_filter)]

    with col3:
        # Referral Specialty
        referral_specialty_list = safe_unique_list(filtered_df_current, 'referral_specialty') or ["No values available"]
        referral_specialty_filter = st.multiselect(
            "Referral Specialty",
            referral_specialty_list,
            key=f"referral_specialty_{tab_key}",
            help="Select referral specialties for the selected filters and date range"
        )
        if referral_specialty_filter and referral_specialty_filter != ["No values available"]:
            filtered_df = filtered_df[filtered_df['referral_specialty'].isin(referral_specialty_filter)]
            filtered_df_discharges = filtered_df_discharges[filtered_df_discharges['referral_specialty'].isin(referral_specialty_filter)]
            filtered_df_admissions = filtered_df_admissions[filtered_df_admissions['referral_specialty'].isin(referral_specialty_filter)]
            filtered_df_current = filtered_df_current[filtered_df_current['referral_specialty'].isin(referral_specialty_filter)]
            filtered_df_discharges_current = filtered_df_discharges_current[filtered_df_discharges_current['referral_specialty'].isin(referral_specialty_filter)]
            filtered_df_admissions_current = filtered_df_admissions_current[filtered_df_admissions_current['referral_specialty'].isin(referral_specialty_filter)]

        # Referring Name
        ref_name_list = safe_unique_list(filtered_df_current, 'refname') or ["No values available"]
        ref_name_filter = st.multiselect(
            "Referring Name",
            ref_name_list,
            key=f"ref_name_{tab_key}",
            help="Select referring names for the selected filters and date range"
        )
        if ref_name_filter and ref_name_filter != ["No values available"]:
            filtered_df = filtered_df[filtered_df['refname'].isin(ref_name_filter)]
            filtered_df_discharges = filtered_df_discharges[filtered_df_discharges['refname'].isin(ref_name_filter)]
            filtered_df_admissions = filtered_df_admissions[filtered_df_admissions['refname'].isin(ref_name_filter)]
            filtered_df_current = filtered_df_current[filtered_df_current['refname'].isin(ref_name_filter)]
            filtered_df_discharges_current = filtered_df_discharges_current[filtered_df_discharges_current['refname'].isin(ref_name_filter)]
            filtered_df_admissions_current = filtered_df_admissions_current[filtered_df_admissions_current['refname'].isin(ref_name_filter)]

    with col4:
        # Group
        group_list = safe_unique_list(filtered_df_current, 'Group') or ["No values available"]
        group_filter = st.multiselect(
            "Group",
            group_list,
            key=f"group_{tab_key}",
            help="Select groups for the selected filters and date range"
        )
        if group_filter and group_filter != ["No values available"]:
            filtered_df = filtered_df[filtered_df['Group'].isin(group_filter)]
            filtered_df_discharges = filtered_df_discharges[filtered_df_discharges['Group'].isin(group_filter)]
            filtered_df_admissions = filtered_df_admissions[filtered_df_admissions['Group'].isin(group_filter)]
            filtered_df_current = filtered_df_current[filtered_df_current['Group'].isin(group_filter)]
            filtered_df_discharges_current = filtered_df_discharges_current[filtered_df_discharges_current['Group'].isin(group_filter)]
            filtered_df_admissions_current = filtered_df_admissions_current[filtered_df_admissions_current['Group'].isin(group_filter)]

        # Credit Company
        credit_company_list = safe_unique_list(filtered_df_current, 'CREDIT COMPANY') or ["No values available"]
        credit_company_filter = st.multiselect(
            "Credit Company",
            credit_company_list,
            key=f"credit_company_{tab_key}",
            help="Select credit companies for the selected filters and date range"
        )
        if credit_company_filter and credit_company_filter != ["No values available"]:
            filtered_df = filtered_df[filtered_df['CREDIT COMPANY'].isin(credit_company_filter)]
            filtered_df_discharges = filtered_df_discharges[filtered_df_discharges['CREDIT COMPANY'].isin(credit_company_filter)]
            filtered_df_admissions = filtered_df_admissions[filtered_df_admissions['CREDIT COMPANY'].isin(credit_company_filter)]
            filtered_df_current = filtered_df_current[filtered_df_current['CREDIT COMPANY'].isin(credit_company_filter)]
            filtered_df_discharges_current = filtered_df_discharges_current[filtered_df_discharges_current['CREDIT COMPANY'].isin(credit_company_filter)]
            filtered_df_admissions_current = filtered_df_admissions_current[filtered_df_admissions_current['CREDIT COMPANY'].isin(credit_company_filter)]

        # TPA/CORPORATE
        tpa_corporate_list = safe_unique_list(filtered_df_current, 'TPA/CORPORATE') or ["No values available"]
        tpa_corporate_filter = st.multiselect(
            "TPA/CORPORATE",
            tpa_corporate_list,
            key=f"tpa_corporate_{tab_key}",
            help="Select TPA/CORPORATE for the selected filters and date range"
        )
        if tpa_corporate_filter and tpa_corporate_filter != ["No values available"]:
            filtered_df = filtered_df[filtered_df['TPA/CORPORATE'].isin(tpa_corporate_filter)]
            filtered_df_discharges = filtered_df_discharges[filtered_df_discharges['TPA/CORPORATE'].isin(tpa_corporate_filter)]
            filtered_df_admissions = filtered_df_admissions[filtered_df_admissions['TPA/CORPORATE'].isin(tpa_corporate_filter)]
            filtered_df_current = filtered_df_current[filtered_df_current['TPA/CORPORATE'].isin(tpa_corporate_filter)]
            filtered_df_discharges_current = filtered_df_discharges_current[filtered_df_discharges_current['TPA/CORPORATE'].isin(tpa_corporate_filter)]
            filtered_df_admissions_current = filtered_df_admissions_current[filtered_df_admissions_current['TPA/CORPORATE'].isin(tpa_corporate_filter)]

        # Patient Expired
        patient_expired_list = safe_unique_list(filtered_df_current, 'patient_expired') or ["No values available"]
        patient_expired_filter = st.multiselect(
            "Patient Expired",
            patient_expired_list,
            key=f"patient_expired_{tab_key}",
            help="Select patient expired statuses for the selected filters and date range"
        )
        if patient_expired_filter and patient_expired_filter != ["No values available"]:
            filtered_df = filtered_df[filtered_df['patient_expired'].isin(patient_expired_filter)]
            filtered_df_discharges = filtered_df_discharges[filtered_df_discharges['patient_expired'].isin(patient_expired_filter)]
            filtered_df_admissions = filtered_df_admissions[filtered_df_admissions['patient_expired'].isin(patient_expired_filter)]
            filtered_df_current = filtered_df_current[filtered_df_current['patient_expired'].isin(patient_expired_filter)]
            filtered_df_discharges_current = filtered_df_discharges_current[filtered_df_discharges_current['patient_expired'].isin(patient_expired_filter)]
            filtered_df_admissions_current = filtered_df_admissions_current[filtered_df_admissions_current['patient_expired'].isin(patient_expired_filter)]

        # Case Type
        case_type_list = safe_unique_list(filtered_df_current, 'cse_typ_dcd') or ["No values available"]
        case_type_filter = st.multiselect(
            "Case Type",
            case_type_list,
            key=f"case_type_{tab_key}",
            help="Select case types (e.g., Elective, Emergency) for the selected filters and date range"
        )
        if case_type_filter and case_type_filter != ["No values available"]:
            filtered_df = filtered_df[filtered_df['cse_typ_dcd'].isin(case_type_filter)]
            filtered_df_discharges = filtered_df_discharges[filtered_df_discharges['cse_typ_dcd'].isin(case_type_filter)]
            filtered_df_admissions = filtered_df_admissions[filtered_df_admissions['cse_typ_dcd'].isin(case_type_filter)]
            filtered_df_current = filtered_df_current[filtered_df_current['cse_typ_dcd'].isin(case_type_filter)]
            filtered_df_discharges_current = filtered_df_discharges_current[filtered_df_discharges_current['cse_typ_dcd'].isin(case_type_filter)]
            filtered_df_admissions_current = filtered_df_admissions_current[filtered_df_admissions_current['cse_typ_dcd'].isin(case_type_filter)]

    st.markdown('</div>', unsafe_allow_html=True)

    return {
        "date_filter": date_filter,
        "consultant_specialty": consultant_specialty_filter,
        "doc_name": doc_name_filter,
        "referral_specialty": referral_specialty_filter,
        "ref_name": ref_name_filter,
        "group": group_filter,
        "credit_company": credit_company_filter,
        "tpa_corporate": tpa_corporate_filter,
        "patient_expired": patient_expired_filter,
        "case_type": case_type_filter,
        "filtered_df": filtered_df_current,
        "filtered_df_admissions": filtered_df_admissions_current,
        "filtered_df_discharges": filtered_df_discharges_current,
        "filtered_df_full": filtered_df,
        "filtered_df_admissions_full": filtered_df_admissions,
        "filtered_df_discharges_full": filtered_df_discharges
    }