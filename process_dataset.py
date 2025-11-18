import pandas as pd
import json
from pathlib import Path

def load_existing_database():
    """Load the existing Ayurvedic database"""
    try:
        with open('data/herbal_remedies.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def process_csv_dataset():
    """Process the CSV dataset and convert it to our database format"""
    # Read the CSV file
    df = pd.read_csv('herbal_remedies_dataset.csv')
    
    # Create a new dictionary for the processed data
    processed_data = {}
    
    for _, row in df.iterrows():
        herb_name = row['Plant Name']
        
        # Skip if herb name is missing
        if pd.isna(herb_name):
            continue
            
        herb_data = {
            'scientific_name': row.get('Scientific Name', ''),
            'part_used': row.get('Part Used', ''),
            'treats_conditions': [cond.strip() for cond in str(row.get('Medical Condition Treated', '')).split(',')],
            'usage': f"{row.get('Usage Method', '')}. Dosage: {row.get('Dosage', '')}",
            'effectiveness': row.get('Effectiveness Score', ''),
            'precautions': [effect.strip() for effect in str(row.get('Side Effects', '')).split(',')],
            'region': row.get('Region Grown', ''),
            'climate': row.get('Climate Preference', ''),
            'nutritional_benefits': [benefit.strip() for benefit in str(row.get('Nutritional Benefits', '')).split(',')],
            'drug_interactions': [drug.strip() for drug in str(row.get('Drug Interactions', '')).split(',')]
        }
        
        processed_data[herb_name] = herb_data
    
    return processed_data

def merge_databases(existing_db, new_db):
    """Merge the existing Ayurvedic database with the new processed data"""
    merged_db = existing_db.copy()
    
    for herb_name, new_data in new_db.items():
        if herb_name in merged_db:
            # Update existing entry
            merged_db[herb_name].update({
                'scientific_name': new_data['scientific_name'],
                'part_used': new_data['part_used'],
                'effectiveness': new_data['effectiveness'],
                'region': new_data['region'],
                'climate': new_data['climate'],
                'nutritional_benefits': new_data['nutritional_benefits'],
                'drug_interactions': new_data['drug_interactions']
            })
            
            # Merge conditions and precautions
            merged_db[herb_name]['treats_conditions'].extend(new_data['treats_conditions'])
            merged_db[herb_name]['precautions'].extend(new_data['precautions'])
            
            # Remove duplicates and empty values
            merged_db[herb_name]['treats_conditions'] = list(set(filter(None, merged_db[herb_name]['treats_conditions'])))
            merged_db[herb_name]['precautions'] = list(set(filter(None, merged_db[herb_name]['precautions'])))
        else:
            # Add new entry
            merged_db[herb_name] = {
                'sanskrit_name': '',  # To be filled manually
                'dosha_balance': [],  # To be filled manually
                'properties': [],     # To be filled manually
                'treats_symptoms': [],  # To be filled manually
                **new_data
            }
    
    return merged_db

def main():
    # Create data directory if it doesn't exist
    Path('data').mkdir(exist_ok=True)
    
    # Load existing database
    existing_db = load_existing_database()
    
    # Process CSV dataset
    new_db = process_csv_dataset()
    
    # Merge databases
    merged_db = merge_databases(existing_db, new_db)
    
    # Save merged database
    with open('data/herbal_remedies_merged.json', 'w') as f:
        json.dump(merged_db, f, indent=4)
    
    print(f"Successfully processed dataset and merged databases!")
    print(f"Total number of herbs in merged database: {len(merged_db)}")
    print("New database saved as: data/herbal_remedies_merged.json")

if __name__ == "__main__":
    main() 