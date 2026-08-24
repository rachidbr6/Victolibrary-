from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
import traceback

import mysql.connector.locales.eng

app = Flask(__name__)
app.secret_key = "super_secret_key"


@app.errorhandler(Exception)
def handle_exception(e):
    return f"<pre>{traceback.format_exc()}</pre>", 500

# Connexion à la base MySQL
def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="library",
        auth_plugin='mysql_native_password',
        use_pure=True
    )
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="library",
    auth_plugin='mysql_native_password',
    use_pure=True,
    charset='utf8',           # option d’encodage
    use_unicode=True
)

# Initialisation DB
def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            author VARCHAR(255),
            total_pages INT,
            current_page INT DEFAULT 1,
            is_favorite BOOLEAN DEFAULT FALSE
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

init_db()

# Middleware login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# Liste des PDF
def get_available_books():
    folder = os.path.join('static', 'books')
    if not os.path.exists(folder):
        os.makedirs(folder)
    return [f for f in os.listdir(folder) if f.endswith('.pdf')]

# === Routes ===
@app.route('/')
@login_required
def index():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books")
    books = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("index.html", books=books, available_books=get_available_books(), username=session["username"])

@app.route('/add', methods=['POST'])
@login_required
def add_book():
    title = request.form['title']
    author = request.form.get('author', '')
    total_pages = request.form.get('total_pages') or 0
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO books (title, author, total_pages) VALUES (%s, %s, %s)", (title, author, total_pages))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/add_from_list', methods=['POST'])
@login_required
def add_from_list():
    title = request.form['title']
    author = ""
    total_pages = 0
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO books (title, author, total_pages) VALUES (%s, %s, %s)", (title, author, total_pages))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/update/<int:book_id>', methods=['POST'])
@login_required
def update_progress(book_id):
    current_page = request.form['current_page']
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE books SET current_page = %s WHERE id = %s", (current_page, book_id))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/delete/<int:book_id>')
@login_required
def delete_book(book_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM books WHERE id = %s", (book_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/favorite/<int:book_id>')
@login_required
def toggle_favorite(book_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE books SET is_favorite = NOT is_favorite WHERE id = %s", (book_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('index'))

@app.route('/read/<int:book_id>')
@login_required
def read_book(book_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT title, current_page FROM books WHERE id = %s", (book_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if result:
        title, current_page = result
        return jsonify({"title": title, "current_page": current_page})
    else:
        return jsonify({"error": "Livre non trouvé"}), 404

@app.route('/update_page/<int:book_id>', methods=['POST'])
@login_required
def update_page(book_id):
    data = request.get_json()
    page = data.get('page', 1)
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE books SET current_page = %s WHERE id = %s", (page, book_id))
        conn.commit()
        return jsonify({"message": "Progress updated", "page": page})
    except mysql.connector.Error as err:
        return jsonify({"error": str(err)}), 500
    finally:
        cursor.close()
        conn.close()

# Authentification
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, password FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user[1], password):
            session["user_id"] = user[0]
            session["username"] = username
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Identifiants incorrects")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            return render_template("register.html", error="Les mots de passe ne correspondent pas")

        hashed_password = generate_password_hash(password)
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
            conn.commit()
        except mysql.connector.IntegrityError:
            return render_template("register.html", error="Nom d’utilisateur déjà pris")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for("login"))

    return render_template("register.html")

# Lancer le serveur même si exécuté par run_desktop.py
def start_app():
    app.run(debug=True, use_reloader=False)

if __name__ == '__main__':
    start_app()
