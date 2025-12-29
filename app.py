from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify,send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from flask_login import login_required, current_user
from flask import render_template
import uuid
import os,io
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseUpload
import pickle

app = Flask(__name__)
app.secret_key = "secret123"

DB_PATH = os.path.join(os.path.dirname(__file__), "vocale.db")
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged'):   # <== IMPORTANT !
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route("/logout")
def logout():
    session['logged'] = False
    session.pop('user', None)
    session.pop('articles', None)
    return redirect(url_for('login'))

@app.template_filter("milliers")
def milliers(value):
    try:
        return "{:,}".format(int(value)).replace(",", " ")
    except:
        return value

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        # Vérification champs
        if not username or not password:
            flash("Tous les champs sont obligatoires")
            return redirect(url_for("register"))

        if password != confirm:
            flash("Les mots de passe ne correspondent pas")
            return redirect(url_for("register"))

        db = connecter_sqlite()
        try:
            # Vérifier si utilisateur existe déjà
            user = db.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,)
            ).fetchone()

            if user:
                flash("Nom d'utilisateur déjà utilisé")
                return redirect(url_for("register"))

            # Création utilisateur
            db.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                (username, generate_password_hash(password), "user")
            )
            db.commit()

            flash("Compte créé avec succès, connectez-vous")
            return redirect(url_for("login"))

        finally:
            db.close()   # 🔴 TRÈS IMPORTANT

    return render_template("register.html")


def connecter_sqlite():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # accès par nom de colonne
    return conn

# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("Champs obligatoires")
            return render_template("login.html"), 400  # Bad Request

        db = connecter_sqlite()
        try:
            user = db.execute(
                "SELECT id, username, password, role FROM users WHERE username = ?",
                (username,)
            ).fetchone()
        finally:
            db.close()

        if user and check_password_hash(user["password"], password):
            session["logged"] = True
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            return redirect(url_for("accueil")), 302  # Redirection OK

        flash("Utilisateur ou mot de passe incorrect")
        return render_template("login.html"), 401  # Unauthorized

    return render_template("login.html"), 200

@app.template_filter("milliers")
def milliers(value):
    try:
        return "{:,}".format(int(value)).replace(",", " ")
    except:
        return value

# Dashboard facture
@app.route("/")
@login_required
def accueil():
    username = session.get('username', 'Invité')
    return render_template(
        'index.html',
        date=datetime.now().strftime('%Y-%m-%d'),
        username=username,
    )

@app.route('/get_client', methods=['GET'])
def get_client():
    # Récupération du paramètre code
    code = request.args.get('code', '')
    if not code:
        return jsonify({"nom": ""})

    conn = connecter_sqlite()
    cursor = conn.cursor()

    # Normalisation du code : majuscules + enlever espaces
    code_modifie = code.strip().upper().replace(' ', '')
    

    cursor.execute(
        "SELECT nom_client FROM correspondance_client WHERE code=?",
        (code_modifie,)
    )

    row = cursor.fetchone()
    if row:
        return jsonify({"nom": row["nom_client"]})
    else:
        return jsonify({"nom": ""})

@app.route('/get_article', methods=['GET'])
def get_article():
    code = request.args.get('code', '')
    if not code:
        return jsonify({"reference": "", "designation": ""})

    conn = connecter_sqlite()
    cursor = conn.cursor()

    # Normalisation
    code_modifie = code.strip().upper().replace(' ', '')

    cursor.execute(
        "SELECT reference, designation FROM correspondance_article WHERE code=?",
        (code_modifie,)
    )

    row = cursor.fetchone()
    conn.close()

    if row:
        return jsonify({
            "reference": row["reference"],
            "designation": row["designation"]
        })
    else:
        return jsonify({"reference": "", "designation": ""})

@app.route('/get_tsena', methods=['GET'])
def get_tsena():
     # Récupération du paramètre code
    code = request.args.get('code', '')
    if not code:
        return jsonify({
            "code_tsena": "",
            "depot": "",
            "affaire": "",
            "num_fact": ""
        })

    conn = connecter_sqlite()
    cursor = conn.cursor()

    # Normalisation du code : majuscules + enlever espaces
    code_modifie = code.strip().upper().replace(' ', '')

    cursor.execute(
        "SELECT code_tsena, depot, affaire FROM correspondance WHERE code=?",
        (code_modifie,)
    )

    row = cursor.fetchone()
    conn.close()

    # Vérification obligatoire
    if not row:
        return jsonify({
            "code_tsena": "",
            "depot": "",
            "affaire": "",
            "num_fact": ""
        })

    # ----- génération num_fact -----
    base_date = datetime.now()
    jour = base_date.day
    mois = base_date.month
    short_year = str(base_date.year)[-2:]

    # nettoyage depot
    t = row["depot"].replace("DP", "").lstrip("0")
    jour_clean = str(jour).lstrip("0")

    num_fact = f"{t}FA{jour_clean}{mois}{short_year}"

    # Retour JSON
    return jsonify({
        "code_tsena": row["code_tsena"],
        "depot": row["depot"],
        "affaire": row["affaire"],
        "num_fact": num_fact
    })
def get_drive_service():
    """
    Authentifie l'utilisateur et retourne le service Google Drive
    """
    creds = None
    
    # Charger le token sauvegardé si disponible
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # Si pas de credentials valides, demander l'authentification
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Rafraîchissement du token...")
            creds.refresh(Request())
        else:
            print("🔐 Première connexion - Une fenêtre de navigateur va s'ouvrir...")
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError(
                    "❌ Fichier 'credentials.json' non trouvé!\n"
                    "Téléchargez-le depuis Google Cloud Console et placez-le dans ce dossier."
                )
            
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            print("✅ Authentification réussie!")
        
        # Sauvegarder le token pour les prochaines utilisations
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
            print("💾 Token sauvegardé dans token.pickle")
    
    return build('drive', 'v3', credentials=creds)

def upload_to_drive(file_content, filename, folder_id=None, mime_type='text/plain'):
    """
    Upload un fichier sur Google Drive
    
    Args:
        file_content: Contenu du fichier (bytes)
        filename: Nom du fichier
        folder_id: ID du dossier cible (optionnel)
        mime_type: Type MIME du fichier
    
    Returns:
        tuple: (file_id, web_link)
    """
    try:
        service = get_drive_service()
        
        file_metadata = {'name': filename}
        
        # Si un dossier spécifique est défini
        if folder_id:
            file_metadata['parents'] = [folder_id]
        
        # Créer le média à uploader
        fh = io.BytesIO(file_content)
        media = MediaIoBaseUpload(fh, mimetype=mime_type, resumable=True)
        
        # Uploader le fichier
        print(f"📤 Upload de '{filename}' sur Google Drive...")
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink, createdTime'
        ).execute()
        
        print(f"✅ Fichier uploadé avec succès!")
        print(f"   ID: {file.get('id')}")
        print(f"   Lien: {file.get('webViewLink')}")
        
        return file.get('id'), file.get('webViewLink')
    
    except Exception as e:
        print(f"❌ Erreur lors de l'upload sur Drive: {str(e)}")
        raise

@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Route Flask pour uploader un fichier
    """
    try:
        # Récupérer le fichier
        uploaded_file = request.files.get('file')
        if not uploaded_file:
            return jsonify({"error": "Aucun fichier reçu"}), 400

        # Récupérer les métadonnées
        rec = request.form.get('rec', 'unknown')
        recs = request.form.get('recs', 'unknown')
        nom_client = request.form.get('nom_client', 'unknown')
        date_fact = request.form.get('date_fact', 'unknown')

        # Nettoyer le nom du fichier
        def clean(s):
            return "".join(c if c.isalnum() or c in (' ', '-', '_') else "_" for c in s)

        # Générer le nom du fichier
        if "vente" in recs.lower():
            filename = f"VENTE_{clean(rec)}_{clean(nom_client)}_{clean(date_fact)}.txt"
        else:
            filename = f"ACHAT_{clean(rec)}_{clean(nom_client)}_{clean(date_fact)}.txt"

        print(f"\n{'='*60}")
        print(f"📝 Nouveau fichier à uploader: {filename}")
        print(f"   Type: {recs}")
        print(f"   Client: {nom_client}")
        print(f"   Date: {date_fact}")
        print(f"{'='*60}")

        # Lire le contenu du fichier
        file_content = uploaded_file.read()
        
        # Upload sur Google Drive
        # OPTIONNEL: Remplacez None par l'ID d'un dossier spécifique
        folder_id = None  # Ex: '1a2b3c4d5e6f7g8h9i0j'
        file_id, web_link = upload_to_drive(
            file_content, 
            filename, 
            folder_id=folder_id
        )

        return jsonify({
            "success": True,
            "message": "Fichier enregistré sur Google Drive",
            "filename": filename,
            "file_id": file_id,
            "link": web_link
        }), 200

    except FileNotFoundError as e:
        print(f"❌ {str(e)}")
        return jsonify({"error": str(e)}), 500
    
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Erreur serveur: {str(e)}"}), 500

@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    db = connecter_sqlite()
    try:
        token_data = db.execute(
            "SELECT * FROM reset_tokens WHERE token = ?", (token,)
        ).fetchone()

        if not token_data:
            flash("Lien invalide")
            return redirect(url_for("login"))

        if datetime.fromisoformat(token_data["expires_at"]) < datetime.now():
            flash("Lien expiré")
            return redirect(url_for("login"))

        if request.method == "POST":
            password = request.form.get("password")
            confirm = request.form.get("confirm")
            if password != confirm:
                flash("Les mots de passe ne correspondent pas")
                return redirect(url_for("reset_password", token=token))

            db.execute(
                "UPDATE users SET password = ? WHERE id = ?",
                (generate_password_hash(password), token_data["user_id"])
            )
            db.execute(
                "DELETE FROM reset_tokens WHERE id = ?", (token_data["id"],)
            )
            db.commit()
            flash("Mot de passe réinitialisé avec succès")
            return redirect(url_for("login"))

    finally:
        db.close()

    return render_template("reset_password.html")

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        if not username:
            flash("Veuillez entrer votre nom d'utilisateur")
            return redirect(url_for("forgot_password"))

        db = connecter_sqlite()
        try:
            user = db.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone()
            
            if not user:
                flash("Utilisateur non trouvé")
                return redirect(url_for("forgot_password"))

            # Générer token unique
            token = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(hours=1)

            db.execute(
                "INSERT INTO reset_tokens (user_id, token, expires_at) VALUES (?, ?, ?)",
                (user["id"], token, expires_at)
            )
            db.commit()

            # Ici on "simule" l'envoi d'email
            reset_link = url_for("reset_password", token=token, _external=True)
            flash(f"Lien de réinitialisation (simulation) : {reset_link}")
            return redirect(url_for("login"))

        finally:
            db.close()

    return render_template("forgot_password.html")

@app.route('/')
def index():
    return "Serveur OCR actif"

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Démarrage du serveur Flask...")
    print("="*60 + "\n")
    
    # Vérifier la présence de credentials.json
    if not os.path.exists('credentials.json'):
        print("⚠️  ATTENTION: credentials.json non trouvé!")
        print("   Téléchargez-le depuis Google Cloud Console")
        print("   et placez-le dans: D:\\Arbiochem\\Mahefa\\OCR\\en cours\\\n")
    
    app.run(debug=True, port=5000)

# Endpoint pour télécharger un fichier déjà enregistré
@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)


if __name__ == "__main__":
    db = connecter_sqlite()

    db.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'user'
    )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS reset_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token TEXT NOT NULL UNIQUE,
        expires_at DATETIME NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    """)

    db.commit()
    db.close()
    app.run(debug=True, host="0.0.0.0", port=5000)
