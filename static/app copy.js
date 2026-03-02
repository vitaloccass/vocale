let recognition;
let isListening = false;

let facture = {
    type:"",
    numero: "",
    date: new Date().toISOString().substring(0, 10),
    client: { nom: "", adresse: "" },
    articles: [],
    total: 0,
    stock:0,
};

let price = 0;
let qte_sto = 0;
let nom_tsena="";

document.addEventListener("DOMContentLoaded", () => {
    let select = document.getElementById("mySelect");

    if (select) {
        select.addEventListener("change", function () {
            price = parseFloat(this.selectedOptions[0].dataset.price);
            qte_sto = parseFloat(this.selectedOptions[0].dataset.qte);

            document.getElementById("prixUnitaire").textContent = price;
            document.getElementById("qtesto").textContent = qte_sto;
        });
    }
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

function initRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();

    recognition.lang = "fr-FR";
    recognition.continuous = false;      // 🚨 OBLIGATOIRE MOBILE
    recognition.interimResults = false;  // PLUS STABLE
    recognition.maxAlternatives = 1;

    recognition.onend = () => {
        isListening = false;
        const btn = document.getElementById("micBtn");
        btn.classList.remove("listening");
        btn.innerText = "🎤 Commencer";
    };

    recognition.onerror = (e) => {
        console.error("Erreur micro :", e);
        recognition.stop();
    };

    recognition.onresult = (event) => {
        const text = event.results[0][0].transcript.toLowerCase();
        traiterCommande(text);
    };
}

function isMobile() {
    return /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
}

function handleMicClick() {
    if (isMobile()) {
        toggleListenings();
    } else {
        toggleListening();
    }
}

function toggleListenings() {
    const btn = document.getElementById("micBtn");

    if (!recognition) initRecognition();

    if (isListening) {
        recognition.stop();
        return;
    }

    recognition.start();    // 🚨 DOIT être dans un clic utilisateur
    isListening = true;

    btn.classList.add("listening");
    btn.innerText = "🎙️ Parlez…";
}

function toggleListening() {
    let btn = document.getElementById("micBtn");

    if(btn.innerText != "⏸️ Arrêter"){
        afficherDebut();
    }else{
        location.reload();
    }

    if (!recognition) {
        alert("La reconnaissance vocale n'est pas supportée sur ce navigateur.");
        return;
    }

    if (!isListening) {
        recognition.lang = 'fr-FR';
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

function normalizeCmd(cmd) {
    return cmd
        .toLowerCase()
        .replace(/\s+/g, ' ')
        .replace(/0\s*[.,]?\s*(\d)/g, '0.$1'); // 0 8 / 0,8 / 0.8 → 0.8
}

let articlesFiltre = [];
function filtrerArticles(motCle) {
    const selectArticle = document.querySelector('#articleSelect');
    
    if (!selectArticle) return;
    
    // Récupérer toutes les options
    const options = Array.from(selectArticle.options);
    
    // IMPORTANT : Remplir articlesFiltre avec les options filtrées
    articlesFiltre = options.filter(option => {
        const texte = option.textContent.toLowerCase();
        return texte.includes(motCle);
    });
    
    // Afficher/Cacher les options
    options.forEach(option => {
        const texte = option.textContent.toLowerCase();
        
        if (texte.includes(motCle)) {
            option.style.display = ""; // Afficher
        } else {
            option.style.display = "none"; // Cacher
        }
    });
    
    // Afficher la liste numérotée
    afficherListeFiltre(articlesFiltre);
    
    console.log(`${articlesFiltre.length} articles trouvés avec "${motCle}"`);
}

function selectionnerArticleParNumero(numero) {
    console.log("Numéro reçu:", numero);
    console.log("Articles disponibles:", articlesFiltre.length);
    
    if (articlesFiltre.length === 0) {
        console.log("Aucun article filtré. Dites d'abord 'Article PAIN' par exemple");
        return;
    }
    
    if (numero < 1 || numero > articlesFiltre.length) {
        console.log(`Numéro invalide. Choisissez entre 1 et ${articlesFiltre.length}`);
        return;
    }
    
    const selectArticle = document.querySelector('#articleSelect');
    if (!selectArticle) return;
    
    // Sélectionner l'option correspondante
    const optionChoisie = articlesFiltre[numero - 1];
    selectArticle.value = optionChoisie.value;
    
    // Déclencher l'événement change
    selectArticle.dispatchEvent(new Event('change', { bubbles: true }));
    
    console.log(`✓ Article sélectionné : ${optionChoisie.textContent}`);
    
    // Fermer la liste affichée
    const listeDiv = document.getElementById('liste-articles-filtre');
    if (listeDiv) {
        listeDiv.remove();
    }

    let rows = document.querySelectorAll("#table-body tr");
    if (!rows.length) return;

    let targetRow = null;

    // chercher la ligne "vide" (colonne client vide)
    rows.forEach(row => {
        const tdClient = row.children[3]; // colonne Nom client
        if (tdClient && tdClient.innerText.trim() === "" && !targetRow) {
            targetRow = row;
        }
    });

    // si aucune ligne vide trouvée → prendre la dernière
    if (!targetRow) {
        targetRow = rows[rows.length - 1];
    }
    const code_article = targetRow.children[4];
    const nom_article = targetRow.children[5];
    const fournisseur = targetRow.children[3];

    const elements = optionChoisie.value.split('#');
    
    code_article.innerText   = elements[1];
    nom_article.innerText   = optionChoisie.textContent;

    if (fournisseur && elements[0]) {
        recuperer_fournisseur(elements[0], fournisseur);
    }
}

function selectionnerTypeParNumero(numero) {
    console.log("Numéro reçu:", numero);
    
    if (numero < 1 || numero > 2) {
        console.log(`Numéro invalide. Choisissez entre 1 et 2`);
        return;
    }
    
    const selectType = document.querySelector('.lbltype');
    if (!selectType) return;
    
    // Sélectionner l'option correspondante
    const optionChoisie = articlesFiltre[numero - 1];
    selectType.value = optionChoisie.value;
    
    // Déclencher l'événement change
    selectArticle.dispatchEvent(new Event('change', { bubbles: true }));
    
    console.log(`✓ Article sélectionné : ${optionChoisie.textContent}`);
    
    // Fermer la liste affichée
    const listeDiv = document.getElementById('liste-articles-filtre');
    if (listeDiv) {
        listeDiv.remove();
    }

        let rows = document.querySelectorAll("#table-body tr");
        if (!rows.length) return;

        let targetRow = null;

        // chercher la ligne "vide" (colonne client vide)
        rows.forEach(row => {
            const tdClient = row.children[3]; // colonne Nom client
            if (tdClient && tdClient.innerText.trim() === "" && !targetRow) {
                targetRow = row;
            }
        });

        // si aucune ligne vide trouvée → prendre la dernière
        if (!targetRow) {
            targetRow = rows[rows.length - 1];
        }
        const code_article = targetRow.children[4];
        const nom_article = targetRow.children[5];
        const fournisseur = targetRow.children[3];

        const elements = optionChoisie.value.split('#');
        
        code_article.innerText   = elements[1];
        nom_article.innerText   = optionChoisie.textContent;

        if (fournisseur && elements[0]) {
            recuperer_fournisseur(elements[0], fournisseur);
        }
}

function recuperer_fournisseur(code_fournisseur, elementFournisseur) {
    fetch(`http://127.0.0.1:5000/get_fournisseur`)
        .then(response => response.json())
        .then(data => {
            if (data.list && Array.isArray(data.list)) {
                data.list.forEach(fournisseur => {
                    if(fournisseur.id==code_fournisseur){
                        console.log(data);
                        // Afficher le nom du fournisseur
                        elementFournisseur.innerText = fournisseur.fullname;
                        console.log("Fournisseur récupéré:", data);
                    }
                });
            } else {
                console.error("Format de données inattendu");
            }
        })
        .catch(error => {
            console.error("Erreur lors de la récupération du fournisseur:", error);
            elementFournisseur.innerText = "Erreur";
        });
}

function afficherListeFiltre(articles) {
    // CORRECTION : changer l'ID pour éviter le conflit avec le select
    let listeDiv = document.getElementById('liste-articles-filtre');
    
    if (!listeDiv) {
        listeDiv = document.createElement('div');
        listeDiv.id = 'liste-articles-filtre';
        listeDiv.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            border: 2px solid #333;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            z-index: 9999;
            max-height: 400px;
            overflow-y: auto;
        `;
        document.body.appendChild(listeDiv);
    }
    
    listeDiv.innerHTML = '<h3>Articles trouvés (dites le numéro) :</h3>';
    
    const ul = document.createElement('ul');
    ul.style.cssText = 'list-style: none; padding: 0;';
    
    articles.forEach((opt, index) => {
        const li = document.createElement('li');
        li.style.cssText = 'padding: 8px; margin: 5px 0; background: #f0f0f0; border-radius: 4px;';
        li.textContent = `${index + 1}. ${opt.textContent}`;
        ul.appendChild(li);
    });
    
    listeDiv.appendChild(ul);
}

let magasinsFiltre = ["AMPEFILOHA","AMPITATAFIKA","AMPITATAFIKA","ANDOHARANOFOTSY","BYPASS","ANALAMAHITSY","ANALAKELY","ANDRAVOAHANGY","SABOTSY NAMEHANA","67 HA","AMBOHIPO","MAHAZO",""];
function afficher_magasins(magasins){
// CORRECTION : changer l'ID pour éviter le conflit avec le select
    let listeDiv = document.getElementById('liste-magasins-filtre');
    
    if (!listeDiv) {
        listeDiv = document.createElement('div');
        listeDiv.id = 'liste-magasins-filtre';
        listeDiv.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            border: 2px solid #333;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            z-index: 9999;
            overflow-y: hidden;
        `;
        document.body.appendChild(listeDiv);
    }
    
    listeDiv.innerHTML = '<h3>Magasins trouvés (dites le numéro) :</h3>';
    
    const ul = document.createElement('ul');
    ul.style.cssText = 'list-style: none; padding: 0;';
    
    const li1 = document.createElement('li');
    li1.style.cssText = 'padding: 8px; margin: 5px 0; background: #f0f0f0; border-radius: 4px;';
    li1.textContent = `1. AMPEFILOHA`;
    ul.appendChild(li1);
    
    const li2 = document.createElement('li');
    li2.style.cssText = 'padding: 8px; margin: 5px 0; background: #f0f0f0; border-radius: 4px;';
    li2.textContent = `2. AMPITATAFIKA`;
    ul.appendChild(li2);

    const li3 = document.createElement('li');
    li3.style.cssText = 'padding: 8px; margin: 5px 0; background: #f0f0f0; border-radius: 4px;';
    li3.textContent = `3. ANDOHARANOFOTSY`;
    ul.appendChild(li3);

    const li4 = document.createElement('li');
    li4.style.cssText = 'padding: 8px; margin: 5px 0; background: #f0f0f0; border-radius: 4px;';
    li4.textContent = `4. BYPASS`;
    ul.appendChild(li4);

    const li5 = document.createElement('li');
    li5.style.cssText = 'padding: 8px; margin: 5px 0; background: #f0f0f0; border-radius: 4px;';
    li5.textContent = `5. ANALAMAHITSY`;
    ul.appendChild(li5);

    const li6 = document.createElement('li');
    li6.style.cssText = 'padding: 8px; margin: 5px 0; background: #f0f0f0; border-radius: 4px;';
    li6.textContent = `6. ANALAKELY`;
    ul.appendChild(li6);

    const li7 = document.createElement('li');
    li7.style.cssText = 'padding: 8px; margin: 5px 0; background: #f0f0f0; border-radius: 4px;';
    li7.textContent = `7. ANDRAVOAHANGY`;
    ul.appendChild(li7);

    const li8 = document.createElement('li');
    li8.style.cssText = 'padding: 8px; margin: 5px 0; background: #f0f0f0; border-radius: 4px;';
    li8.textContent = `8. SABOTSY NAMEHANA`;
    ul.appendChild(li8);

    const li9 = document.createElement('li');
    li9.style.cssText = 'padding: 8px; margin: 5px 0; background: #f0f0f0; border-radius: 4px;';
    li9.textContent = `9. 67 HA`;
    ul.appendChild(li9);

    const li10 = document.createElement('li');
    li10.style.cssText = 'padding: 8px; margin: 5px 0; background: #f0f0f0; border-radius: 4px;';
    li10.textContent = `10. AMBOHIPO`;
    ul.appendChild(li10);

    const li11 = document.createElement('li');
    li11.style.cssText = 'padding: 8px; margin: 5px 0; background: #f0f0f0; border-radius: 4px;';
    li11.textContent = `11. MAHAZO`;
    ul.appendChild(li11);
    
    listeDiv.appendChild(ul);
}

function selectionnermagasin(numero){
    console.log("Numéro choisi:", numero);
    
    if (numero < 1 || numero > magasinsFiltre.length) {
        console.log("Numéro invalide");
        return;
    }
    
    const choix = magasinsFiltre[numero - 1];
    let code = '';

    switch(numero){
        case 1 :code=180188;break;
        case 2 :code=180170;break;
        case 3 :code=180189;break;
        case 4 :code=187823;break;
        case 5 :code=180190;break;
        case 6 :code=180186;break;
        case 7 :code=186109;break;
        case 8 :code=180191;break;
        case 9 :code=180192;break;
        case 10 :code=181290;break;
        case 11 :code=183405;break;
    }
        
    let rows = document.querySelectorAll("#table-body tr");
    if (!rows.length) return;

    let targetRow = null;

    rows.forEach(row => {
        const tdClient = row.children[3];
        if (tdClient && tdClient.innerText.trim() === "" && !targetRow) {
            targetRow = row;
        }
    });

    // si aucune ligne vide trouvée → prendre la dernière
    if (!targetRow) {
        targetRow = rows[rows.length - 1];
    }

    const tdDate = targetRow.children[1];   // colonne Date

    // Date du jour (YYYY-MM-DD)
    let d = new Date();
    let date =
        d.getFullYear() + "-" +
        String(d.getMonth() + 1).padStart(2, "0") + "-" +
        String(d.getDate()).padStart(2, "0");

    // ✅ écrire la date
    tdDate.innerText = date;

    const tdtsena = targetRow.children[2]; // colonne code tsena
    const tdNumFact = targetRow.children[0]; // colonne numero facture
    const tdDepot = targetRow.children[11]; // colonne depot
    const tdAffaire = targetRow.children[12]; // colonne affaire

    recup_code_tsena(code, data => {
        const lblMagasin = document.querySelector(".lblmagasin");
        const lbldepot = document.querySelector(".lbldepot");
        const lblaffaire = document.querySelector(".lblaffaire");
        const lblnumfact = document.querySelector(".lblnum_fact");

        lblMagasin.innerText = data.code_tsena;
        lbldepot.innerText = data.depot;
        lblaffaire.innerText = data.affaire;
        lblnumfact.innerText = data.num_fact;

        const rec = lblMagasin.innerText;
        const rec1 = lbldepot.innerText;
        const rec2 = lblaffaire.innerText;
        const rec3 = lblnumfact.innerText;

        tdtsena.innerText   = rec;
        tdDepot.innerText   = rec1;
        tdAffaire.innerText = rec2;
        tdNumFact.innerText = rec3;

        nom_tsena=data.nom_tsena;

        const select = document.getElementById('articleSelect');
        select.innerHTML = '';

        fetch(`http://127.0.0.1:5000/get_stock?name_tsena=${encodeURIComponent(data.nom_tsena)}`)
        .then(response => response.json())
        .then(data => {
            if (data.list && Array.isArray(data.list)) {
                data.list.forEach(article => {
                    if (article.name) {
                        const option = document.createElement('option');
                        option.value = article.id_supplier+"#"+article.article_reference;
                        option.textContent = article.n_product;
                        //option.value = article.id;
                        //option.textContent = article.name;
                        select.appendChild(option);
                        
                    }
                });
            } else {
                console.error("Format de données inattendu");
            }
        })

    });
       
    
    // Fermer la liste
    const listeDiv = document.getElementById('liste-magasins-filtre');
    if (listeDiv) {
        listeDiv.remove();
    }
}

let choixDebut = ["VENTE", "ACHAT"];
function afficherDebut() {
    let listeDiv = document.getElementById('liste-debut-filtre');
    
    if (!listeDiv) {
        listeDiv = document.createElement('div');
        listeDiv.id = 'liste-debut-filtre';
        listeDiv.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            border: 2px solid #333;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            z-index: 9999;
            max-height: 400px;
            overflow-y: auto;
        `;
        document.body.appendChild(listeDiv);
    }
    
    listeDiv.innerHTML = '<h3>Choisissez (dites le numéro) :</h3>';
    
    const ul = document.createElement('ul');
    ul.style.cssText = 'list-style: none; padding: 0;';
    
    const li1 = document.createElement('li');
    li1.style.cssText = 'padding: 8px; margin: 5px 0; background: #f0f0f0; border-radius: 4px;';
    li1.textContent = `1. VENTE`;
    ul.appendChild(li1);
    
    const li2 = document.createElement('li');
    li2.style.cssText = 'padding: 8px; margin: 5px 0; background: #f0f0f0; border-radius: 4px;';
    li2.textContent = `2. ACHAT`;
    ul.appendChild(li2);

    listeDiv.appendChild(ul);
}

function selectionnerDebut(numero) {
    console.log("Numéro choisi:", numero);
    
    if (numero < 1 || numero > choixDebut.length) {
        console.log("Numéro invalide");
        return;
    }
    
    const choix = choixDebut[numero - 1];
    
    // Afficher dans .lbltype
    const lbltype = document.querySelector('.lbltype');
    if (lbltype) {
        lbltype.innerText = "Type :"+choix;
        console.log("Type sélectionné:", choix);
    }
    
    // Fermer la liste
    const listeDiv = document.getElementById('liste-debut-filtre');
    if (listeDiv) {
        listeDiv.remove();
    }

    afficher_magasins();
}

const motsVersChiffres = {
    'zéro': '0', 'zero': '0',
    'un': '1', 'une': '1',
    'deux': '2',
    'trois': '3',
    'quatre': '4',
    'cinq': '5',
    'six': '6',
    'sept': '7',
    'huit': '8',
    'neuf': '9',
    'dix': '10',
    'onze': '11',
    'douze': '12',
    'treize': '13',
    'quatorze': '14',
    'quinze': '15',
    'seize': '16',
    'dix-sept': '17', 'dix sept': '17',
    'dix-huit': '18', 'dix huit': '18',
    'dix-neuf': '19', 'dix neuf': '19',
    'vingt': '20',
    'trente': '30',
    'quarante': '40',
    'cinquante': '50',
    'soixante': '60',
    'soixante-dix': '70', 'soixante dix': '70',
    'quatre-vingt': '80', 'quatre vingt': '80',
    'quatre-vingt-dix': '90', 'quatre vingt dix': '90',
    'cent': '100',
    'mille': '1000'
};

// Fonction de conversion
function convertirMotsEnChiffres(texte) {
    const texteLower = texte.toLowerCase().trim();
    
    // Si c'est déjà un chiffre, retourner tel quel
    if (/^\d+$/.test(texteLower)) {
        return texteLower;
    }
    
    // Si c'est un mot connu, le convertir
    if (motsVersChiffres[texteLower]) {
        return motsVersChiffres[texteLower];
    }
    
    // Gérer les nombres composés (ex: "vingt-trois")
    const mots = texteLower.split(/[\s-]+/);
    let total = 0;
    
    for (const mot of mots) {
        if (motsVersChiffres[mot]) {
            const valeur = parseInt(motsVersChiffres[mot], 10);
            if (valeur >= 100) {
                total *= valeur;
            } else {
                total += valeur;
            }
        }
    }
    
    if (total > 0) {
        return total.toString();
    }
    
    // Si aucune conversion, retourner le texte original
    return texte;
}

let recup="";

function traiterCommande(transcript) {
    transcript = transcript.trim().toLowerCase();

    const cmd = transcript
        .toLowerCase()
        .replace(/[.,!?]/g, "")
        .trim();

    if(cmd=="ligne" || cmd=="lignes"){
        ajouterLigne();
    }else if (cmd.startsWith("article") || cmd.startsWith("Article")) {
         const motCle = cmd.replace("article", "").trim();
    
        if (motCle) {
            filtrerArticles(motCle);
        }
    } else if (/^\d+$/.test(convertirMotsEnChiffres(cmd))) {
        const numero = parseInt(convertirMotsEnChiffres(cmd));
    
        // Vérifier si la liste de début est affichée
        const listeDebut = document.getElementById('liste-debut-filtre');
        
        if (listeDebut) {
            // Si la liste de début est affichée, sélectionner vente/achat
            selectionnerDebut(numero);
            recup="1";
        } else if (articlesFiltre.length > 0) {
            // Sinon, sélectionner un article
            if(recup != ""){
                selectionnerArticleParNumero(numero);
            }
        } else if (magasinsFiltre.length > 0) {
            // Sinon, sélectionner un magasin

            if(recup != ""){
                selectionnermagasin(numero);
            }
        }
    }else if(cmd=="envoyer"){
        exporterTXT();
    }else if(cmd.includes("nouvelle")){
        reinitialiser(); 
    }else if(cmd.includes("quantité")){
        const qteMatch = cmd.match(/quantité?\s*(\d+(?:[.,]\d+)?)\b/i);
        let code=0;
        if (qteMatch) {
            code = Number(convertirMotsEnChiffres(qteMatch[1]));
            console.log(code); 
        }

        let rows = document.querySelectorAll("#table-body tr");
        if (!rows.length) return;

        let targetRow = null;

        // chercher la ligne "vide" (colonne client vide)
        rows.forEach(row => {
            const tdClient = row.children[3]; // colonne Nom client
            if (tdClient && tdClient.innerText.trim() === "" && !targetRow) {
                targetRow = row;
            }
        });

        // si aucune ligne vide trouvée → prendre la dernière
        if (!targetRow) {
            targetRow = rows[rows.length - 1];
        }
        const tdqte = targetRow.children[6]; // colonne qte article
        console.log("Qte reçu :", code);
        tdqte.innerText = code;
        calculerTTC();
    }else if(cmd.includes("tarif")){
        // Regex corrigée pour capturer le nombre après "prix"
        const prixMatch = cmd.match(/tarif\s*,?\s*(\d+(?:[.,]\d+)?)/i);
        let prix = 0;
        
        if (prixMatch) {
            // Remplacer la virgule par un point pour Number()
            prix = Number(prixMatch[1].replace(',', '.'));
            console.log("Prix extrait:", prix); 
        } else {
            console.log("Aucun prix trouvé dans:", cleanCmd);
            return;
        }

        let rows = document.querySelectorAll("#table-body tr");
        if (!rows.length) return;

        let targetRow = null;

        // chercher la ligne "vide" (colonne client vide)
        rows.forEach(row => {
            const tdClient = row.children[3]; // colonne Nom client
            if (tdClient && tdClient.innerText.trim() === "" && !targetRow) {
                targetRow = row;
            }
        });

        // si aucune ligne vide trouvée → prendre la dernière
        if (!targetRow) {
            targetRow = rows[rows.length - 1];
        }
        
        const tdpu = targetRow.children[7]; // colonne PU
        console.log("Prix reçu :", prix);
        tdpu.innerText = prix;
        calculerTTC();
    }else if(cmd.includes("remise") || cmd.includes("remises")){
        const remiseMatch = cmd.match(/\bremises?\s+(\d+)\b/i);
        if (!remiseMatch) {
            console.warn("Aucune remise trouvée dans la commande :", cmd);
            return;
        }

        const code = convertirMotsEnChiffres(remiseMatch[1]);
        console.log("Remise reçue :", code);

        let rows = document.querySelectorAll("#table-body tr");
        if (!rows.length) return;

        let targetRow = Array.from(rows).find(row => {
            const tdClient = row.children[3];
            return tdClient && tdClient.innerText.trim() === "";
        }) || rows[rows.length - 1];

        const tdremise = targetRow.children[8];
        if (tdremise) {
            tdremise.innerText = code;
            calculerTTC();
        }

    }
}

function recup_client(code, callback) {
    fetch(`/get_client?code=${encodeURIComponent(code)}`)
        .then(r => r.json())
        .then(data => callback(data.nom || ""));
}

function reinitialiser(){
    // Réinitialiser le label
    const lbltype = document.querySelector(".lblType");
    lbltype.innerHTML = "Type :";

    // Réinitialiser le tableau
    const tableBody = document.getElementById("table-body");
    tableBody.innerHTML = ""; // vide toutes les lignes existantes

    // Créer une nouvelle ligne vide
    const nouvelleLigne = document.createElement("tr");
    nouvelleLigne.classList.add("ligne");
    nouvelleLigne.style.fontSize = "14px";

    // Ajouter les 13 cellules comme dans ton HTML
    for (let i = 0; i < 13; i++) {
        const td = document.createElement("td");

        // rendre certaines cellules éditables
        if ([0,1,3,4,5,6,7,8].includes(i)) td.contentEditable = "true";
        if (i === 1) td.setAttribute("onfocus", "init()");
        if ([6,7,8].includes(i)) td.setAttribute("oninput", "calculerTTC()");
        if (i === 9) td.classList.add("tot_ttc");
        if ([10,11,12].includes(i)) td.style.visibility = "hidden";

        nouvelleLigne.appendChild(td);
    }

    tableBody.appendChild(nouvelleLigne);
}

function recup_code_tsena(code, callback) {
    fetch(`/get_tsena?code=${encodeURIComponent(code)}`)
    .then(r => r.json())
    .then(data => {
        console.log(data);
        if (callback) callback(data);
    })
    .catch(err => {
        console.error("Erreur récupération article :", err);
        if (callback) callback({
            code_tsena: "",
            depot: "",
            affaire: "",
            nom_tsena: "",
            num_fact: ""
        });
    });

    const idPointOfSale =code;
        fetch(`/get_stock?id_point_of_sale=${idPointOfSale}`)
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('articleSelect');
            //console.log("Articles reçus:", data);
            
            if (data.list && Array.isArray(data.list)) {
                data.list.forEach(article => {
                    const option = document.createElement('option');
                    option.value = article.id_supplier+"#"+article.article_reference;
                    option.textContent = article.n_product;
                    //option.value = article.name;
                    //option.textContent = article.name;
                    select.appendChild(option);
                });
            } else {
                console.error("Format de données inattendu");
            }
        })
        .catch(err => console.error("Erreur chargement fournisseurs :", err));
}

function ajouterLigne() {
    let tbody = document.getElementById("table-body");

    let newRow = document.createElement("tr");
    newRow.classList.add("ligne");
    newRow.style.fontSize = "14px"; 

    for (let i = 0; i < 13; i++) {
        let td = document.createElement("td");

        if (i == 9) {
            td.classList.add("tot_ttc");
            td.contentEditable = "false";
        }

        if (i == 0) {
            const lblnumfact = document.querySelector(".lblnum_fact");

            if (!lblnumfact) {
                console.warn("⚠ lblnumfact introuvable !");
            } else {
                const rec = lblnumfact.textContent; // plus fiable que innerText pour éléments invisibles
                console.log("Valeur récupérée :", rec);

                if (td) {
                    td.textContent = rec;
                } else {
                    console.warn("⚠ td introuvable !");
                }
            }
        }

        if (i == 2) {
            const lblmagasin = document.querySelector(".lblmagasin");

            if (!lblmagasin) {
                console.warn("⚠ lblmagasin introuvable !");
            } else {
                const rec = lblmagasin.textContent; // plus fiable que innerText pour éléments invisibles
                console.log("Valeur récupérée :", rec);

                if (td) {
                    td.textContent = rec;
                } else {
                    console.warn("⚠ td introuvable !");
                }
            }
        }

        // ------------------------
        if (i == 10 || i == 11 || i == 12) {
            td.style.visibility = "hidden";
            td.contentEditable = "false";

            if (i == 11) {
                const lbldepot = document.querySelector(".lbldepot");

                if (!lbldepot) {
                    console.warn("⚠ lbldepot introuvable !");
                } else {
                    const rec = lbldepot.textContent; // plus fiable que innerText pour éléments invisibles
                    console.log("Valeur récupérée :", rec);

                    if (td) {
                        td.textContent = rec;
                    } else {
                        console.warn("⚠ td introuvable !");
                    }
                }
            }

             if (i == 12) {
                const lblaffaire = document.querySelector(".lblaffaire");

                if (!lblaffaire) {
                    console.warn("⚠ lblaffaire introuvable !");
                } else {
                    const rec = lblaffaire.textContent; // plus fiable que innerText pour éléments invisibles
                    console.log("Valeur récupérée :", rec);

                    if (td) {
                        td.textContent = rec;
                    } else {
                        console.warn("⚠ td introuvable !");
                    }
                }
            }

        }

        // ------------------------
        // Colonnes 7, 8, 9 : recalcul automatique du TTC
        // (Qté, PU, Remise)
        // ------------------------
        if (i == 6 || i == 7 || i == 8) {
            td.addEventListener("input", calculerTTC);
            td.contentEditable = "true";
        }

        // ------------------------
        // Colonne 1 : date du jour auto
        // ------------------------
        if (i == 1) {
            let d = new Date();
            let date =
                d.getFullYear() + "-" +
                String(d.getMonth() + 1).padStart(2, "0") + "-" +
                String(d.getDate()).padStart(2, "0");

            td.innerText = date;
            td.contentEditable = "true"; // si tu veux pouvoir changer la date
        }

        // ------------------------
        // Autres colonnes éditables
        // ------------------------
        if (td.contentEditable !== "false") {
            td.contentEditable = "true";
        }

        newRow.appendChild(td);
    }

    tbody.appendChild(newRow);

    // Mise à jour automatique du Code Tsena pour la nouvelle ligne
    recup_code_tsena();
}


function init(){
    let trs = document.querySelectorAll("#table-body tr");

    trs.forEach(tr => {
        let d = new Date();
        let date =
            d.getFullYear() + "-" +
            String(d.getMonth() + 1).padStart(2, "0") + "-" +
            String(d.getDate()).padStart(2, "0");

        let td = document.activeElement;
        td.innerText = date;

    });
}

function calculerTTC(){
    let trs = document.querySelectorAll("#table-body tr");

    trs.forEach(tr => {
        let tds = tr.querySelectorAll("td");

        //if (tds[4].innerText.trim() !== "") { // Si Réf article non vide
            let qte = tds[6].innerText.trim();
            let pu = tds[7].innerText.trim();
            let remise = tds[8].innerText.trim();

            let mtt = Number(qte) * Number(pu) * (1 - Number(remise)/100);

            tds[9].innerText = mtt.toFixed(2);
        //}
    });
}

function clean(str) {
    return str
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/[^\w.-]/g, "_");
}

function clean(str) {
    return str.replace(/[^a-z0-9-_]/gi, '_');
}

function exporterTXT() {
    alert("Felana");
    let trs = document.querySelectorAll("#table-body tr");
    let lines = [];

    const lblMagasin = document.querySelector(".lblmagasin");
    const lbltype = document.querySelector(".lblType");
    const rec = lblMagasin ? lblMagasin.innerText.trim() : "unknown";
    const recs = lbltype ? lbltype.innerText.trim() : "unknown";
    let nomClient = "";
    let dateFact = "";

    trs.forEach(tr => {
        let tds = tr.querySelectorAll("td");
        if (tds[3].innerText.trim() !== "") {
            let numFact = tds[0].innerText.trim();
            dateFact = tds[1].innerText.trim();
            nomClient = tds[3].innerText.trim();
            let tsena = tds[2].innerText.trim();
            let ref = tds[4].innerText.trim();
            let article = tds[5].innerText.trim();
            let qte = tds[6].innerText.trim();
            let pu = tds[7].innerText.trim();
            let remise = tds[8].innerText.trim();
            let depot = tds[11].innerHTML;
            let affaire = tds[12].innerHTML;

            let mtt = Number(qte) * Number(pu) * (1 - Number(remise)/100);

            if (recs.includes("vente")){
                lines.push(
                    `0\t7\t${numFact}\t${dateFact}\t${tsena}\t${nomClient}\t${ref}\t${article}\t${qte}\t${pu}\t${mtt.toFixed(2)}\t${remise}\t0\t${depot}\t${affaire}\t1`
                );
            }else{
                lines.push(
                    `0\t6\t${numFact}\t${dateFact}\t${tsena}\t${nomClient}\t${ref}\t${article}\t${qte}\t${pu}\t${mtt.toFixed(2)}\t${remise}\t0\t${depot}\t${affaire}\t1`
                );
            }
        }
    });

    const content = lines.join("\n");
    let filename ='';

    if (recs.includes("vente")){
        filename = `VENTE_${rec}_${nomClient}_${dateFact}.txt`;
    }else{
        filename = `ACHAT_${rec}_${nomClient}_${dateFact}.txt`;
    }

    
    // ✅ Création du blob **avant** de l’utiliser
    const blob = new Blob([content], { type: "text/plain" });

    const formData = new FormData();
    formData.append("file", blob, filename);
    formData.append("rec", rec);
    formData.append("recs", recs);
    formData.append("nom_client", nomClient);
    formData.append("date_fact", dateFact);

    
    fetch("/upload", { method: "POST", body: formData })
        .then(response => response.blob())
        .then(blob => {  // ce blob est différent du précédent, c'est la réponse du serveur
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            URL.revokeObjectURL(url);
        })
        .catch(err => console.error("Erreur upload:", err));
}

