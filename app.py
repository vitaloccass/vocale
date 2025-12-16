from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify,send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime
from functools import wraps
from flask_login import login_required, current_user
from flask import render_template
import uuid
import os,io

app = Flask(__name__)
app.secret_key = "secret123"

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "Livraison")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DB_PATH = os.path.join(os.path.dirname(__file__), "vocale.db")

SERVICE_ACCOUNT_FILE = "credentials.json"
SCOPES = ['https://www.googleapis.com/auth/drive.file']

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)

drive_service = build('drive', 'v3', credentials=credentials)

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

# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        user = request.form['username']
        pwd = request.form['password']

        if (user == "admin" and pwd == "admin123") or (user == "demo" and pwd == "demo123"):
            session['logged'] = True
            session['username']=user
            return redirect(url_for('accueil'))
        else:
            flash("Utilisateur ou mot de passe incorrect!!!")
            return redirect(url_for('login'))   # 🔥 IMPORTANT !
    
    return render_template('login.html')
    

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

def connecter_sqlite():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # accès par nom de colonne
    return conn

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
    conn.close()

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
 
@app.route('/upload', methods=['POST'])
def upload_file():
   uploaded_file = request.files.get('file')
    if not uploaded_file:
        return "Aucun fichier reçu", 400

    rec = request.form.get('rec', 'unknown')
    nom_client = request.form.get('nom_client', 'unknown')
    date_fact = request.form.get('date_fact', 'unknown')

    # Nettoyer le nom du fichier
    def clean(s):
        return "".join(c if c.isalnum() else "_" for c in s)

    filename = f"{clean(rec)}_{clean(nom_client)}_{clean(date_fact)}.txt"

    # Convertir le fichier en objet IO
    file_stream = io.BytesIO(uploaded_file.read())
    media = MediaIoBaseUpload(file_stream, mimetype='text/plain', resumable=True)

    file_metadata = {
        'name': filename,
        # 'parents': ['ID_DU_DOSSIER']  # facultatif : mettre l’ID du dossier Drive
    }

    # Upload sur Google Drive
    file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    return jsonify({
        "message": "Fichier enregistré sur Google Drive",
        "file_id": file.get('id')
    })

# Endpoint pour télécharger un fichier déjà enregistré
@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
