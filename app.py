from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
import uuid
import os
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import requests
import json
from google.oauth2 import service_account
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow


app = Flask(__name__)
app.secret_key = "secret123"  # CHANGEZ CETTE CLÉ EN PRODUCTION

DB_PATH = os.path.join(os.path.dirname(__file__), "vocale.db")
SCOPES = ['https://www.googleapis.com/auth/gmail.send']
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")

# Créer le dossier uploads s'il n'existe pas
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

TURSO_URL = "https://vocale-vitaloccass.aws-ap-northeast-1.turso.io"
TURSO_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3NzcwMjA0MDgsImlkIjoiMDE5ZGJlYTEtM2EwMS03MmU2LWE2ZDgtN2ZmM2RkYzVlMTZhIiwicmlkIjoiY2JiOTcwYWUtYmQxOC00MjYzLTgzYzgtMTU4NDk0OGNiODk4In0.3qmHkcN6TVLTq7Kbql4hRevVfsB8nCMOMXlbsvslIb3P1Fe-mQeU9_v8aTxiONu8RrYhWfHywUu8X3-PA28PAQ"

headers = {
    "Authorization": f"Bearer {TURSO_TOKEN}",
    "Content-Type": "application/json"
}

#def connecter_sqlite():
#    """Connexion à la base de données SQLite"""
#    conn = sqlite3.connect(DB_PATH)
#    conn.row_factory = sqlite3.Row
#    return conn


def _turso_execute(sql, params=[]):
    args = [{"type": "text", "value": str(p)} for p in params]
    res = requests.post(
        f"{TURSO_URL}/v2/pipeline",
        headers=headers,
        json={"requests": [{"type": "execute", "stmt": {"sql": sql, "args": args}}]}
    )
    data = res.json()
    result = data["results"][0]["response"]["result"]
    cols = [c["name"] for c in result["cols"]]
    return [dict(zip(cols, [v["value"] for v in row])) for row in result["rows"]]

class TursoCursor:
    def __init__(self):
        self.results = []

    def execute(self, sql, params=[]):
        self.results = _turso_execute(sql, params)
        return self

    def fetchall(self):
        return self.results

    def fetchone(self):
        return self.results[0] if self.results else None

class TursoConnection:
    def cursor(self):
        return TursoCursor()

    def execute(self, sql, params=[]):
        c = TursoCursor()
        c.execute(sql, params)
        return c

    def commit(self):
        pass

    def close(self):
        pass

def connecter_sqlite():
    return TursoConnection()

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
    
            if(ctype=="admin"):
                db.execute(
                    "INSERT INTO users (username, password, role, code_tsena) VALUES (?, ?, ?, ?)",
                    (username, generate_password_hash(password), ctype, 'admin')
                )
                db.commit()
                flash("Compte créé avec succès, connectez-vous")
                return redirect(url_for("login"))
            else:
                db.execute(
                    "INSERT INTO users (username, password, role, code_tsena) VALUES (?, ?, ?, ?)",
                    (username, generate_password_hash(password), ctype, code_tsena)
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
                "SELECT id, username, password, role, code_tsena FROM users WHERE username = ?",
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

@app.route('/get_tsena')
def get_tsena():
    try:
        code = request.args.get('code', '')
        if not code:
            return jsonify({
                "code_tsena": "",
                "depot": "",
                "affaire": "",
                "nom_tsena": "",
                "souche": "",
                "num_fact": ""
            })

        conn = connecter_sqlite()
        code_modifie = code.strip().upper().replace(' ', '')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT code_tsena, depot, affaire, nom_tsena, souche FROM correspondance WHERE code=?",
            (code_modifie,)
        )
        row_correspondance = cursor.fetchone()

        if not row_correspondance:
            return jsonify({
                "code_tsena": "",
                "depot": "",
                "affaire": "",
                "nom_tsena": "",
                "souche": "",
                "num_fact": ""
            })

        base_date = datetime.now()
        jour = base_date.day
        mois = base_date.month
        short_year = str(base_date.year)[-2:]
        t = row_correspondance["depot"].replace("DP", "").lstrip("0")
        jour_clean = str(jour).lstrip("0")
        date_jour = f"{jour_clean}{mois}{short_year}"

        cursor.execute(
            "SELECT date, compteur FROM compteur WHERE code_tsena=?",
            (code_modifie,)
        )
        row_compteur = cursor.fetchone()

        if row_compteur["date"] != date_jour:
            # Nouveau jour → reset à 1
            compteur = 1
        else:
            # Même jour → incrémenter
            compteur = row_compteur["compteur"] + 1

        cursor.execute(
            "UPDATE compteur SET date=?, compteur=? WHERE code_tsena=?",
            (date_jour, compteur, code_modifie)
        )
        conn.commit()

        num_fact = f"{t}FA{date_jour}{compteur}"

        return jsonify({
            "code_tsena": row_correspondance["code_tsena"],
            "depot":      row_correspondance["depot"],
            "affaire":    row_correspondance["affaire"],
            "nom_tsena":  row_correspondance["nom_tsena"],
            "souche":     row_correspondance["souche"],
            "num_fact":   num_fact
        })

    except Exception as e:
        # ✅ Retourne l'erreur en JSON au lieu d'une page HTML 500
        return jsonify({"error": str(e)}), 500

# ============= GOOGLE DRIVE (SERVICE ACCOUNT - MOBILE COMPATIBLE) =============

def get_drive_service():
    creds_raw = os.environ.get("GOOGLE_CREDENTIALS", "")
    
    # ✅ Fix 1 : nettoie les guillemets parasites (cause du "Extra data" error)
    creds_raw = creds_raw.strip().strip("'").strip('"')
    
    if not creds_raw:
        raise ValueError("❌ Variable GOOGLE_CREDENTIALS manquante !")
    
    creds_dict = json.loads(creds_raw)
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=SCOPES
    )
    print("✅ Authentification Service Account réussie!")
    return build('drive', 'v3', credentials=credentials)

def get_or_create_folder(service, folder_name, parent_id=None, drive_id=None):
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    list_params = {
        "q": query,
        "fields": "files(id, name)",
        "supportsAllDrives": True,
        "includeItemsFromAllDrives": True,
    }
    if drive_id:
        list_params["corpora"] = "drive"
        list_params["driveId"] = drive_id

    results = service.files().list(**list_params).execute()
    files = results.get('files', [])

    if files:
        print(f"📁 Dossier existant : {folder_name}")
        return files[0]['id']

    print(f"📁 Création dossier : {folder_name}")
    metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
    }
    if parent_id:
        metadata['parents'] = [parent_id]

    folder = service.files().create(
        body=metadata,
        fields='id',
        supportsAllDrives=True
    ).execute()
    return folder.get('id')

def upload_to_supabase(file_content, filename, tsena):
    try:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        supabase = create_client(url, key)

        date_today = datetime.now().strftime("%Y-%m-%d")
        path = f"{tsena}/{date_today}/{filename}"

        supabase.storage.from_("vocale-files").upload(
            path=path,
            file=file_content,
            file_options={"content-type": "text/plain", "upsert": "true"}
        )

        link = supabase.storage.from_("vocale-files").create_signed_url(path, 86400)
        print(f"✅ Uploadé : {path}")
        return path, link['signedURL']

    except Exception as e:
        print(f"❌ Erreur Supabase: {str(e)}")
        raise

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        uploaded_file = request.files.get('file')
        if not uploaded_file:
            return jsonify({"error": "Aucun fichier reçu"}), 400

        rec = request.form.get('rec', 'unknown')
        recs = request.form.get('recs', 'unknown')
        nom_client = request.form.get('nom_client', 'unknown')
        date_fact = request.form.get('date_fact', 'unknown')
        nom_tsens = request.form.get('tsena', 'unknown')

        def clean(s):
            return "".join(c if c.isalnum() or c in (' ', '-', '_') else "_" for c in s)

        if "vente" in recs.lower():
            filename = f"VENTE_{clean(rec)}_{clean(nom_client)}_{clean(date_fact)}.txt"
        else:
            if "BC" in (recs):
                filename = f"BC_ACHAT_{clean(rec)}_{clean(nom_client)}_{clean(date_fact)}.txt"
            else:
                filename = f"FA_ACHAT_{clean(rec)}_{clean(nom_client)}_{clean(date_fact)}.txt"

        
        print(f"\n{'='*60}")
        print(f"📝 Nouveau fichier: {filename}")
        print(f"   Type: {recs}")
        print(f"   Client: {nom_client}")
        print(f"   Date: {date_fact}")
        print(f"{'='*60}")

        # ✅ 1. Créer le dossier temporaire si besoin
        temp_dir = os.path.join(os.path.dirname(__file__), "temp_uploads")
        os.makedirs(temp_dir, exist_ok=True)

        # ✅ 2. Sauvegarder le fichier uploadé sur le disque
        chemin_fichier = os.path.join(temp_dir, filename)
        uploaded_file.save(chemin_fichier)
        print(f"✅ Fichier sauvegardé : {chemin_fichier}")

        # ✅ 3. Envoyer avec le chemin complet
        envoyer_avec_pj("andrivolavita@gmail.com", nom_tsens, "Bonjour", chemin_fichier, filename)
        print("✅ Email envoyé avec succèsss")

        # ✅ 4. Supprimer le fichier temporaire après envoi
        os.remove(chemin_fichier)

        return jsonify({"success": True, "message": "Email envoyé !"}), 200

    except FileNotFoundError as e:
        print(f"❌ {str(e)}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Erreur serveur: {str(e)}"}), 500

def envoyer_avec_pj(destinataire, nom_tsens, sujet, fichier, nom_affiche=None):
    creds_raw = os.environ.get("GOOGLE_CREDENTIALS")
    
    if not creds_raw:
        raise Exception("❌ Variable GOOGLE_CREDENTIALS manquante sur Render")
    
    try:
        creds_data = json.loads(creds_raw)
    except json.JSONDecodeError:
        raise Exception("❌ GOOGLE_CREDENTIALS n'est pas un JSON valide")
    
    # Vérifier les champs requis
    required = ["refresh_token", "client_id", "client_secret"]
    for field in required:
        if field not in creds_data:
            raise Exception(f"❌ Champ manquant dans GOOGLE_CREDENTIALS: {field}")
    
    creds = Credentials(
        token=None,
        refresh_token=creds_data["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=creds_data["client_id"],
        client_secret=creds_data["client_secret"]
    )

    service = build('gmail', 'v1', credentials=creds)

    # Créer le message
    msg = MIMEMultipart()
    msg['To'] = destinataire
    msg['Subject'] = nom_tsens
    msg.attach(MIMEText("Bonjour", 'plain'))

    # Pièce jointe
    if fichier:
        with open(fichier, "rb") as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename={os.path.basename(fichier)}'
        )
        msg.attach(part)

    # Encoder et envoyer
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(
        userId='me',
        body={'raw': raw}
    ).execute()
    
    print("✅ Email envoyé via Gmail API")
    
@app.route('/download/<filename>')
def download_file(filename):
    """Télécharger un fichier"""
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

# ============= API EXTERNES =============

@app.route('/get_fournisseur', methods=['GET'])
def get_fournisseur():
    conn = connecter_sqlite()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT code_fournisseur, nom_fournisseur FROM fournisseur"
        )
        rows = cursor.fetchall()

        if not rows:
            return jsonify([])

        # Return list of all suppliers
        return jsonify([
            {
                "code_fournisseur": row[0],
                "nom_fournisseur": row[1]
            }
            for row in rows
        ])
    finally:
        conn.close()


@app.route('/get_stock', methods=['GET'])
def get_stock():
    conn = connecter_sqlite()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT reference, designation FROM correspondance_article"
        )
        rows = cursor.fetchall()

        articles_valides = [
            {"id": row[0], "name": row[1]}
            for row in rows
            if row[0] and row[1] and
            str(row[0]).strip() != '' and
            str(row[1]).strip() != ''
        ]

        articles_uniques = {article['id']: article for article in articles_valides}
        articles_list = list(articles_uniques.values())

        print(f"✅ {len(articles_list)} articles uniques")

        return jsonify({"list": articles_list}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_code/<designation>', methods=['GET'])
def get_code(designation):
    conn = connecter_sqlite()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT reference FROM correspondance_article WHERE designation = ?",
            (designation,)
        )
        row = cursor.fetchone()

        if row:
            return jsonify({"reference": row[0]})
        else:
            return jsonify({"error": "Article non trouvé"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()


# ============= AJOUT ARTICLE =============

@app.route('/add_article', methods=['POST'])
@login_required
def add_article():
    """Ajouter un nouvel article (référence + désignation) dans correspondance_article"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Données JSON manquantes"}), 400

    reference  = (data.get("reference", "") or "").strip().upper()
    designation = (data.get("designation", "") or "").strip().upper()

    if not reference or not designation:
        return jsonify({"error": "Référence et désignation obligatoires"}), 400

    conn = connecter_sqlite()
    try:
        # Vérifier si la référence existe déjà
        existing = conn.execute(
            "SELECT reference FROM correspondance_article WHERE reference = ?",
            (reference,)
        ).fetchone()

        if existing:
            return jsonify({"error": f"La référence '{reference}' existe déjà"}), 409

        conn.execute(
            "INSERT INTO correspondance_article (reference, designation) VALUES (?, ?)",
            (reference, designation)
        )
        conn.commit()
        print(f"✅ Article ajouté : {reference} - {designation}")
        return jsonify({"success": True, "reference": reference, "designation": designation}), 201

    except Exception as e:
        print(f"❌ Erreur ajout article : {str(e)}")
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()


# ============= MODIFIER ARTICLE =============

@app.route('/search_article', methods=['GET'])
@login_required
def search_article():
    """Rechercher un article par référence ou désignation"""
    q = request.args.get('q', '').strip().upper()
    if not q:
        return jsonify({"articles": []})

    conn = connecter_sqlite()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT reference, designation FROM correspondance_article
               WHERE UPPER(reference) LIKE ? OR UPPER(designation) LIKE ?
               ORDER BY designation LIMIT 30""",
            (f"%{q}%", f"%{q}%")
        )
        rows = cursor.fetchall()
        return jsonify({
            "articles": [{"reference": row[0], "designation": row[1]} for row in rows]
        })
    finally:
        conn.close()


@app.route('/edit_article', methods=['POST'])
@login_required
def edit_article():
    """Modifier la référence et/ou la désignation d'un article existant"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Données JSON manquantes"}), 400

    reference_originale = (data.get("reference_originale", "") or "").strip().upper()
    nouvelle_reference  = (data.get("nouvelle_reference", "") or "").strip().upper()
    nouvelle_designation = (data.get("nouvelle_designation", "") or "").strip().upper()

    if not reference_originale:
        return jsonify({"error": "Référence originale obligatoire"}), 400

    if not nouvelle_reference or not nouvelle_designation:
        return jsonify({"error": "Nouvelle référence et désignation obligatoires"}), 400

    conn = connecter_sqlite()
    try:
        # Vérifier que l'article à modifier existe
        existing = conn.execute(
            "SELECT reference FROM correspondance_article WHERE reference = ?",
            (reference_originale,)
        ).fetchone()

        if not existing:
            return jsonify({"error": f"Article '{reference_originale}' introuvable"}), 404

        # Si la référence change, vérifier que la nouvelle n'est pas déjà prise
        if nouvelle_reference != reference_originale:
            conflict = conn.execute(
                "SELECT reference FROM correspondance_article WHERE reference = ?",
                (nouvelle_reference,)
            ).fetchone()
            if conflict:
                return jsonify({"error": f"La référence '{nouvelle_reference}' existe déjà"}), 409

        conn.execute(
            """UPDATE correspondance_article
               SET reference = ?, designation = ?
               WHERE reference = ?""",
            (nouvelle_reference, nouvelle_designation, reference_originale)
        )
        conn.commit()
        print(f"✅ Article modifié : {reference_originale} → {nouvelle_reference} / {nouvelle_designation}")
        return jsonify({
            "success": True,
            "reference": nouvelle_reference,
            "designation": nouvelle_designation
        }), 200

    except Exception as e:
        print(f"❌ Erreur modification article : {str(e)}")
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()


@app.route('/delete_article', methods=['POST'])
@login_required
def delete_article():
    """Supprimer un article par sa référence"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Données JSON manquantes"}), 400

    reference = (data.get("reference", "") or "").strip().upper()
    if not reference:
        return jsonify({"error": "Référence obligatoire"}), 400

    conn = connecter_sqlite()
    try:
        existing = conn.execute(
            "SELECT reference FROM correspondance_article WHERE reference = ?",
            (reference,)
        ).fetchone()

        if not existing:
            return jsonify({"error": f"Article '{reference}' introuvable"}), 404

        conn.execute(
            "DELETE FROM correspondance_article WHERE reference = ?",
            (reference,)
        )
        conn.commit()
        print(f"🗑️ Article supprimé : {reference}")
        return jsonify({"success": True, "reference": reference}), 200

    except Exception as e:
        print(f"❌ Erreur suppression article : {str(e)}")
        return jsonify({"error": str(e)}), 500

    finally:
        conn.close()


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
                role TEXT DEFAULT 'user',
                code_tsena TEXT DEFAULT ''
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

        # S'assurer que la table correspondance_article existe
        db.execute("""
            CREATE TABLE IF NOT EXISTS correspondance_article (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference TEXT UNIQUE NOT NULL,
                designation TEXT NOT NULL
            )
        """)

        db.commit()
        print("✅ Base de données initialisée")
    finally:
        db.close()


# ============= DÉMARRAGE =============

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True, ssl_context='adhoc')
    # Pour la production avec HTTPS, utilisez nginx + certbot (Let's Encrypt)
    # NE PAS utiliser ssl_context='adhoc' en production