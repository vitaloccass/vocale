/**********************
 * SPEECH RECOGNITION
 **********************/
let recognition = null;
let isListening = false;

function initSpeech() {
    const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        alert("Reconnaissance vocale non supportée sur ce navigateur");
        return;
    }

    recognition = new SpeechRecognition();
    recognition.lang = "fr-FR";
    recognition.continuous = false;      // ✅ OBLIGATOIRE mobile
    recognition.interimResults = false;  // ✅ OBLIGATOIRE mobile
    recognition.maxAlternatives = 1;

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript.toLowerCase();
        document.getElementById("transcript").innerText = transcript;
        traiterCommande(transcript);
    };

    recognition.onerror = (e) => {
        console.error("Erreur micro :", e.error);
        stopListening();
    };

    recognition.onend = () => {
        stopListening(); // mobile stop automatiquement
    };
}

function startListening() {
    if (!recognition) initSpeech();
    if (!recognition) return;

    recognition.start();
    isListening = true;

    const btn = document.getElementById("micBtn");
    btn.classList.add("listening");
    btn.innerText = "⏸️ Arrêter";
}

function stopListening() {
    if (recognition) recognition.stop();
    isListening = false;

    const btn = document.getElementById("micBtn");
    btn.classList.remove("listening");
    btn.innerText = "🎤 Commencer";
}

function toggleListening() {
    if (!isListening) startListening();
    else stopListening();
}

/**********************
 * COMMANDE VOCALE
 **********************/
function traiterCommande(cmd) {
    cmd = cmd
        .toLowerCase()
        .replace(/[.,!?]/g, "")
        .trim();

    console.log("🎙 CMD =", cmd);

    if (cmd === "ligne" || cmd === "lignes") {
        ajouterLigne();
        return;
    }

    if (cmd.includes("vente") || cmd.includes("achat")) {
        const match = cmd.match(/\b(vente|achat)\b/i);
        if (match) {
            document.querySelector(".lblType").innerText = "Type : " + match[1];
        }
        return;
    }

    if (cmd === "exporter") {
        exporterTXT();
        return;
    }

    if (cmd === "nouvelle") {
        reinitialiser();
        return;
    }

    if (cmd.includes("magasin")) {
        const m = cmd.match(/magasin\s*(\d+)/);
        if (m) chargerMagasin("MAGASIN" + m[1]);
        return;
    }

    if (cmd.includes("client")) {
        const m = cmd.match(/client\s*(\d+)/);
        if (m) chargerClient("CLIENT" + m[1]);
        return;
    }

    if (cmd.includes("article")) {
        const m = cmd.match(/article\s*(\d+)/);
        if (m) chargerArticle("ARTICLE" + m[1]);
        return;
    }

    if (cmd.includes("quantité")) {
        const m = cmd.match(/quantité\s*(\d+)/);
        if (m) remplirColonne(6, m[1]);
        return;
    }

    if (cmd.includes("prix")) {
        const m = cmd.match(/prix\s*(\d+)/);
        if (m) {
            remplirColonne(7, m[1]);
            calculerTTC();
        }
        return;
    }

    if (cmd.includes("remise")) {
        const m = cmd.match(/remise\s*(\d+)/);
        if (m) {
            remplirColonne(8, m[1]);
            calculerTTC();
        }
    }
}

/**********************
 * AIDES TABLEAU
 **********************/
function getTargetRow() {
    let rows = document.querySelectorAll("#table-body tr");
    if (!rows.length) return null;

    return (
        Array.from(rows).find(r => r.children[3].innerText.trim() === "") ||
        rows[rows.length - 1]
    );
}

function remplirColonne(index, value) {
    const row = getTargetRow();
    if (row) row.children[index].innerText = value;
}

/**********************
 * BACKEND CALLS
 **********************/
function chargerClient(code) {
    const row = getTargetRow();
    if (!row) return;

    fetch(`/get_client?code=${code}`)
        .then(r => r.json())
        .then(d => {
            row.children[1].innerText = new Date().toISOString().slice(0, 10);
            row.children[3].innerText = d.nom || "";
        });
}

function chargerArticle(code) {
    const row = getTargetRow();
    if (!row) return;

    fetch(`/get_article?code=${code}`)
        .then(r => r.json())
        .then(d => {
            row.children[4].innerText = d.reference || "";
            row.children[5].innerText = d.designation || "";
        });
}

function chargerMagasin(code) {
    fetch(`/get_tsena?code=${code}`)
        .then(r => r.json())
        .then(d => {
            document.querySelector(".lblmagasin").innerText = d.code_tsena;
            document.querySelector(".lbldepot").innerText = d.depot;
            document.querySelector(".lblaffaire").innerText = d.affaire;
            document.querySelector(".lblnum_fact").innerText = d.num_fact;
        });
}

/**********************
 * TTC
 **********************/
function calculerTTC() {
    document.querySelectorAll("#table-body tr").forEach(tr => {
        let qte = Number(tr.children[6].innerText || 0);
        let pu = Number(tr.children[7].innerText || 0);
        let rem = Number(tr.children[8].innerText || 0);
        tr.children[9].innerText =
            (qte * pu * (1 - rem / 100)).toFixed(2);
    });
}
