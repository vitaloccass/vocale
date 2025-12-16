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
    }else if (cmd.toLowerCase().includes("vente") || cmd.toLowerCase().includes("achat")) {
        console.log("CMD =", cmd);

        const lbltype = document.querySelector(".lblType");
        console.log("LBL =", lbltype);

        const typeMatch = cmd.toLowerCase().match(/\b\s*(achat|vente)\b/i);
        console.log("MATCH =", typeMatch);

        if (lbltype && typeMatch) {
            lbltype.innerText = "Type : " + typeMatch[1];
            cmd.innerHTML="";
        }
    }else if(cmd=="exporter"){
        exporterTXT();
    }else if(cmd=="nouvelle"){
        reinitialiser();
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

