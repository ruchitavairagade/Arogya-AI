import os
import mysql.connector
import pandas as pd
import requests

# Your Google Drive Download Link (CHANGE THIS TO YOUR CSV LINK)
DRIVE_URL = "https://drive.google.com/uc?export=download&id=1X_8OloXb7bD6L4Hf0pCTBWH949eYzU9y"

LOCAL_FILE = "dataset.csv"

# Download dataset
print("Downloading dataset from Google Drive...")
r = requests.get(DRIVE_URL)
with open(LOCAL_FILE, "wb") as f:
    f.write(r.content)

print("Dataset downloaded successfully.")

# MySQL Config
config = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "arogya_db"
}

print("Connecting to MySQL...")
conn = mysql.connector.connect(**config)
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS remedies (
        id INT AUTO_INCREMENT PRIMARY KEY,
        plant_name VARCHAR(255),
        symptoms TEXT,
        herbs TEXT,
        recommendations TEXT,
        precautions TEXT
    );
""")

print("Importing data into MySQL...")

df = pd.read_csv(LOCAL_FILE)

for _, row in df.iterrows():
    cursor.execute("""
        INSERT INTO remedies (plant_name, symptoms, herbs, recommendations, precautions)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        row['plant_name'],
        row['symptoms'],
        row['herbs'],
        row['recommendations'],
        row.get('precautions', '')
    ))

conn.commit()
cursor.close()
conn.close()

print("Data imported successfully into MySQL!")

