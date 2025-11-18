import pandas as pd
import mysql.connector
from mysql_config import MYSQL_CONFIG

# Load your CSV file
csv_path = 'herbal_remedies_dataset.csv'
df = pd.read_csv(csv_path)

print(f"✅ Loaded {len(df)} rows from {csv_path}")
print(f"📄 Columns found: {list(df.columns)}")

# Connect to MySQL
conn = mysql.connector.connect(**MYSQL_CONFIG)
cursor = conn.cursor()

# Create the remedies table
cursor.execute('''
CREATE TABLE IF NOT EXISTS remedies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plant_name VARCHAR(255),
    scientific_name VARCHAR(255),
    part_used VARCHAR(255),
    medical_condition_treated TEXT,
    usage_method TEXT,
    dosage TEXT,
    effectiveness_score FLOAT,
    side_effects TEXT,
    region_grown VARCHAR(255),
    climate_preference VARCHAR(255),
    nutritional_benefits TEXT,
    drug_interactions TEXT
)
''')

# Insert data into the table
for _, row in df.iterrows():
    cursor.execute('''
        INSERT INTO remedies (
            plant_name, scientific_name, part_used, medical_condition_treated,
            usage_method, dosage, effectiveness_score, side_effects,
            region_grown, climate_preference, nutritional_benefits, drug_interactions
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (
        str(row.get('Plant Name', '')),
        str(row.get('Scientific Name', '')),
        str(row.get('Part Used', '')),
        str(row.get('Medical Condition Treated', '')),
        str(row.get('Usage Method', '')),
        str(row.get('Dosage', '')),
        float(row.get('Effectiveness Score', 0)) if pd.notna(row.get('Effectiveness Score')) else 0,
        str(row.get('Side Effects', '')),
        str(row.get('Region Grown', '')),
        str(row.get('Climate Preference', '')),
        str(row.get('Nutritional Benefits', '')),
        str(row.get('Drug Interactions', ''))
    ))

conn.commit()
cursor.close()
conn.close()

print("🌿 All remedies imported successfully into MySQL!")
