let recognition;
let isListening = false;
let recs_tsena= "";
let rec_souche="";
let recup_tsena="";
let rec_code_tsena="";
let rec_depot="";
let rec_num_fact="";
let rec_affaire="";

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

    const connection_internet = document.getElementById("connexion");
    let wasOffline = false;

    setInterval(() => {
        fetch("https://www.google.com", { method: "HEAD", mode: "no-cors", cache: "no-cache" })
            .then(() => {
                if (wasOffline) {
                    wasOffline = false;
                    connection_internet.innerHTML = "✅ Internet OK";
                    location.reload();
                    connection_internet.innerHTML = "✅ Internet OK";
                } else {
                    connection_internet.innerHTML = "✅ Internet OK";
                }
            })
            .catch(() => {
                wasOffline = true;
                connection_internet.innerHTML = "❌ Pas d'internet";
            });
    }, 3000);
});


if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();

    recognition.lang = "fr-FR";
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

    recognition.onend = () => {
        if (isListening) {
            setTimeout(() => {
                try {
                    recognition.start();
                } catch(e) {
                    if (e.name !== 'InvalidStateError') {
                        console.error("Mic restart error:", e);
                    }
                }
            }, 300);
        } else {
            const btn = document.getElementById("micBtn");
            btn.classList.remove("listening");
            btn.innerText = "🎤 Commencer";
        }
    };

    recognition.onerror = (event) => {
        // 'aborted' = interruption normale, pas une vraie erreur
        if (event.error === 'aborted') return;

        // 'no-speech' = silence, on laisse onend relancer tout seul
        if (event.error === 'no-speech') return;

        // Erreurs bloquantes : on coupe tout
        if (event.error === 'not-allowed' || event.error === 'audio-capture') {
            console.error("Micro inaccessible :", event.error);
            isListening = false; // ← empêche onend de relancer
            const btn = document.getElementById("micBtn");
            btn.classList.remove("listening");
            btn.innerText = "🎤 Commencer";
            return;
        }

        // Autres erreurs : log seulement, onend s'occupe du restart
        console.warn("Erreur reconnaissance :", event.error);
    };
}

function isMobile() {
    return /Android|iPhone|iPad|iPod/i.test(navigator.userAgent) 
        || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
}

function handleMicClick() {
    if (isMobile()) {
        toggleListenings();
    } else {
        toggleListening();
    }
}

function toggleListenings() {
    let btn = document.getElementById("micBtn");

    if (!recognition) {
        alert("La reconnaissance vocale n'est pas supportée sur ce navigateur.");
        return;
    }

    if (!isListening) {
        recognition.lang = 'fr-FR';
        recognition.continuous = false;
        recognition.interimResults = false;

        // Définir onend AVANT start() pour éviter la race condition
        recognition.onend = () => {
            if (isListening) {
                recognition.start();
            }
        };

        const ctype = document.getElementById('type');
        
        afficherDebuts();

        setTimeout(() => {
            recognition.start();
        }, 100);

        isListening = true;
        btn.classList.add("listening");
        btn.innerText = "⏸️ Arrêter";

    } else {
        isListening = false;
        recognition.onend = null;
        recognition.stop();
        btn.classList.remove("listening");
        btn.innerText = "🎤 Commencer";
    }
}

function toggleListening() {
    let btn = document.getElementById("micBtn");

    if(btn.innerText != "⏸️ Arrêter"){
        afficherDebuts();
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
    
    const options = Array.from(selectArticle.options);
    
    // Normaliser motCle en tableau de mots
    const mots = Array.isArray(motCle) 
        ? motCle.map(m => m.toLowerCase())
        : String(motCle).toLowerCase().split(/[\s,]+/).filter(m => m.length > 0);

    // Filtrer les articles
    articlesFiltre = options.filter(option => {
        const texte = option.textContent.toLowerCase();
        return mots.some(mot => texte.includes(mot));
    });
    
    // Afficher/Cacher les options
    options.forEach(option => {
        const texte = option.textContent.toLowerCase();
        const visible = mots.some(mot => texte.includes(mot));
        option.style.display = visible ? "" : "none";
    });
    
    // Afficher la liste numérotée
    afficherListeFiltre(articlesFiltre);
    
    const select = document.getElementById('fournisseurSelect');
    if (select) {
        select.dispatchEvent(new Event('change', { bubbles: true }));
    }

    console.log(`${articlesFiltre.length} articles trouvés avec "${motCle}"`);
}

let fournisseurFiltre = [];

function afficherListeFiltre(articles) {
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
            width: 90vw;
            max-width: 1200px;
            max-height: 85vh;
        `;
        document.body.appendChild(listeDiv);
    }

    listeDiv.innerHTML = '<h3 style="margin-bottom: 15px; font-size: 1.5rem;">Articles trouvés (dites le numéro ou cliquez) :</h3>';

    // ✅ Définir le nombre de colonnes selon le nombre d'articles
    const nbArticles = articles.length;
    let nbColonnes = 3; // Par défaut 3 colonnes

    if (nbArticles > 100) {
        nbColonnes = 5;
    } else if (nbArticles > 50) {
        nbColonnes = 4;
    }

    // ✅ Container avec colonnes fixes
    const columnsContainer = document.createElement('div');
    columnsContainer.style.cssText = `
        display: grid;
        grid-template-columns: repeat(${nbColonnes}, 1fr);
        gap: 10px;
        max-height: calc(85vh - 100px);
        overflow-y: auto;
    `;

    articles.forEach((opt, index) => {
        const div = document.createElement('div');
        div.style.cssText = `
            padding: 12px 15px;
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            font-size: 0.42rem;
            cursor: pointer;
            transition: all 0.2s;
            text-align: left;
        `;
        
        div.textContent = `${index + 1}. ${opt.textContent}`;
        
        // ✅ Hover effect
        div.addEventListener('mouseenter', () => {
            div.style.background = '#007bff';
            div.style.color = 'white';
            div.style.transform = 'scale(1.02)';
        });
        
        div.addEventListener('mouseleave', () => {
            div.style.background = '#f8f9fa';
            div.style.color = 'black';
            div.style.transform = 'scale(1)';
        });
        
        // ✅ Clic sur l'article
        div.addEventListener('click', () => {
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
            const code_article = targetRow.children[6];
            const nom_article = targetRow.children[7];
            

            if(opt.textContent.includes('/')){
                const elements = opt.textContent.split('/');
                
                code_article.innerText   = elements[0];
                if(elements.length>2){
                    nom_article.innerText   = elements[1]+"/"+elements[2];
                }else{
                    nom_article.innerText   = elements[1];
                }
            }else{
                nom_article.innerText   = opt.textContent;
            }
            // Sélectionner l'article dans le select original
            const select = document.getElementById('articleSelect');
            if (select) {
                select.value = opt.value;
                // Déclencher l'événement change si nécessaire
                select.dispatchEvent(new Event('change', { bubbles: true }));
            }
            
            // Fermer la popups
            listeDiv.remove();
            const lblfournisseur = document.querySelector(".lblfournisseur");

            if (lblfournisseur && lblfournisseur.innerText.trim() === "") {
                recupererFournisseurs();
            }else{
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
                        width: 90vw;
                        max-width: 1200px;
                        max-height: 85vh;
                    `;
                    document.body.appendChild(listeDiv);
                }

                listeDiv.innerHTML = '<h3 style="margin-bottom: 15px; font-size: 1.5rem;">Articles trouvés (dites le numéro ou cliquez) :</h3>';

                listeDiv.innerHTML = `
                <label for="quantite-input" style="font-size: 0.8rem; font-weight: bold; display: block; margin: 15px 0 10px;">
                    Quelle quantité ?
                </label>
                <input 
                    type="number" 
                    id="quantite-input" 
                    placeholder="Entrez la quantité"
                    min="0"
                    value="0"
                    autofocus
                    style="
                        width: 100%;
                        padding: 12px;
                        font-size: 0.8rem;
                        border: 2px solid #007bff;
                        border-radius: 4px;
                        margin-bottom: 15px;
                    "
                />

                <label for="pu-input" style="font-size: 0.8rem; font-weight: bold; display: block; margin: 15px 0 10px;">
                    Quel PU ?
                </label>
                <input 
                    type="number" 
                    id="pu-input" 
                    placeholder="Entrez le PU"
                    min="0"
                    value="0"
                    autofocus
                    style="
                        width: 30%;
                        padding: 12px;
                        font-size: 0.8rem;
                        border: 2px solid #007bff;
                        border-radius: 4px;
                        margin-bottom: 15px;
                    "
                />

                <label for="remise-input" style="font-size: 0.8rem; font-weight: bold; display: block; margin: 15px 0 10px;">
                    Quelle remise ?
                </label>
                <input 
                    type="number" 
                    id="remise-input" 
                    placeholder="Entrez la remise"
                    min="0"
                    value="0"
                    autofocus
                    style="
                        width: 30%;
                        padding: 12px;
                        font-size: 0.8rem;
                        border: 2px solid #007bff;
                        border-radius: 4px;
                        margin-bottom: 15px;
                    "
                />

                <button id="valider-quantite" style="
                    width: 30%;
                    padding: 12px;
                    font-size: 0.8rem;
                    background: #28a745;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                ">
                    ✓ Valider
                </button>
            `;
            
            // Bouton valider
            document.getElementById('valider-quantite').addEventListener('click', () => {
                const quantite = document.getElementById('quantite-input').value || 0;
                const pu = document.getElementById('pu-input').value || 0;
                const remise = document.getElementById('remise-input').value || 0;

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
                const tdqte = targetRow.children[8]; // colonne qte article
                console.log("Qte reçu :", quantite);
                tdqte.innerText = quantite;

                const tdpu = targetRow.children[9]; // colonne pu article
                console.log("PU reçu :", pu);
                tdpu.innerText = pu;

                const tdremise = targetRow.children[10]; // colonne remise article
                console.log("Remise reçu :", remise);
                tdremise.innerText = remise;

                calculerTTC();

                console.log(`✅ Article : ${opt.textContent}, Quantité : ${quantite}`);
                
                // Sélectionner l'article dans le select
                const select = document.getElementById('articleSelect');
                if (select) {
                    select.value = opt.value;
                    select.dispatchEvent(new Event('change', { bubbles: true }));
                }
                
                // TODO : Envoyer la quantité à votre backend ou stocker dans une variable
                
                listeDiv.remove();
            });
            }
            
        });

        columnsContainer.appendChild(div);
    });

    listeDiv.appendChild(columnsContainer);
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
    const code_article = targetRow.children[6];
    const nom_article = targetRow.children[7];

    if(optionChoisie.textContent.includes('/')){
        const elements = optionChoisie.textContent.split('/');
        
        code_article.innerText   = elements[0];
        if(elements.length>2){
             nom_article.innerText   = elements[1]+"/"+elements[2];
        }else{
             nom_article.innerText   = elements[1];
        }
    }else{
        nom_article.innerText   = optionChoisie.textContent;
    }

    const lblfournisseur = document.querySelector(".lblfournisseur");
    if (lblfournisseur && lblfournisseur.innerText.trim() === "") {
        recupererFournisseurs();
    }else{
        let listeDiv = document.getElementById('liste-fournisseurs-filtre');
        if (!listeDiv) {
            listeDiv = document.createElement('div');
            listeDiv.id = 'liste-fournisseurs-filtre';
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
                width: 90vw;
                max-width: 1200px;
                max-height: 85vh;
            `;
            document.body.appendChild(listeDiv);
        }

        listeDiv.innerHTML = `
            <label for="quantite-input" style="font-size: 0.8rem; font-weight: bold; display: block; margin: 15px 0 10px;">
                Quelle quantité ?
            </label>
            <input 
                type="number" 
                id="quantite-input" 
                placeholder="Entrez la quantité"
                min="0"
                value="0"
                autofocus
                style="
                    width: 100%;
                    padding: 12px;
                    font-size: 0.8rem;
                    border: 2px solid #007bff;
                    border-radius: 4px;
                    margin-bottom: 15px;
                "
            />

            <label for="pu-input" style="font-size: 0.8rem; font-weight: bold; display: block; margin: 15px 0 10px;">
                Quel PU ?
            </label>
            <input 
                type="number" 
                id="pu-input" 
                placeholder="Entrez le PU"
                min="0"
                value="0"
                autofocus
                style="
                    width: 100%;
                    padding: 12px;
                    font-size: 0.8rem;
                    border: 2px solid #007bff;
                    border-radius: 4px;
                    margin-bottom: 15px;
                "
            />

            <label for="remise-input" style="font-size: 0.8rem; font-weight: bold; display: block; margin: 15px 0 10px;">
                Quelle remise ?
            </label>
            <input 
                type="number" 
                id="remise-input" 
                placeholder="Entrez la remise"
                min="0"
                value="0"
                autofocus
                style="
                    width: 100%;
                    padding: 12px;
                    font-size: 0.8rem;
                    border: 2px solid #007bff;
                    border-radius: 4px;
                    margin-bottom: 15px;
                "
            />

            <button id="valider-quantite" style="
                width: 100%;
                padding: 12px;
                font-size: 0.8rem;
                background: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            ">
                ✓ Valider
            </button>
        `;
        
        // Bouton valider
        document.getElementById('valider-quantite').addEventListener('click', () => {
            const quantite = document.getElementById('quantite-input').value || 0;
            const pu = document.getElementById('pu-input').value || 0;
            const remise = document.getElementById('remise-input').value || 0;

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
            const tdqte = targetRow.children[8]; // colonne qte article
            console.log("Qte reçu :", quantite);
            tdqte.innerText = quantite;

            const tdpu = targetRow.children[9]; // colonne pu article
            console.log("PU reçu :", pu);
            tdpu.innerText = pu;

            const tdremise = targetRow.children[10]; // colonne remise article
            console.log("Remise reçu :", remise);
            tdremise.innerText = remise;

            calculerTTC();

            // Sélectionner l'article dans le select
            const select = document.getElementById('articleSelect');
            if (select) {
                select.value = optionChoisie.value;
                select.dispatchEvent(new Event('change', { bubbles: true }));
            }
            
            // TODO : Envoyer la quantité à votre backend ou stocker dans une variable
            
            listeDiv.remove();
        });
    }
}

function selectionnerFournisseurParNumero(numero) {
    console.log("Numéro reçu:", numero);
    console.log("Fournisseurs disponibles:", fournisseurFiltre.length);
    
    if (fournisseurFiltre.length === 0) {
        console.log("Aucun fournisseur filtré");
        return;
    }
    
    if (numero < 1 || numero > fournisseurFiltre.length) {
        console.log(`Numéro invalide. Choisissez entre 1 et ${fournisseurFiltre.length}`);
        return;
    }
    
    const selectFournisseur = document.querySelector('#fournisseurSelect');
    if (!selectFournisseur) return;
    
    // Sélectionner l'option correspondante
    const optionChoisie = fournisseurFiltre[numero - 1];
    selectFournisseur.value = optionChoisie.value;

    console.log(`✓ Fournisseur sélectionné : ${optionChoisie.textContent}`);
    
    // Fermer la liste affichée
    const listeDiv = document.getElementById('liste-fournisseurs-filtre');
    
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
    
    const fournisseur = targetRow.children[5];
    const codefournisseur = targetRow.children[4];
    
    const recup=optionChoisie.textContent.split('/');
    codefournisseur.innerText   = recup[0];
    fournisseur.innerText   = recup[1];

    const lblfournisseur = document.querySelector(".lblfournisseur");
    lblfournisseur.innerText= optionChoisie.textContent;

    // Afficher le formulaire quantité
    listeDiv.innerHTML = `
        <label for="quantite-input" style="font-size: 0.8rem; font-weight: bold; display: block; margin: 15px 0 10px;">
            Quelle quantité ?
        </label>
        <input 
            type="number" 
            id="quantite-input" 
            placeholder="Entrez la quantité"
            min="0"
            value="0"
            autofocus
            style="
                width: 100%;
                padding: 12px;
                font-size: 0.8rem;
                border: 2px solid #007bff;
                border-radius: 4px;
                margin-bottom: 15px;
            "
        />

        <label for="pu-input" style="font-size: 0.8rem; font-weight: bold; display: block; margin: 15px 0 10px;">
            Quel PU ?
        </label>
        <input 
            type="number" 
            id="pu-input" 
            placeholder="Entrez le PU"
            min="0"
            value="0"
            autofocus
            style="
                width: 100%;
                padding: 12px;
                font-size: 0.8rem;
                border: 2px solid #007bff;
                border-radius: 4px;
                margin-bottom: 15px;
            "
        />

        <label for="remise-input" style="font-size: 0.8rem; font-weight: bold; display: block; margin: 15px 0 10px;">
            Quelle remise ?
        </label>
        <input 
            type="number" 
            id="remise-input" 
            placeholder="Entrez la remise"
            min="0"
            value="0"
            autofocus
            style="
                width: 100%;
                padding: 12px;
                font-size: 0.8rem;
                border: 2px solid #007bff;
                border-radius: 4px;
                margin-bottom: 15px;
            "
        />

        <button id="valider-quantite" style="
            width: 100%;
            padding: 12px;
            font-size: 0.8rem;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        ">
            ✓ Valider
        </button>
    `;
    
    // Bouton valider
    document.getElementById('valider-quantite').addEventListener('click', () => {
        const quantite = document.getElementById('quantite-input').value || 0;
        const pu = document.getElementById('pu-input').value || 0;
        const remise = document.getElementById('remise-input').value || 0;

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
        const tdqte = targetRow.children[8]; // colonne qte article
        console.log("Qte reçu :", quantite);
        tdqte.innerText = quantite;

        const tdpu = targetRow.children[9]; // colonne pu article
        console.log("PU reçu :", pu);
        tdpu.innerText = pu;

        const tdremise = targetRow.children[10]; // colonne remise article
        console.log("Remise reçu :", remise);
        tdremise.innerText = remise;

        calculerTTC();

        // Sélectionner l'article dans le select
        const select = document.getElementById('articleSelect');
        if (select) {
            select.value = optionChoisie.value;
            select.dispatchEvent(new Event('change', { bubbles: true }));
        }
        
        // TODO : Envoyer la quantité à votre backend ou stocker dans une variable
        
        listeDiv.remove();
    });
}


function afficherFournisseurFiltre(fournisseur) {
    let listeDiv = document.getElementById('liste-fournisseurs-filtre');

    if (!listeDiv) {
        listeDiv = document.createElement('div');
        listeDiv.id = 'liste-fournisseurs-filtre';
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
            width: 90vw;
            max-width: 1200px;
            max-height: 85vh;
            font-size:7px;
        `;
        document.body.appendChild(listeDiv);
    }

    listeDiv.innerHTML = '<h3 style="margin-bottom: 15px; font-size: 1.5rem;">Fournisseurs trouvés (dites le numéro ou cliquez) :</h3>';

    // ✅ Définir le nombre de colonnes selon le nombre de fournisseurs
    const nbFournisseur = fournisseur.length;
    let nbColonnes = 3; // Par défaut 3 colonnes

    if (nbFournisseur > 100) {
        nbColonnes = 5;
    } else if (nbFournisseur > 50) {
        nbColonnes = 4;
    }

    // ✅ Container avec colonnes fixes
    const columnsContainer = document.createElement('div');
    columnsContainer.style.cssText = `
        display: grid;
        grid-template-columns: repeat(${nbColonnes}, 1fr);
        gap: 10px;
        max-height: calc(85vh - 100px);
        overflow-y: auto;
    `;

    fournisseur.forEach((opt, index) => {
        const div = document.createElement('div');
        div.style.cssText = `
            padding: 12px 15px;
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.2s;
            text-align: left;
            font-size:7px;
        `;
        
        div.textContent = `${index + 1}. ${opt.textContent}`;
        
        // ✅ Hover effect
        div.addEventListener('mouseenter', () => {
            div.style.background = '#007bff';
            div.style.color = 'white';
            div.style.transform = 'scale(1.02)';
        });
        
        div.addEventListener('mouseleave', () => {
            div.style.background = '#f8f9fa';
            div.style.color = 'black';
            div.style.transform = 'scale(1)';
        });
        
        // ✅ Clic sur le fournisseur
        div.addEventListener('click', () => {
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

            const fournisseur = targetRow.children[5];
            const codefournisseur = targetRow.children[4];
            
            const recup=opt.textContent.split('/');
            codefournisseur.innerText   = recup[0];
            fournisseur.innerText   = recup[1];
            const lblfournisseur = document.querySelector(".lblfournisseur");
            lblfournisseur.innerText= opt.textContent;

            // Masquer la liste
            columnsContainer.style.display = 'none';

            // Afficher le formulaire quantité
            listeDiv.innerHTML = `
                <h3>Article sélectionné : ${opt.textContent}</h3>
                <label for="quantite-input" style="font-size: 0.8rem; font-weight: bold; display: block; margin: 15px 0 10px;">
                    Quelle quantité ?
                </label>
                <input 
                    type="number" 
                    id="quantite-input" 
                    placeholder="Entrez la quantité"
                    min="0"
                    value="0"
                    autofocus
                    style="
                        width: 100%;
                        padding: 12px;
                        font-size: 0.8rem;
                        border: 2px solid #007bff;
                        border-radius: 4px;
                        margin-bottom: 15px;
                    "
                />

                <label for="pu-input" style="font-size: 0.8rem; font-weight: bold; display: block; margin: 15px 0 10px;">
                    Quel PU ?
                </label>
                <input 
                    type="number" 
                    id="pu-input" 
                    placeholder="Entrez le PU"
                    min="0"
                    value="0"
                    autofocus
                    style="
                        width: 100%;
                        padding: 12px;
                        font-size: 0.8rem;
                        border: 2px solid #007bff;
                        border-radius: 4px;
                        margin-bottom: 15px;
                    "
                />

                <label for="remise-input" style="font-size: 0.8rem; font-weight: bold; display: block; margin: 15px 0 10px;">
                    Quelle remise ?
                </label>
                <input 
                    type="number" 
                    id="remise-input" 
                    placeholder="Entrez la remise"
                    min="0"
                    value="0"
                    autofocus
                    style="
                        width: 100%;
                        padding: 12px;
                        font-size: 0.8rem;
                        border: 2px solid #007bff;
                        border-radius: 4px;
                        margin-bottom: 15px;
                    "
                />

                <button id="valider-quantite" style="
                    width: 100%;
                    padding: 12px;
                    font-size: 0.8rem;
                    background: #28a745;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                ">
                    ✓ Valider
                </button>
            `;
            
            // Bouton valider
            document.getElementById('valider-quantite').addEventListener('click', () => {
                const quantite = document.getElementById('quantite-input').value || 0;
                const pu = document.getElementById('pu-input').value || 0;
                const remise = document.getElementById('remise-input').value || 0;

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
                const tdqte = targetRow.children[8]; // colonne qte article
                console.log("Qte reçu :", quantite);
                tdqte.innerText = quantite;

                const tdpu = targetRow.children[9]; // colonne pu article
                console.log("PU reçu :", pu);
                tdpu.innerText = pu;

                const tdremise = targetRow.children[10]; // colonne remise article
                console.log("Remise reçu :", remise);
                tdremise.innerText = remise;

                calculerTTC();

                console.log(`✅ Article : ${opt.textContent}, Quantité : ${quantite}`);
                
                // Sélectionner l'article dans le select
                const select = document.getElementById('articleSelect');
                if (select) {
                    select.value = opt.value;
                    select.dispatchEvent(new Event('change', { bubbles: true }));
                }
                
                // TODO : Envoyer la quantité à votre backend ou stocker dans une variable
                
                listeDiv.remove();
            });

            // Sélectionner le fournisseur dans le select original
            const select = document.getElementById('fournisseurSelect');
            if (select) {
                select.value = opt.value;
                // Déclencher l'événement change si nécessaire
                select.dispatchEvent(new Event('change', { bubbles: true }));
            }
        });
        
        columnsContainer.appendChild(div);
    });

    listeDiv.appendChild(columnsContainer);
}

function afficherArticles(articles) {

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
            padding: 12px;
            border-radius: 8px;
            box-shadow: 0 6px 20px rgba(0,0,0,0.2);
            z-index: 9999;
            width: 95vw;
            max-width: 1200px;
            max-height: 90vh;
            overflow: hidden;
        `;
        document.body.appendChild(listeDiv);
    }

    const isMobile = window.innerWidth <= 768;

    listeDiv.innerHTML = `
        <h3 style="
            margin-bottom: 15px; 
            font-size: ${isMobile ? "1rem" : "1.5rem"};
        ">
            Articles trouvés (dites le numéro ou cliquez) :
        </h3>
    `;

    const nbArticles = articles.length;
    let nbColonnes;

    if (isMobile) {
        nbColonnes = 1; // Mobile = 1 colonne
    } else {
        nbColonnes = 3;
        if (nbArticles > 100) nbColonnes = 5;
        else if (nbArticles > 50) nbColonnes = 4;
    }

    const columnsContainer = document.createElement('div');
    columnsContainer.style.cssText = `
        display: grid;
        grid-template-columns: repeat(${nbColonnes}, 1fr);
        gap: 8px;
        max-height: calc(90vh - 80px);
        overflow-y: auto;
    `;

    articles.forEach((opt, index) => {

        const div = document.createElement('div');
        div.style.cssText = `
            padding: ${isMobile ? "8px" : "12px"};
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 6px;
            font-size: ${isMobile ? "0.85rem" : "1rem"};
            cursor: pointer;
            transition: all 0.2s;
        `;

        div.textContent = `${index + 1}. ${opt.textContent}`;

        div.addEventListener('mouseenter', () => {
            div.style.background = '#007bff';
            div.style.color = 'white';
            div.style.transform = 'scale(1.02)';
        });

        div.addEventListener('mouseleave', () => {
            div.style.background = '#f8f9fa';
            div.style.color = 'black';
            div.style.transform = 'scale(1)';
        });

        div.addEventListener('click', () => {

            let rows = document.querySelectorAll("#table-body tr");
            if (!rows.length) return;

            let targetRow = null;

            rows.forEach(row => {
                const tdClient = row.children[3];
                if (tdClient && tdClient.innerText.trim() === "" && !targetRow) {
                    targetRow = row;
                }
            });

            if (!targetRow) {
                targetRow = rows[rows.length - 1];
            }

            const code_article = targetRow.children[6];
            const nom_article = targetRow.children[7];

            if (opt.textContent.includes('/')) {
                const elements = opt.textContent.split('/');
                code_article.innerText = elements[0];
                nom_article.innerText = elements.slice(1).join('/');
            } else {
                nom_article.innerText = opt.textContent;
            }

            const select = document.getElementById('articleSelect');
            if (select) {
                select.value = opt.value;
                select.dispatchEvent(new Event('change', { bubbles: true }));
            }

            listeDiv.innerHTML = `
                <label style="font-size:${isMobile ? "1rem" : "1.2rem"}; font-weight:bold;">
                    Quantité
                </label>
                <input type="number" inputmode="decimal"
                    id="quantite-input"
                    min="0" value="0"
                    style="width:100%; padding:10px; font-size:${isMobile ? "1rem" : "1.2rem"}; margin-bottom:12px; border:2px solid #007bff; border-radius:6px;" />

                <label style="font-size:${isMobile ? "1rem" : "1.2rem"}; font-weight:bold;">
                    PU
                </label>
                <input type="number" inputmode="decimal"
                    id="pu-input"
                    min="0" value="0"
                    style="width:100%; padding:10px; font-size:${isMobile ? "1rem" : "1.2rem"}; margin-bottom:12px; border:2px solid #007bff; border-radius:6px;" />

                <label style="font-size:${isMobile ? "1rem" : "1.2rem"}; font-weight:bold;">
                    Remise
                </label>
                <input type="number" inputmode="decimal"
                    id="remise-input"
                    min="0" value="0"
                    style="width:100%; padding:10px; font-size:${isMobile ? "1rem" : "1.2rem"}; margin-bottom:15px; border:2px solid #007bff; border-radius:6px;" />

                <button id="valider-quantite"
                    style="width:100%; padding:12px; font-size:1rem; background:#28a745; color:white; border:none; border-radius:6px;">
                    ✓ Valider
                </button>
            `;

            document.getElementById('valider-quantite').addEventListener('click', () => {

                const quantite = document.getElementById('quantite-input').value || 0;
                const pu = document.getElementById('pu-input').value || 0;
                const remise = document.getElementById('remise-input').value || 0;

                const tdqte = targetRow.children[8];
                const tdpu = targetRow.children[9];
                const tdremise = targetRow.children[10];

                tdqte.innerText = quantite;
                tdpu.innerText = pu;
                tdremise.innerText = remise;

                calculerTTC();

                listeDiv.remove();
            });

        });

        columnsContainer.appendChild(div);
    });

    listeDiv.appendChild(columnsContainer);
}

function recupererFournisseurs(){
    const selectFournisseur = document.querySelector('#fournisseurSelect');
    const type = document.querySelector('.lbltype');
    if (!selectFournisseur) return;
    
    // Récupérer toutes les options
    const options = Array.from(selectFournisseur.options);
    const BASE_URL = window.location.origin;
    const url = `${BASE_URL}/get_fournisseur`;

    fetch(url)
        .then(response => response.json())
        .then(data => {
            //selectFournisseur.innerHTML = '<option value="">-- Sélectionner un fournisseur --</option>';
            if (data && Array.isArray(data)) {
                // ✅ Check empty array early
                if (data.length === 0) {
                    selectFournisseur.innerHTML = '<option value="">Aucun fournisseur disponible</option>';
                    return;
                }

                // Filtrer et dédupliquer
                const fournisseursUniques = new Set();

                // ✅ Iterate directly on `data`, not `data.list`
                data.forEach(fournisseur => {
                    const name = String(
                        (fournisseur.code_fournisseur ?? "") + '/' + (fournisseur.nom_fournisseur ?? "")
                    ).trim();
                    if (name && name !== '/') fournisseursUniques.add(name);
                });

                // Tri alphabétique
                const fournisseursTries = [...fournisseursUniques].sort(
                    (a, b) => a.localeCompare(b, "fr", { sensitivity: "base" })
                );

                // Reset du select
                selectFournisseur.innerHTML = '<option value="">-- Sélectionner un fournisseur --</option>';

                // Ajout au select
                fournisseursTries.forEach(name => {
                    const option = document.createElement("option");
                    option.value = name;
                    option.textContent = name;
                    selectFournisseur.appendChild(option);
                });

                // ✅ Filter with an actual condition (example: exclude placeholder)
                const options = Array.from(selectFournisseur.options);
                fournisseurFiltre = options.filter(option => option.value !== "");
                
                afficherFournisseurFiltre(fournisseurFiltre);
            }
        })
        .catch(err => {
            console.error("Erreur:", err);
            document.getElementById('fournisseurSelect').innerHTML = '<option value="">❌ Erreur</option>';
        });
        
}

let magasinsFiltre = [
    "AMPEFILOHA",
    "AMPITATAFIKA",
    "ANDOHARANOFOTSY",
    "BYPASS",
    "ANALAMAHITSY",
    "ANALAKELY",
    "ANDRAVOAHANGY",
    "SABOTSY NAMEHANA",
    "67 HA",
    "AMBOHIPO",
    "MAHAZO"
];

function afficher_magasins(magasins) {
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
            max-width: 800px;
        `;
        document.body.appendChild(listeDiv);
    }
    
    listeDiv.innerHTML = '<h3 style="margin-bottom: 15px;">Magasins trouvés (dites le numéro) :</h3>';
    
    // ✅ Container avec 3 colonnes
    const columnsContainer = document.createElement('div');
    columnsContainer.style.cssText = `
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 10px;
    `;
    
    // ✅ Créer les items dynamiquement
    magasinsFiltre.forEach((magasin, index) => {
        if (magasin.trim() !== '') { // Ignorer les éléments vides
            const div = document.createElement('div');
            
            const screenWidth = window.innerWidth;
            const screenHeight = window.innerHeight;
            let nbColonnes = 1;
            let fontSize = '1rem';
            let padding = '8px 12px';

            if (screenWidth < 480) {
                // Mobile : maximiser l'espace
                nbColonnes = 3; // 3 colonnes serrées
                fontSize = '0.65rem'; // Très petit mais lisible
                padding = '4px 6px';
            } else if (screenWidth < 768) {
                nbColonnes = 4;
                fontSize = '0.75rem';
                padding = '6px 8px';
            } else if (screenWidth < 1024) {
                nbColonnes = 4;
                fontSize = '0.85rem';
                padding = '8px 10px';
            } else {
                nbColonnes = 5;
                fontSize = '1rem';
                padding = '8px 12px';
            }

            div.style.cssText = `
                position: relative;
                padding: ${padding};
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 3px;
                cursor: pointer;
                transition: all 0.2s;
                font-size: ${fontSize};
                line-height: 1.2;
                justify-content: left;   /* centre horizontal */
                align-items: left;       /* centre vertical */
                text-align: center;
                word-wrap: break-word;
                overflow-wrap: break-word;
                word-break: break-word;
                max-width: 100%;
                box-sizing: border-box;
            `;
            div.textContent = `${index + 1}. ${magasin}`;
            
            // Effet hover
            div.addEventListener('mouseenter', () => {
                div.style.background = '#007bff';
                div.style.color = 'white';
                div.style.transform = 'scale(1.02)';
            });
            
            div.addEventListener('mouseleave', () => {
                div.style.background = '#f8f9fa';
                div.style.color = 'black';
                div.style.transform = 'scale(1)';
            });
            
            // Click handler
            div.onclick = () => {
                const choix = magasinsFiltre[index];
                let code = '';
                switch(index+1){
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
                recup_code_tsena(code, data => {
                    const num_fact = targetRow.children[0];
                    const tdDate = targetRow.children[1];
                    const code_tsena = targetRow.children[2];
                    const tsena = targetRow.children[3];
                    const depot = targetRow.children[12];
                    const affaire = targetRow.children[13];
                    const code_fournisseur = targetRow.children[4];
                    const fournisseur = targetRow.children[5];

                    num_fact.innerText=data.num_fact;

                    let d = new Date();
                    let date =
                        d.getFullYear() + "-" +
                        String(d.getMonth() + 1).padStart(2, "0") + "-" +
                        String(d.getDate()).padStart(2, "0");

                    // ✅ écrire la date
                    tdDate.innerText = date;

                    const ctype = document.getElementById('type');
                    if(ctype.textContent.trim() !== "user")
                    {
                        code_tsena.innerText=data.code_tsena;
                        tsena.innerText=data.nom_tsena.replace('LOCCA','').trim();
                    }

                    
                    if(ctype.textContent.trim() == "user"){
                        code_fournisseur.innerText = data.code_tsena;
                        fournisseur.innerText = data.nom_tsena.replace('LOCCA','').trim();
                    }

                    depot.innerText=data.depot;
                    affaire.innerText=data.affaire;
                });
                    
                // Fermer la liste
                const listeDiv = document.getElementById('liste-magasins-filtre');
                if (listeDiv) {
                    listeDiv.remove();
                }
            };
            
            columnsContainer.appendChild(div);
            columnsContainer.style.display = "grid";
            columnsContainer.style.gridTemplateColumns = "repeat(auto-fit, minmax(90px, 1fr))";
            div.style.fontSize = "0.5rem";
            columnsContainer.style.size="5px";
            columnsContainer.style.width = "100%";
            columnsContainer.style.boxSizing = "border-box";
        }
    });
    
    listeDiv.appendChild(columnsContainer);
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

    const ctype = document.getElementById('type');
    const cdtsena = targetRow.children[2];
    const tdtsena = targetRow.children[3];

    const tdNumFact = targetRow.children[0]; // colonne numero facture
    const tdDepot = targetRow.children[13]; // colonne depot
    const tdAffaire = targetRow.children[14]; // colonne affaire

    recup_code_tsena(code, data => {
        const lblMagasin = document.querySelector(".lblmagasin");
        const lbldepot = document.querySelector(".lbldepot");
        const lblaffaire = document.querySelector(".lblaffaire");
        const lblnumfact = document.querySelector(".lblnum_fact");
        
        if(ctype.textContent.trim() !== "user"){
            lblMagasin.innerText = data.code_tsena;
        }else{
            lblMagasin.innerText = data.nom_tsena;
        }

        lbldepot.innerText = data.depot;
        lblaffaire.innerText = data.affaire;
        lblnumfact.innerText = data.num_fact;

        const rec = lblMagasin.innerText;
        const rec1 = lbldepot.innerText;
        const rec2 = lblaffaire.innerText;
        const rec3 = lblnumfact.innerText;

        cdtsena.innerText   = rec;
        tdDepot.innerText   = rec1;
        tdAffaire.innerText = rec2;
        tdNumFact.innerText = rec3;

        nom_tsena=data.nom_tsena;
        tdtsena.innerText=data.nom_tsena.replace('LOCCA','').trim();
    });

    // Fermer la liste
    const listeDiv = document.getElementById('liste-magasins-filtre');
    if (listeDiv) {
        listeDiv.remove();
    }
}

// Fonction pour traiter le choix
function traiterChoixdebut(choix) {
    const lbltype = document.querySelector('.lbltype');
    const ctype = document.getElementById('type');

    if (lbltype) {
        lbltype.innerText = "Type : "+choix;

        if(ctype.textContent.trim() !== "user"){
            afficher_magasins(magasinsFiltre);
        }else{
            recup="";
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
            const tdDepot = targetRow.children[13]; // colonne depot
            const tdAffaire = targetRow.children[14]; // colonne affaire
            const valeur = document.getElementById('tsena');
            const code = valeur.textContent.trim();

            const code_fournisseur = targetRow.children[2];
            const fournisseur = targetRow.children[3];

            recup_code_tsena(code, data => {
                const lblMagasin = document.querySelector(".lblmagasin");
                const lbldepot = document.querySelector(".lbldepot");
                const lblaffaire = document.querySelector(".lblaffaire");
                const lblnumfact = document.querySelector(".lblnum_fact");
                if(ctype.textContent.trim() !== "user"){
                    lblMagasin.innerText = data.code_tsena;
                }else{
                    lblMagasin.innerText = data.nom_tsena;
                }

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

                code_fournisseur.innerText=data.code_tsena;
                fournisseur.innerText=data.nom_tsena.replace('LOCCA','').trim();
            });
        }
    }

    fetch(`/get_stock`)
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('articleSelect');
            const chargement = document.getElementById('chargement');
            select.innerHTML = '<option value="">-- Sélectionner un article --</option>';
            
            if (data.list && Array.isArray(data.list)) {
                // Filtrer et dédupliquer
                const articlesUniques = new Map();
                
                data.list.forEach(article => {
                    if (article?.name && article?.id) {
                        const name = String(article.name).trim();
                        const id = String(article.id).trim();
                        
                        if (name && id) {
                            articlesUniques.set(id, name);
                        }
                    }
                });
                
                // ✅ Trier par nom alphabétiquement
                const articlesTries = Array.from(articlesUniques.entries())
                    .sort((a, b) => a[1].localeCompare(b[1])); // Tri par nom
                
                // Ajouter au select
                articlesTries.forEach(([id, name]) => {
                    const option = document.createElement('option');
                    option.value = id;
                    option.textContent = name;
                    select.appendChild(option);
                });
                
                console.log(`✅ ${articlesUniques.size} articles uniques et triés`);
                chargement.innerText=`✅ ${articlesUniques.size} articles uniques et triés`;
                if (articlesUniques.size === 0) {
                    select.innerHTML = '<option value="">Aucun article disponible</option>';
                }
            }
        })
        .catch(err => {
            console.error("Erreur:", err);
            document.getElementById('articleSelect').innerHTML = '<option value="">❌ Erreur</option>';
        });
}

let choixDebuts = ["VENTE", "BC ACHAT", "FACT ACHAT"];
function afficherDebuts() {
    select = document.getElementById('articleSelect');
    const select1 = document.getElementById('fournisseurSelect');
    select.innerHTML = '';
    select1.innerHTML = '';

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

    listeDiv.innerHTML = '<h3>Choisissez (dites le numéro ou cliquez) :</h3>';

    const ul = document.createElement('ul');
    ul.style.cssText = 'list-style: none; padding: 0;';

    const ctype = document.getElementById('type');
    if(ctype.textContent.trim() !== "user"){
        const li1 = document.createElement('li');
        li1.style.cssText = `
            padding: 8px; 
            margin: 5px 0; 
            background: #f0f0f0; 
            border-radius: 4px;
            cursor: pointer;
            transition: background 0.2s;
        `;
        li1.textContent = `1. VENTE`;

        // ✅ Hover effect
        li1.addEventListener('mouseenter', () => {
            li1.style.background = '#d0d0d0';
        });
        li1.addEventListener('mouseleave', () => {
            li1.style.background = '#f0f0f0';
        });

        // ✅ Clic sur BC ACHAT
        li1.addEventListener('click', () => {
            console.log("✅ VENTE sélectionné");
            // Votre action ici
            traiterChoixdebut('VENTE');
            listeDiv.remove(); // ferme la popup
        });

        ul.appendChild(li1);

        const li2 = document.createElement('li');
        li2.style.cssText = `
            padding: 8px; 
            margin: 5px 0; 
            background: #f0f0f0; 
            border-radius: 4px;
            cursor: pointer;
            transition: background 0.2s;
        `;
        li2.textContent = `2. BC ACHAT`;

        li2.addEventListener('mouseenter', () => {
            li2.style.background = '#d0d0d0';
        });
        li2.addEventListener('mouseleave', () => {
            li2.style.background = '#f0f0f0';
        });

        // ✅ Clic sur FACT ACHAT
        li2.addEventListener('click', () => {
            console.log("✅ BC ACHAT sélectionné");
            traiterChoixdebut('BC ACHAT');
            listeDiv.remove();
        });

        ul.appendChild(li2);

        const li3 = document.createElement('li');
        li3.style.cssText = `
            padding: 8px; 
            margin: 5px 0; 
            background: #f0f0f0; 
            border-radius: 4px;
            cursor: pointer;
            transition: background 0.2s;
        `;
        li3.textContent = `3. FACT ACHAT`;

        li3.addEventListener('mouseenter', () => {
            li3.style.background = '#d0d0d0';
        });
        li3.addEventListener('mouseleave', () => {
            li3.style.background = '#f0f0f0';
        });

        // ✅ Clic sur FACT ACHAT
        li3.addEventListener('click', () => {
            console.log("✅ FACT ACHAT sélectionné");
            traiterChoixdebut('FACT ACHAT');
            listeDiv.remove();
        });

        ul.appendChild(li3);
    }else{

        const li1 = document.createElement('li');
        li1.style.cssText = `
            padding: 8px; 
            margin: 5px 0; 
            background: #f0f0f0; 
            border-radius: 4px;
            cursor: pointer;
            transition: background 0.2s;
        `;
        li1.textContent = `1. BC ACHAT`;

        // ✅ Hover effect
        li1.addEventListener('mouseenter', () => {
            li1.style.background = '#d0d0d0';
        });
        li1.addEventListener('mouseleave', () => {
            li1.style.background = '#f0f0f0';
        });

        // ✅ Clic sur BC ACHAT
        li1.addEventListener('click', () => {
            console.log("✅ BC ACHAT sélectionné");
            // Votre action ici
            traiterChoixdebut('BC ACHAT');
            listeDiv.remove(); // ferme la popup
        });

        ul.appendChild(li1);

        const li2 = document.createElement('li');
        li2.style.cssText = `
            padding: 8px; 
            margin: 5px 0; 
            background: #f0f0f0; 
            border-radius: 4px;
            cursor: pointer;
            transition: background 0.2s;
        `;
        li2.textContent = `2. FACT ACHAT`;

        li2.addEventListener('mouseenter', () => {
            li2.style.background = '#d0d0d0';
        });
        li2.addEventListener('mouseleave', () => {
            li2.style.background = '#f0f0f0';
        });

        // ✅ Clic sur FACT ACHAT
        li2.addEventListener('click', () => {
            console.log("✅ FACT ACHAT sélectionné");
            traiterChoixdebut('FACT ACHAT');
            listeDiv.remove();
        });

        ul.appendChild(li2);
    }

    listeDiv.appendChild(ul);
}

function selectionnerDebut(numero) {
        fetch(`/get_stock`)
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('articleSelect');
            select.innerHTML = '<option value="">-- Sélectionner un article --</option>';
            
            if (data.list && Array.isArray(data.list)) {
                // Filtrer et dédupliquer
                const articlesUniques = new Map();
                
                data.list.forEach(article => {
                    if (article?.name && article?.id) {
                        const name = String(article.name).trim();
                        const id = String(article.id).trim();
                        
                        if (name && id) {
                            articlesUniques.set(id, name);
                        }
                    }
                });
                
                // ✅ Trier par nom alphabétiquement
                const articlesTries = Array.from(articlesUniques.entries())
                    .sort((a, b) => a[1].localeCompare(b[1])); // Tri par nom
                
                // Ajouter au select
                articlesTries.forEach(([id, name]) => {
                    const option = document.createElement('option');
                    option.value = id;
                    option.textContent = name;
                    select.appendChild(option);
                });
                
                console.log(`✅ ${articlesUniques.size} articles uniques et triés`);
                
                if (articlesUniques.size === 0) {
                    select.innerHTML = '<option value="">Aucun article disponible</option>';
                }
            }
        })
        .catch(err => {
            console.error("Erreur:", err);
            document.getElementById('articleSelect').innerHTML = '<option value="">❌ Erreur</option>';
        });

    console.log("Numéro choisi:", numero);
    const ctype = document.getElementById('type');

    if(ctype.textContent.trim() !== "user"){
        if (numero < 1 || numero > choixDebuts.length) {
            console.log("Numéro invalide");
            return;
        }
        
        const choix = choixDebuts[numero - 1];
        
        // Afficher dans .lbltype
        const lbltype = document.querySelector('.lbltype');
        if (lbltype) {
            lbltype.innerText = "Type : "+choix;
            console.log("Type sélectionné:", choix);
        }
    }else{
        if (numero < 1 || numero > choixDebut.length) {
            console.log("Numéro invalide");
            return;
        }
        
        const choix = choixDebut[numero - 1];
        
        // Afficher dans .lbltype
        const lbltype = document.querySelector('.lbltype');
        if (lbltype) {
            lbltype.innerText = "Type : "+choix;
            console.log("Type sélectionné:", choix);
        }
    }
    
    // Fermer la liste
    const listeDiv = document.getElementById('liste-debut-filtre');
    if (listeDiv) {
        listeDiv.remove();
    }

        // Utilisation

    
    if(ctype.textContent.trim() !== "user"){
        afficher_magasins(magasinsFiltre);
    }else{
        recup="";
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
        const valeur = document.getElementById('tsena');
        const code = valeur.textContent.trim();

        const lblMagasin = document.querySelector(".lblmagasin");
        const lbldepot = document.querySelector(".lbldepot");
        const lblaffaire = document.querySelector(".lblaffaire");
        const lblnumfact = document.querySelector(".lblnum_fact");

        recup_code_tsena(code, data => {
            const num_fact = targetRow.children[0];
            const tdDate = targetRow.children[1];
            const code_tsena = targetRow.children[2];
            const tsena = targetRow.children[3];
            const depot = targetRow.children[12];
            const affaire = targetRow.children[13];
            const code_fournisseur = targetRow.children[4];
            const fournisseur = targetRow.children[5];

            num_fact.innerText=data.num_fact;

            let d = new Date();
            let date =
                d.getFullYear() + "-" +
                String(d.getMonth() + 1).padStart(2, "0") + "-" +
                String(d.getDate()).padStart(2, "0");

            // ✅ écrire la date
            tdDate.innerText = date;

            const ctype = document.getElementById('type');

            code_tsena.innerText=data.code_tsena;
            tsena.innerText=data.nom_tsena.replace('LOCCA','').trim();

            depot.innerText=data.depot;
            affaire.innerText=data.affaire;
        });
    }
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
    }else if (cmd.includes("article") || cmd.includes("Article")) {
        const motCle = cmd.replace("article", "").trim();

        if (motCle) {
            if(motCle=='repas'){
                filtrerArticles(['vary','henomby','pizza','mayonnaise','ketchup','pate','saucisse','totokena','vantan']);
            }else{
                filtrerArticles(motCle);
            }
        }
    } else if (/^\d+$/.test(convertirMotsEnChiffres(cmd))) {
        const numero = parseInt(convertirMotsEnChiffres(cmd));
        // Vérifier si la liste de début est affichée
        const listeDebut = document.getElementById('liste-debut-filtre');
        recs_tsena=recup_tsena;
        
        if (listeDebut) {
            selectionnerDebut(numero);
            recup="1";
        } else if (articlesFiltre.length > 0) {
            if(fournisseurFiltre.length == 0){
                selectionnerArticleParNumero(numero);
            }else{
                selectionnerFournisseurParNumero(numero);
            }
        } else if (magasinsFiltre.length > 0) {
            selectionnermagasin(numero);
        } 
    }else if(cmd.includes("envoyer")){
        exporterTXT();
        reinitialiser(); 
    }else if(cmd.includes("nouvelle")){
        reinitialiser(); 
    }
}

function recup_client(code, callback) {
    fetch(`/get_client?code=${encodeURIComponent(code)}`)
        .then(r => r.json())
        .then(data => callback(data.nom || ""));
}

function reinitialiser(){
    // Réinitialiser le label
    const lbltype = document.querySelector(".lbltype");
    lbltype.innerHTML = "Type : ";

    const lblfournisseur = document.querySelector(".lblfournisseur");
    lblfournisseur.innerHTML = "";

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
        if ([8,9,10].includes(i)) td.setAttribute("oninput", "calculerTTC()");
        if (i === 11) td.classList.add("tot_ttc");
        if ([12,13,14].includes(i)) td.style.visibility = "hidden";

        nouvelleLigne.appendChild(td);
    }

    tableBody.appendChild(nouvelleLigne);
    
    let btn = document.getElementById("micBtn");
    isListening = false;
    btn.classList.remove("listening");
    btn.innerText = "🎤 Commencer";

    // Relancer seulement quand recognition est vraiment arrêté
    recognition.onend = () => {
        recognition.onend = null;
        handleMicClick(); // ← appelé ici, pas avant
    };

    recognition.stop();

}

function recup_code_tsena(code, callback) {
    fetch(`/get_tsena?code=${encodeURIComponent(code)}`)
    .then(r => r.json())
    .then(data => {
        console.log(data);
        rec_code_tsena=data.code_tsena;
        rec_affaire=data.affaire;
        rec_depot=data.depot;
        rec_num_fact=data.num_fact;
        recup_tsena=data.nom_tsena;
        rec_souche=data.souche;
        if (callback) callback(data);
    })
    .catch(err => {
        console.error("Erreur récupération article :", err);
        if (callback) callback({
            code_tsena: "",
            depot: "",
            affaire: "",
            nom_tsena: "",
            num_fact: "",
            souche:""
        });
    });
}

function ajouterLigne() {
    let tbody = document.getElementById("table-body");
    fournisseurFiltre = []; 
    let newRow = document.createElement("tr");
    newRow.classList.add("ligne");
    newRow.style.fontSize = "10px"; 

    for (let i = 0; i < 14; i++) {
        let td = document.createElement("td");

        if (i == 11) {
            td.classList.add("tot_ttc");
            td.contentEditable = "false";
        }

        if (i == 0) {
            const firstRow = tbody.querySelector("tr.ligne");
            
            if (firstRow && firstRow.cells[0]) {
                // Copier la valeur de la colonne 2 de la première ligne
                const premiereValeur = firstRow.cells[0].textContent.trim();
                td.textContent = premiereValeur;
                console.log("✓ Colonne 2 : copié depuis première ligne =", premiereValeur);
            } else {
                // Fallback : utiliser lblmagasin si aucune ligne n'existe encore
                const lblmagasin = document.querySelector(".lblmagasin");
                if (lblmagasin) {
                    td.textContent = lblmagasin.textContent.trim();
                    console.log("✓ Colonne 2 : depuis lblmagasin =", td.textContent);
                } else {
                    console.warn("⚠ Première ligne et lblmagasin introuvables !");
                }
            }
            td.contentEditable = "true";
        }

        // Colonne 1 : Date
        if (i == 1) {
            let d = new Date();
            let date =
                d.getFullYear() + "-" +
                String(d.getMonth() + 1).padStart(2, "0") + "-" +
                String(d.getDate()).padStart(2, "0");

            td.innerText = date;
            td.contentEditable = "true";
        }

        // Colonne 2 : Récupérer la valeur de la première ligne existante
        if (i == 2) {
            // Vérifier s'il existe déjà une ligne dans le tableau
            const firstRow = tbody.querySelector("tr.ligne");
            
            if (firstRow && firstRow.cells[2]) {
                // Copier la valeur de la colonne 2 de la première ligne
                const premiereValeur = firstRow.cells[2].textContent.trim();
                td.textContent = premiereValeur;
                console.log("✓ Colonne 2 : copié depuis première ligne =", premiereValeur);
            } else {
                // Fallback : utiliser lblmagasin si aucune ligne n'existe encore
                const lblmagasin = document.querySelector(".lblmagasin");
                if (lblmagasin) {
                    td.textContent = lblmagasin.textContent.trim();
                    console.log("✓ Colonne 2 : depuis lblmagasin =", td.textContent);
                } else {
                    console.warn("⚠ Première ligne et lblmagasin introuvables !");
                }
            }
            td.contentEditable = "true";
        }

        if (i == 4) {
            // Vérifier s'il existe déjà une ligne dans le tableau
            const firstRow = tbody.querySelector("tr.ligne");
            
            if (firstRow && firstRow.cells[4]) {
                // Copier la valeur de la colonne 2 de la première ligne
                const premiereValeur = firstRow.cells[4].textContent.trim();
                td.textContent = premiereValeur;
                console.log("✓ Colonne 2 : copié depuis première ligne =", premiereValeur);
            } else {
                // Fallback : utiliser lblmagasin si aucune ligne n'existe encore
                const lblmagasin = document.querySelector(".lblmagasin");
                if (lblmagasin) {
                    td.textContent = lblmagasin.textContent.trim();
                    console.log("✓ Colonne 2 : depuis lblmagasin =", td.textContent);
                } else {
                    console.warn("⚠ Première ligne et lblmagasin introuvables !");
                }
            }
            td.contentEditable = "true";
        }

        if (i == 3) {
           const firstRow = tbody.querySelector("tr.ligne");
            
            if (firstRow && firstRow.cells[3]) {
                const premiereValeur = firstRow.cells[3].textContent.trim();
                td.textContent = premiereValeur;
            } else {
                if (lblmagasin) {
                    td.textContent = recs_tsena;
                } else {
                    console.warn("⚠ Première ligne et lblmagasin introuvables !");
                }
            }
            td.contentEditable = "true";
        }

        if (i == 5) {
           const firstRow = tbody.querySelector("tr.ligne");
            
            if (firstRow && firstRow.cells[5]) {
                const premiereValeur = firstRow.cells[5].textContent.trim();
                td.textContent = premiereValeur;
            } else {
                if (lblmagasin) {
                    td.textContent = recs_tsena;
                } else {
                    console.warn("⚠ Première ligne et lblmagasin introuvables !");
                }
            }
            td.contentEditable = "true";
        }

        // ------------------------
        if (i == 12 || i == 13 || i == 14) {
            td.style.visibility = "hidden";
            td.contentEditable = "false";

            if (i == 13) {
                const lbldepot = document.querySelector(".lbldepot");

                if (!lbldepot) {
                    console.warn("⚠ lbldepot introuvable !");
                } else {
                    const rec = lbldepot.textContent.trim();
                    console.log("Valeur récupérée :", rec);

                    if (td) {
                        td.textContent = rec;
                    } else {
                        console.warn("⚠ td introuvable !");
                    }
                }
            }

            if (i == 14) {
                const lblaffaire = document.querySelector(".lblaffaire");

                if (!lblaffaire) {
                    console.warn("⚠ lblaffaire introuvable !");
                } else {
                    const rec = lblaffaire.textContent.trim();
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
        if (i == 8 || i == 9 || i == 10) {
            td.addEventListener("input", calculerTTC);
            td.contentEditable = "true";
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
    if (!trs.length) return;

    let targetRow = null;


    // si aucune ligne vide trouvée → prendre la dernière
    if (!targetRow) {
        targetRow = trs[trs.length - 1];
    }

    trs.forEach(tr => {
        let tds = tr.querySelectorAll("td");

        //if (tds[4].innerText.trim() !== "") { // Si Réf article non vide
            let qte = tds[8].innerText.trim();
            let pu = tds[9].innerText.trim();
            let remise = tds[10].innerText.trim();
            let code_fournisseur = targetRow.children[4].innerText.trim();

            let mtt = 0;

            const fournisseursSpeciaux = [
                'LOCA001','LOCB001','LOCJ003','LOCP001','LOCP016','LOCU001'
            ];

            if (fournisseursSpeciaux.includes(code_fournisseur)) {
                mtt = Number(qte) * (Number(pu) * 1.2);
            } else {
                mtt = Number(qte) * Number(pu) * (1 - Number(remise) / 100);
            }

            tds[11].innerText = mtt.toFixed(2);
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
    let trs = document.querySelectorAll("#table-body tr");
    let lines = [];

    const lblMagasin = document.querySelector(".lblmagasin");
    const lbltype = document.querySelector(".lbltype");

    const rec = lblMagasin ? lblMagasin.innerText.trim() : "unknown";
    const recs = lbltype ? lbltype.textContent.trim() : "unknown";
    let nomClient = "";
    let dateFact = "";

    trs.forEach(tr => {
        let tds = tr.querySelectorAll("td");
        //console.log(tds);
        if (tds[3].innerText.trim() !== "") {
            let numFact  = tds[0].innerText.trim();
            dateFact     = tds[1].innerText.trim().split('-').reverse().join('/');
            nomClient    = tds[5].innerText.trim();
            let tsena    = tds[13].innerText.trim();
            let ref      = tds[6].innerText.trim();
            let article  = tds[7].innerText.trim();
            let qte      = tds[8].innerText.trim();

            let pu = 0;

            const fournisseursSpeciaux = [
                'LOCA001','LOCB001','LOCJ003','LOCP001','LOCP016','LOCU001'
            ];

            let prix = tds[9]?.innerText?.trim() || '0';

            // conversion propre
            function toNumber(val) {
                return Number(val.replace(/\s/g, '').replace(',', '.')) || 0;
            }

            let prixNum = toNumber(prix);
            let code_fournisseur = tds[4] ? tds[4].innerHTML : "";
            if (fournisseursSpeciaux.includes(code_fournisseur)) {
                pu = prixNum * 1.2;
            } else {
                pu = prixNum;
            }

            let remise   = tds[11].innerText.trim();
            let depot    = tds[13].innerHTML;
            let affaire  = tds[14].innerHTML;

            let mtt = Number(qte) * Number(pu) * (1 - Number(remise) / 100);

            if (recs.toLowerCase().includes("vente")) {
                lines.push(`1\t6\t${numFact}\t${dateFact}\t${tsena}\t${nomClient}\t${ref}\t${article}\t${pu}\t${qte}\t${remise}\t${depot}\t${affaire}\t${rec_souche}`);
            } else if (recs.toLowerCase().includes("bc")) {
                lines.push(`1\t12\t${numFact}\t${dateFact}\t${code_fournisseur}\t${nomClient}\t${ref}\t${article}\t${pu}\t${qte}\t${remise}\t${depot}\t${affaire}\t${rec_souche}`);
            } else {
                lines.push(`1\t16\t${numFact}\t${dateFact}\t${code_fournisseur}\t${nomClient}\t${ref}\t${article}\t${pu}\t${qte}\t${remise}\t${depot}\t${affaire}\t${rec_souche}`);
            }
        }
    });

    const content = lines.join("\n");

    // ✅ Fonction qui construit formData et envoie
    function envoyerFichier(tsenaFinal) {
        let filename = '';
        if (recs.toLowerCase().includes("vente")) {
            filename = `VENTE_${rec}_${nomClient}_${dateFact}.txt`;
        } else if (recs.toLowerCase().includes("bc")) {
            filename = `BC_ACHAT_${rec}_${nomClient}_${dateFact}.txt`;
        } else {
            filename = `FA_ACHAT_${rec}_${nomClient}_${dateFact}.txt`;
        }

        const blob = new Blob([content], { type: "text/plain" });
        const formData = new FormData();
        formData.append("file", blob, filename);
        formData.append("rec", rec);
        formData.append("recs", recs);
        formData.append("nom_client", nomClient);
        formData.append("date_fact", dateFact);
        formData.append("tsena", tsenaFinal);
        
        blob.text().then(text => {
            console.log("📄 Contenu du blob :", text); // doit afficher tes données
        });

        console.log("📤 Envoi avec tsena:", tsenaFinal);
    }

    // ✅ Récupérer tsena puis envoyer
    const valeur = document.getElementById('tsena');
    const code = valeur.textContent.trim();

    const tsenaFinal = (recup_tsena || "").replace('LOCCA ', '');
    envoyerFichier(tsenaFinal);

    let filename = '';
    if (recs.toLowerCase().includes("vente")) {
        filename = `VENTE_${rec}_${nomClient}_${dateFact}.txt`;
    } else if (recs.toLowerCase().includes("bc")) {
        filename = `BC_ACHAT_${rec}_${nomClient}_${dateFact}.txt`;
    } else {
        filename = `FA_ACHAT_${rec}_${nomClient}_${dateFact}.txt`;
    }

    const blob = new Blob([content], { type: "text/plain" });
    const formData = new FormData();
    formData.append("file", blob, filename);
    formData.append("rec", rec);
    formData.append("recs", recs);
    formData.append("nom_client", nomClient);
    formData.append("date_fact", dateFact);
    formData.append("tsena", tsenaFinal); // ✅ valeur correcte ici

    const BASE_URL = window.location.origin;
    const url = `${BASE_URL}/upload`;

    fetch(url, {
        method: "POST",
        body: formData
    })
    .then(response => response.json())   // ← conversion en JSON obligatoire
    .then(data => {
        if (data.success) {
            console.log("✅ Upload OK :", data.link);
            window.open(data.link, "_blank");
        } else {
            console.error("❌ Upload échoué :", data.error);
            alert("Erreur upload : " + data.error);
        }
    })
    .catch(err => {
        console.error("❌ Erreur fetch :", err);
        alert("Erreur fetch : " + err.message);
    });
}


