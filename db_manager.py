import sqlite3
from tabulate import tabulate
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path='data/arogya.db'):
        self.db_path = db_path

    def connect(self):
        return sqlite3.connect(self.db_path)

    def show_all_tables(self):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("\nAvailable Tables:")
        for table in tables:
            print(f"- {table[0]}")
        conn.close()

    def show_table_data(self, table_name):
        conn = self.connect()
        cursor = conn.cursor()
        try:
            # Get column names
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Get data
            cursor.execute(f"SELECT * FROM {table_name};")
            data = cursor.fetchall()
            
            # Print using tabulate for better formatting
            print(f"\nTable: {table_name}")
            print(tabulate(data, headers=columns, tablefmt="grid"))
            print(f"Total records: {len(data)}")
        except sqlite3.Error as e:
            print(f"Error accessing table {table_name}: {e}")
        conn.close()

    def add_test_data(self):
        conn = self.connect()
        cursor = conn.cursor()
        try:
            # Add test users
            test_users = [
                ('patient@test.com', 'Test Patient', 'pbkdf2:sha256:600000$test123$test123', 0),
                ('doctor@test.com', 'Test Doctor', 'pbkdf2:sha256:600000$test123$test123', 1),
            ]
            cursor.executemany('''
                INSERT OR REPLACE INTO users (email, name, password, is_medical_professional)
                VALUES (?, ?, ?, ?)
            ''', test_users)

            # Add test chat sessions
            cursor.execute('''
                INSERT INTO chat_sessions (user_email, title)
                VALUES (?, ?)
            ''', ('patient@test.com', 'First Consultation'))
            session_id = cursor.lastrowid

            # Add test chat history
            test_messages = [
                ('patient@test.com', 'What herbs help with stress?', 'Based on your query, I recommend Ashwagandha and Brahmi...'),
                ('patient@test.com', 'Tell me more about Ashwagandha', 'Ashwagandha is an adaptogenic herb that helps reduce stress...'),
            ]
            cursor.executemany('''
                INSERT INTO chat_history (user_email, user_message, bot_response)
                VALUES (?, ?, ?)
            ''', test_messages)

            conn.commit()
            print("Test data added successfully!")
        except sqlite3.Error as e:
            print(f"Error adding test data: {e}")
        finally:
            conn.close()

def main():
    db = DatabaseManager()
    while True:
        print("\nDatabase Management Menu:")
        print("1. Show all tables")
        print("2. View users table")
        print("3. View chat sessions")
        print("4. View chat history")
        print("5. Add test data")
        print("6. Exit")
        
        choice = input("\nEnter your choice (1-6): ")
        
        if choice == '1':
            db.show_all_tables()
        elif choice == '2':
            db.show_table_data('users')
        elif choice == '3':
            db.show_table_data('chat_sessions')
        elif choice == '4':
            db.show_table_data('chat_history')
        elif choice == '5':
            db.add_test_data()
        elif choice == '6':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == '__main__':
    main() 