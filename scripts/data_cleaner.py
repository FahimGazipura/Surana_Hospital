from scripts.data_loader import load_all_data
from scripts.utils import clean_numeric_column, clean_name
import pandas as pd

def compute_revenue(row):
    """Compute revenue safely converting values to numeric first."""
    stlmt_amt = pd.to_numeric(row.get('stlmt_amt', 0), errors='coerce') or 0
    settlement_gross = pd.to_numeric(row.get('Settlement Gross', 0), errors='coerce') or 0
    depbalamt = pd.to_numeric(row.get('DepBalAmt', 0), errors='coerce') or 0
    approved_amt = pd.to_numeric(row.get('Approved Amt', 0), errors='coerce') or 0
    bill_amt = pd.to_numeric(row.get('BillAmt', 0), errors='coerce') or 0

    if stlmt_amt > 0:
        return stlmt_amt
    elif settlement_gross > 0:
        return settlement_gross + depbalamt
    elif approved_amt > 0:
        return approved_amt + depbalamt
    else:
        return bill_amt
    
def clean_ip_detail(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans the ip_detail_df.
    """
    columns_to_keep = [
        'ip_no', 'vch_dt', 'rev_dt', 'srv_desc', 'chrg_cd3',
        'chrg_desc2', 'ShrDoc1', 'ptn_cls_desc', 'no_units', 'amt'
    ]
    df = df[columns_to_keep].copy()

    # Clean numeric columns
    for col in ['amt', 'no_units']:
        df[col] = clean_numeric_column(df, col)

    # Integer columns
    for col in ['chrg_cd3']:
        df[col] = pd.to_numeric(df[col], errors='coerce', downcast='integer')

    # String columns
    str_columns = ['ip_no', 'srv_desc', 'chrg_desc2', 'ShrDoc1', 'ptn_cls_desc']
    df[str_columns] = df[str_columns].astype('string')

    # Date columns
    for col in ['vch_dt', 'rev_dt']:
        df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')

    # Rename columns
    df.rename(columns={
        'chrg_cd3': 'charge_code',
        'chrg_desc2': 'charge_desc',
        'ShrDoc1': 'service_doctor',
        'srv_desc': 'service_description'
    }, inplace=True)

    df['Service_Doctor_Mapping'] = df["service_doctor"].apply(clean_name)
    df['srv_desc_mapping'] = df['service_description'].apply(clean_name)

    print("✅ ip_detail_df cleaned successfully")
    return df

def clean_admission_list(df: pd.DataFrame) -> pd.DataFrame:
    import re
    
    df = df[['ip_no', 'Textbox73']].copy()

    # Clean ip_no
    df['ip_no'] = df['ip_no'].astype(str).str.strip()
    df = df[df['ip_no'] != '']
    df.drop_duplicates(subset='ip_no', inplace=True)

    # Rename column
    df = df.rename(columns={'Textbox73': 'adm_dt'})

    # Convert everything to string
    df['adm_dt'] = df['adm_dt'].astype(str)

    # Remove prefix 'Admission Date : ' and any non-date text using regex
    df['adm_dt'] = df['adm_dt'].str.replace(r'.*?(\d{1,2}/\d{1,2}/\d{2,4}).*', r'\1', regex=True).str.strip()

    # Try parsing date
    df['adm_dt'] = pd.to_datetime(df['adm_dt'], errors='coerce', dayfirst=True)

    # Drop invalid dates
    df = df.dropna(subset=['adm_dt'])

    # Add year & month info
    df['admission_year'] = df['adm_dt'].dt.year
    df['admission_month_name'] = df['adm_dt'].dt.month_name()
    df['admission_month_no'] = df['adm_dt'].dt.month

    print(f"✅ admission_list_df cleaned successfully: {df.shape[0]} rows")
    return df

def clean_ip_discharge(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans and processes the IP Discharge DataFrame.
    """
    columns_to_keep = [
        "Textbox142", "ip_no", "Ptn_No", "WrdDesc", "cse_typ_dcd", "dcd",
        "rm_name", "bed_no", "Ptn_Cls_Dcd", "DocName", "refname",
         "dschg_dt", "BillAmt", "ConcAmt", "stlmt_amt",
        "DepBalAmt", "trnvalue"
    ]
    # Add patient_expired if it exists
    if 'patient_expired' in df.columns:
        columns_to_keep.append('patient_expired')
    # Add columns expected by filter_ip_data if they exist
    for col in ['consultant_specialty', 'Group', 'referral_specialty', 'TPA/CORPORATE']:
        if col in df.columns:
            columns_to_keep.append(col)

    df = df[columns_to_keep].copy()

    # Numeric columns
    for col in ["BillAmt", "ConcAmt", "stlmt_amt", "DepBalAmt", "trnvalue"]:
        df[col] = clean_numeric_column(df, col)

    # # Compute line_revenue
    # df['line_revenue'] = df.apply(compute_revenue, axis=1)

    # Integer ID columns
    for col in ["bed_no"]:
        df[col] = pd.to_numeric(df[col], errors="coerce", downcast="integer")

    # String columns
    str_columns = ["ip_no", "Ptn_No", "Textbox142", "WrdDesc", "cse_typ_dcd", "dcd",
                   "rm_name", "Ptn_Cls_Dcd", "DocName", "refname"]
    if 'patient_expired' in df.columns:
        str_columns.append('patient_expired')
    for col in ['consultant_specialty', 'Group', 'referral_specialty', 'TPA/CORPORATE']:
        if col in df.columns:
            str_columns.append(col)
    df[str_columns] = df[str_columns].astype("string")

    # Date columns
    for col in ["dschg_dt"]:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].str.replace("-", "/", regex=False)
        df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce")

    # Rename columns
    df.rename(columns={
        "Textbox142": "CREDIT COMPANY",
        "Ptn_No": "ptn_no"
    }, inplace=True)

    # Add year & month info
    df['dis_year'] = df['dschg_dt'].dt.year
    df['dis_month_name'] = df['dschg_dt'].dt.month_name()
    df['dis_month_no'] = df['dschg_dt'].dt.month

    # Keep latest discharge per patient
    df = df.sort_values("dschg_dt").drop_duplicates(subset="ip_no", keep="last")

    # Clean CREDIT COMPANY
    df['CREDIT COMPANY'] = (
        df['CREDIT COMPANY']
        .astype(str)
        .str.split(":", expand=True)[1]
        .fillna("NOT FOUND")
        .str.strip()
        .str.upper()
    )

    # Clean names
    df['Doctor Mapping'] = df['DocName'].apply(clean_name)
    df['Doctor_Mapping_referral'] = df['refname'].apply(clean_name)

    # Add patient_status
    first_ipd = df.groupby('ptn_no')['dschg_dt'].min().reset_index()
    first_ipd.columns = ['ptn_no', 'first_ipd_date']
    df = df.merge(first_ipd, on='ptn_no', how='left')
    df['patient_status'] = df.apply(
        lambda row: 'New' if row['dschg_dt'] == row['first_ipd_date'] else 'Existing', axis=1
    )

    print("✅ ip_discharge_df cleaned successfully")
    return df

def clean_opd_detail(df: pd.DataFrame) -> pd.DataFrame:
    columns_to_keep = ['vch_no', 'vch_dt', 'DoctorFullName', 'srv_desc', 'ShrDoc', 'UNITS1', 'NetAmt']
    df = df[columns_to_keep].copy()

    df["vch_no"] = df["vch_no"].astype(str)
    df["vch_dt"] = pd.to_datetime(df["vch_dt"], errors="coerce", dayfirst=True)
    df["DoctorFullName"] = df["DoctorFullName"].astype(str)
    df["srv_desc"] = df["srv_desc"].astype(str)
    df["ShrDoc"] = df["ShrDoc"].astype(str)
    df["UNITS1"] = pd.to_numeric(df["UNITS1"], errors="coerce")
    df["NetAmt"] = pd.to_numeric(df["NetAmt"], errors="coerce")
    df['Doctor Mapping'] = df["DoctorFullName"].apply(clean_name)

    print("✅ opd_detail_df cleaned successfully")
    return df

def clean_op_discharge_df(df: pd.DataFrame) -> pd.DataFrame:
    columns_to_keep = ['vch_no', 'ptn_no', 'rev_dt1', 'Textbox88']
    df = df[columns_to_keep].copy()

    df["vch_no"] = df["vch_no"].astype(str)
    df["ptn_no"] = df["ptn_no"].astype(str)
    df["rev_dt1"] = pd.to_datetime(df["rev_dt1"], errors="coerce", dayfirst=True)
    df["Textbox88"] = df["Textbox88"].astype(str)
    df.rename(columns={"Textbox88": "credit_company"}, inplace=True)
    df['credit_company'] = (
        df['credit_company']
        .astype(str)
        .str.replace(r"^Credit Company:-\s*\d+\s*", "", regex=True)
        .str.strip()
        .str.upper()
    )
    df = df.sort_values("rev_dt1").drop_duplicates(subset="vch_no", keep="last")

    print("✅ op_discharge_df cleaned successfully")
    return df


def clean_patient_details(df: pd.DataFrame) -> pd.DataFrame:
    columns_to_keep = [
        "crt_dt", "ptn_no", "PtnName", "Age", "sex", "Religion",
        "prmnt_addrs1", "prmnt_addrs2", "mobile"
    ]
    df = df[columns_to_keep].copy()

    # Convert dates
    df["crt_dt"] = pd.to_datetime(df["crt_dt"], dayfirst=True, errors="coerce")

    # Clean Age column
    df["Age"] = df["Age"].astype(str).str.replace(r"\D", "", regex=True)
    df["Age"] = pd.to_numeric(df["Age"], errors="coerce", downcast="integer")

    # Clean string columns
    str_columns = ["PtnName", "ptn_no", "Religion", "prmnt_addrs1", "prmnt_addrs2", "sex"]
    for col in str_columns:
        df[col] = df[col].astype("string").str.strip()

    # Clean mobile column
    df["mobile"] = df["mobile"].astype(str).str.strip()

    # Keep latest record per patient
    df = df.sort_values(by="crt_dt", ascending=False).drop_duplicates(subset="ptn_no", keep="first")

    print("✅ patient_details_df cleaned successfully")
    return df


def clean_doctor_master(df: pd.DataFrame) -> pd.DataFrame:
    df["Doctor Mapping"] = df["DOCTOR NAME"].apply(clean_name)
    df = df.drop_duplicates(subset="Doctor Mapping").copy()
    df["Doctor Mapping"] = df["Doctor Mapping"].astype("string")

    print("✅ doctor_master_df cleaned successfully")
    return df

def clean_code_master(df: pd.DataFrame) -> pd.DataFrame:
    df["srv_desc_mapping"] = df["srv_desc"].apply(clean_name)
    df = df.drop_duplicates(subset="srv_desc_mapping").copy()
    for col in ['Charge_desc', 'srv_desc', 'Group', 'Type of Surgery', 'srv_desc_mapping']:
        if col in df.columns:
            df[col] = df[col].fillna('NOT APPLICABLE').apply(clean_name)

    print("✅ code_master_df cleaned successfully")
    return df

def clean_marketing_agent_df(df: pd.DataFrame) -> pd.DataFrame:
    df["mkt_agent_mapping"] = df["Marketing Agents"].apply(clean_name)
    df = df.drop_duplicates(subset="mkt_agent_mapping").copy()

    print("✅ marketing_agent_df cleaned successfully")
    return df

def clean_tpa_mapping_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['company_mapping'] = df['Company'].apply(clean_name)
    df.drop_duplicates(subset='company_mapping', keep='first', inplace=True)

    print("✅ tpa_mapping_df cleaned successfully")
    return df

def clean_op_deposit(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.str.strip()
    useful_cols = ['rev_dt', 'Textbox53', 'dep_typ_dcd1', 'Dep_Amt', 'Textbox29']
    df = df[useful_cols]
    df = df.rename(columns={
        'Textbox53': 'ptn_no',
        'Textbox29': 'package',
        'dep_typ_dcd1': 'deposit_type'
    })
    df['rev_dt'] = pd.to_datetime(df['rev_dt'], dayfirst=True, errors='coerce')
    df['Dep_Amt'] = df['Dep_Amt'].astype(str).str.replace(',', '').astype(float)
    df['package'] = df['package'].astype(str).str.replace(',', '').astype(float)
    df['ptn_no'] = df['ptn_no'].astype(str).str.replace(',', '')
    df['deposit_type'] = df['deposit_type'].astype(str).str.strip()
    df = df.drop_duplicates(subset='ptn_no', keep='first')

    print("✅ op_deposit_df cleaned successfully")
    return df