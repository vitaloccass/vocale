from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import uuid
import os
import json
import base64
import requests
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret123")  # Changez en production via variable d'env

# ============= CONFIGURATION =============

SCOPES = ['https://www.googleapis.com/auth/gmail.send']
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

TURSO_URL = os.environ.get("TURSO_URL", "")
TURSO_TOKEN = os.environ.get("TURSO_TOKEN", "")

# ============= CONNEXION TURSO =============

def _turso_execute(sql, params=[]):
    """Exécute une requête SQL sur Turso et retourne les résultats sous forme de liste de dicts."""
    headers = {
        "Authorization": f"Bearer {TURSO_TOKEN}",
        "Content-Type": "application/json"
    }
    args = [{"type": "text", "value": str(p)} for p in params]
    res = requests.post(
        f"{TURSO_URL}/v2/pipeline",
        headers=headers,
        json={"requests": [{"type": "execute", "stmt": {"sql": sql, "args": args}}]}
    )
    res.raise_for_status()
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

    def __getitem__(self, index):
        """Accès par index pour compatibilité row[0], row[1]"""
        if self.results:
            row = self.results[0]
            keys = list(row.keys())
            if isinstance(index, int):
                return row[keys[index]]
        return None


class TursoConnection:
    def cursor(self):
        return TursoCursor()

    def execute(self, sql, params=[]):
        c = TursoCursor()
        c.execute(sql, params)
        return c

    def commit(self):
        pass  # Turso auto-commit via HTTP

    def close(self):
        pass


def connecter_sqlite():
    return TursoConnection()

# ============= DÉCORATEURS =============

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ============= FILTRES =============

@app.template_filter("milliers")
def milliers(value):
    try:
        return "{:,}".format(int(value)).replace(",", " ")
    except Exception:
        return value

# ============= AUTHENTIFICATION =============

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username   = request.form.get("username", "").strip()
        password   = request.form.get("password", "")
        confirm    = request.form.get("confirm", "")
        ctype      = request.form.get("ctype", "")
        code_tsena = request.form.get("tsena", "")

        if not username or not password:
            flash("Tous les champs sont obligatoires")
            return redirect(url_for("register"))

        if password != confirm:
            flash("Les mots de passe ne correspondent pas")
            return redirect(url_for("register"))

        db = connecter_sqlite()
        try:
            user = db.execute(
                "SELECT id FROM users WHERE username = ?", (username,)
            ).fetchone()

            if user:
                flash("Nom d'utilisateur déjà utilisé")
                return redirect(url_for("register"))

            code = "admin" if ctype == "admin" else code_tsena
            db.execute(
                "INSERT INTO users (username, password, role, code_tsena) VALUES (?, ?, ?, ?)",
                (username, generate_password_hash(password), ctype, code)
            )
            db.commit()
            flash("Compte créé avec succès, connectez-vous")
            return redirect(url_for("login"))
        finally:
            db.close()

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
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
            session["logged"]     = True
            session["user_id"]    = user["id"]
            session["username"]   = user["username"]
            session["type"]       = user["role"]
            session["code_tsena"] = user["code_tsena"]
            return redirect(url_for("accueil"))

        flash("Utilisateur ou mot de passe incorrect")
        return render_template("login.html"), 401

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


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

            token      = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(hours=1)

            db.execute(
                "INSERT INTO reset_tokens (user_id, token, expires_at) VALUES (?, ?, ?)",
                (user["id"], token, expires_at.isoformat())
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
            password = request.form.get("password", "")
            confirm  = request.form.get("confirm", "")
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

# ============= PAGE PRINCIPALE =============

@app.route("/")
@login_required
def accueil():
    return render_template(
        "index.html",
        date=datetime.now().strftime("%Y-%m-%d"),
        username=session.get("username", "Invité"),
        type=session.get("type", ""),
        tsena=session.get("code_tsena", ""),
    )

# ============= API : TSENA =============

@app.route("/get_tsena")
def get_tsena():
    try:
        code = request.args.get("code", "").strip().upper().replace(" ", "")
        if not code:
            return jsonify({"code_tsena": "", "depot": "", "affaire": "",
                            "nom_tsena": "", "souche": "", "num_fact": ""})

        conn = connecter_sqlite()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT code_tsena, depot, affaire, nom_tsena, souche FROM correspondance WHERE code=?",
            (code,)
        )
        row = cursor.fetchone()

        if not row:
            return jsonify({"code_tsena": "", "depot": "", "affaire": "",
                            "nom_tsena": "", "souche": "", "num_fact": ""})

        now       = datetime.now()
        jour      = str(now.day).lstrip("0")
        mois      = now.month
        short_year = str(now.year)[-2:]
        date_jour = f"{jour}{mois}{short_year}"
        t         = row["depot"].replace("DP", "").lstrip("0")

        cursor.execute(
            "SELECT date, compteur FROM compteur WHERE code_tsena=?", (code,)
        )
        row_compteur = cursor.fetchone()

        if not row_compteur or row_compteur["date"] != date_jour:
            compteur = 1
        else:
            compteur = int(row_compteur["compteur"]) + 1

        if row_compteur:
            _turso_execute(
                "UPDATE compteur SET date=?, compteur=? WHERE code_tsena=?",
                (date_jour, compteur, code)
            )
        else:
            _turso_execute(
                "INSERT INTO compteur (code_tsena, date, compteur) VALUES (?, ?, ?)",
                (code, date_jour, compteur)
            )

        num_fact = f"{t}FA{date_jour}{compteur}"

        return jsonify({
            "code_tsena": row["code_tsena"],
            "depot":      row["depot"],
            "affaire":    row["affaire"],
            "nom_tsena":  row["nom_tsena"],
            "souche":     row["souche"],
            "num_fact":   num_fact
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============= API : FOURNISSEURS =============

@app.route("/get_fournisseur", methods=["GET"])
def get_fournisseur():
    conn = connecter_sqlite()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT code_fournisseur, nom_fournisseur FROM fournisseur")
        rows = cursor.fetchall()
        return jsonify([
            {"code_fournisseur": row["code_fournisseur"],
             "nom_fournisseur":  row["nom_fournisseur"]}
            for row in rows
        ])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

# ============= API : STOCK / ARTICLES =============

@app.route("/get_stock", methods=["GET"])
def get_stock():
    conn = connecter_sqlite()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT reference, designation FROM correspondance_article")
        rows = cursor.fetchall()

        seen = {}
        for row in rows:
            ref  = str(row["reference"]).strip()
            desc = str(row["designation"]).strip()
            if ref and desc:
                seen[ref] = {"id": ref, "name": desc}

        return jsonify({"list": list(seen.values())}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/get_code/<designation>", methods=["GET"])
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
            return jsonify({"reference": row["reference"]})
        return jsonify({"error": "Article non trouvé"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/add_article", methods=["POST"])
@login_required
def add_article():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Données JSON manquantes"}), 400

    reference   = (data.get("reference", "") or "").strip().upper()
    designation = (data.get("designation", "") or "").strip().upper()

    if not reference or not designation:
        return jsonify({"error": "Référence et désignation obligatoires"}), 400

    conn = connecter_sqlite()
    try:
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
        return jsonify({"success": True, "reference": reference, "designation": designation}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/search_article", methods=["GET"])
@login_required
def search_article():
    q = request.args.get("q", "").strip().upper()
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
            "articles": [{"reference": row["reference"], "designation": row["designation"]}
                         for row in rows]
        })
    finally:
        conn.close()


@app.route("/edit_article", methods=["POST"])
@login_required
def edit_article():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Données JSON manquantes"}), 400

    ref_orig  = (data.get("reference_originale", "") or "").strip().upper()
    new_ref   = (data.get("nouvelle_reference", "") or "").strip().upper()
    new_desc  = (data.get("nouvelle_designation", "") or "").strip().upper()

    if not ref_orig:
        return jsonify({"error": "Référence originale obligatoire"}), 400
    if not new_ref or not new_desc:
        return jsonify({"error": "Nouvelle référence et désignation obligatoires"}), 400

    conn = connecter_sqlite()
    try:
        existing = conn.execute(
            "SELECT reference FROM correspondance_article WHERE reference = ?",
            (ref_orig,)
        ).fetchone()
        if not existing:
            return jsonify({"error": f"Article '{ref_orig}' introuvable"}), 404

        if new_ref != ref_orig:
            conflict = conn.execute(
                "SELECT reference FROM correspondance_article WHERE reference = ?",
                (new_ref,)
            ).fetchone()
            if conflict:
                return jsonify({"error": f"La référence '{new_ref}' existe déjà"}), 409

        conn.execute(
            "UPDATE correspondance_article SET reference = ?, designation = ? WHERE reference = ?",
            (new_ref, new_desc, ref_orig)
        )
        conn.commit()
        return jsonify({"success": True, "reference": new_ref, "designation": new_desc}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()


@app.route("/delete_article", methods=["POST"])
@login_required
def delete_article():
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
            "DELETE FROM correspondance_article WHERE reference = ?", (reference,)
        )
        conn.commit()
        return jsonify({"success": True, "reference": reference}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

# ============= UPLOAD + EMAIL =============

@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        uploaded_file = request.files.get("file")
        if not uploaded_file:
            return jsonify({"error": "Aucun fichier reçu"}), 400

        rec        = request.form.get("rec", "unknown")
        recs       = request.form.get("recs", "unknown")
        nom_client = request.form.get("nom_client", "unknown")
        date_fact  = request.form.get("date_fact", "unknown")
        nom_tsens  = request.form.get("tsena", "unknown")

        def clean(s):
            return "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in s)

        recs_lower = recs.lower()
        if "vente" in recs_lower:
            filename = f"VENTE_{clean(rec)}_{clean(nom_client)}_{clean(date_fact)}.txt"
        elif "BC" in recs:
            filename = f"BC_ACHAT_{clean(rec)}_{clean(nom_client)}_{clean(date_fact)}.txt"
        else:
            filename = f"FA_ACHAT_{clean(rec)}_{clean(nom_client)}_{clean(date_fact)}.txt"

        temp_dir = os.path.join(os.path.dirname(__file__), "temp_uploads")
        os.makedirs(temp_dir, exist_ok=True)

        chemin_fichier = os.path.join(temp_dir, filename)
        uploaded_file.save(chemin_fichier)

        destinataire = os.environ.get("EMAIL_DESTINATAIRE", "andrivolavita@gmail.com")
        envoyer_avec_pj(destinataire, nom_tsens, "Bonjour", chemin_fichier, filename)

        os.remove(chemin_fichier)
        return jsonify({"success": True, "message": "Email envoyé !"}), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Erreur serveur: {str(e)}"}), 500


def envoyer_avec_pj(destinataire, nom_tsens, sujet, fichier, nom_affiche=None):
    """Envoie un email avec pièce jointe via Gmail API (OAuth2 refresh token)."""
    creds_raw = os.environ.get("GOOGLE_CREDENTIALS")
    if not creds_raw:
        raise Exception("Variable GOOGLE_CREDENTIALS manquante")

    try:
        creds_data = json.loads(creds_raw.strip().strip("'").strip('"'))
    except json.JSONDecodeError as e:
        raise Exception(f"GOOGLE_CREDENTIALS JSON invalide : {e}")

    for field in ("refresh_token", "client_id", "client_secret"):
        if field not in creds_data:
            raise Exception(f"Champ manquant dans GOOGLE_CREDENTIALS : {field}")

    creds = Credentials(
        token=None,
        refresh_token=creds_data["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=creds_data["client_id"],
        client_secret=creds_data["client_secret"],
        scopes=SCOPES,
    )

    service = build("gmail", "v1", credentials=creds)

    msg = MIMEMultipart()
    msg["To"]      = destinataire
    msg["Subject"] = nom_tsens
    msg.attach(MIMEText(sujet, "plain"))

    if fichier and os.path.exists(fichier):
        with open(fichier, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f'attachment; filename="{nom_affiche or os.path.basename(fichier)}"'
        )
        msg.attach(part)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
    print("✅ Email envoyé via Gmail API")


@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

# ============= INITIALISATION DB =============

def init_db():
    """Crée les tables si elles n'existent pas encore."""
    stmts = [
        """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            code_tsena TEXT DEFAULT ''
        )""",
        """CREATE TABLE IF NOT EXISTS reset_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL UNIQUE,
            expires_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )""",
        """CREATE TABLE IF NOT EXISTS correspondance_article (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference TEXT UNIQUE NOT NULL,
            designation TEXT NOT NULL
        )""",
    ]
    for sql in stmts:
        _turso_execute(sql)
    print("✅ Base de données initialisée")

# ============= DÉMARRAGE =============

if __name__ == "__main__":
    init_db()
    # Développement local uniquement – utilisez gunicorn + nginx en production
    app.run(host="0.0.0.0", port=5000, debug=True)