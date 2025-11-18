# app.py
import os
import logging
import json
from collections import defaultdict
from pathlib import Path
import re
import string
import datetime

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import mysql.connector
from mysql.connector import Error
from mysql_config import MYSQL_CONFIG
from werkzeug.security import generate_password_hash, check_password_hash

import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from fuzzywuzzy import fuzz

# -------------------- Logging & Flask Setup --------------------
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

# -------------------- NLTK Setup --------------------
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')
    nltk.download('wordnet')

lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words('english'))

# -------------------- Database helper --------------------
def get_db():
    """
    Returns a new connection to the arogya_db database using MYSQL_CONFIG.
    Caller must close connection when done.
    """
    cfg = MYSQL_CONFIG.copy()
    cfg['database'] = 'arogya_db'
    return mysql.connector.connect(**cfg)

# -------------------- In-memory Herbal DB (kept for fallback/help) --------------------
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

# -------------------- Utility & NLP helpers --------------------
def preprocess_text(text):
    """Tokenize, remove punctuation/stopwords, lemmatize"""
    tokens = word_tokenize(text.lower())
    tokens = [t for t in tokens if t not in string.punctuation and t not in stop_words]
    return [lemmatizer.lemmatize(t) for t in tokens]

def fuzzy_match(query, choices, threshold=80):
    """Return list of (choice, score) with score >= threshold"""
    results = []
    q = query.lower()
    for c in choices:
        score = fuzz.ratio(q, c.lower())
        if score >= threshold:
            results.append((c, score))
    return sorted(results, key=lambda x: x[1], reverse=True)

def extract_symptoms_conditions(message):
    """
    Very simple keyword based extraction. Expand lists as needed.
    Returns (symptoms[], conditions[])
    """
    symptom_keywords = ['pain', 'ache', 'stress', 'anxiety', 'fatigue', 'insomnia', 'digestion', 'cough', 'fever', 'headache', 'cold']
    condition_keywords = ['diabetes', 'arthritis', 'hypertension', 'asthma', 'digestive', 'digestive issues']
    words = re.findall(r"\w+", message.lower())
    symptoms = [w for w in words if w in symptom_keywords]
    conditions = [w for w in words if w in condition_keywords]
    return symptoms, conditions

def identify_doshas(symptoms):
    """Naive dosha matcher from symptom list"""
    dosha_patterns = {
        'vata': ['anxiety', 'stress', 'insomnia', 'dry', 'cold', 'constipation'],
        'pitta': ['inflammation', 'fever', 'burning', 'acid', 'rash'],
        'kapha': ['congestion', 'weight', 'lethargy', 'mucus', 'heaviness']
    }
    symptoms_text = ' '.join(symptoms).lower()
    found = []
    for d, pats in dosha_patterns.items():
        if any(p in symptoms_text for p in pats):
            found.append(d)
    return found

# -------------------- Database-specific functions --------------------
def get_remedies_by_condition(condition, limit=5):
    """
    Search remedies table for matching condition text.
    Uses WHERE symptoms LIKE %condition% OR plant_name LIKE %condition%.
    Returns list of dicts with keys plant_name, symptoms, herbs, recommendations, precautions.
    """
    cnx = get_db()
    cursor = cnx.cursor(dictionary=True)
    try:
        like = f"%{condition}%"
        query = """
            SELECT plant_name, symptoms, herbs, recommendations, precautions
            FROM remedies
            WHERE symptoms LIKE %s OR plant_name LIKE %s
            LIMIT %s
        """
        cursor.execute(query, (like, like, limit))
        rows = cursor.fetchall()
        return rows
    except mysql.connector.Error as e:
        logger.error("MySQL error in get_remedies_by_condition: %s", e)
        return []
    finally:
        cursor.close()
        cnx.close()

def save_chat_message(user_email, user_message, bot_response, session_id=None):
    """
    Save chat message to DB. If session_id is None, create a new chat_sessions row.
    Returns session_id used.
    """
    cnx = get_db()
    cursor = cnx.cursor()
    try:
        if not session_id:
            title = (user_message[:47] + '...') if len(user_message) > 50 else user_message
            cursor.execute(
                "INSERT INTO chat_sessions (user_email, title, created_at) VALUES (%s, %s, %s)",
                (user_email, title, datetime.datetime.utcnow())
            )
            session_id = cursor.lastrowid

        # Insert user message (is_bot = 0)
        cursor.execute(
            "INSERT INTO chat_history (session_id, message, is_bot, created_at) VALUES (%s, %s, %s, %s)",
            (session_id, user_message, 0, datetime.datetime.utcnow())
        )

        # Insert bot response (is_bot = 1)
        cursor.execute(
            "INSERT INTO chat_history (session_id, message, is_bot, created_at) VALUES (%s, %s, %s, %s)",
            (session_id, bot_response, 1, datetime.datetime.utcnow())
        )

        # Update last_message_at on session (if column exists)
        try:
            cursor.execute(
                "UPDATE chat_sessions SET last_message_at = %s WHERE id = %s",
                (datetime.datetime.utcnow(), session_id)
            )
        except Exception:
            # If last_message_at column not present, ignore
            pass

        cnx.commit()
        return session_id
    except mysql.connector.Error as e:
        cnx.rollback()
        logger.error("Error saving chat message: %s", e)
        raise
    finally:
        cursor.close()
        cnx.close()

def get_user_chat_history(user_email):
    """
    Returns list of sessions with last message info for the given user.
    """
    cnx = get_db()
    cursor = cnx.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT id, title, created_at
            FROM chat_sessions
            WHERE user_email = %s
            ORDER BY created_at DESC
        """, (user_email,))
        sessions = []
        for row in cursor.fetchall():
            sid = row['id']
            cursor.execute("""
                SELECT message, is_bot, created_at
                FROM chat_history
                WHERE session_id = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (sid,))
            last = cursor.fetchone()
            sessions.append({
                'id': sid,
                'title': row['title'],
                'created_at': row.get('created_at'),
                'last_message': last['message'] if last else None,
                'last_message_time': last['created_at'] if last else None
            })
        return sessions
    finally:
        cursor.close()
        cnx.close()
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
            'message': str(row.get('message', '')),
            'is_bot': bool(row.get('is_bot', False)),
            'created_at': str(row.get('created_at', '')) if row.get('created_at') else ''
        })
    
    cursor.close()
    cnx.close()
    return messages

# -------------------- Routes: Auth & Pages --------------------
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
        try:
            cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
            user = cursor.fetchone()
        finally:
            cursor.close()
            cnx.close()

        if user and check_password_hash(user['password'], password):
            logger.debug('Login successful for email: %s', email)
            session.clear()
            session['user_email'] = email
            session['user_name'] = user.get('name')
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
        try:
            cursor.execute('SELECT * FROM users WHERE email = %s AND is_medical_professional = 1', (email,))
            user = cursor.fetchone()
        finally:
            cursor.close()
            cnx.close()

        if user and check_password_hash(user['password'], password):
            session['user_email'] = email
            session['user_name'] = user.get('name')
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
        try:
            # Check if email exists
            cursor.execute('SELECT email FROM users WHERE email = %s', (email,))
            if cursor.fetchone():
                return render_template('register.html', error='Email already registered')

            cursor.execute('''
                INSERT INTO users (email, name, password, is_medical_professional, created_at)
                VALUES (%s, %s, %s, %s, %s)
            ''', (email, name, generate_password_hash(password), int(is_medical_professional), datetime.datetime.utcnow()))
            cnx.commit()
        finally:
            cursor.close()
            cnx.close()

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

    chat_sessions = get_user_chat_history(session['user_email'])
    return render_template('chat_history.html', chat_sessions=chat_sessions, user_name=session.get('user_name'))

@app.route('/chat')
def chat():
    if 'user_email' not in session:
        return redirect(url_for('patient_login'))
    return render_template('index.html', user_name=session.get('user_name'))

@app.route('/chat/<int:session_id>')
def continue_chat(session_id):
    if 'user_email' not in session:
        return redirect(url_for('patient_login'))

    try:
        messages = get_session_messages(session_id)

        # Ensure data is serializable
        clean_messages = []
        for msg in messages:
            clean_messages.append({
                'message': str(msg.get('message', '')),
                'is_bot': bool(msg.get('is_bot', False)),
                'created_at': str(msg.get('created_at', '')) if msg.get('created_at') else ''
            })

        return render_template(
            'index.html',
            user_name=session.get('user_name', 'User'),
            chat_history=clean_messages or []
        )

    except Exception as e:
        app.logger.error(f"Error rendering chat session: {e}")
        return render_template('index.html', 
                               user_name=session.get('user_name', 'User'), 
                               chat_history=[])


# -------------------- Lower-level Remedy query used in old code --------------------
def get_remedy_by_symptoms(cursor, symptoms):
    """
    This function mirrors old behavior but uses real columns:
    The original code expected `condition_name` etc. We'll use `plant_name` and `symptoms`.
    """
    # Build regex pattern to search words; this is a direct replacement of the old approach
    terms = re.findall(r'\w+', symptoms.lower())
    if not terms:
        return None
    pattern = '|'.join(terms)
    query = """
        SELECT plant_name, symptoms, herbs, recommendations, precautions
        FROM remedies
        WHERE LOWER(symptoms) REGEXP %s OR LOWER(plant_name) REGEXP %s
        LIMIT 10
    """
    cursor.execute(query, (pattern, pattern))
    rows = cursor.fetchall()
    if rows:
        # Format similar to old function expected output (string)
        response_parts = []
        for r in rows:
            # r is a tuple or dict depending on cursor config; here we expect tuple
            if isinstance(r, dict):
                plant = r.get('plant_name', '')
                sym = r.get('symptoms', '')
                herbs = r.get('herbs', '')
                rec = r.get('recommendations', '')
                prec = r.get('precautions', '')
            else:
                plant, sym, herbs, rec, prec = r
            response_parts.append(f"For {plant}:\nRecommended herbs: {herbs}\nTreatment recommendations:\n{rec}\n")
            if prec:
                response_parts.append(f"Precautions: {prec}\n")
            response_parts.append("---\n")
        return "\n".join(response_parts)
    return None

# -------------------- Chat API and message processing --------------------
@app.route('/api/chat', methods=['POST'])
def chat_api():
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id')
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400

        # Ensure user is logged in
        user_email = session.get('user_email')
        if not user_email:
            return jsonify({'error': 'User not logged in'}), 403

        # Process message and generate bot response
        bot_response = process_message(user_message)

        # Save conversation to DB
        try:
            used_session_id = save_chat_message(user_email, user_message, bot_response, session_id=session_id)
        except Exception as e:
            # Log but continue; chat can still return
            logger.error("Failed to save chat history: %s", e)
            used_session_id = session_id

        return jsonify({'response': bot_response, 'session_id': used_session_id})

    except Exception as e:
        logger.error("Error in chat_api: %s", e)
        return jsonify({'error': 'I apologize, but I encountered an error. Please try again.'}), 500

def process_message(user_message):
    try:
        config = MYSQL_CONFIG.copy()
        config['database'] = 'arogya_db'
        cnx = mysql.connector.connect(**config)
        cursor = cnx.cursor(buffered=True, dictionary=True)

        message = user_message.lower().strip()

        # 🌿 GREETING DETECTION
        if any(greet in message for greet in ['hi', 'hello', 'hey', 'namaste']):
            return (
                "🙏 Namaste! I’m your Ayurvedic health assistant.\n\n"
                "You can ask me things like:\n"
                "• Remedies for fever, cold, or cough\n"
                "• How to boost immunity\n"
                "• Tell me about Turmeric or Ashwagandha\n"
                "• Natural solutions for digestion or stress"
            )

        # 🍃 CHECK DATABASE FOR HERB OR SYMPTOM
        cursor.execute("""
            SELECT plant_name, symptoms, herbs, recommendations, precautions
            FROM remedies
            WHERE LOWER(plant_name) LIKE %s
               OR LOWER(symptoms) LIKE %s
               OR LOWER(herbs) LIKE %s
               OR LOWER(recommendations) LIKE %s
        """, (f"%{message}%", f"%{message}%", f"%{message}%", f"%{message}%"))
        results = cursor.fetchall()

        if results:
            response = "🌿 Based on your query, here are some Ayurvedic remedies:\n\n"
            for r in results[:5]:
                response += f"🪴 **{r['plant_name']}**\n"
                if r['symptoms']:
                    response += f"• Used for: {r['symptoms']}\n"
                if r['herbs']:
                    response += f"• Contains herbs: {r['herbs']}\n"
                if r['recommendations']:
                    response += f"• Recommendation: {r['recommendations']}\n"
                if r['precautions']:
                    response += f"⚠️ Precautions: {r['precautions']}\n"
                response += "\n"
            return response.strip()

        # 🌡 FEVER HANDLING
        if "fever" in message:
            return (
                "🌡 **Ayurvedic Remedies for Fever:**\n\n"
                "🌿 **Tulsi (Holy Basil)** – Reduces fever and clears toxins.\n"
                "🌿 **Guduchi (Giloy)** – Known as ‘Amrita’, boosts immunity.\n"
                "🌿 **Turmeric** – Anti-inflammatory and helps fight infection.\n\n"
                "💧 Drink warm water and herbal tea with ginger & honey."
            )

        # 🤧 COUGH OR COLD
        if "cough" in message or "cold" in message:
            return (
                "😷 **Ayurvedic Remedies for Cough & Cold:**\n\n"
                "🌿 **Tulsi + Honey** – Soothes throat and clears mucus.\n"
                "🌿 **Turmeric milk (Haldi Doodh)** – Natural anti-inflammatory.\n"
                "🌿 **Licorice Root (Yashtimadhu)** – Relieves sore throat.\n\n"
                "💡 Avoid cold food, drink warm water, and rest well."
            )

        # 💪 IMMUNITY BOOST
        if "immunity" in message or "boost immunity" in message:
            return (
                "💪 **To naturally boost immunity:**\n\n"
                "🌿 **Ashwagandha** – Reduces stress & enhances strength.\n"
                "🌿 **Turmeric** – Antioxidant and anti-inflammatory.\n"
                "🌿 **Amla (Indian Gooseberry)** – Rich in Vitamin C.\n"
                "🌿 **Tulsi (Holy Basil)** – Fights infections.\n\n"
                "🧘 Tips: Eat freshly cooked food, meditate daily, and sleep well."
            )

        # 🥴 INDIGESTION / STOMACH ISSUES
        if any(word in message for word in ["indigestion", "digestion", "stomach", "bloating"]):
            return (
                "🥗 **Ayurvedic Remedies for Digestion:**\n\n"
                "🌿 **Triphala** – Aids digestion and detoxifies the gut.\n"
                "🌿 **Ginger** – Stimulates digestive fire (Agni).\n"
                "🌿 **Cumin + Fennel Tea** – Reduces gas and bloating.\n\n"
                "💡 Eat warm meals, avoid overeating, and stay hydrated."
            )

        # 😫 STRESS / ANXIETY
        if any(word in message for word in ["stress", "anxiety", "tension"]):
            return (
                "🧘 **Ayurvedic Remedies for Stress & Anxiety:**\n\n"
                "🌿 **Ashwagandha** – Reduces cortisol & promotes calm.\n"
                "🌿 **Brahmi** – Enhances focus and mental clarity.\n"
                "🌿 **Jatamansi** – Natural mood stabilizer.\n\n"
                "💤 Practice deep breathing, yoga, and maintain 7–8 hrs sleep."
            )

        # 🌿 SPECIFIC HERBS
        for herb in ["turmeric", "ashwagandha", "tulsi", "amla", "brahmi", "triphala"]:
            if herb in message:
                herb_info = {
                    "turmeric": (
                        "🌿 **Turmeric (Curcuma longa)**\n\n"
                        "• Properties: Anti-inflammatory, antioxidant.\n"
                        "• Benefits: Helps with pain, immunity, and digestion.\n"
                        "• Usage: Add to food, or drink with warm milk.\n"
                        "• Precautions: Avoid excess if you have gallstones."
                    ),
                    "ashwagandha": (
                        "🌿 **Ashwagandha (Withania somnifera)**\n\n"
                        "• Properties: Adaptogenic, stress reliever.\n"
                        "• Benefits: Improves energy, immunity, and focus.\n"
                        "• Usage: 1 tsp powder with milk or tablets daily.\n"
                        "• Precautions: Avoid if pregnant."
                    ),
                    "tulsi": (
                        "🌿 **Tulsi (Holy Basil)**\n\n"
                        "• Benefits: Treats cough, fever, and stress.\n"
                        "• Usage: Boil leaves in water and drink.\n"
                        "• Precautions: Avoid if you’re on blood-thinning medication."
                    ),
                    "amla": (
                        "🌿 **Amla (Indian Gooseberry)**\n\n"
                        "• Benefits: Boosts immunity and eye health.\n"
                        "• Usage: Eat raw or as juice daily.\n"
                        "• Precautions: Avoid mixing with milk immediately after."
                    ),
                    "brahmi": (
                        "🌿 **Brahmi (Bacopa monnieri)**\n\n"
                        "• Benefits: Enhances memory and reduces anxiety.\n"
                        "• Usage: 1 tsp powder or capsule daily.\n"
                        "• Precautions: Consult before using with antidepressants."
                    ),
                    "triphala": (
                        "🌿 **Triphala**\n\n"
                        "• Benefits: Supports digestion and detox.\n"
                        "• Usage: 1 tsp powder before bed with warm water.\n"
                        "• Precautions: Avoid overuse — may cause loose motions."
                    )
                }
                return herb_info[herb]

        # 🗣 DEFAULT RESPONSE
        return (
            "🤔 I couldn’t find a specific remedy for that.\n\n"
            "You can try asking:\n"
            "• Remedies for fever, stress, or cold\n"
            "• Tell me about Ashwagandha or Turmeric\n"
            "• How to boost immunity naturally"
        )

    except mysql.connector.Error as err:
        app.logger.error(f"MySQL error: {err}")
        return "⚠️ Database error — unable to fetch herbal remedies."
    except Exception as e:
        app.logger.error(f"Error processing message: {e}")
        return "⚠️ I faced an issue understanding your request. Please try again."
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'cnx' in locals() and cnx.is_connected():
            cnx.close()



# -------------------- Recommendation helpers kept from original --------------------
def get_recommendations(symptoms, conditions):
    """Return a short recommendations string using small rule dictionaries."""
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

    recommendations = []
    for s in symptoms:
        if s in symptom_herbs:
            recommendations.extend(symptom_herbs[s])
    for c in conditions:
        if c in condition_herbs:
            recommendations.extend(condition_herbs[c])
    recommendations = list(dict.fromkeys(recommendations))
    if not recommendations:
        return None
    response = "Based on your query, here are some recommended herbs:\n\n"
    for herb in recommendations:
        info = herbal_db.get(herb, {})
        response += f"- {herb}: {info.get('Benefits', 'Benefits not available')}\n"
    return response

def format_herb_info(herb):
    info = herbal_db.get(herb, {})
    if not info:
        return "I apologize, but I don't have detailed information about that herb."
    response = f"Here's what I know about {herb}:\n\n"
    for key, value in info.items():
        response += f"{key}: {value}\n"
    return response

def format_help_message():
    return ("I can help you with:\n"
            "- Information about Ayurvedic herbs\n"
            "- Common health concerns and remedies\n"
            "- Understanding your dosha type\n"
            "- General wellness advice\n\nFeel free to ask about specific herbs or health concerns!")

# -------------------- Run the app --------------------
if __name__ == '__main__':
    app.run(debug=True)
