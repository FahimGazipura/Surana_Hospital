import pandas as pd
import numpy as np
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pathlib import Path
from scripts.csv_reader import CSVReader
from scripts.gsheet_reader import read_sheet_to_df
import time


# ----------------------------
# Setup requests session with retries
# ----------------------------
session = requests.Session()
# response = session.get("https://www.google.com", verify=False)
# print(response.status_code)

retries = Retry(total=5, backoff_factor=1, status_forcelist=[502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries))

# dtype placeholder if needed
dtype = np.void

# ----------------------------
# Define project root and data path
# ----------------------------
# Correct PROJECT_ROOT
PROJECT_ROOT = Path(__file__).resolve().parents[1]  # one level up from scripts/
DATA_PATH = PROJECT_ROOT / "data"

# ----------------------------
# Helper functions
# ----------------------------
def load_tpa_sheet(url, sheet_name, retries=5, delay=3):
    """
    Load Google Sheet safely with SSL retry logic.
    Returns empty DataFrame if all retries fail.
    """
    for attempt in range(1, retries + 1):
        try:
            print(f"Attempt {attempt} to load TPA sheet...")
            df = read_sheet_to_df(url, sheet_name)
            print("TPA data loaded successfully!")
            return df
        except requests.exceptions.SSLError as e:
            print(f"SSL Error on attempt {attempt}: {e}")
            time.sleep(delay)
        except Exception as e:
            print(f"Error on attempt {attempt}: {e}")
            time.sleep(delay)
    print("Failed to load TPA data after multiple attempts.")
    return pd.DataFrame()

def load_folder_csv(folder_relative_path, skiprows=None):
    folder_path = DATA_PATH / folder_relative_path
    csvreader = CSVReader(folder_path)
    csvreader.read_csv_files(skiprows=skiprows)
    return csvreader.get_combined_dataframe()

# scripts/data_loader.py
import pandas as pd
import numpy as np
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pathlib import Path
from scripts.csv_reader import CSVReader
from scripts.gsheet_reader import read_sheet_to_df
import time

# ... (other imports and setup remain unchanged)

def load_all_data(load_only=None):
    """
    load_only: list of dataframe keys to load, e.g. ['ip_detail_df', 'tpa_data_df']
               If None, loads everything.
    """
    dfs = {}
    DATA_PATH = Path(__file__).resolve().parents[1] / "data"

    # Load CSV folders
    if load_only is None or 'ip_detail_df' in load_only:
        dfs['ip_detail_df'] = load_folder_csv('IP Details', skiprows=3)
        print("Dataframe created: ip_detail_df")

    if load_only is None or 'ip_discharge_df' in load_only:
        dfs['ip_discharge_df'] = load_folder_csv('IP Discharge')
        print("Dataframe created: ip_discharge_df")

    if load_only is None or 'op_detail_df' in load_only:
        dfs['op_detail_df'] = load_folder_csv('OP details', skiprows=3)
        print("Dataframe created: op_detail_df")

    if load_only is None or 'op_discharge_df' in load_only:
        dfs['op_discharge_df'] = load_folder_csv('OP Discharge')
        print("Dataframe created: op_discharge_df")

    if load_only is None or 'patient_detail_df' in load_only:
        dfs['patient_detail_df'] = load_folder_csv('Patient Details')
        print("Dataframe created: patient_detail_df")

    if load_only is None or 'op_deposit_df' in load_only:
        dfs['op_deposit_df'] = load_folder_csv('OP Deposit')
        print("Dataframe created: op_deposit_df")

    if load_only is None or 'expired_pt' in load_only:
        dfs['expired_pt'] = load_folder_csv('Expire Patient')
        print("Dataframe created: expired_pt")

    if load_only is None or 'admission_list' in load_only:
        dfs['admission_list'] = load_folder_csv('Admission list')
        print("Dataframe created: admission_list")

    # Load individual CSV files
    if load_only is None or 'doctor_master_df' in load_only:
        dfs['doctor_master_df'] = pd.read_csv(DATA_PATH / 'Reference' / 'Doctor_Master.csv')
        print("Dataframe created: doctor_master_df")

    if load_only is None or 'code_master_df' in load_only:
        file_path = DATA_PATH / 'Reference' / 'Ipd_Charge_Code_Commercial.csv'
        try:
            dfs['code_master_df'] = pd.read_csv(file_path, encoding='Windows-1252')
            print("Dataframe created: code_master_df")
        except UnicodeDecodeError as e:
            raise Exception(f"Error decoding 'Ipd_Charge_Code_Commercial.csv': {e}")

    if load_only is None or 'opd_code_master_df' in load_only:
        dfs['opd_code_master_df'] = pd.read_csv(DATA_PATH / 'Reference' / 'opd_group.csv')
        print("Dataframe created: opd_code_master_df")

    if load_only is None or 'marketing_agent_df' in load_only:
        dfs['marketing_agent_df'] = pd.read_csv(DATA_PATH / 'Reference' / 'Marketing Agents.csv', usecols=[0])
        print("Dataframe created: marketing_agent_df")

    if load_only is None or 'tpa_mapping_df' in load_only:
        dfs['tpa_mapping_df'] = pd.read_csv(DATA_PATH / 'Reference' / 'tpa.csv')
        print("Dataframe created: tpa_mapping_df")

    if load_only is None or 'op_charge_code' in load_only:
        dfs['op_charge_code'] = pd.read_csv(DATA_PATH / 'Reference' / 'op_charge_codes.csv')
        print("Dataframe created: op_charge_code")

    # Load Google Sheets
    if load_only is None or 'tpa_data_df' in load_only:
        dfs['tpa_data_df'] = read_sheet_to_df(
            "https://docs.google.com/spreadsheets/d/1CvRmeduK6j4EZ4S4BpqawO61EcbPFh0Hhzy_-YgXvYM/edit?gid=1179037448#gid=1179037448",
            "MPCTUpdate"
        )
        print("Dataframe created: tpa_data_df")

    if load_only is None or 'mjpjay_df' in load_only:
        dfs['mjpjay_df'] = read_sheet_to_df(
            "https://docs.google.com/spreadsheets/d/1toFjVR7LdMRJtATpbUxXqZdEd0ZtS7DjnuKGxKZ8OyY/edit?gid=0",
            "Data"
        )
        print("Dataframe created: mjpjay_df")

    return dfs