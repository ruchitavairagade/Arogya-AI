import os
import gdown

FILE_ID = "1DSLN0QP5ntplKM6LroCeV6WwPYRCzqj7"
URL = f"https://drive.google.com/uc?id={FILE_ID}"

FILE_NAME = "herbal_remedies_dataset.csv"   # ← Change this to your real file name

def download_dataset():
    if os.path.exists(FILE_NAME):
        print("Dataset already exists. Skipping download.")
        return

    print("Downloading dataset from Google Drive...")
    gdown.download(URL, FILE_NAME, quiet=False)

    print("Dataset downloaded successfully.")

if __name__ == "__main__":
    download_dataset()
