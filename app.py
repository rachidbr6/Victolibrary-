from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
import re
import traceback
import html
import requests
import ebooklib
from ebooklib import epub
from pypdf import PdfReader
from xhtml2pdf import pisa
from dotenv import load_dotenv

import mysql.connector.locales.eng

load_dotenv()

app = Flask(__name__)
app.secret_key = "super_secret_key"

# Project Gutenberg (public domain books) search API
GUTENDEX_API = "https://gutendex.com/books/"
HTTP_HEADERS = {"User-Agent": "Mozilla/5.0 (VictoLibrary book search)"}

# Big Book API (catalog search: covers, ratings, authors - metadata only, no files)
BIGBOOK_API_KEY = os.environ.get("BIGBOOK_API_KEY")
BIGBOOK_SEARCH_URL = "https://api.bigbookapi.com/search-books"


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
    cursor.execute("SHOW COLUMNS FROM books LIKE 'cover_url'")
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE books ADD COLUMN cover_url VARCHAR(500) DEFAULT NULL")
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

def sanitize_filename(name):
    name = re.sub(r'[\\/*?:"<>|]', "", name).strip()
    return name[:150] if name else "livre"

def fetch_cover_url(title, author=""):
    if not BIGBOOK_API_KEY or not title:
        return None
    try:
        resp = requests.get(
            BIGBOOK_SEARCH_URL,
            params={"query": f"{title} {author}".strip(), "api-key": BIGBOOK_API_KEY},
            timeout=8,
        )
        resp.raise_for_status()
        for entry in resp.json().get("books", []):
            book = entry[0] if isinstance(entry, list) and entry else entry
            if book and book.get("image"):
                return book["image"]
    except requests.RequestException:
        pass
    return None

PDF_STYLE = """
<style>
  body { font-family: Helvetica, Arial, sans-serif; font-size: 11pt; line-height: 1.4; }
  a { color: inherit; text-decoration: none; }
  h1, h2, h3 { color: #222; }
</style>
"""

def _extract_body(html_bytes):
    text = html_bytes.decode('utf-8', errors='ignore')
    match = re.search(r'<body[^>]*>(.*?)</body>', text, re.DOTALL | re.IGNORECASE)
    return match.group(1) if match else text

def convert_epub_to_pdf(epub_path, pdf_path):
    book = epub.read_epub(epub_path)
    chapters = [
        _extract_body(item.get_content())
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT)
    ]
    page_break = '<div style="page-break-before: always;"></div>'
    full_html = f"<html><head>{PDF_STYLE}</head><body>{page_break.join(chapters)}</body></html>"
    with open(pdf_path, 'wb') as f:
        result = pisa.CreatePDF(full_html, dest=f)
    return not result.err

def convert_txt_to_pdf(txt_path, pdf_path):
    with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()
    escaped = html.escape(text)
    full_html = f"<html><head>{PDF_STYLE}</head><body><pre style='white-space:pre-wrap;font-family:monospace;font-size:9pt;'>{escaped}</pre></body></html>"
    with open(pdf_path, 'wb') as f:
        result = pisa.CreatePDF(full_html, dest=f)
    return not result.err

# === Routes ===

@app.route('/search_books')
@login_required
def search_books():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({"results": []})

    try:
        resp = requests.get(
            GUTENDEX_API,
            params={"search": query},
            headers=HTTP_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException:
        return jsonify({"error": "Service de recherche indisponible, réessaie dans un instant."}), 502

    results = []
    for item in data.get("results", [])[:15]:
        formats = item.get("formats", {})
        download_url = (
            formats.get("application/epub+zip")
            or formats.get("text/plain; charset=utf-8")
            or formats.get("text/plain; charset=us-ascii")
        )
        if not download_url:
            continue
        authors = ", ".join(a.get("name", "") for a in item.get("authors", [])) or "Auteur inconnu"
        results.append({
            "title": item.get("title", "Sans titre"),
            "author": authors,
            "download_url": download_url,
        })

    return jsonify({"results": results})

@app.route('/search_catalog')
@login_required
def search_catalog():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({"results": []})

    if not BIGBOOK_API_KEY:
        return jsonify({"error": "Clé API Big Book manquante côté serveur."}), 500

    try:
        resp = requests.get(
            BIGBOOK_SEARCH_URL,
            params={"query": query, "api-key": BIGBOOK_API_KEY},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException:
        return jsonify({"error": "Service de recherche indisponible, réessaie dans un instant."}), 502

    results = []
    for entry in data.get("books", [])[:15]:
        book = entry[0] if isinstance(entry, list) and entry else entry
        if not book:
            continue
        authors = ", ".join(a.get("name", "") for a in book.get("authors", [])) or "Auteur inconnu"
        results.append({
            "title": book.get("title", "Sans titre"),
            "author": authors,
            "image": book.get("image"),
            "rating": book.get("rating", {}).get("average"),
        })

    return jsonify({"results": results})

@app.route('/add_from_catalog', methods=['POST'])
@login_required
def add_from_catalog():
    data = request.get_json() or {}
    title = (data.get("title") or "").strip()
    author = (data.get("author") or "").strip()
    cover_url = (data.get("image") or "").strip() or None

    if not title:
        return jsonify({"error": "Titre manquant"}), 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO books (title, author, total_pages, cover_url) VALUES (%s, %s, %s, %s)",
        (title, author, 0, cover_url),
    )
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"success": True})

@app.route('/download_book', methods=['POST'])
@login_required
def download_book():
    data = request.get_json() or {}
    url = data.get("url")
    title = data.get("title") or "Livre"
    author = data.get("author", "")

    if not url:
        return jsonify({"error": "URL manquante"}), 400

    if ".epub" in url.lower():
        ext = ".epub"
    elif ".txt" in url.lower():
        ext = ".txt"
    else:
        ext = ".epub"

    folder = os.path.join('static', 'books')
    if not os.path.exists(folder):
        os.makedirs(folder)

    base_name = sanitize_filename(title)
    source_path = os.path.join(folder, base_name + ext)

    try:
        file_resp = requests.get(url, headers=HTTP_HEADERS, timeout=30)
        file_resp.raise_for_status()
        with open(source_path, 'wb') as f:
            f.write(file_resp.content)
    except requests.RequestException:
        return jsonify({"error": "Le téléchargement a échoué, réessaie."}), 502

    filename = os.path.basename(source_path)
    total_pages = 0

    pdf_path = os.path.join(folder, base_name + ".pdf")
    try:
        converted = (
            convert_epub_to_pdf(source_path, pdf_path) if ext == ".epub"
            else convert_txt_to_pdf(source_path, pdf_path)
        )
    except Exception:
        converted = False

    if converted:
        os.remove(source_path)
        filename = os.path.basename(pdf_path)
        try:
            total_pages = len(PdfReader(pdf_path).pages)
        except Exception:
            total_pages = 0

    cover_url = fetch_cover_url(title, author)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO books (title, author, total_pages, cover_url) VALUES (%s, %s, %s, %s)",
        (filename, author, total_pages, cover_url),
    )
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"success": True, "title": filename})

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
    cover_url = fetch_cover_url(title, author)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO books (title, author, total_pages, cover_url) VALUES (%s, %s, %s, %s)",
        (title, author, total_pages, cover_url),
    )
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
    cover_url = fetch_cover_url(title)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO books (title, author, total_pages, cover_url) VALUES (%s, %s, %s, %s)",
        (title, author, total_pages, cover_url),
    )
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
        file_path = os.path.join('static', 'books', title)
        has_file = os.path.isfile(file_path)
        return jsonify({"title": title, "current_page": current_page, "has_file": has_file})
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
