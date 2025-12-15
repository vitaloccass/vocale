from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify,send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import pyodbc
from datetime import datetime
from functools import wraps
from flask_login import login_required, current_user
from flask import render_template
import uuid
import mysql.connector
import os,io

app = Flask(__name__)
app.secret_key = "secret123"

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "Livraison")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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

def connecter_sql():
    db_params = {}
    config_file = 'connexion.txt'

    try:
        # 1. Lire le fichier et stocker les paramètres dans un dictionnaire
        with open(config_file, 'r') as f:
            for line in f:
                # Ignorer les lignes vides ou celles qui ne sont pas des paires clé=valeur
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    db_params[key.strip()] = value.strip()
        
        # 2. Vérifier que tous les champs nécessaires sont présents
        if not all(k in db_params for k in ["DRIVER", "SERVER", "DATABASE", "UID", "PWD"]):
            print("Erreur : Le fichier de configuration est incomplet.")
            return None

        # 3. Construire la chaîne de connexion
        connection_string = (
            f"DRIVER={db_params['DRIVER']};"
            f"SERVER={db_params['SERVER']};"
            f"DATABASE={db_params['DATABASE']};"
            f"UID={db_params['UID']};"
            f"PWD={db_params['PWD']};"
        )
        
        # 4. Connexion
        conn = pyodbc.connect(connection_string)
        return conn
    
    except FileNotFoundError:
        print(f"Erreur : Le fichier de configuration '{config_file}' est introuvable.")
        return None
    except pyodbc.Error as ex:
        print(f"Erreur de connexion SQL: {ex}")
        return None

def lister_depot():
    conn = connecter_sql()
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

    conn = None
    try:
        # Connexion MySQL
        conn = mysql.connector.connect(
            host="localhost",   # ou db_params['SERVER'] si config
            user="root",
            password="",
            database="vocale"
        )

        cursor = conn.cursor(dictionary=True)  # dictionnaire pour fetchone

        
        # Normalisation du code : majuscules + enlever espaces
        code_modifie = code.strip().upper().replace(' ', '')
        

        cursor.execute(
            "SELECT nom_client FROM correspondance_client WHERE code=%s",
            (code_modifie,)
        )

        row = cursor.fetchone()
        if row:
            return jsonify({"nom": row["nom_client"]})
        else:
            return jsonify({"nom": ""})

    except mysql.connector.Error as e:
        print(f"[Erreur MySQL] {e}")
        return jsonify({"nom": ""})

    finally:
        if conn and conn.is_connected():
            conn.close()

@app.route('/get_article', methods=['GET'])
def get_article():
    # Récupération du paramètre code
    code = request.args.get('code', '')
    if not code:
        return jsonify({
            "reference": "",
            "designation": ""
        })

    conn = None
    try:
        # Connexion MySQL
        conn = mysql.connector.connect(
            host="localhost",   # ou db_params['SERVER'] si config
            user="root",
            password="",
            database="vocale"
        )

        cursor = conn.cursor(dictionary=True)  # dictionnaire pour fetchone

        
        # Normalisation du code : majuscules + enlever espaces
        code_modifie = code.strip().upper().replace(' ', '')
        
        cursor.execute(
            "SELECT reference,designation FROM correspondance_article WHERE code=%s",
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

    except mysql.connector.Error as e:
        print(f"[Erreur MySQL] {e}")
        return jsonify({
            "reference": "",
            "designation": ""
        })

    finally:
        if conn and conn.is_connected():
            conn.close()

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

    conn = None
    try:
        # Connexion MySQL
        conn = mysql.connector.connect(
            host="localhost",   # ou db_params['SERVER'] si config
            user="root",
            password="",
            database="vocale"
        )

        cursor = conn.cursor(dictionary=True)  # dictionnaire pour fetchone

        
        # Normalisation du code : majuscules + enlever espaces
        code_modifie = code.strip().upper().replace(' ', '')
        
        cursor.execute(
            "SELECT code_tsena,depot,affaire FROM correspondance WHERE code=%s",
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
        
    except mysql.connector.Error as e:
        print(f"[Erreur MySQL] {e}")
        return jsonify({
            "code_tsena": "",
            "depot": "",
            "affaire": "",
            "num_fact":""
        })

    finally:
        if conn and conn.is_connected():
            conn.close()

def get_correspondance():
    config_file = 'connexion.txt'
    db_params = {}
    conn = None  # <==== AJOUT IMPORTANT
  
    try:
        with open(config_file, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    db_params[key.strip()] = value.strip()
        
        if "SERVER" not in db_params:
            print("Erreur : Le fichier de configuration est incomplet.")
            return []

        conn = mysql.connector.connect(
            host=db_params['SERVER'],
            user="root",
            password="",
            database="vocale"
        )

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

    except mysql.connector.Error as e:
        print(f"[Erreur MySQL] {e}")
        return []

    finally:
        if conn is not None and conn.is_connected():
            conn.close()

@app.route('/upload', methods=['POST'])
def upload_file():
    print("test")
    uploaded_file = request.files.get('file')
    if not uploaded_file:
        return "Aucun fichier reçu", 400

    rec = request.form.get('rec', 'unknown')
    nom_client = request.form.get('nom_client', 'unknown')
    date_fact = request.form.get('date_fact', 'unknown')

    # Nettoyer le nom du fichier
    def clean(s):
        return "".join(c if c.isalnum() else "_" for c in s)

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
