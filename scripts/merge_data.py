# scripts/merge_data.py
import pandas as pd
import numpy as np
import os
from scripts.data_loader import load_all_data
from scripts.data_cleaner import (
    clean_ip_detail, clean_admission_list, clean_ip_discharge,
    clean_opd_detail, clean_op_discharge_df, clean_patient_details,
    clean_doctor_master, clean_code_master, clean_marketing_agent_df,
    clean_tpa_mapping_df, clean_op_deposit, compute_revenue
)
from scripts.utils import clean_numeric_column, clean_name


def merge_data():
    """
    Load, clean, and merge data to create ip_merge_df and op_merge_df.
    Filters ip_merge_df to include only records with line_revenue > 0.
    Returns:
    - ip_merge_df: Merged IP data with line_revenue > 0
    - op_merge_df: Merged OP data
    """
    try:
        # Load all data
        data = load_all_data()

        # Extract DataFrames safely
        ip_detail_df = data.get('ip_detail_df', pd.DataFrame())
        admission_list_df = data.get('admission_list', pd.DataFrame())
        ip_discharge_df = data.get('ip_discharge_df', pd.DataFrame())
        opd_detail_df = data.get('op_detail_df', pd.DataFrame())
        op_discharge_df = data.get('op_discharge_df', pd.DataFrame())
        patient_details_df = data.get('patient_detail_df', pd.DataFrame())
        doctor_master_df = data.get('doctor_master_df', pd.DataFrame())
        code_master_df = data.get('code_master_df', pd.DataFrame())
        marketing_agent_df = data.get('marketing_agent_df', pd.DataFrame())
        tpa_mapping_df = data.get('tpa_mapping_df', pd.DataFrame())
        op_deposit_df = data.get('op_deposit_df', pd.DataFrame())
        tpa_data_df = data.get('tpa_data_df', pd.DataFrame())

        if code_master_df.empty:
            raise ValueError("code_master_df is empty, check 'ipd_charge_code_commercial.csv' loading")

        # Clean DataFrames
        ip_detail_df = clean_ip_detail(ip_detail_df)
        admission_list_df = clean_admission_list(admission_list_df)
        ip_discharge_df = clean_ip_discharge(ip_discharge_df)
        opd_detail_df = clean_opd_detail(opd_detail_df)
        op_discharge_df = clean_op_discharge_df(op_discharge_df)
        patient_details_df = clean_patient_details(patient_details_df)
        doctor_master_df = clean_doctor_master(doctor_master_df)
        code_master_df = clean_code_master(code_master_df)
        marketing_agent_df = clean_marketing_agent_df(marketing_agent_df)
        tpa_mapping_df = clean_tpa_mapping_df(tpa_mapping_df)
        op_deposit_df = clean_op_deposit(op_deposit_df)

        # Merge IP Data
        admission_df = admission_list_df.copy()
        print(f"admission_df: {admission_df.shape[0]} rows, unique ip_no: {admission_df['ip_no'].nunique()}")
        discharge_df = ip_discharge_df.copy()
        print(f"discharge_df: {discharge_df.shape[0]} rows, unique ip_no: {discharge_df['ip_no'].nunique()}")
        ip_merge_df = admission_df.merge(discharge_df, on='ip_no', how='left', validate='one_to_one')
        print(f"After merging admission and discharge: {ip_merge_df.shape[0]} rows, unique ip_no: {ip_merge_df['ip_no'].nunique()}")

        # Add patient details
        ip_merge_df = ip_merge_df.merge(
            patient_details_df[['ptn_no', 'PtnName', 'Age', 'sex', 'Religion', 'prmnt_addrs1', 'prmnt_addrs2', 'mobile']],
            on='ptn_no', how='left', validate='many_to_one'
        )
        print(f"After merging patient details: {ip_merge_df.shape[0]} rows, unique ip_no: {ip_merge_df['ip_no'].nunique()}")

        # Add ip_detail
        ip_detail_agg = ip_detail_df.groupby('ip_no').agg({
            'amt': 'sum',
            'no_units': 'sum',
            'service_doctor': 'first',
            'service_description': 'first',
            'Service_Doctor_Mapping': 'first',
            'srv_desc_mapping': 'first'
        }).reset_index()
        print(f"ip_detail_agg: {ip_detail_agg.shape[0]} rows, unique ip_no: {ip_detail_agg['ip_no'].nunique()}")
        ip_merge_df = ip_merge_df.merge(ip_detail_agg, on='ip_no', how='left', validate='one_to_one')
        print(f"After merging ip_detail aggregation: {ip_merge_df.shape[0]} rows, unique ip_no: {ip_merge_df['ip_no'].nunique()}")

        # Add Group from code_master_df
        ip_merge_df = ip_merge_df.merge(
            code_master_df[['srv_desc_mapping', 'Group']],
            on='srv_desc_mapping', how='left', validate='many_to_one'
        )
        print(f"After merging Group info: {ip_merge_df.shape[0]} rows, unique ip_no: {ip_merge_df['ip_no'].nunique()}")

        # Merge consultant specialty
        if 'Doctor Mapping' not in doctor_master_df.columns or 'SPECIALITY' not in doctor_master_df.columns:
            raise KeyError("Column 'Doctor Mapping' or 'SPECIALITY' not found in doctor_master_df")
        ip_merge_df = ip_merge_df.merge(
            doctor_master_df[['Doctor Mapping', 'SPECIALITY']],
            on='Doctor Mapping',
            how='left', validate='many_to_one'
        ).rename(columns={'SPECIALITY': 'consultant_specialty'})
        print(f"After merging consultant specialty: {ip_merge_df.shape[0]} rows, unique ip_no: {ip_merge_df['ip_no'].nunique()}")

        # Merge referral specialty
        if 'Doctor_Mapping_referral' not in ip_merge_df.columns:
            raise KeyError("Column 'Doctor_Mapping_referral' not found in ip_merge_df")
        ip_merge_df = ip_merge_df.merge(
            doctor_master_df[['Doctor Mapping', 'SPECIALITY']],
            left_on='Doctor_Mapping_referral',
            right_on='Doctor Mapping',
            how='left', validate='many_to_one'
        ).rename(columns={'SPECIALITY': 'referral_specialty'})
        print(f"After merging referral specialty: {ip_merge_df.shape[0]} rows, unique ip_no: {ip_merge_df['ip_no'].nunique()}")

        # Merge TPA data
        tpa_cols = ['voucher_number', 'Claim_No', 'Approved Amt', 'Settlement Gross', 'CREDIT COMPANY']
        tpa_merge_df = tpa_data_df[tpa_cols].copy()
        tpa_merge_df = tpa_merge_df.rename(columns={'CREDIT COMPANY': 'CREDIT_COMPANY_TPA'})
        ip_merge_df = ip_merge_df.merge(
            tpa_merge_df,
            left_on='ip_no',
            right_on='voucher_number',
            how='left', validate='many_to_one'
        )
        print(f"After merging TPA data: {ip_merge_df.shape[0]} rows, unique ip_no: {ip_merge_df['ip_no'].nunique()}")

        # Handle CREDIT COMPANY
        if 'CREDIT COMPANY' in ip_merge_df.columns:
            ip_merge_df['CREDIT COMPANY'] = ip_merge_df['CREDIT COMPANY'].fillna(ip_merge_df['CREDIT_COMPANY_TPA'])
        else:
            ip_merge_df['CREDIT COMPANY'] = ip_merge_df['CREDIT_COMPANY_TPA']
        ip_merge_df = ip_merge_df.drop(columns=['CREDIT_COMPANY_TPA', 'voucher_number'], errors='ignore')

        # TPA Mapping Merge with Ip Merge
        ip_merge_df['company_mapping'] = ip_merge_df['CREDIT COMPANY'].apply(clean_name)
        ip_merge_df = ip_merge_df.merge(tpa_mapping_df, on='company_mapping', how='left')
        print(f"After merging TPA mapping: {ip_merge_df.shape[0]} rows, unique ip_no: {ip_merge_df['ip_no'].nunique()}")


        # Revenue calculations
        if 'amt' not in ip_merge_df.columns:
            raise KeyError("Column 'amt' not found in ip_merge_df for revenue calculation")
        ip_merge_df['revenue'] = ip_merge_df.apply(compute_revenue, axis=1)
        ip_merge_df['amt'] = ip_merge_df['amt'].fillna(0)
        ip_merge_df['revenue'] = ip_merge_df['revenue'].fillna(0)
        total_amt_per_ip = ip_merge_df.groupby('ip_no')['amt'].transform('sum').replace(0, np.nan)
        ip_merge_df['line_revenue'] = (ip_merge_df['amt'] / total_amt_per_ip) * ip_merge_df['revenue']
        ip_merge_df['line_revenue'] = ip_merge_df['line_revenue'].replace([np.inf, -np.inf], np.nan).fillna(0).astype(int)
        print(f"After revenue calculations: {ip_merge_df.shape[0]} rows, unique ip_no: {ip_merge_df['ip_no'].nunique()}")

        # Filter for line_revenue > 0
#        ip_merge_df = ip_merge_df[ip_merge_df['line_revenue'] > 0]
#        print(f"After filtering line_revenue > 0: {ip_merge_df.shape[0]} rows, unique ip_no: {ip_merge_df['ip_no'].nunique()}")

        # Check for duplicates and remove if necessary
        if ip_merge_df['ip_no'].duplicated().any():
            print(f"Warning: Found {ip_merge_df['ip_no'].duplicated().sum()} duplicate ip_no values")
            duplicate_ip_nos = ip_merge_df[ip_merge_df['ip_no'].duplicated()]['ip_no'].unique()
            print(f"Sample duplicate ip_no: {list(duplicate_ip_nos)[:10]}")
            ip_merge_df = ip_merge_df.drop_duplicates(subset='ip_no', keep='first')
            print(f"After removing duplicates: {ip_merge_df.shape[0]} rows, unique ip_no: {ip_merge_df['ip_no'].nunique()}")

        # Merge expired patients
        expired_df = data.get('expired_pt', pd.DataFrame())
        if not expired_df.empty:
            expired_data = expired_df[['ip_no']].copy()
            expired_data['patient_expired'] = 'yes'
            expired_data['ip_no'] = expired_data['ip_no'].astype(str).str.strip()
            expired_data['ip_no'] = expired_data['ip_no'].replace(r'[^\x00-\x7F]+', '', regex=True)
            expired_data.dropna(subset=['ip_no'], inplace=True)
            expired_data.drop_duplicates(subset='ip_no', inplace=True)
            print(f"Unique ip_no in expired_data: {expired_data['ip_no'].nunique()}")
            ip_merge_df['ip_no'] = ip_merge_df['ip_no'].astype(str).str.strip()
            ip_merge_df['ip_no'] = ip_merge_df['ip_no'].replace(r'[^\x00-\x7F]+', '', regex=True)
            print(f"Unique ip_no in ip_merge_df before merge: {ip_merge_df['ip_no'].nunique()}")
            ip_merge_df = ip_merge_df.merge(expired_data, on='ip_no', how='left', validate='many_to_one')
            ip_merge_df['patient_expired'] = ip_merge_df['patient_expired'].fillna('no')
            print(f"After merging expired patients: {ip_merge_df.shape[0]} rows, unique ip_no: {ip_merge_df['ip_no'].nunique()}")
        else:
            ip_merge_df['patient_expired'] = 'no'
            print("No expired patients data available, setting patient_expired to 'no'")
        
        ip_merge_df['TPA/CORPORATE'] = ip_merge_df['Type of Company']

        # Ensure required columns
        required_columns = [
            'ip_no', 'ptn_no', 'dis_year', 'dis_month_name', 'line_revenue',
            'DocName', 'refname', 'patient_expired', 'consultant_specialty',
            'Group', 'referral_specialty', 'CREDIT COMPANY', 'TPA/CORPORATE'
        ]
        for col in required_columns:
            if col not in ip_merge_df.columns:
                ip_merge_df[col] = 'UNKNOWN' if col in [
                    'consultant_specialty', 'Group', 'referral_specialty', 'TPA/CORPORATE'
                ] else 0
        print(f"Final ip_merge_df: {ip_merge_df.shape[0]} rows, unique ip_no: {ip_merge_df['ip_no'].nunique()}")

        # Merge OP Data
        op_merge_df = op_discharge_df.copy()
        op_merge_df = op_merge_df.merge(
            opd_detail_df[['vch_no', 'DoctorFullName', 'NetAmt', 'Doctor Mapping']],
            on='vch_no', how='left'
        )
        op_merge_df = op_merge_df.merge(
            patient_details_df[['ptn_no', 'PtnName', 'Age', 'sex']],
            on='ptn_no', how='left'
        )

        print("✅ Data merged successfully")
        return ip_merge_df, op_merge_df

    except Exception as e:
        raise Exception(f"Error in merge_data: {e}")