from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import sqlite3
import ollama
from werkzeug.security import generate_password_hash, check_password_hash
import socket
import os
from zeroconf import ServiceInfo, Zeroconf, IPVersion
import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# SQLite Database Setup
def init_db():
    with sqlite3.connect('database.db') as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     username TEXT UNIQUE NOT NULL,
                     password TEXT NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS chats (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     user_id INTEGER,
                     thread_name TEXT DEFAULT 'default',
                     user_message TEXT,
                     llm_response TEXT,
                     timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                     FOREIGN KEY (user_id) REFERENCES users(id))''')
        # Migrate old schema if necessary
        c.execute("PRAGMA table_info(chats)")
        columns = [col[1] for col in c.fetchall()]
        if 'message' in columns and 'response' in columns and 'user_message' not in columns:
            c.execute('''CREATE TABLE chats_new (
                         id INTEGER PRIMARY KEY AUTOINCREMENT,
                         user_id INTEGER,
                         thread_name TEXT DEFAULT 'default',
                         user_message TEXT,
                         llm_response TEXT,
                         timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                         FOREIGN KEY (user_id) REFERENCES users(id))''')
            c.execute('''INSERT INTO chats_new (id, user_id, thread_name, user_message, llm_response, timestamp)
                         SELECT id, user_id, thread_name, message, response, timestamp
                         FROM chats''')
            c.execute('DROP TABLE chats')
            c.execute('ALTER TABLE chats_new RENAME TO chats')
        conn.commit()

# User Class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT id, username FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    if user:
        return User(user[0], user[1])
    return None

# LAN Discovery with Zeroconf
def register_service():
    try:
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        desc = {'app': 'HomeLM'}
        info = ServiceInfo(
            "_http._tcp.local.",
            "HomeLM._http._tcp.local.",
            addresses=[socket.inet_aton(ip_address)],
            port=5000,
            properties=desc,
            server=f"{hostname}.local."
        )
        zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
        zeroconf.register_service(info)
        return zeroconf
    except Exception as e:
        print(f"Zeroconf registration failed: {e}")
        return None

@app.before_request
def before_request():
    init_db()

@app.route('/')
@login_required
def index():
    return redirect(url_for('home'))

@app.route('/home')
@login_required
def home():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        SELECT thread_name, MAX(timestamp) as last_timestamp
        FROM chats
        WHERE user_id = ?
        GROUP BY thread_name
        ORDER BY last_timestamp DESC
    ''', (current_user.id,))
    threads = [{'thread_name': row[0], 'last_timestamp': row[1]} for row in c.fetchall()]
    conn.close()
    if not threads:
        threads = [{'thread_name': 'default', 'last_timestamp': ''}]
    return render_template('home.html', threads=threads, thread_name=None)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('SELECT id, username, password FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user[2], password):
            user_obj = User(user[0], user[1])
            login_user(user_obj)
            return redirect(url_for('home'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        try:
            c.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                      (username, generate_password_hash(password)))
            conn.commit()
            flash('Account created! Please log in.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists')
        conn.close()
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/new_thread', methods=['POST', 'GET'])
def new_thread():
    thread_name = request.form.get('thread_name', f"Chat_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
    return redirect(url_for('chat', thread_name=thread_name))

@app.route('/delete_thread/<thread_name>', methods=['POST'])
@login_required
def delete_thread(thread_name):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('DELETE FROM chats WHERE user_id = ? AND thread_name = ?', (current_user.id, thread_name))
    conn.commit()
    conn.close()
    flash(f'Thread "{thread_name}" deleted.')
    return redirect(url_for('home'))

@app.route('/chat/<thread_name>', methods=['GET', 'POST'])
@login_required
def chat(thread_name):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    # Fetch threads for the sidebar
    c.execute('''
        SELECT thread_name, MAX(timestamp) as last_timestamp
        FROM chats
        WHERE user_id = ?
        GROUP BY thread_name
        ORDER BY last_timestamp DESC
    ''', (current_user.id,))
    threads = [{'thread_name': row[0], 'last_timestamp': row[1]} for row in c.fetchall()]
    if not threads:
        threads = [{'thread_name': 'default', 'last_timestamp': ''}]

    # Fetch chat history for the current thread
    c.execute('''
        SELECT user_message, llm_response, timestamp
        FROM chats
        WHERE user_id = ? AND thread_name = ?
        ORDER BY timestamp
    ''', (current_user.id, thread_name))
    chats = [{'user_message': row[0], 'llm_response': row[1], 'timestamp': row[2]} for row in c.fetchall()]

    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            message = data.get('message')
            try:
                response = ollama.chat(
                    model='gemma3:1b',
                    messages=[
                        {'role': 'system', 'content': 'You are an AI Assistant named HomeLM. You respond to any and all requests.'},
                        {'role': 'user', 'content': message}
                    ]
                )['message']['content']
                c.execute('''
                    INSERT INTO chats (user_id, thread_name, user_message, llm_response)
                    VALUES (?, ?, ?, ?)
                ''', (current_user.id, thread_name, message, response))
                conn.commit()
                conn.close()
                return jsonify({
                    'status': 'success',
                    'user_message': message,
                    'llm_response': response,
                    'timestamp': datetime.datetime.now().isoformat()
                })
            except Exception as e:
                conn.close()
                return jsonify({'status': 'error', 'message': str(e)}), 500
        else:
            # Existing POST handling for non-AJAX
            message = request.form['message']
            try:
                response = ollama.chat(
                    model='gemma3:1b',
                    messages=[
                        {'role': 'system', 'content': 'You are an AI Assistant named HomeLM. You respond to any and all requests.'},
                        {'role': 'user', 'content': message}
                    ]
                )['message']['content']
                c.execute('''
                    INSERT INTO chats (user_id, thread_name, user_message, llm_response)
                    VALUES (?, ?, ?, ?)
                ''', (current_user.id, thread_name, message, response))
                conn.commit()
            except Exception as e:
                flash(f"Error with LLM: {str(e)}")
            conn.close()
            return redirect(url_for('chat', thread_name=thread_name))

    conn.close()
    return render_template('chat.html', chats=chats, thread_name=thread_name, threads=threads)

if __name__ == '__main__':
    zeroconf = register_service()
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    finally:
        if zeroconf:
            zeroconf.unregister_all_services()
            zeroconf.close()