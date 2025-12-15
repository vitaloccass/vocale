from flask import Flask, render_template_string, jsonify, request, send_file, session, redirect, url_for, flash
from datetime import datetime
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import requests, json


app = Flask(__name__)
app.secret_key = "votre_cle_secrete_a_changer"  # À modifier en production

# Base de données simple des utilisateurs (en production, utilisez une vraie DB)
USERS = {
    "admin": generate_password_hash("admin123"),
    "demo": generate_password_hash("demo123")
}

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
    <h1>🎤 Facture vocale bilingue</h1>
    <p>Dictez votre facture en <b>français</b> ou <b>malagasy</b>.</p>

    <button id="micBtn" class="btn-mic" onclick="toggleListening()">🎤 Commencer</button>

    <select id="langSelect">
        <option value="fr-FR">🇫🇷 Français</option>
        <option value="mg-MG">🇲🇬 Malagasy</option>
    </select>

    <button class="btn-reset" onclick="resetFacture()">🗑️ Réinitialiser</button>
    <button class="btn-download" onclick="telechargerPDF()">📥 PDF</button>

    <h3>📌 Transcription :</h3>
    <div id="transcript" style="background:#f3f4f6;padding:10px;border-radius:6px;">En attente…</div>

    <h2>FACTURE <span id="factureNumero"></span></h2>
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

    <div class="total">TOTAL : <span id="totalAmount">0.00</span> Ar</div>
</div>

<script>
let recognition;
let isListening = false;

let price =0;
document.getElementById("mySelect").addEventListener("change", function () {
    price = this.selectedOptions[0].dataset.price;
    document.getElementById("prixUnitaire").textContent = price;
});

let facture = {
    numero: "",
    date: "{{date}}",
    client: { nom: "", adresse: "" },
    articles: [],
    total: 0
};

if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;

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
    let prix = prompt("Prix unitaire (Ar) :", price);
    if (!prix || prix < 0) return;
    
    let art = {
        id: Date.now(),
        nom: selectedOption.dataset.name,
        quantite: parseInt(quantite),
        prixUnitaire: parseFloat(prix.replace(' ','')),
    };

    art.total = art.quantite * art.prixUnitaire;

    facture.articles.push(art);
    afficherArticles();
    
    // Réinitialiser le select
    select.selectedIndex = 0;
    document.getElementById("prixUnitaire").innerHTML="0";
}

function traiterCommande(t) {
    // Numéro facture
    let m1 = t.match(/(?:numéro|numero|laharana)\s+([\w-]+)/);
    if (m1) {
        facture.numero = m1[1];
        document.getElementById("factureNumero").innerHTML = "N° " + m1[1];
    }

    // Nom client
    let m2 = t.match(/(?:client|mpanjifa)\s+(.+)/);
    if (m2) {
        facture.client.nom = m2[1];
        document.getElementById("clientNom").innerHTML = m2[1];
    }

    // Adresse
    let m3 = t.match(/(?:adresse|adresy)\s+(.+)/);
    if (m3) {
        facture.client.adresse = m3[1];
        document.getElementById("clientAdresse").innerHTML = m3[1];
    }

    // Articles
    let m4 = t.match(/(?:article|produit|zavatra)\s+(.+?)\s+(?:quantité|isa)\s+(\d+)\s+(?:prix|vidiny)\s+(\d+)/);
    if (m4) {
        let art = {
            id: Date.now(),
            nom: m4[1],
            quantite: parseInt(m4[2]),
            prixUnitaire: parseFloat(m4[3]),
        };
        art.total = art.quantite * art.prixUnitaire;

        facture.articles.push(art);
        afficherArticles();
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

def recup_article_cashmag():
    """Récupère les articles depuis l'API CashMag"""
    url = "https://api.fulleapps.io/products"
    headers = {
        "X-Api-Key": "LwwMBbtNxMxvdMVcX4gXRVhscf5Q4K",
        "Authorization": "Mutual f585bd1e3b10f9a8eb7ac4c82f6478c6ae94d73a",
    }
    params = {"page": 1, "offset": 0, "limit": 1000}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if isinstance(data, dict) and "list" in data:
            articles = data["list"]
            
            # Retourner les données nécessaires pour le select
            return [
                {
                    'id': str(a.get('id', '')),
                    'name': str(a.get('name', 'Sans nom')),
                    'price': str((a.get("prices") or [{}])[0].get("price", ""))
                }
                for a in articles
            ]
        else:
            return []
            
    except Exception as e:
        print(f"ERREUR API: {type(e).__name__}: {e}")
        return []

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
    articles = recup_article_cashmag()
    articles.sort(key=lambda x: x['name'].lower())

    if articles is None:
        articles = []
    
    return render_template_string(
        HTML_TEMPLATE, 
        date=datetime.now().strftime("%d/%m/%Y"),
        username=session.get('user', 'Inconnu'),
        articles=articles
    )

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