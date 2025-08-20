from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import json
from pathlib import Path
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import string
import re
from fuzzywuzzy import fuzz
from collections import defaultdict
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import Error
import os
import logging
from mysql_config import MYSQL_CONFIG

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'

@app.before_request
def before_request():
    logger.debug('Session before request: %s', dict(session))

@app.after_request
def after_request(response):
    logger.debug('Session after request: %s', dict(session))
    return response

def get_db():
    config = MYSQL_CONFIG.copy()
    config['database'] = 'arogya_db'
    return mysql.connector.connect(**config)

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')
    nltk.download('wordnet')

# Initialize NLTK components
lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words('english'))

# Herbal database
herbal_db = {
    "Ashwagandha": {
        "Properties": "Adaptogenic herb that helps reduce stress and anxiety",
        "Benefits": "Boosts immunity, improves sleep, reduces inflammation",
        "Usage": "Available as powder, capsules, or liquid extract"
    },
    "Turmeric": {
        "Properties": "Anti-inflammatory and antioxidant properties",
        "Benefits": "Reduces inflammation, supports joint health, boosts immunity",
        "Usage": "Can be used in cooking, as supplements, or golden milk"
    },
    "Brahmi": {
        "Properties": "Brain tonic and memory enhancer",
        "Benefits": "Improves memory, reduces anxiety, supports brain health",
        "Usage": "Available as powder, tablets, or liquid extract"
    },
    "Shatavari": {
        "Properties": "Rejuvenating herb for reproductive health",
        "Benefits": "Balances hormones, supports immune system, improves vitality",
        "Usage": "Can be taken as powder, tablets, or liquid extract"
    },
    "Triphala": {
        "Properties": "Combination of three fruits with detoxifying properties",
        "Benefits": "Improves digestion, cleanses colon, supports eye health",
        "Usage": "Usually taken as powder or tablets before bed"
    }
}

# Create symptom and condition indices for faster lookup
symptom_index = defaultdict(list)
condition_index = defaultdict(list)
herb_properties_index = defaultdict(list)

def initialize_indices():
    """Initialize search indices for faster lookup"""
    for herb, info in herbal_db.items():
        # Index symptoms
        for symptom in info.get('treats_symptoms', []):
            symptom_index[symptom.lower()].append(herb)
        
        # Index conditions
        for condition in info.get('treats_conditions', []):
            condition_index[condition.lower()].append(herb)
        
        # Index properties
        for prop in info.get('properties', []):
            herb_properties_index[prop.lower()].append(herb)

initialize_indices()

def preprocess_text(text):
    """Preprocess text for better matching"""
    # Tokenize
    tokens = word_tokenize(text.lower())
    # Remove punctuation and stopwords
    tokens = [token for token in tokens if token not in string.punctuation and token not in stop_words]
    # Lemmatize
    tokens = [lemmatizer.lemmatize(token) for token in tokens]
    return tokens

def fuzzy_match(query, choices, threshold=80):
    """Find fuzzy matches in a list of choices"""
    matches = []
    query = query.lower()
    for choice in choices:
        ratio = fuzz.ratio(query, choice.lower())
        if ratio >= threshold:
            matches.append((choice, ratio))
    return sorted(matches, key=lambda x: x[1], reverse=True)

def identify_doshas(symptoms):
    """Identify potential dosha imbalances based on symptoms"""
    dosha_patterns = {
        'vata': [
            'anxiety', 'stress', 'insomnia', 'dry', 'cold', 'constipation', 
            'joint pain', 'nervousness', 'restlessness', 'irregular digestion'
        ],
        'pitta': [
            'inflammation', 'anger', 'acid', 'burning', 'fever', 'rash',
            'irritation', 'hot', 'sharp pain', 'excessive hunger'
        ],
        'kapha': [
            'congestion', 'weight', 'lethargy', 'depression', 'slow',
            'cold', 'mucus', 'heaviness', 'drowsiness', 'water retention'
        ]
    }
    
    identified_doshas = []
    symptoms_text = ' '.join(symptoms).lower()
    
    for dosha, patterns in dosha_patterns.items():
        if any(pattern in symptoms_text for pattern in patterns):
            identified_doshas.append(dosha)
    
    return identified_doshas

def extract_symptoms_conditions(message):
    """Extract symptoms and conditions from message"""
    # Simple keyword-based extraction
    symptoms = []
    conditions = []
    
    symptom_keywords = ['pain', 'ache', 'stress', 'anxiety', 'fatigue', 'insomnia', 'digestion']
    condition_keywords = ['diabetes', 'arthritis', 'hypertension', 'asthma']
    
    words = message.lower().split()
    
    for word in words:
        if word in symptom_keywords:
            symptoms.append(word)
        if word in condition_keywords:
            conditions.append(word)
    
    return symptoms, conditions

def get_recommendations(symptoms, conditions):
    """Get herb recommendations based on symptoms and conditions"""
    recommendations = []
    
    symptom_herbs = {
        'stress': ['Ashwagandha', 'Brahmi'],
        'anxiety': ['Brahmi', 'Ashwagandha'],
        'pain': ['Turmeric'],
        'fatigue': ['Ashwagandha', 'Shatavari'],
        'insomnia': ['Ashwagandha', 'Brahmi'],
        'digestion': ['Triphala']
    }
    
    condition_herbs = {
        'diabetes': ['Turmeric', 'Triphala'],
        'arthritis': ['Turmeric'],
        'hypertension': ['Brahmi'],
        'asthma': ['Turmeric']
    }
    
    # Add recommendations based on symptoms
    for symptom in symptoms:
        if symptom in symptom_herbs:
            recommendations.extend(symptom_herbs[symptom])
    
    # Add recommendations based on conditions
    for condition in conditions:
        if condition in condition_herbs:
            recommendations.extend(condition_herbs[condition])
    
    # Remove duplicates while preserving order
    recommendations = list(dict.fromkeys(recommendations))
    
    if not recommendations:
        return None
    
    response = "Based on your query, here are some recommended herbs:\n\n"
    for herb in recommendations:
        response += f"- {herb}: {herbal_db[herb]['Benefits']}\n"
    
    return response

def save_chat_message(user_email, user_message, bot_response, session_id=None):
    db = get_db()
    c = db.cursor()
    
    # If no session_id provided, create a new session with first message as title
    if not session_id:
        title = user_message[:50] + "..." if len(user_message) > 50 else user_message
        c.execute('''
            INSERT INTO chat_sessions (user_email, title)
            VALUES (?, ?)
        ''', (user_email, title))
        session_id = c.lastrowid
    
    # Save the message
    c.execute('''
        INSERT INTO chat_history (user_email, user_message, bot_response)
        VALUES (?, ?, ?)
    ''', (user_email, user_message, bot_response))
    
    # Update session's last message timestamp
    c.execute('''
        UPDATE chat_sessions
        SET last_message_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (session_id,))
    
    db.commit()
    db.close()
    return session_id

def get_user_chat_history(user_email):
    cnx = get_db()
    cursor = cnx.cursor(dictionary=True)
    
    # Get all chat sessions for the user
    cursor.execute('''
        SELECT id, title, created_at
        FROM chat_sessions
        WHERE user_email = %s
        ORDER BY created_at DESC
    ''', (user_email,))
    
    sessions = []
    for row in cursor.fetchall():
        # Get the last message for each session
        cursor.execute('''
            SELECT message, is_bot, created_at
            FROM chat_history
            WHERE session_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        ''', (row['id'],))
        last_message = cursor.fetchone()
        
        sessions.append({
            'id': row['id'],
            'title': row['title'],
            'created_at': row['created_at'],
            'last_message': last_message['message'] if last_message else None
        })
    
    cursor.close()
    cnx.close()
    return sessions

def get_session_messages(session_id):
    cnx = get_db()
    cursor = cnx.cursor(dictionary=True)
    
    cursor.execute('''
        SELECT message, is_bot, created_at
        FROM chat_history
        WHERE session_id = %s
        ORDER BY created_at ASC
    ''', (session_id,))
    
    messages = []
    for row in cursor.fetchall():
        messages.append({
            'message': row['message'],
            'is_bot': row['is_bot'],
            'created_at': row['created_at']
        })
    
    cursor.close()
    cnx.close()
    return messages

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/patient/login', methods=['GET', 'POST'])
def patient_login():
    logger.debug('Starting patient login')
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        logger.debug('Login attempt for email: %s', email)
        
        cnx = get_db()
        cursor = cnx.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()
        cursor.close()
        cnx.close()
        
        if user and check_password_hash(user['password'], password):
            logger.debug('Login successful for email: %s', email)
            session.clear()
            session['user_email'] = email
            session['user_name'] = user['name']
            session['logged_in'] = True
            session.modified = True
            logger.debug('Session after login: %s', dict(session))
            return redirect(url_for('chat_history'))
        
        logger.debug('Login failed for email: %s', email)
        return render_template('patient_login.html', error='Invalid email or password')
    
    return render_template('patient_login.html')

@app.route('/medical/login', methods=['GET', 'POST'])
def medical_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        cnx = get_db()
        cursor = cnx.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE email = %s AND is_medical_professional = 1', (email,))
        user = cursor.fetchone()
        cursor.close()
        cnx.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_email'] = email
            session['user_name'] = user['name']
            session['is_medical_professional'] = True
            return redirect(url_for('chat_history'))
        
        return render_template('medical_login.html', error='Invalid email or password')
    
    return render_template('medical_login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        is_medical_professional = request.form.get('is_medical_professional') == 'on'
        
        if password != confirm_password:
            return render_template('register.html', error='Passwords do not match')
        
        cnx = get_db()
        cursor = cnx.cursor()
        
        # Check if email already exists
        cursor.execute('SELECT email FROM users WHERE email = %s', (email,))
        if cursor.fetchone():
            cursor.close()
            cnx.close()
            return render_template('register.html', error='Email already registered')
        
        # Create new user
        cursor.execute('''
            INSERT INTO users (email, name, password, is_medical_professional)
            VALUES (%s, %s, %s, %s)
        ''', (email, name, generate_password_hash(password), is_medical_professional))
        
        cnx.commit()
        cursor.close()
        cnx.close()
        
        # Redirect medical professionals to medical login, patients to patient login
        if is_medical_professional:
            return redirect(url_for('medical_login'))
        return redirect(url_for('patient_login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/chat_history')
def chat_history():
    if 'user_email' not in session:
        return redirect(url_for('patient_login'))
    
    cnx = get_db()
    cursor = cnx.cursor(dictionary=True)
    
    # Get all chat sessions for the user with their last messages
    cursor.execute('''
        SELECT 
            cs.id,
            cs.title,
            cs.created_at,
            ch.created_at as last_message_at,
            ch.message as last_message
        FROM chat_sessions cs
        LEFT JOIN (
            SELECT 
                session_id,
                message,
                created_at,
                ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY created_at DESC) as rn
            FROM chat_history
        ) ch ON cs.id = ch.session_id AND ch.rn = 1
        WHERE cs.user_email = %s
        ORDER BY COALESCE(ch.created_at, cs.created_at) DESC
    ''', (session['user_email'],))
    
    chat_sessions = []
    for row in cursor.fetchall():
        chat_sessions.append({
            'id': row['id'],
            'title': row['title'],
            'created_at': row['created_at'],
            'last_message_at': row['last_message_at'] or row['created_at'],
            'last_message': row['last_message'] or 'No messages yet'
        })
    
    cursor.close()
    cnx.close()
    
    return render_template('chat_history.html', 
                         chat_sessions=chat_sessions,
                         user_name=session.get('user_name'))

@app.route('/chat')
def chat():
    if 'user_email' not in session:
        return redirect(url_for('patient_login'))
    return render_template('index.html', user_name=session.get('user_name'))

@app.route('/chat/<int:session_id>')
def continue_chat(session_id):
    if 'user_email' not in session:
        return redirect(url_for('patient_login'))
    
    messages = get_session_messages(session_id)
    return render_template('index.html', 
                         user_name=session.get('user_name'),
                         chat_history=messages)

def get_remedy_by_symptoms(cursor, symptoms):
    # Search for remedies based on symptoms
    search_terms = symptoms.lower().split()
    query = '''
        SELECT condition_name, symptoms, herbs, recommendations, precautions 
        FROM remedies 
        WHERE LOWER(symptoms) REGEXP %s
    '''
    
    # Create a regex pattern that matches any of the search terms
    pattern = '|'.join(search_terms)
    cursor.execute(query, (pattern,))
    
    remedies = cursor.fetchall()
    if remedies:
        response = []
        for remedy in remedies:
            response.append(f"For {remedy[0]}:\n")
            response.append(f"Recommended herbs: {remedy[2]}\n")
            response.append("Treatment recommendations:\n")
            response.append(f"{remedy[3]}\n")
            if remedy[4]:  # If there are precautions
                response.append(f"Precautions: {remedy[4]}\n")
            response.append("---\n")
        return '\n'.join(response)
    return None

@app.route('/api/chat', methods=['POST'])
def chat_api():
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id')
        
        if not user_message:
            return jsonify({'error': 'No message provided'})
            
        # Get user email from session
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'error': 'User not logged in'})

        # Connect to MySQL database
        config = MYSQL_CONFIG.copy()
        config['database'] = 'arogya_db'
        cnx = mysql.connector.connect(**config)
        cursor = cnx.cursor(buffered=True)

        try:
            # Create new chat session if needed
            if not session_id:
                # Use first 50 characters of user message as title
                title = (user_message[:47] + '...') if len(user_message) > 50 else user_message
                cursor.execute('''
                    INSERT INTO chat_sessions (user_email, title)
                    VALUES (%s, %s)
                ''', (user_email, title))
                session_id = cursor.lastrowid

            # Save user message
            cursor.execute('''
                INSERT INTO chat_history (session_id, message, is_bot)
                VALUES (%s, %s, %s)
            ''', (session_id, user_message, False))

            # Process message and get bot response
            bot_response = process_message(user_message)

            # Save bot response
            cursor.execute('''
                INSERT INTO chat_history (session_id, message, is_bot)
                VALUES (%s, %s, %s)
            ''', (session_id, bot_response, True))

            cnx.commit()
            
            return jsonify({
                'response': bot_response,
                'session_id': session_id
            })

        except mysql.connector.Error as err:
            app.logger.error(f"Error in chat endpoint: {err}")
            cnx.rollback()
            return jsonify({'error': 'I apologize, but I encountered an error. Please try again.'})
        finally:
            cursor.close()
            cnx.close()

    except Exception as e:
        app.logger.error(f"Error in chat endpoint: {e}")
        return jsonify({'error': 'I apologize, but I encountered an error. Please try again.'})

def process_message(user_message):
    try:
        # Connect to MySQL for remedies lookup
        config = MYSQL_CONFIG.copy()
        config['database'] = 'arogya_db'
        cnx = mysql.connector.connect(**config)
        cursor = cnx.cursor(buffered=True)

        # Convert message to lowercase for matching
        message = user_message.lower()

        # Check for greetings
        if any(greeting in message for greeting in ['hi', 'hello', 'hey']):
            return "Hello! I'm your Ayurvedic health assistant. How can I help you today?"

        # Check for digestive issues
        digestive_keywords = ['digestion', 'digestive', 'indigestion', 'stomach', 'gut', 'bloating', 'gas', 'constipation']
        if any(keyword in message for keyword in digestive_keywords):
            cursor.execute('''
                SELECT condition_name, symptoms, herbs, recommendations, precautions 
                FROM remedies 
                WHERE condition_name = 'Digestive Issues'
            ''')
            remedy = cursor.fetchone()
            if remedy:
                response = "🌿 For Digestive Issues:\n\n"
                response += f"Common symptoms: {remedy[1]}\n\n"
                response += f"Recommended herbs: {remedy[2]}\n\n"
                response += "Treatment recommendations:\n"
                response += f"{remedy[3]}\n\n"
                if remedy[4]:  # If there are precautions
                    response += f"⚠️ Precautions: {remedy[4]}\n\n"
                response += "\nWould you like to know more about any specific herb mentioned above?"
                return response

        # Look for specific herb mentions
        cursor.execute('SELECT DISTINCT herbs FROM remedies')
        all_herbs = []
        for herbs_str in cursor.fetchall():
            all_herbs.extend(herbs_str[0].split(', '))
        all_herbs = list(set(all_herbs))  # Remove duplicates
        
        for herb in all_herbs:
            if herb.lower() in message:
                return format_herb_info(herb)

        # Look for condition matches in remedies
        cursor.execute('''
            SELECT condition_name, symptoms, herbs, recommendations, precautions 
            FROM remedies 
            WHERE LOWER(condition_name) LIKE %s 
            OR LOWER(symptoms) LIKE %s
        ''', (f'%{message}%', f'%{message}%'))
        
        remedies = cursor.fetchall()
        if remedies:
            response = []
            for remedy in remedies:
                response.append(f"For {remedy[0]}:\n")
                response.append(f"Recommended herbs: {remedy[2]}\n")
                response.append("Treatment recommendations:\n")
                response.append(f"{remedy[3]}\n")
                if remedy[4]:  # If there are precautions
                    response.append(f"Precautions: {remedy[4]}\n")
                response.append("---\n")
            return '\n'.join(response)

        # Extract symptoms and try to match them
        symptoms, conditions = extract_symptoms_conditions(message)
        if symptoms or conditions:
            recommendations = get_recommendations(symptoms, conditions)
            if recommendations:
                return recommendations

        # If no specific condition found, provide a general response
        return ("I understand you're asking about health concerns. Could you please be more specific? "
                "You can ask about:\n\n"
                "1. Specific conditions (e.g., digestive issues, stress, headaches)\n"
                "2. Specific symptoms (e.g., bloating, anxiety, pain)\n"
                "3. Specific herbs (e.g., Ashwagandha, Triphala, Brahmi)\n"
                "4. General health advice")

    except mysql.connector.Error as err:
        app.logger.error(f"Error processing message: {err}")
        return "I apologize, but I encountered an error. Please try again."
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'cnx' in locals() and cnx.is_connected():
            cnx.close()

def generate_chat_response(user_message):
    """Generate a chat response"""
    try:
        user_message_lower = user_message.lower()
        
        # Check for basic greetings
        greeting_words = ['hi', 'hello', 'namaste', 'hey', 'hola', 'greetings']
        if any(word == user_message_lower for word in greeting_words):
            return format_greeting()
        
        # Check for specific herb queries
        for herb in herbal_db.keys():
            if herb.lower() in user_message_lower:
                return format_herb_info(herb)
        
        # Extract symptoms and conditions
        symptoms, conditions = extract_symptoms_conditions(user_message)
        if symptoms or conditions:
            recommendations = get_recommendations(symptoms, conditions)
            if recommendations:
                return recommendations
        
        # If no specific query was identified, provide a helpful response
        return format_help_message()
        
    except Exception as e:
        print(f"Error generating response: {str(e)}")
        return format_help_message()  # Fallback to help message on error

def format_recommendations(recommendations):
    """Format herb recommendations"""
    if not recommendations:
        return format_help_message()
        
    response = ["🌿 Based on your symptoms, here are some recommended herbs:\n"]
    
    for rec in recommendations[:3]:  # Show top 3 recommendations
        herb = rec['herb']
        response.extend([
            f"• {herb}",
            f"  - {rec.get('description', '').split('.')[0]}",
            f"  - Usage: {rec.get('usage', '')}",
            ""
        ])
    
    response.append("\nWould you like more details about any of these herbs?")
    return "\n".join(response)

def format_greeting():
    """Format a greeting message"""
    greetings = [
        "Namaste! 🙏 I'm your Ayurvedic health assistant. How can I help you today?",
        "Welcome! I'm here to guide you through Ayurvedic wellness. What would you like to know?",
        "Greetings! I'm your Ayurvedic guide. How may I assist you on your wellness journey?"
    ]
    return greetings[0]  # Using first greeting for consistency

def format_herb_info(herb):
    """Format herb information"""
    info = herbal_db.get(herb, {})
    if not info:
        return "I apologize, but I don't have detailed information about that herb."
    
    response = f"Here's what I know about {herb}:\n\n"
    for key, value in info.items():
        response += f"{key}: {value}\n"
    return response

def format_digestive_response(user_message):
    """Format response for digestive health queries"""
    # Find herbs that treat digestive issues from the database
    digestive_herbs = []
    digestive_symptoms = ['digestion', 'digestive', 'stomach', 'gut', 'bloating', 'gas', 'constipation']
    
    for herb, info in herbal_db.items():
        if any(symptom.lower() in digestive_symptoms for symptom in info.get('treats_symptoms', [])):
            digestive_herbs.append((herb, info))
    
    # Sort by effectiveness score if available
    digestive_herbs.sort(key=lambda x: x[1].get('effectiveness', 0), reverse=True)
    
    response = ["🌿 Ayurvedic Remedies for Digestive Health\n"]
    
    # Take top 4 most effective herbs
    for herb, info in digestive_herbs[:4]:
        response.extend([
            f"• {herb} ({info.get('scientific_name', '')})",
            f"  - {info.get('description', '').split('.')[0]}",
            f"  - Usage: {info.get('usage', '')}"
        ])
        
        if info.get('effectiveness'):
            response.append(f"  - Effectiveness score: {info['effectiveness']}/10")
            
        if info.get('precautions'):
            response.append(f"  - Precaution: {info['precautions'][0]}")
            
        response.append("")  # Add blank line between herbs
    
    response.append("📝 Recommended Daily Practices:")
    practices = [
        "• Drink warm water throughout the day",
        "• Eat mindfully and at regular times",
        "• Include fresh ginger tea in your routine",
        "• Avoid eating late at night",
        "• Chew your food thoroughly"
    ]
    response.extend(practices)
    
    response.append("\nWould you like specific details about any of these herbs or additional digestive health tips?")
    return "\n".join(response)

def format_help_message():
    """Format a help message"""
    return """I can help you with:
- Information about Ayurvedic herbs
- Common health concerns and remedies
- Understanding your dosha type
- General wellness advice

Feel free to ask about specific herbs or health concerns!"""

if __name__ == '__main__':
    app.run(debug=True)