from flask import Flask, render_template_string, jsonify, request, send_file, session, redirect, url_for, flash
from datetime import datetime
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import requests, json
import pyodbc


app = Flask(__name__)
app.secret_key = "votre_cle_secrete_a_changer"  # À modifier en production

# Base de données simple des utilisateurs (en production, utilisez une vraie DB)
USERS = {
    "admin": generate_password_hash("admin123"),
    "demo": generate_password_hash("demo123")
}

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


def lister_articles():
    """
    Récupère la liste des articles de la DB et la retourne sous forme de liste de dictionnaires.
    Chaque dictionnaire contient l'ID (AR_Ref), le nom (AR_Design) et le prix de vente (AR_PrixVen).
    """
    conn = connecter_sql()
    articles_list = []
    
    # 1. Gestion de la connexion échouée (important)
    if conn is None:
        print("Avertissement : Impossible de se connecter à la base de données SQL.")
        # Retourne des données de simulation pour éviter un crash complet
        return [
            {'id': 'SIM001', 'name': 'Article Simulé 1', 'price': 100.00},
            {'id': 'SIM002', 'name': 'Article Simulé 2', 'price': 250.00},
        ]
        
    try:
        cursor = conn.cursor()

        # Nous sélectionnons uniquement les colonnes nécessaires (Ref, Design, PrixVen)
        query = """
            SELECT AR_Ref, AR_Design, AR_PrixVen
            FROM F_ARTICLE
            ORDER BY AR_Design ASC;
        """

        cursor.execute(query)

        # 2. Récupération des données et formatage en liste de dictionnaires
        # pyodbc retourne des tuples par défaut. Nous les transformons.
        for row in cursor.fetchall():
            # row[0] = AR_Ref (id), row[1] = AR_Design (name), row[2] = AR_PrixVen (price)
            articles_list.append({
                'id': row[0],
                'name': row[1],
                'price': float(row[2]) if row[2] is not None else 0.00 # S'assurer que c'est un float
            })

    except Exception as e:
        print(f"Erreur lors de la récupération des articles : {e}")
        # En cas d'erreur de requête, retourne la liste vide
        return []

    finally:
        # 3. Fermeture de la connexion (très important)
        if conn:
            conn.close()
            
    # 4. Retourne la liste des articles
    return articles_list

# =============================
# DÉCORATEUR D'AUTHENTIFICATION
# =============================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# =============================
# TEMPLATE LOGIN
# =============================
LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Connexion - Facture vocale</title>

    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .login-card {
            background: white;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            width: 100%;
            max-width: 400px;
        }
        h1 {
            color: #4f46e5;
            text-align: center;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 600;
        }
        input {
            width: 100%;
            padding: 12px;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 16px;
            box-sizing: border-box;
            transition: border-color 0.3s;
        }
        input:focus {
            outline: none;
            border-color: #4f46e5;
        }
        button {
            width: 100%;
            padding: 14px;
            background: #4f46e5;
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.3s;
        }
        button:hover {
            background: #4338ca;
        }
        .alert {
            padding: 12px;
            margin-bottom: 20px;
            border-radius: 8px;
            background: #fee2e2;
            color: #dc2626;
            border: 1px solid #fecaca;
        }
        .info {
            background: #e0e7ff;
            color: #4f46e5;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
            font-size: 14px;
        }
        .info strong {
            display: block;
            margin-bottom: 5px;
        }
    </style>
</head>
<body>
<div class="login-card">
    <h1>🔐 Connexion</h1>
    
    {% if error %}
    <div class="alert">{{ error }}</div>
    {% endif %}
    
    <form method="POST">
        <div class="form-group">
            <label for="username">Nom d'utilisateur</label>
            <input type="text" id="username" name="username" required autofocus>
        </div>
        
        <div class="form-group">
            <label for="password">Mot de passe</label>
            <input type="password" id="password" name="password" required>
        </div>
        
        <button type="submit">Se connecter</button>
    </form>
    
    <div class="info">
        <strong>Comptes de démonstration :</strong>
        admin / admin123<br>
        demo / demo123
    </div>
</div>
</body>
</html>
'''

# =============================
# TEMPLATE HTML PRINCIPAL
# =============================
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Facture vocale bilingue</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #eef2ff;
            padding: 20px;
            margin: 0;
        }
        .header {
            background: white;
            padding: 15px 20px;
            border-radius: 10px;
            max-width: 900px;
            margin: 0 auto 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .user-info {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        .btn-logout {
            background: #dc2626;
            color: white;
            padding: 8px 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            text-decoration: none;
            font-size: 14px;
        }
        .btn-logout:hover {
            background: #b91c1c;
        }
        .card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            max-width: 900px;
            margin: auto;
            box-shadow: 0 5px 25px rgba(0,0,0,0.15);
        }
        .horizontal {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .info {
            background: #e0e7ff;
            color: #4f46e5;
            padding: 15px;
            border-radius: 8px;
            margin: 20px;
            font-size: 14px;
        }
        .info strong {
            color:green;
            --bg: #ffffff;
            --muted: #6b7280;
            --text: #0f172a;
            --accent: #0ea5a4;
            --surface: #f8fafc;
            --code-bg: #0b1220;
            --code-line: rgba(255,255,255,0.04);
            --border: #e6eef3;
            --radius: 12px;
            --max-width: 900px;
            --sidebar-width: 260px;
            --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, "Roboto Mono", "Courier New", monospace;
            --ui: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
            --shadow: 0 6px 20px rgba(16,24,40,0.06);
        }

        .horizontal h3 {
            margin: 0;
        }
        button {
            padding: 12px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            margin-right: 10px;
            font-size: 16px;
        }
        .btn-mic { background: #4f46e5; color: white; }
        .btn-reset { background: #6b7280; color: white; }
        .btn-download { background: #059669; color: white; }
        .btn-add { background: #059669; color: white; padding: 10px 15px; }
        .listening { background: #dc2626 !important; }

        select {
            padding: 10px;
            border: 2px solid #e5e7eb;
            border-radius: 6px;
            font-size: 16px;
            min-width: 250px;
        }

        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th { background: #4f46e5; color: white; padding: 12px; text-align: left; }
        td { padding: 12px; border-bottom: 1px solid #ddd; }
        .delete-btn { background: #dc2626; color: white; padding: 6px; cursor: pointer; }

        .total { text-align: right; font-size: 22px; font-weight: bold; margin-top: 10px; }

        .titre-facture {
            font-family: "Segoe UI", Roboto, Arial, sans-serif;
            font-size: 28px;
            font-weight: 700;
            color: #222;
            padding: 14px 20px;
            background: linear-gradient(90deg, #fff, #f7f7f7);
            border-left: 6px solid #4a90e2;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            display: flex;
            align-items: center;
            gap: 10px;
            letter-spacing: 1px;
            text-align:center;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
        }

        .titre-facture .icon {
            font-size: 32px;
            display: inline-block;
            transform: translateY(-1px);
        }
    </style>
</head>

<body>
<div class="header">
    <div class="user-info">
        <span>👤 Connecté en tant que : <strong>{{ username }}</strong></span>
    </div>
    <a href="{{ url_for('logout') }}" class="btn-logout">🚪 Déconnexion</a>
</div>

<div class="card">
    <h1 class="titre-facture">
        <span class="icon">🧾</span>  Facture vocale bilingue
    </h1>
    
    <p>Dictez votre facture en <b>français</b> ou <b>malagasy</b>.</p>
    <div class="info">
        <p>Cette application est compatible avec Google Chrome</p>
        <strong>Guide d'utilisation :</strong><br>
        1- Choisir la langue à utiliser<br>
        2- Cliquer sur <span style="color: red;">Commencer</span> pour la dictée<br>
        3- Pour le type de facture : Dire <span style="color: red;">achat</span> ou <span style="color: red;">vente</span> ou <span style="color: red;">fividianana</span> ou <span style="color: red;">fivarotana</span><br>
        4- Pour le numéro de facture : Dire <span style="color: red;">numéro</span> ou <span style="color: red;">numero</span> ou <span style="color: red;">laharana</span> ou <span style="color: red;">1</span><br>
        5- Pour le client : Dire <span style="color: red;">client</span> ou <span style="color: red;">mpanjifa</span> ou <span style="color: red;">2</span><br>
        6- Pour l'adresse : Dire <span style="color: red;">adresse</span> ou <span style="color: red;">adiresy</span> ou <span style="color: red;">3</span><br><br>
        <strong> Pour L'ajout d'un article :</strong><br>
        a- Pour l'article :' Dire <span style="color: red;">article</span> ou <span style="color: red;">produit</span> ou <span style="color: red;">zavatra</span> ou <span style="color: red;">art</span> ou <span style="color: red;">4</span>, ensuite le nom de l'article<br>
        b- Pour la quantité : Dire <span style="color: red;">quantité</span> ou <span style="color: red;">isa</span> ou <span style="color: red;">5</span><br>
        c- Pour le prix : Dire <span style="color: red;">prix</span> ou <span style="color: red;">vidiny</span> ou <span style="color: red;">6</span>
    </div>

    <button id="micBtn" class="btn-mic" onclick="toggleListening()">🎤 Commencer</button>

    <select id="langSelect">
        <option value="fr-FR">🇫🇷 Français</option>
        <option value="mg-MG">🇲🇬 Malagasy</option>
    </select>

    <button class="btn-reset" onclick="resetFacture()">🗑️ Réinitialiser</button>
    <button class="btn-download" onclick="telechargerPDF()">📥 PDF</button>

    <h3>📌 Transcription :</h3>
    <div id="transcript" style="background:#f3f4f6;padding:10px;border-radius:6px;">En attente…</div>

    <h2 class="titre-facture">
        <span class="icon">📋</span> Détails
    </h2>

    <form method="POST" action="save_facture()">
        <p><b>Type :</b> <span id="factureType">-</span></p>
        <p><b>Numéro :</b><span id="factureNumero">-</span></p>
        <p><b>Date :</b> {{date}}</p>

        <h3>👤 Client</h3>
        <p><b>Nom :</b> <span id="clientNom">-</span></p>
        <p><b>Adresse :</b> <span id="clientAdresse">-</span></p>

        <!-- Select Articles -->
        <div class="horizontal">
            <h3>📦 Articles</h3>
            <select id="mySelect">
                <option value="" disabled selected>Choisissez un article</option>
                {% if articles %}
                    {% for article in articles %}
                        <option value="{{ article.id }}" data-name="{{ article.name }}" data-price="{{ article.price | milliers }}">
                            {{ article.name }}
                        </option>
                    {% endfor %}
                {% else %}
                    <option disabled>Aucun article disponible</option>
                {% endif %}
            </select>
            <p>PU : <span id="prixUnitaire">0</span> Ar</p>
            <button class="btn-add" onclick="ajouterArticleDepuisSelect()">➕ Ajouter</button>
        </div>

        <div id="articlesContainer">Aucun article ajouté</div>
        <button type="submit">Submit</button>
    </form>
    <div class="total">TOTAL : <span id="totalAmount">0.00</span> Ar</div>
</div>

<script>
let recognition;
let isListening = false;

let facture = {
    type:"",
    numero: "",
    date: "{{date}}",
    client: { nom: "", adresse: "" },
    articles: [],
    total: 0
};


let price =0;
document.getElementById("mySelect").addEventListener("change", function () {
    price = this.selectedOptions[0].dataset.price;
    document.getElementById("prixUnitaire").textContent = price;
});

if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1; 
    

    recognition.onresult = (event) => {
        let text = "";
        for (let i = event.resultIndex; i < event.results.length; i++) {
            let result = event.results[i][0].transcript;
            if (event.results[i].isFinal) traiterCommande(result.toLowerCase());
            text = result;
        }
        document.getElementById("transcript").innerHTML = text;
    };
}

function toggleListening() {
    let btn = document.getElementById("micBtn");

    if (!isListening) {
        recognition.lang = document.getElementById("langSelect").value;
        recognition.start();
        isListening = true;
        btn.classList.add("listening");
        btn.innerText = "⏸️ Arrêter";
    } else {
        recognition.stop();
        isListening = false;
        btn.classList.remove("listening");
        btn.innerText = "🎤 Commencer";
    }
}

function ajouterArticleDepuisSelect() {
    let select = document.getElementById("mySelect");
    let selectedOption = select.options[select.selectedIndex];
    
    if (!selectedOption.value) {
        alert("Veuillez sélectionner un article");
        return;
    }
    
    // Demander la quantité
    let quantite = prompt("Quantité :", "1");
    if (!quantite || quantite <= 0) return;
    
    // Demander le prix
    let prix = prompt("Prix unitaire (Ar) :", "0");
    if (!prix || prix < 0) return;
    
    let art = {
        id: Date.now(),
        nom: selectedOption.dataset.name,
        quantite: parseInt(quantite),
        prixUnitaire: parseFloat(prix),
    };

    art.total = art.quantite * art.prixUnitaire;

    facture.articles.push(art);
    afficherArticles();
    

}

function traiterCommande(transcript) {
    transcript = transcript.trim().toLowerCase();

    // -------------------------
    // Type de facture : achat ou vente
    // -------------------------

    const typeMatch = transcript.match(/(?:Type|0)\s+([\w-]+)/i);
    if (typeMatch) {
        const type = typeMatch[1];
        facture.type = type;
        document.getElementById("factureType").textContent = facture.type;
    }

    // -------------------------
    // Numéro de facture
    // -------------------------
    const numeroMatch = transcript.match(/(?:numéro|numero|laharana|1)\s+([\w-]+)/i);
    if (numeroMatch) {
        const numero = numeroMatch[1];
        facture.numero = numero;
        document.getElementById("factureNumero").textContent = "N° " + numero;
    }

    // -------------------------
    // Nom du client
    // -------------------------
    const clientMatch = transcript.match(/(?:client|mpanjifa|2)\s+(.+)/i);
    if (clientMatch) {
        const nomClient = clientMatch[1];
        facture.client.nom = nomClient;
        document.getElementById("clientNom").textContent = nomClient;
    }

    // -------------------------
    // Adresse du client
    // -------------------------
    const adresseMatch = transcript.match(/(?:adresse|adiresy|3)\s+(.+)/i);
    if (adresseMatch) {
        const adresse = adresseMatch[1];
        facture.client.adresse = adresse;
        document.getElementById("clientAdresse").textContent = adresse;
    }

    // -------------------------
    // Ajout d'un article
    // -------------------------
    const articleMatch = transcript.match(
        /(?:article|produit|zavatra|art|4)\s+(.+?)\s+(?:quantité|isa|5)\s+(\d+)\s+(?:prix|vidiny|6)\s+(\d+(\.\d+)?)/i
    );

    if (articleMatch) {
        const nomArticle = articleMatch[1];
        const quantite = parseInt(articleMatch[2], 10);
        const prixUnitaire = parseFloat(articleMatch[3]);

        if (!isNaN(quantite) && !isNaN(prixUnitaire)) {
            const nouvelArticle = {
                id: Date.now(),
                nom: nomArticle,
                quantite: quantite,
                prixUnitaire: prixUnitaire,
                total: quantite * prixUnitaire
            };

            facture.articles.push(nouvelArticle);
            afficherArticles();
        }
    }
}

function afficherArticles() {
    let div = document.getElementById("articlesContainer");
    if (facture.articles.length === 0) {
        div.innerHTML = "Aucun article ajouté";
        document.getElementById("totalAmount").innerHTML = "0.00";
        return;
    }

    let html = "<table><tr><th>Article</th><th>Qté</th><th>Prix</th><th>Total</th><th></th></tr>";
    facture.total = 0;

    facture.articles.forEach(a => {
        facture.total += a.total;
        html += `<tr>
            <td>${a.nom}</td>
            <td>${a.quantite}</td>
            <td>${a.prixUnitaire.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} Ar</td>
            <td>${a.total.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} Ar</td>
            <td><button class="delete-btn" onclick="supprimer(${a.id})">X</button></td>
        </tr>`;
    });

    html += "</table>";
    div.innerHTML = html;

    document.getElementById("totalAmount").innerHTML = facture.total.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function supprimer(id) {
    facture.articles = facture.articles.filter(a => a.id !== id);
    afficherArticles();
}

function resetFacture() {
    facture = {
        numero: "",
        date: "{{date}}",
        client: { nom: "", adresse: "" },
        articles: [],
        total: 0
    };
    document.getElementById("factureNumero").innerHTML = "";
    document.getElementById("clientNom").innerHTML = "-";
    document.getElementById("clientAdresse").innerHTML = "-";
    document.getElementById("articlesContainer").innerHTML = "Aucun article ajouté";
    document.getElementById("totalAmount").innerHTML = "0.00";
}

function telechargerPDF() {
    fetch("/generer_pdf", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(facture)
    })
    .then(r => r.blob())
    .then(blob => {
        let url = URL.createObjectURL(blob);
        let a = document.createElement("a");
        a.href = url;
        a.download = "facture.pdf";
        a.click();
        URL.revokeObjectURL(url);
    });
}

function saveFacture() {
    fetch("/save_facture", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(facture)
    })
    .then(r => r.blob())
    .then(blob => {
        let url = URL.createObjectURL(blob);
        let a = document.createElement("a");
        a.href = url;
        a.download = "facture.pdf";
        a.click();
        URL.revokeObjectURL(url);
    });
}
</script>

</body>
</html>
'''

# =============================
# FONCTIONS UTILITAIRES
# =============================

@app.template_filter("milliers")
def milliers(value):
    try:
        return "{:,}".format(int(value)).replace(",", " ")
    except:
        return value

# =============================
# ROUTES 
# =============================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if username in USERS and check_password_hash(USERS[username], password):
            session['user'] = username
            return redirect(url_for('index'))
        else:
            return render_template_string(LOGIN_TEMPLATE, error="Nom d'utilisateur ou mot de passe incorrect")
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route("/logout")
def logout():
    session.pop('user', None)
    session.pop('articles', None)
    return redirect(url_for('login'))

@app.route("/")
@login_required
def index():
    articles=lister_articles()

    return render_template_string(
        HTML_TEMPLATE, 
        date=datetime.now().strftime("%d/%m/%Y"),
        username=session.get('user', 'Inconnu'),
        articles=articles
    )

@app.route("/save_facture", methods=["POST"])
def save_facture():
    print("totototo")
    return;

@app.route("/generer_pdf", methods=["POST"])
@login_required
def generer_pdf():
    data = request.json

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    p.setFont("Helvetica-Bold", 24)
    p.drawString(2*cm, height - 3*cm, "FACTURE")

    if data.get("numero"):
        p.setFont("Helvetica", 14)
        p.drawString(2*cm, height - 4*cm, f"N° {data['numero']}")

    # Client
    p.setFont("Helvetica-Bold", 14)
    p.drawString(2*cm, height - 6*cm, "CLIENT :")

    y = height - 7*cm
    p.setFont("Helvetica", 12)
    p.drawString(2*cm, y, data["client"]["nom"])
    y -= 0.7*cm
    p.drawString(2*cm, y, data["client"]["adresse"])

    # Articles
    y -= 1.5*cm
    p.setFont("Helvetica-Bold", 14)
    p.drawString(2*cm, y, "ARTICLES :")

    y -= 1*cm
    p.setFont("Helvetica-Bold", 10)
    p.drawString(2*cm, y, "Article")
    p.drawString(9*cm, y, "Qté")
    p.drawString(11*cm, y, "Prix")
    p.drawString(15*cm, y, "Total")

    y -= 0.5*cm
    p.setFont("Helvetica", 10)

    for a in data["articles"]:
        if y < 3*cm:
            p.showPage()
            y = height - 3*cm
            p.setFont("Helvetica", 10)

        p.drawString(2*cm, y, a["nom"][:40])
        p.drawString(9*cm, y, str(a["quantite"]))
        p.drawString(11*cm, y, f"{a['prixUnitaire']:.2f}")
        p.drawString(15*cm, y, f"{a['total']:.2f}")
        y -= 0.6*cm

    # Total
    y -= 1*cm
    p.setFont("Helvetica-Bold", 16)
    p.drawString(12*cm, y, "TOTAL :")
    p.drawString(15*cm, y, f"{data['total']:.2f} Ar")

    p.showPage()
    p.save()

    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", download_name="facture.pdf")

# =============================
# LANCEMENT SERVEUR
# =============================
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)