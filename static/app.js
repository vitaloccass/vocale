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

function toggleListening() {
    let btn = document.getElementById("micBtn");

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

function traiterCommande(transcript) {
    transcript = transcript.trim().toLowerCase();

    const cmd = transcript
        .toLowerCase()
        .replace(/[.,!?]/g, "")
        .trim();
        

    if(cmd=="ligne" || cmd=="lignes"){
         ajouterLigne();
    }else if(cmd=="exporter"){
         exporterTXT();
    }else if(cmd.includes("magasin") || cmd.includes("magasins")){
        const magasinMatch = cmd.match(/\magasins?\s*(\d+)\b/i);
        const code = "MAGASIN" + magasinMatch[1];
        console.log(code);
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
        });
    }else if(cmd.includes("client") || cmd.includes("clients")){
        const clientMatch = cmd.match(/\bclients?\s*(\d+)\b/i);
        const code = "CLIENT" + clientMatch[1];
        console.log(code);
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

        const tdDate = targetRow.children[1];   // colonne Date
        const tdClient = targetRow.children[3]; // colonne Client

        // Date du jour (YYYY-MM-DD)
        let d = new Date();
        let date =
            d.getFullYear() + "-" +
            String(d.getMonth() + 1).padStart(2, "0") + "-" +
            String(d.getDate()).padStart(2, "0");

        // ✅ écrire la date
        tdDate.innerText = date;

        // appel backend
        recup_client(code, nom => {
            console.log("Nom reçu :", nom);
            tdClient.innerText = nom;
        });
    }else if(cmd.includes("article") || cmd.includes("articles")){
        const articleMatch = cmd.match(/\barticles?\s*(\d+)\b/i);
        const code = "ARTICLE" + articleMatch[1];
        console.log(code);
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

        const tdref = targetRow.children[4]; // colonne ref article
        const tddesignation = targetRow.children[5]; // colonne designation article

        // appel backend
        recup_article(code,
            reference => {
                console.log("reference reçu :", reference);
                tdref.innerText = reference;
            }, designation => {
                console.log("designation reçu :", designation);
                tddesignation.innerText = designation;
            }
        );
    }else if(cmd.includes("quantité") || cmd.includes("quantités")){
        const qteMatch = cmd.match(/\quantités?\s*(\d+)\b/i);
        const code = qteMatch[1];
        console.log(code);
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
    }else if(cmd.includes("prix")){
        const puMatch = cmd.match(/\prix?\s*(\d+)\b/i);
        const code = puMatch[1];
        console.log(code);
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
        const tdpu = targetRow.children[7]; // colonne pu article
        console.log("PU reçu :", code);
        tdpu.innerText = code;
        calculerTTC();
    }else if(cmd.includes("remise") || cmd.includes("remises")){
        const remiseMatch = cmd.match(/remises?\s*(\d+)\b/i);
        if (!remiseMatch) {
            console.warn("Aucune remise trouvée dans la commande :", cmd);
            return;
        }

        const code = remiseMatch[1];
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

function recup_code_tsena(code, callback) {
    fetch(`/get_tsena?code=${encodeURIComponent(code)}`)
    .then(r => r.json())
    .then(data => {
        if (callback) callback(data);
    })
    .catch(err => {
        console.error("Erreur récupération article :", err);
        if (callback) callback({
            code_tsena: "",
            depot: "",
            affaire: "",
            num_fact: ""
        });
    });
}

function recup_article(code, callbackRef, callbackDesig) {
    fetch(`/get_article?code=${encodeURIComponent(code)}`)
        .then(r => r.json())
        .then(data => {
            if (callbackRef) callbackRef(data.reference || "");
            if (callbackDesig) callbackDesig(data.designation || "");
        })
        .catch(err => {
            console.error("Erreur récupération article :", err);
            if (callbackRef) callbackRef("");
            if (callbackDesig) callbackDesig("");
        });
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

        if (tds[4].innerText.trim() !== "") { // Si Réf article non vide
            let qte = tds[6].innerText.trim();
            let pu = tds[7].innerText.trim();
            let remise = tds[8].innerText.trim();

            let mtt = Number(qte) * Number(pu) * (1 - Number(remise)/100);

            tds[9].innerText = mtt.toFixed(2);
        }
    });
}

/*function exporterTXT() {
    let trs = document.querySelectorAll("#table-body tr");
    let lines = [];

    trs.forEach(tr => {
        let tds = tr.querySelectorAll("td");
        let nomClient="";
        const lblMagasin = document.querySelector(".lblmagasin");
        const rec = lblMagasin.innerText;
        let dateFact="";

        if (tds[3].innerText.trim() !== "") {
            let numFact = tds[0].innerText.trim();
            dateFact = tds[1].innerText.trim();
            let tsena = tds[2].innerText.trim();
            nomClient = tds[3].innerText.trim();
            let ref = tds[4].innerText.trim();
            let article = tds[5].innerText.trim();
            let qte = tds[6].innerText.trim();
            let pu = tds[7].innerText.trim();
            let remise = tds[8].innerText.trim();
            let ttc = tds[9].innerText.trim();
            let f = 0;
            let depot = tds[11].innerHTML;
            let affaire = tds[12].innerHTML;
            let g = 1;

            let mtt = Number(qte) * Number(pu) * (1 - Number(remise)/100);

            lines.push(
                `0\t6\t${numFact}\t${dateFact}\t${tsena}\t${nomClient}\t${ref}\t${article}\t${qte}\t${pu}\t${mtt.toFixed(2)}\t${remise}\t${f}\t${depot}\t${affaire}\t${g}`
            );
        }
    });

    let blob = new Blob([lines.join("\n")], { type: "text/plain" });
    let url = URL.createObjectURL(blob);

    let a = document.createElement("a");
    a.href = url;
    a.download ="ACHAT"+"_"+rec+_+nomClient+"_"+dateFact+".txt";

    // 🔥 Très important : on doit ajouter le lien au DOM pour mobile
    document.body.appendChild(a);

    a.click();       // simulate click
    a.remove();      // remove link
    URL.revokeObjectURL(url);
}*/

// Fonction pour enregistrer dans Google Drive
async function exporterTXT() {
    let trs = document.querySelectorAll("#table-body tr");
    let lines = [];

    trs.forEach(tr => {
        let tds = tr.querySelectorAll("td");
        let nomClient = "";
        const lblMagasin = document.querySelector(".lblmagasin");
        const rec = lblMagasin.innerText;
        let dateFact = "";

        if (tds[3].innerText.trim() !== "") {
            let numFact = tds[0].innerText.trim();
            dateFact = tds[1].innerText.trim();
            let tsena = tds[2].innerText.trim();
            nomClient = tds[3].innerText.trim();
            let ref = tds[4].innerText.trim();
            let article = tds[5].innerText.trim();
            let qte = tds[6].innerText.trim();
            let pu = tds[7].innerText.trim();
            let remise = tds[8].innerText.trim();
            let ttc = tds[9].innerText.trim();
            let f = 0;
            let depot = tds[11].innerHTML;
            let affaire = tds[12].innerHTML;
            let g = 1;

            let mtt = Number(qte) * Number(pu) * (1 - Number(remise)/100);

            lines.push(
                `0\t6\t${numFact}\t${dateFact}\t${tsena}\t${nomClient}\t${ref}\t${article}\t${qte}\t${pu}\t${mtt.toFixed(2)}\t${remise}\t${f}\t${depot}\t${affaire}\t${g}`
            );
        }
    });

    const lblMagasin = document.querySelector(".lblmagasin");
    const rec = lblMagasin.innerText;
    let nomClient = "";
    let dateFact = "";
    
    // Récupérer le premier client et date pour le nom du fichier
    let firstTr = document.querySelector("#table-body tr");
    if (firstTr) {
        let firstTds = firstTr.querySelectorAll("td");
        if (firstTds[3].innerText.trim() !== "") {
            nomClient = firstTds[3].innerText.trim();
            dateFact = firstTds[1].innerText.trim();
        }
    }

    const fileName = `ACHAT_${rec}_${nomClient}_${dateFact}.txt`;
    const fileContent = lines.join("\n");

    // Utiliser Google Picker API pour choisir le dossier
    // Note: Vous devez avoir configuré l'API Google Drive au préalable
    
    try {
        // Méthode 1: Avec Google Drive API
        const metadata = {
            name: fileName,
            mimeType: 'text/plain'
        };

        const blob = new Blob([fileContent], { type: 'text/plain' });
        const formData = new FormData();
        formData.append('metadata', new Blob([JSON.stringify(metadata)], { type: 'application/json' }));
        formData.append('file', blob);

        const response = await fetch('https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart', {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + gapi.auth.getToken().access_token
            },
            body: formData
        });

        if (response.ok) {
            const result = await response.json();
            alert(`Fichier enregistré avec succès dans Google Drive!\nID: ${result.id}`);
            console.log('File saved:', result);
        } else {
            throw new Error('Échec de l\'enregistrement');
        }
    } catch (error) {
        console.error('Erreur:', error);
        alert('Erreur lors de l\'enregistrement dans Google Drive. Vérifiez que vous êtes connecté et que l\'API est configurée.');
        
        // Fallback: téléchargement local
        let blob = new Blob([fileContent], { type: "text/plain" });
        let url = URL.createObjectURL(blob);
        let a = document.createElement("a");
        a.href = url;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
    }
}

// Configuration de l'API Google Drive (à placer dans votre HTML)
function loadGoogleDriveAPI() {
    gapi.load('client:auth2', initClient);
}

function initClient() {
    gapi.client.init({
        apiKey: 'VOTRE_API_KEY',
        clientId: 'VOTRE_CLIENT_ID',
        discoveryDocs: ['https://www.googleapis.com/discovery/v1/apis/drive/v3/rest'],
        scope: 'https://www.googleapis.com/auth/drive.file'
    }).then(() => {
        console.log('Google Drive API prête');
    });
}
