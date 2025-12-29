from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify, send_from_directory
)
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
import uuid
import os
import io

# Google Drive
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# Sessions persistantes
from flask_session import Session

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "vocale.db")

SERVICE_ACCOUNT_FILE = "service_account.json"
SCOPES = ['https://www.googleapis.com/auth/drive.file']

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --------------------------------------------------
# APP
# --------------------------------------------------

app = Flask(__name__)
app.secret_key = "CHANGE_ME_SECRET_KEY"

# Sessions (PC + Mobile OK)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(BASE_DIR, "flask_sessions")
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

Session(app)

# --------------------------------------------------
# DB
# --------------------------------------------------

def connecter_sqlite():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# --------------------------------------------------
# AUTH DECORATOR
# --------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("logged"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# --------------------------------------------------
# GOOGLE DRIVE (SERVICE ACCOUNT)
# --------------------------------------------------

def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )
    return build('drive', 'v3', credentials=creds)

def upload_to_drive(file_content, filename, folder_id=None):
    service = get_drive_service()

    metadata = {"name": filename}
    if folder_id:
        metadata["parents"] = [folder_id]

    media = MediaIoBaseUpload(
        io.BytesIO(file_content),
        mimetype="text/plain",
        resumable=True
    )

    file = service.files().create(
        body=metadata,
        media_body=media,
        fields="id, webViewLink"
    ).execute()

    return file["id"], file["webViewLink"]

# --------------------------------------------------
# ROUTES
# --------------------------------------------------

@app.route("/")
@login_required
def accueil():
    return render_template(
        "index.html",
        username=session.get("username"),
        date=datetime.now().strftime("%Y-%m-%d")
    )

# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = connecter_sqlite()
        user = db.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        ).fetchone()
        db.close()

        if user and check_password_hash(user["password"], password):
            session["logged"] = True
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("accueil"))

        flash("Identifiants incorrects")

    return render_template("login.html")

# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        confirm = request.form["confirm"]

        if password != confirm:
            flash("Mot de passe différent")
            return redirect(url_for("register"))

        db = connecter_sqlite()
        try:
            db.execute(
                "INSERT INTO users(username,password,role) VALUES (?,?,?)",
                (username, generate_password_hash(password), "user")
            )
            db.commit()
            flash("Compte créé")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Utilisateur existe déjà")
        finally:
            db.close()

    return render_template("register.html")

# ---------------- UPLOAD ----------------

@app.route("/upload", methods=["POST"])
@login_required
def upload():
    uploaded_file = request.files.get("file")
    if not uploaded_file:
        return jsonify({"error": "Aucun fichier"}), 400

    rec = request.form.get("rec", "")
    recs = request.form.get("recs", "")
    nom_client = request.form.get("nom_client", "")
    date_fact = request.form.get("date_fact", "")

    def clean(s):
        return "".join(c if c.isalnum() or c in " -_" else "_" for c in s)

    prefix = "VENTE" if "vente" in recs.lower() else "ACHAT"
    filename = f"{prefix}_{clean(rec)}_{clean(nom_client)}_{clean(date_fact)}.txt"

    content = uploaded_file.read()

    file_id, link = upload_to_drive(content, filename)

    return jsonify({
        "success": True,
        "filename": filename,
        "file_id": file_id,
        "link": link
    })

# --------------------------------------------------
# API (CLIENT / ARTICLE)
# --------------------------------------------------

@app.route("/get_client")
def get_client():
    code = request.args.get("code", "").strip().upper()
    db = connecter_sqlite()
    row = db.execute(
        "SELECT nom_client FROM correspondance_client WHERE code=?",
        (code,)
    ).fetchone()
    db.close()
    return jsonify({"nom": row["nom_client"] if row else ""})

@app.route("/get_article")
def get_article():
    code = request.args.get("code", "").strip().upper()
    db = connecter_sqlite()
    row = db.execute(
        "SELECT reference,designation FROM correspondance_article WHERE code=?",
        (code,)
    ).fetchone()
    db.close()
    return jsonify(row or {"reference": "", "designation": ""})

# --------------------------------------------------
# INIT DB
# --------------------------------------------------

def init_db():
    db = connecter_sqlite()

    db.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS reset_tokens(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            token TEXT UNIQUE,
            expires_at DATETIME
        )
    """)

    db.commit()
    db.close()

# --------------------------------------------------
# MAIN
# --------------------------------------------------

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
