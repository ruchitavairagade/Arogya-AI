import os
import gdown
import zipfile

# Google Drive file ID
FILE_ID = "1DSLN0QP5ntplKM6LroCeV6WwPYRCzqj7"
URL = f"https://drive.google.com/uc?id={FILE_ID}"

ZIP_PATH = "dataset.zip"
DATASET_FOLDER = "dataset"

def download_and_extract():
    # Check if dataset folder exists
    if os.path.exists(DATASET_FOLDER):
        print("✅ Dataset already exists. Skipping download.")
        return
    
    print("⬇️ Downloading dataset from Google Drive...")
    gdown.download(URL, ZIP_PATH, quiet=False)
    
    print("📦 Extracting dataset...")
    with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
        zip_ref.extractall(DATASET_FOLDER)
    
    print("✅ Dataset is ready!")

if __name__ == "__main__":
    download_and_extract()
