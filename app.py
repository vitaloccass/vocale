from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
import uuid
import os
import io
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseUpload
import pickle
import requests
import speech_recognition as sr

app = Flask(__name__)
app.secret_key = "secret123"  # CHANGEZ CETTE CLÉ EN PRODUCTION

DB_PATH = os.path.join(os.path.dirname(__file__), "vocale.db")
SCOPES = ['https://www.googleapis.com/auth/drive.file']
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")

# Créer le dossier uploads s'il n'existe pas
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def connecter_sqlite():
    """Connexion à la base de données SQLite"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    """Décorateur pour protéger les routes"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.template_filter("milliers")
def milliers(value):
    """Filtre pour formater les nombres avec des espaces"""
    try:
        return "{:,}".format(int(value)).replace(",", " ")
    except:
        return value

# ============= ROUTES D'AUTHENTIFICATION =============

@app.route("/register", methods=["GET", "POST"])
def register():
    """Inscription d'un nouvel utilisateur"""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        ctype = request.form.get("ctype", "")
        code_tsena = request.form.get("tsena", "")
        role = request.form.get("ctype", "")

        if not username or not password:
            flash("Tous les champs sont obligatoires")
            return redirect(url_for("register"))

        if password != confirm:
            flash("Les mots de passe ne correspondent pas")
            return redirect(url_for("register"))

        db = connecter_sqlite()
        try:
            user = db.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,)
            ).fetchone()

            if user:
                flash("Nom d'utilisateur déjà utilisé")
                return redirect(url_for("register"))

            db.execute(
                "INSERT INTO users (username, password, role,code_tsena) VALUES (?, ?, ?, ?)",
                (username, generate_password_hash(password), ctype,code_tsena)
            )
            db.commit()
            flash("Compte créé avec succès, connectez-vous")
            return redirect(url_for("login"))
        finally:
            db.close()

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Connexion utilisateur"""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
       
        if not username or not password:
            flash("Champs obligatoires")
            return render_template("login.html"), 400

        db = connecter_sqlite()
        try:
            user = db.execute(
                "SELECT id, username, password, role,code_tsena FROM users WHERE username = ?",
                (username,)
            ).fetchone()
        finally:
            db.close()

        if user and check_password_hash(user["password"], password):
            session["logged"] = True
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["type"] = user["role"]
            session["code_tsena"] = user["code_tsena"]
            return redirect(url_for("accueil"))

        flash("Utilisateur ou mot de passe incorrect")
        return render_template("login.html"), 401

    return render_template("login.html")

@app.route("/logout")
def logout():
    """Déconnexion"""
    session.clear()
    return redirect(url_for('login'))

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Demande de réinitialisation de mot de passe"""
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

            token = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(hours=1)

            db.execute(
                "INSERT INTO reset_tokens (user_id, token, expires_at) VALUES (?, ?, ?)",
                (user["id"], token, expires_at)
            )
            db.commit()

            reset_link = url_for("reset_password", token=token, _external=True)
            flash(f"Lien de réinitialisation : {reset_link}")
            return redirect(url_for("login"))
        finally:
            db.close()

    return render_template("forgot_password.html")

@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Réinitialisation du mot de passe"""
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

# ============= ROUTES PRINCIPALES =============

@app.route("/")
@login_required
def accueil():
    """Page d'accueil"""
    username = session.get('username', 'Invité')
    ctype = session.get('type', 'type')
    tsena = session.get('code_tsena', 'code_tsena')
    return render_template(
        'index.html',
        date=datetime.now().strftime('%Y-%m-%d'),
        username=username,
        type=ctype,
        tsena=tsena,
    )

# ============= API ENDPOINTS =============

@app.route('/get_tsena', methods=['GET'])
def get_tsena():
    """Récupérer les infos Tsena et générer le numéro de facture"""
    code = request.args.get('code', '')
    if not code:
        return jsonify({
            "code_tsena": "",
            "depot": "",
            "affaire": "",
            "nom_tsena": "",
            "num_fact": ""
        })

    conn = connecter_sqlite()
    try:
        code_modifie = code.strip().upper().replace(' ', '')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT code_tsena, depot, affaire,nom_tsena FROM correspondance WHERE code=?",
            (code_modifie,)
        )
        row = cursor.fetchone()

        if not row:
            return jsonify({
                "code_tsena": "",
                "depot": "",
                "affaire": "",
                "nom_tsena": "",
                "num_fact": ""
            })

        # Génération du numéro de facture
        base_date = datetime.now()
        jour = base_date.day
        mois = base_date.month
        short_year = str(base_date.year)[-2:]
        t = row["depot"].replace("DP", "").lstrip("0")
        jour_clean = str(jour).lstrip("0")
        num_fact = f"{t}FA{jour_clean}{mois}{short_year}"

        return jsonify({
            "code_tsena": row["code_tsena"],
            "depot": row["depot"],
            "affaire": row["affaire"],
            "nom_tsena": row["nom_tsena"],
            "num_fact": num_fact
        })
    finally:
        conn.close()

# ============= GOOGLE DRIVE =============

def get_drive_service():
    """Authentification et retour du service Google Drive"""
    creds = None
    
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Rafraîchissement du token...")
            creds.refresh(Request())
        else:
            print("🔐 Première connexion...")
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError(
                    "❌ Fichier 'credentials.json' non trouvé!"
                )
            
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            #creds = flow.run_local_server(port=0)
            creds = flow.run_local_server(port=8093)
            print("✅ Authentification réussie!")
        
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
            print("💾 Token sauvegardé")
    
    return build('drive', 'v3', credentials=creds)

def get_or_create_folder(service, folder_name, parent_id=None):
    """Cherche un dossier par nom, le crée s'il n'existe pas"""
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    
    if files:
        print(f"📁 Dossier existant trouvé : {folder_name}")
        return files[0]['id']
    else:
        print(f"📁 Création du dossier : {folder_name}")
        metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            metadata['parents'] = [parent_id]
        
        folder = service.files().create(body=metadata, fields='id').execute()
        return folder.get('id')

def upload_to_drive(file_content, filename, folder_id=None, mime_type='text/plain'):
    """Upload un fichier sur Google Drive"""
    try:
        service = get_drive_service()
        tsena = request.form.get('tsena', '0')

        # 📁 Dossier principal
        DOSSIER_PRINCIPAL = tsena  # ← changez le nom si vous voulez
        main_folder_id = get_or_create_folder(service, DOSSIER_PRINCIPAL)

        # 📅 Sous-dossier date du jour (format : 2026-02-17)
        date_today = datetime.now().strftime("%Y-%m-%d")
        date_folder_id = get_or_create_folder(service, date_today, parent_id=main_folder_id)

        # 📄 Upload du fichier dans le sous-dossier date
        file_metadata = {
            'name': filename,
            'parents': [date_folder_id]
        }

        fh = io.BytesIO(file_content)
        media = MediaIoBaseUpload(fh, mimetype=mime_type, resumable=True)

        print(f"📤 Upload de '{filename}' sur Google Drive...")

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, webViewLink, createdTime'
        ).execute()

        print(f"✅ Fichier uploadé avec succès!")
        print(f"   📁 Dossier : {DOSSIER_PRINCIPAL}/{date_today}/")
        print(f"   📄 Fichier : {filename}")
        print(f"   🔗 Lien : {file.get('webViewLink')}")

        return file.get('id'), file.get('webViewLink')

    except Exception as e:
        print(f"❌ Erreur lors de l'upload sur Drive: {str(e)}")
        raise

@app.route('/upload', methods=['POST'])
def upload_file():
    print("doudodu")
        
    try:
        
        uploaded_file = request.files.get('file')
        if not uploaded_file:
            return jsonify({"error": "Aucun fichier reçu"}), 400

        rec = request.form.get('rec', 'unknown')
        recs = request.form.get('recs', 'unknown')
        nom_client = request.form.get('nom_client', 'unknown')
        date_fact = request.form.get('date_fact', 'unknown')

        def clean(s):
            return "".join(c if c.isalnum() or c in (' ', '-', '_') else "_" for c in s)

        if "vente" in recs.lower():
            filename = f"VENTE_{clean(rec)}_{clean(nom_client)}_{clean(date_fact)}.txt"
        else:
            filename = f"ACHAT_{clean(rec)}_{clean(nom_client)}_{clean(date_fact)}.txt"

        
        print(f"\n{'='*60}")
        print(f"📝 Nouveau fichier: {filename}")
        print(f"   Type: {recs}")
        print(f"   Client: {nom_client}")
        print(f"   Date: {date_fact}")
        print(f"{'='*60}")

        file_content = uploaded_file.read()
        
        folder_id = None

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

@app.route('/download/<filename>')
def download_file(filename):
    """Télécharger un fichier"""
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

# ============= INITIALISATION DB =============

def init_db():
    """Initialiser la base de données"""
    db = connecter_sqlite()
    try:
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
            )
        """)

        db.commit()
        print("✅ Base de données initialisée")
    finally:
        db.close()

@app.route('/get_points', methods=['GET'])
def get_points(nom_tsena):
    url = f"https://api.fulleapps.io/points_of_sale"
    headers = {
        "X-Api-Key": "LwwMBbtNxMxvdMVcX4gXRVhscf5Q4K",
        "Authorization": "Mutual f585bd1e3b10f9a8eb7ac4c82f6478c6ae94d73a",
        "Connection": "keep-alive"
    }
    params = {
        "page": 1,
        "offset": 10000,
        "Limit": 10000,
        "all": 1,
        "name": nom_tsena
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        if data.get('list'):
            for item in data['list']:
                if item.get('name') == nom_tsena:
                    print(f"✅ Trouvé: {item.get('name')} - ID: {item.get('id')}")
                    return jsonify({"id": item.get('id')}), 200  # ✅ Retourner un objet JSON
            
            # ✅ Si aucun élément trouvé après la boucle
            print(f"❌ '{nom_tsena}' non trouvé")
            return jsonify({"error": f"Point de vente '{nom_tsena}' non trouvé"}), 404

        # ✅ Si data['list'] n'existe pas
        return jsonify({"error": "Aucune donnée disponible"}), 500
            
        # Si aucune donnée
        

    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_fournisseur', methods=['GET'])
def get_fournisseur():
    url = f"https://api.fulleapps.io/clients"
    headers = {
        "X-Api-Key": "LwwMBbtNxMxvdMVcX4gXRVhscf5Q4K",
        "Authorization": "Mutual f585bd1e3b10f9a8eb7ac4c82f6478c6ae94d73a",
        "Connection": "keep-alive"
    }
    params = {
        "page": 1,
        "offset": 10000,
        "Limit": 10000,
        "all": 1,
        "supplier":1
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        return jsonify(data), 200

    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_stock', methods=['GET'])
def get_stock():
    name_tsena = request.args.get('name_tsena', '').strip()
    url = f"https://api.fulleapps.io/products"
    headers = {
        "X-Api-Key": "LwwMBbtNxMxvdMVcX4gXRVhscf5Q4K",
        "Authorization": "Mutual f585bd1e3b10f9a8eb7ac4c82f6478c6ae94d73a",
        "Connection": "keep-alive"
    }
    params = {
        "page": 1,
        "offset": 10000,
        "Limit": 10000,
        "all": 1,
        #"id_point_of_sale": id_point_of_sale
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        # ✅ FILTRER les articles invalides côté serveur
        if 'list' in data and isinstance(data['list'], list):
            # ✅ Filtrer les valeurs vides
            articles_valides = [
                article for article in data['list']
                if article.get('name') and 
                article.get('id') and
                str(article.get('name')).strip() != '' and
                str(article.get('id')).strip() != ''
            ]
        
            # ✅ Éliminer les doublons par ID
            articles_uniques = {article['id']: article for article in articles_valides}
            data['list'] = list(articles_uniques.values())
            
            print(f"✅ {len(data['list'])} articles uniques")
        
        return jsonify(data), 200

    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_points')
def get_points_route():
    nom_tsena = request.args.get('name', '').strip()
    if not nom_tsena:
        return jsonify({"error": "Nom manquant"}), 400

    point_id = get_point_id(nom_tsena)
    if not point_id:
        return jsonify({"error": "Point non trouvé"}), 404

    return jsonify({"id": point_id}), 200

@app.route('/toggle_listening', methods=['POST'])
def toggle_listening():
    try:
        recognizer = sr.Recognizer()
        
        with sr.Microphone() as source:
            print("Écoute en cours...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=5)
        
        # Reconnaissance vocale
        text = recognizer.recognize_google(audio, language='fr-FR')
        
        return jsonify({
            'success': True,
            'text': text
        })
    
    except sr.WaitTimeoutError:
        return jsonify({
            'success': False,
            'error': 'Timeout: Aucun son détecté'
        })
    
    except sr.UnknownValueError:
        return jsonify({
            'success': False,
            'error': 'Impossible de comprendre l\'audio'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

def get_point_id(nom_tsena):
    url = "https://api.fulleapps.io/points_of_sale"
    headers = {
        "X-Api-Key": "LwwMBbtNxMxvdMVcX4gXRVhscf5Q4K",
        "Authorization": "Mutual f585bd1e3b10f9a8eb7ac4c82f6478c6ae94d73a",
    }
    params = {
        "page": 1,
        "offset": 10000,
        "limit": 10000,
        "all": 1,
        "name": nom_tsena
    }

    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()

        for item in data.get("list", []):
            if item.get("name") == nom_tsena:
                return item.get("id")

        return None
    except Exception as e:
        print(f"Erreur get_point_id({nom_tsena}) : {e}")
        return None
# ============= DÉMARRAGE ============= #

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Démarrage du serveur Flask...")
    print("="*60 + "\n")
    
    # Initialiser la base de données
    init_db()
    
    # Vérifier credentials.json
    if not os.path.exists('credentials.json'):
        print("⚠️  ATTENTION: credentials.json non trouvé!")
        print("   Téléchargez-le depuis Google Cloud Console\n")
    
    # Lancer l'application
    app.run(debug=True, host="0.0.0.0", port=5000)