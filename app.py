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
    correspondances=get_correspondance()
    depots = lister_depot()
    username = session.get('username', 'Invité')
    return render_template(
        'index.html',
        date=datetime.now().strftime('%Y-%m-%d'),
        depots=depots, 
        username=username,
        correspondances=correspondances,
    )

def connecter_sqlite():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # accès par nom de colonne
    return conn

def lister_depot():
    conn = connecter_sqlite()
    depot_list = []
    
    try:
        cursor = conn.cursor()

        query = """
            SELECT
                DISTINCT DE_No,DE_Intitule 
            FROM F_DEPOT
            ORDER BY DE_No ASC
        """

        cursor.execute(query)

        for row in cursor.fetchall():
            depot_list.append({
                'id': row[0],
                'name': row[1]
            })

    except Exception as e:
        print(f"Erreur lors de la récupération des dépots : {e}")
        return []

    finally:
        if conn:
            conn.close()

    return depot_list

@app.route('/get_client', methods=['GET'])
def get_client():
    # Récupération du paramètre code
    code = request.args.get('code', '')
    if not code:
        return jsonify({"nom": ""})

    conn = connecter_sqlite()
    cursor = conn.cursor(dictionary=True)  # dictionnaire pour fetchone

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
    # Récupération du paramètre code
    code = request.args.get('code', '')
    if not code:
        return jsonify({
            "reference": "",
            "designation": ""
        })

    conn = connecter_sqlite()
    cursor = conn.cursor(dictionary=True)  # dictionnaire pour fetchone

    # Normalisation du code : majuscules + enlever espaces
    code_modifie = code.strip().upper().replace(' ', '')
    
    cursor.execute(
        "SELECT reference,designation FROM correspondance_article WHERE code=?",
        (code_modifie,)
    )

    row = cursor.fetchone()
    if row:
        return jsonify({
            "reference": row["reference"],
            "designation": row["designation"]
        })
    else:
        return jsonify({
            "reference": "",
            "designation": ""
        })

@app.route('/get_tsena', methods=['GET'])
def get_tsena():
    # Récupération du paramètre code
    code = request.args.get('code', '')
    if not code:
        return jsonify({
            "code_tsena": "",
            "depot": "",
            "affaire": "",
            "num_fact":""
        })

    conn = connecter_sqlite()
    cursor = conn.cursor(dictionary=True)  # dictionnaire pour fetchone

    
    # Normalisation du code : majuscules + enlever espaces
    code_modifie = code.strip().upper().replace(' ', '')
    
    cursor.execute(
        "SELECT code_tsena,depot,affaire FROM correspondance WHERE code=?",
        (code_modifie,)
    )

    row = cursor.fetchone()

    # ✅ Vérification OBLIGATOIRE
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

    # ✅ UN SEUL DICTIONNAIRE JSON
    return jsonify({
        "code_tsena": row.get("code_tsena", ""),
        "depot": row.get("depot", ""),
        "affaire": row.get("affaire", ""),
        "num_fact": num_fact
    })
        
def get_correspondance():
    conn = connecter_sqlite()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM correspondance ORDER BY nom_tsena ASC")

    rows = cursor.fetchall()
    result = []

    if rows:
        columns = [col[0] for col in cursor.description]
        for row in rows:
            row_dict = dict(zip(columns, row))
            result.append({
                "nom_tsena": row_dict.get("nom_tsena"),
                "code_tsena": row_dict.get("code_tsena"),
                "depot": row_dict.get("depot"),
                "affaire": row_dict.get("affaire")
            })
    return result

@app.route('/upload', methods=['POST'])
def upload_file():
    uploaded_file = request.files.get('file')
    if not uploaded_file:
        return "Aucun fichier reçu", 400

    rec = request.form.get('rec', 'unknown')
    recs = request.form.get('recs', 'unknown')
    nom_client = request.form.get('nom_client', 'unknown')
    date_fact = request.form.get('date_fact', 'unknown')

    # Nettoyer le nom du fichier
    def clean(s):
        return "".join(c if c.isalnum() else "_" for c in s)

    if "vente" in recs.lower():
        filename = f"VENTE_{clean(rec)}_{clean(nom_client)}_{clean(date_fact)}.txt"
    else:
        filename = f"ACHAT_{clean(rec)}_{clean(nom_client)}_{clean(date_fact)}.txt"

    file_path = os.path.join(UPLOAD_FOLDER, filename)

    # Sauvegarder le fichier
    uploaded_file.save(file_path)

    return jsonify({"message": "Fichier enregistré", "path": f"/download/{filename}"})

# Endpoint pour télécharger un fichier déjà enregistré
@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
