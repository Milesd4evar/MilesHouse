from flask import Flask, request, jsonify, session, render_template
from flask_cors import CORS
import requests
import os
import json
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from datetime import datetime
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your_secret_key')

# DeepSeek API configuration
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_API_URL = os.environ.get('DEEPSEEK_API_URL', 'https://api.deepseek.com/v1/chat/completions')

# Database setup
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        usage_count INTEGER DEFAULT 0,
        usage_limit INTEGER DEFAULT 100
    )
    ''')
    
    conn.execute('''
    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        title TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    conn.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (conversation_id) REFERENCES conversations (id)
    )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Routes
@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    if not username or not email or not password:
        return jsonify({'error': 'Missing fields'}), 400
    
    # Hash the password
    hashed_password = generate_password_hash(password)
    
    # Insert user into database
    conn = get_db_connection()
    try:
        user_id = str(uuid.uuid4())
        conn.execute(
            'INSERT INTO users (id, username, email, password) VALUES (?, ?, ?, ?)',
            (user_id, username, email, hashed_password)
        )
        conn.commit()
        
        # Set session
        session['user_id'] = user_id
        session['username'] = username
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'username': username
        })
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username or email already exists'}), 400
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'error': 'Missing fields'}), 400
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    
    if user and check_password_hash(user['password'], password):
        # Set session
        session['user_id'] = user['id']
        session['username'] = user['username']
        
        return jsonify({
            'success': True,
            'user_id': user['id'],
            'username': user['username']
        })
    else:
        return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/user', methods=['GET'])
def get_user():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    conn = get_db_connection()
    user = conn.execute('SELECT id, username, email, usage_count, usage_limit FROM users WHERE id = ?', 
                       (session['user_id'],)).fetchone()
    conn.close()
    
    if user:
        return jsonify({
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'usage_count': user['usage_count'],
            'usage_limit': user['usage_limit']
        })
    else:
        session.clear()
        return jsonify({'error': 'User not found'}), 404

@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    conn = get_db_connection()
    conversations = conn.execute(
        'SELECT * FROM conversations WHERE user_id = ? ORDER BY created_at DESC',
        (session['user_id'],)
    ).fetchall()
    conn.close()
    
    result = []
    for conv in conversations:
        result.append({
            'id': conv['id'],
            'title': conv['title'],
            'created_at': conv['created_at']
        })
    
    return jsonify(result)

@app.route('/api/conversations', methods=['POST'])
def create_conversation():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.json
    title = data.get('title', 'New Conversation')
    
    conversation_id = str(uuid.uuid4())
    
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO conversations (id, user_id, title) VALUES (?, ?, ?)',
        (conversation_id, session['user_id'], title)
    )
    conn.commit()
    conn.close()
    
    return jsonify({
        'id': conversation_id,
        'title': title,
        'created_at': datetime.now().isoformat()
    })

@app.route('/api/conversations/<conversation_id>/messages', methods=['GET'])
def get_messages(conversation_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    conn = get_db_connection()
    # First verify the conversation belongs to the user
    conv = conn.execute(
        'SELECT * FROM conversations WHERE id = ? AND user_id = ?',
        (conversation_id, session['user_id'])
    ).fetchone()
    
    if not conv:
        conn.close()
        return jsonify({'error': 'Conversation not found'}), 404
    
    messages = conn.execute(
        'SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at',
        (conversation_id,)
    ).fetchall()
    conn.close()
    
    result = []
    for msg in messages:
        result.append({
            'id': msg['id'],
            'role': msg['role'],
            'content': msg['content'],
            'created_at': msg['created_at']
        })
    
    return jsonify(result)

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message')
    
    if not message:
        return jsonify({'error': 'Missing message'}), 400
    
    # Call DeepSeek API
    try:
        response = requests.post(
            DEEPSEEK_API_URL,
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are StudyAI, a helpful AI assistant for students. Provide clear, concise, and accurate information to help with homework, studying, and understanding academic concepts."
                    },
                    {
                        "role": "user",
                        "content": message
                    }
                ]
            }
        )
        
        response_data = response.json()
        print("DeepSeek API Response:", response_data)  # Print the full response for debugging
        
        # More robust way to access the response
        if 'choices' in response_data and len(response_data['choices']) > 0:
            if 'message' in response_data['choices'][0] and 'content' in response_data['choices'][0]['message']:
                ai_response = response_data['choices'][0]['message']['content']
            else:
                ai_response = "Sorry, I could not generate a proper response."
        else:
            # If we can't find the expected structure, try to extract any error message
            ai_response = response_data.get('error', {}).get('message', "Sorry, I could not process your request.")
        
        return jsonify({
            'content': ai_response
        })
        
    except Exception as e:
        print(f"API Error: {str(e)}")
        return jsonify({'error': 'Failed to get response from AI service', 'details': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)