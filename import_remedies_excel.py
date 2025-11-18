import pandas as pd
import mysql.connector
from mysql_config import MYSQL_CONFIG

# ✅ 1. Read your Excel file
excel_path = 'herbal_remedies_dataset.xlsx'   # file must be in the same folder as app.py
df = pd.read_excel(excel_path, engine='openpyxl')

print(f"✅ Loaded {len(df)} rows from {excel_path}")
print("📄 Columns found:", list(df.columns))

# ✅ 2. Connect to your MySQL database
conn = mysql.connector.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

# ✅ 3. Create remedies table if it doesn't exist
cursor.execute('''
CREATE TABLE IF NOT EXISTS remedies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plant_name VARCHAR(255),
    symptoms TEXT,
    herbs TEXT,
    recommendations TEXT,
    precautions TEXT
)
''')

# ✅ 4. Insert each row into the database
for _, row in df.iterrows():
    cursor.execute('''
        INSERT INTO remedies (plant_name, symptoms, herbs, recommendations, precautions)
        VALUES (%s, %s, %s, %s, %s)
    ''', (
        str(row.get('plant name', '')),
        str(row.get('symptoms', '')),
        str(row.get('herbs', '')),
        str(row.get('recommendations', '')),
        str(row.get('precautions', ''))
    ))

conn.commit()
cursor.close()
conn.close()

print("🌿 All remedies imported successfully into MySQL!")
