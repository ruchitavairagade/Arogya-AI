import mysql.connector
from mysql.connector import Error
from werkzeug.security import generate_password_hash
from mysql_config import MYSQL_CONFIG

def create_mysql_database():
    # First connect without database selected
    config = MYSQL_CONFIG.copy()
    if 'database' in config:
        del config['database']
    
    try:
        # Connect to MySQL server
        print("Connecting to MySQL server...")
        cnx = mysql.connector.connect(**config)
        cursor = cnx.cursor(buffered=True)
        
        # Create database if it doesn't exist
        print("Creating database if it doesn't exist...")
        cursor.execute("DROP DATABASE IF EXISTS arogya_db")
        cursor.execute("CREATE DATABASE arogya_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute("USE arogya_db")
        
        # Create users table
        print("Creating users table...")
        cursor.execute('''
            CREATE TABLE users (
                email VARCHAR(255) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                password VARCHAR(255) NOT NULL,
                is_medical_professional BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create chat_sessions table
        print("Creating chat_sessions table...")
        cursor.execute('''
            CREATE TABLE chat_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_email VARCHAR(255) NOT NULL,
                title VARCHAR(255) NOT NULL DEFAULT 'New Chat',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_email) REFERENCES users(email)
            )
        ''')
        
        # Create chat_history table
        print("Creating chat_history table...")
        cursor.execute('''
            CREATE TABLE chat_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                session_id INT NOT NULL,
                message TEXT NOT NULL,
                is_bot BOOLEAN NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
            )
        ''')

        # Create remedies table
        print("Creating remedies table...")
        cursor.execute('''
            CREATE TABLE remedies (
                id INT AUTO_INCREMENT PRIMARY KEY,
                condition_name VARCHAR(255) NOT NULL,
                symptoms TEXT NOT NULL,
                herbs TEXT NOT NULL,
                recommendations TEXT NOT NULL,
                precautions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY unique_condition (condition_name)
            )
        ''')

        # Add test user
        print("\nAdding test user...")
        test_user = ('anand@gmail.com', 'Anand Singh', generate_password_hash('bokaro#1'), False)
        cursor.execute('''
            INSERT INTO users (email, name, password, is_medical_professional)
            VALUES (%s, %s, %s, %s)
        ''', test_user)
        
        # Add test remedies
        print("\nAdding test remedies...")
        test_remedies = [
            ("Digestive Issues", "Bloating, Gas, Indigestion, Stomach pain", 
             "Triphala, Ginger, Cumin, Fennel",
             "1. Take ginger tea before meals\n2. Use cumin in cooking\n3. Avoid heavy meals at night",
             "Consult doctor if symptoms persist for more than a week"),
            
            ("Stress and Anxiety", "Restlessness, Insomnia, Mental tension, Worry",
             "Ashwagandha, Brahmi, Jatamansi, Holy Basil",
             "1. Take Ashwagandha before bed\n2. Practice meditation\n3. Regular exercise",
             "Not recommended during pregnancy"),
            
            ("Headache", "Head pain, Tension, Migraine",
             "Brahmi, Shankhpushpi, Jatamansi",
             "1. Apply diluted peppermint oil\n2. Rest in a dark room\n3. Stay hydrated",
             "Seek immediate help if accompanied by vision changes"),
            
            ("Joint Pain", "Stiffness, Inflammation, Reduced mobility",
             "Turmeric, Guggulu, Ginger, Boswellia",
             "1. Take turmeric with black pepper\n2. Gentle yoga\n3. Warm oil massage",
             "Avoid if on blood thinners"),
            
            ("Respiratory Issues", "Cough, Cold, Congestion, Breathing difficulty",
             "Tulsi, Ginger, Mulethi, Pippali",
             "1. Steam inhalation with tulsi\n2. Ginger-honey tea\n3. Rest and hydration",
             "Seek help if breathing becomes difficult"),
            
            ("Sleep Problems", "Insomnia, Restlessness, Poor sleep quality",
             "Ashwagandha, Jatamansi, Brahmi, Shankhpushpi",
             "1. Take herbs 1 hour before bed\n2. Follow sleep hygiene\n3. Avoid screens",
             "Not recommended with sleeping pills")
        ]
        
        for remedy in test_remedies:
            cursor.execute('''
                INSERT INTO remedies 
                (condition_name, symptoms, herbs, recommendations, precautions)
                VALUES (%s, %s, %s, %s, %s)
            ''', remedy)
        
        cnx.commit()
        print("Database setup completed successfully!")
        
    except Error as err:
        print(f"Error: {err}")
    finally:
        if 'cnx' in locals() and cnx.is_connected():
            cursor.close()
            cnx.close()

if __name__ == "__main__":
    create_mysql_database() 