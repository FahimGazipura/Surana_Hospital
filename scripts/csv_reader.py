import os
import glob
import pandas as pd
from tqdm import tqdm

class CSVReader:
    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.dataframes = []
        self.loaded_files = []

    def list_csv_files(self):
        return glob.glob(os.path.join(self.folder_path, "*.csv"))

    def read_csv_files(self, skiprows=None, index_col=None):
        csv_files = self.list_csv_files()
        self.dataframes = []
        self.loaded_files = []

        print(f"📂 Loading {len(csv_files)} CSV files...")
        for file in tqdm(csv_files, desc="📊 Reading CSVs", unit="file"):
            df = pd.read_csv(file, skiprows=skiprows, index_col=index_col, low_memory=False)
            self.dataframes.append(df)
            self.loaded_files.append(os.path.basename(file))

        print(f"✅ {len(csv_files)} CSV files loaded successfully!")

    def get_combined_dataframe(self):
        if not self.dataframes:
            print("⚠️ No CSV files loaded. Call `read_csv_files()` first.")
            return None
        return pd.concat(self.dataframes, ignore_index=True)
