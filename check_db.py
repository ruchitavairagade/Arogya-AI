import mysql.connector
from mysql_config import MYSQL_CONFIG
from werkzeug.security import generate_password_hash

def test_database_writes():
    try:
        # Connect to MySQL
        print("Connecting to MySQL...")
        config = MYSQL_CONFIG.copy()
        config['database'] = 'arogya_db'
        cnx = mysql.connector.connect(**config)
        cursor = cnx.cursor(buffered=True)

        # Test user insertion
        print("\nTesting user insertion...")
        test_user = ('test_user@example.com', 'Test User', generate_password_hash('test123'), 0)
        cursor.execute('''
            INSERT INTO users (email, name, password, is_medical_professional)
            VALUES (%s, %s, %s, %s)
        ''', test_user)

        # Test chat session creation
        print("Testing chat session creation...")
        cursor.execute('''
            INSERT INTO chat_sessions (user_email, title)
            VALUES (%s, %s)
        ''', ('test_user@example.com', 'Test Session'))

        # Test chat message insertion
        print("Testing chat message insertion...")
        cursor.execute('''
            INSERT INTO chat_history (user_email, user_message, bot_response)
            VALUES (%s, %s, %s)
        ''', ('test_user@example.com', 'Test message', 'Test response'))

        # Commit the changes
        cnx.commit()

        # Verify the insertions
        print("\nVerifying insertions...")
        cursor.execute("SELECT * FROM users WHERE email = 'test_user@example.com'")
        user = cursor.fetchone()
        print(f"User found: {user is not None}")

        cursor.execute("SELECT * FROM chat_sessions WHERE user_email = 'test_user@example.com'")
        session = cursor.fetchone()
        print(f"Chat session found: {session is not None}")

        cursor.execute("SELECT * FROM chat_history WHERE user_email = 'test_user@example.com'")
        message = cursor.fetchone()
        print(f"Chat message found: {message is not None}")

        print("\nAll tests completed successfully!")

    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if 'cnx' in locals() and cnx.is_connected():
            cursor.close()
            cnx.close()

def check_remedies():
    try:
        # Connect to MySQL
        print("Connecting to MySQL...")
        config = MYSQL_CONFIG.copy()
        config['database'] = 'arogya_db'
        cnx = mysql.connector.connect(**config)
        cursor = cnx.cursor(buffered=True)

        # Check remedies
        print("\nChecking remedies in database:")
        cursor.execute("SELECT condition_name, symptoms, herbs FROM remedies")
        remedies = cursor.fetchall()
        
        print(f"\nFound {len(remedies)} remedies:")
        for remedy in remedies:
            print(f"\nCondition: {remedy[0]}")
            print(f"Symptoms: {remedy[1]}")
            print(f"Herbs: {remedy[2]}")
            print("-" * 50)

    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if 'cnx' in locals() and cnx.is_connected():
            cursor.close()
            cnx.close()

def check_user(email):
    try:
        # Connect to MySQL
        print(f"\nChecking user {email} in database...")
        config = MYSQL_CONFIG.copy()
        config['database'] = 'arogya_db'
        cnx = mysql.connector.connect(**config)
        cursor = cnx.cursor(buffered=True)

        # Check user
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if user:
            print(f"User found: {user[1]}")  # Print user name
        else:
            print("User not found!")

    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if 'cnx' in locals() and cnx.is_connected():
            cursor.close()
            cnx.close()

if __name__ == "__main__":
    test_database_writes()
    check_remedies()
    check_user('anand@gmail.com') 