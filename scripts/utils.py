# support.py
import pandas as pd
import numpy as np
import re


def clean_numeric_column(df, column_name):
    """
    Cleans a numeric column by:
    - Converting to string
    - Removing parentheses, commas, and extra spaces
    - Converting to float
    
    Parameters:
        df (pd.DataFrame): The DataFrame containing the column
        column_name (str): The name of the column to clean
        
    Returns:
        pd.Series: Cleaned numeric column as float
    """
    cleaned_col = df[column_name].astype(str)  # Ensure it's string
    cleaned_col = cleaned_col.str.replace(r'[(),]', '', regex=True).str.strip()  # Remove unwanted chars
    cleaned_col = pd.to_numeric(cleaned_col, errors='coerce')  # Convert to float
    return cleaned_col

def clean_name(name):
    """Clean and standardize name strings."""
    if pd.isna(name):
        return ""
    name = str(name)
    name = re.sub(r"\b(Dr|Mr|Mrs)\.?\b", "", name, flags=re.IGNORECASE)
    name = re.sub(r"[().]", "", name)
    name = re.sub(r"\s+", "", name)  # Remove all whitespace
    name = name.strip()
    return name.upper()

