import os
import pandas as pd
import ssl
import certifi
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Ensure Python uses certifi certificates (fix SSL issues on Windows)
os.environ["SSL_CERT_FILE"] = certifi.where()

# Google Sheets API scope
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# Project root (one level above scripts)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Default path for service account credentials
DEFAULT_CREDENTIALS_PATH = os.path.join(PROJECT_ROOT, "secret key faim gajipura.json")


def get_google_sheets_service(credentials_path=DEFAULT_CREDENTIALS_PATH):
    """
    Authenticate with Google Sheets API using a Service Account.
    """
    creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)


def read_sheet_to_df(spreadsheet_url, sheet_name, credentials_path=DEFAULT_CREDENTIALS_PATH):
    """
    Reads a Google Sheet (private) into a DataFrame using Service Account.
    """
    service = get_google_sheets_service(credentials_path)

    # Extract spreadsheet ID from URL
    spreadsheet_id = spreadsheet_url.split("/d/")[1].split("/")[0]

    # Call Sheets API
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=sheet_name).execute()
    values = result.get("values", [])

    if not values:
        print("⚠️ No data found in the sheet.")
        return pd.DataFrame()

    # Convert to DataFrame (first row as headers)
    return pd.DataFrame(values[1:], columns=values[0])
