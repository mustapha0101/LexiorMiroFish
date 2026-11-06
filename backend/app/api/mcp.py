"""
Routes API du Serveur MCP Souverain Lexior (`/api/mcp/*`).
Expose sur Render (HTTPS) et en local les outils de recherche législative déterministe (< 1 ms),
les barèmes actuariels (`quantum_benchmarks`), le scraping LégisQuébec à la demande,
et l'exportation de datasets SFT/DPO (Flywheel).
"""

import os
import re
import glob
import json
import sqlite3
import requests
from bs4 import BeautifulSoup
from flask import request, jsonify
from . import mcp_bp

CCQ_CPC_DB = os.path.join(os.path.dirname(__file__), "../data/ccq_cpc.db")

_SEED_STATUTES = [
    ("LPC", "37", "Un bien qui fait l'objet d'un contrat doit être tel qu'il puisse servir à l'usage auquel il est normalement destiné.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-40.1#se:37"),
    ("LPC", "38", "Un bien qui fait l'objet d'un contrat doit être tel qu'il puisse servir à un usage normal pendant une durée raisonnable, eu égard à son prix, aux dispositions du contrat et aux conditions d'utilisation du bien.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-40.1#se:38"),
    ("LPC", "53", "Le consommateur qui a contracté avec un commerçant a le droit d'exercer directement contre le commerçant ou contre le fabricant un recours fondé sur un vice caché du bien qui a fait l'objet du contrat, sauf si le consommateur pouvait déceler ce vice par un examen ordinaire.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-40.1#se:53"),
    ("LPC", "219", "Aucun commerçant, fabricant ou publicitaire ne peut, par quelque moyen que ce soit, faire une représentation fausse ou trompeuse à un consommateur.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-40.1#se:219"),
    ("LPC", "228", "Aucun commerçant, fabricant ou publicitaire ne peut, dans une représentation qu'il fait à un consommateur, passer sous silence un fait important.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-40.1#se:228"),
    ("LPC", "253", "Lorsque le commerçant ou le fabricant se livre, à l'égard d'un consommateur, à une pratique interdite visée au titre II, il y a présomption absolue que si le consommateur avait eu connaissance de cette pratique, il n'aurait pas contracté ou n'aurait pas donné un prix aussi élevé.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-40.1#se:253"),
    ("LPC", "272", "Si le commerçant ou le fabricant manque à une obligation que lui impose la présente loi, un règlement ou un engagement volontaire, le consommateur peut demander, sous réserve des autres recours prévus par la présente loi : a) l'exécution de l'obligation ; b) l'autorisation de la faire exécuter aux frais du commerçant ; c) la réduction de son obligation ; d) la résiliation du contrat ; e) la résolution du contrat ; ou f) la nullité du contrat, sans préjudice de sa demande en dommages-intérêts dans tous les cas. Il peut également demander des dommages-intérêts punitifs.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-40.1#se:272"),
    ("LNT", "79.1", "Un salarié peut s'absenter du travail pendant une période d'au plus 26 semaines sur une période de 12 mois pour cause de maladie, de don d'organes ou de tissus à des fins de greffe, d'accident, de violence conjugale ou de violence à caractère sexuel.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/N-1.1#se:79_1"),
    ("LNT", "81.18", "Pour l'application de la présente loi, on entend par « harcèlement psychologique » une conduite vexatoire se manifestant soit par des comportements, des paroles, des actes ou des gestes répétés, qui sont hostiles ou non désirés, laquelle porte atteinte à la dignité ou à l'intégrité psychologique ou physique du salarié et qui entraîne, pour celui-ci, un milieu de travail néfaste.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/N-1.1#se:81_18"),
    ("LNT", "82", "Un employeur doit donner un avis écrit à un salarié avant de mettre fin à son contrat de travail ou de le mettre à pied pour six mois ou plus.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/N-1.1#se:82"),
    ("LNT", "122", "Il est interdit à un employeur ou à son agent de congédier, de suspendre ou de déplacer un salarié, d'exercer à son endroit des mesures discriminatoires ou des représailles, ou de lui imposer toute autre sanction à cause de l'exercice par ce salarié d'un droit qui lui résulte de la présente loi.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/N-1.1#se:122"),
    ("LNT", "124", "Le salarié qui justifie de deux ans de service continu dans une même entreprise et qui croit avoir été congédié sans une cause juste et suffisante peut soumettre sa plainte par écrit à la Commission des normes, de l'équité, de la santé et de la sécurité du travail (CNESST) dans les 45 jours de son congédiement.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/N-1.1#se:124"),
    ("LATMP", "2", "Dans la présente loi, on entend par « lésion professionnelle » une blessure ou une maladie qui survient par le fait ou à l'occasion d'un accident du travail, ou une maladie professionnelle, y compris la récidive, la rechute ou l'aggravation.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-3.001#se:2"),
    ("LATMP", "28", "Une blessure qui arrive sur les lieux du travail alors que le travailleur est à son travail est présumée une lésion professionnelle.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-3.001#se:28"),
    ("LATMP", "438", "Un employeur ne peut intenter une action civile contre son travailleur à raison d'une lésion professionnelle, ni un travailleur contre son employeur.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-3.001#se:438"),
    ("LSAQ", "119", "Les administrateurs et les dirigeants doivent, dans l'exercice de leurs fonctions, respecter les obligations que la loi, les statuts et les règlements leur imposent et agir dans les limites des pouvoirs qui leur sont conférés. Ils doivent agir avec prudence et diligence, honnêteté et loyauté dans l'intérêt de la société.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/S-31.1#se:119"),
    ("LSAQ", "450", "Un demandeur peut s'adresser au tribunal en vue d'obtenir une ordonnance visant à redresser la situation en cas d'abus de pouvoir ou d'injustice (recours en oppression) de la part de la société ou de ses administrateurs à l'égard des détenteurs de valeurs mobilières, des administrateurs ou des dirigeants.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/S-31.1#se:450"),
    ("CSR", "328", "Sauf sur les chemins où une signalisation contraire apparaît, nul ne peut conduire un véhicule routier à une vitesse excédant les limites prescrites (50 km/h en agglomération, 90 km/h hors agglomération, 100 km/h sur autoroute).", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/C-24.2#se:328"),
    ("CSR", "359", "À moins d'une signalisation contraire, face à un feu rouge, le conducteur d'un véhicule routier ou d'une bicyclette doit immobiliser son véhicule avant le passage pour piétons ou la ligne d'arrêt.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/C-24.2#se:359"),
    ("LOI25", "3.5", "Toute personne qui exploite une entreprise et qui a des motifs de croire que s'est produit un incident de confidentialité impliquant un renseignement personnel qu'elle détient doit prendre les mesures raisonnables pour diminuer les risques qu'un préjudice soit causé et aviser la Commission d'accès à l'information (CAI) s'il présente un risque de préjudice sérieux.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-39.1#se:3_5"),
    ("LOI25", "17", "Avant de communiquer à l'extérieur du Québec un renseignement personnel, la personne qui exploite une entreprise doit procéder à une évaluation des facteurs relatifs à la vie privée (EFVP).", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-39.1#se:17"),
    ("LOI25", "93.1", "Lorsqu'une atteinte illicite à un droit conféré par la présente loi ou par les articles 35 à 40 du Code civil cause un préjudice et que cette atteinte est intentionnelle ou résulte d'une faute lourde, le tribunal accorde des dommages-intérêts punitifs d'au moins 1 000 $.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/P-39.1#se:93_1"),
    ("LAA", "1", "Dans la présente loi, on entend par « accident » : tout événement au cours duquel un préjudice est causé par une automobile ; et par « préjudice causé par une automobile » : tout préjudice corporel ou matériel causé par une automobile, par son usage ou par son chargement, y compris le préjudice causé par une remorque utilisée avec une automobile, mais à l'exception du préjudice causé par l'action autonome d'un animal faisant partie du chargement et du préjudice causé à une personne ou à un bien en raison d'une action de cette personne reliée à l'entretien, la réparation, la modification ou l'amélioration d'une automobile.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:1"),
    ("LAA", "2", "Dans le présent titre, on entend par « préjudice corporel » : tout préjudice d'ordre physique ou psychique d'une victime, y compris le décès, qui lui est causé dans un accident, ainsi que les dommages aux vêtements que porte la victime lors de l'accident.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:2"),
    ("LAA", "14", "La victime qui, au moment de l'accident, exerçait habituellement un emploi à temps plein a droit à une indemnité de remplacement du revenu (IRR) si, en raison de cet accident, elle est incapable d'exercer son emploi.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:14"),
    ("LAA", "45", "La Société détermine un emploi à une victime à compter du moment où elle est capable d'exercer un emploi à temps plein ou à temps partiel que la Société juge convenable compte tenu de sa formation, de son expérience de travail et de ses capacités physiques et intellectuelles au moment où elle décide de lui déterminer un emploi.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:45"),
    ("LAA", "49", "L'indemnité de remplacement du revenu (IRR) prend fin lorsque la victime redevient capable d'exercer son emploi, lorsqu'elle redevient capable d'exercer l'emploi qui lui aurait été déterminé ou un an après le moment où elle devient capable d'exercer un emploi déterminé par la Société en vertu de l'article 45.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:49"),
    ("LAA", "73", "Pour le préjudice non pécuniaire (perte de jouissance de la vie, douleurs physiques et souffrances psychiques), la victime a droit, dans la mesure déterminée par règlement (Règlement sur le barème des dommages corporels - SUTT), à une indemnité forfaitaire dont le montant ne peut excéder le plafond légal indexé.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:73"),
    ("LAA", "83.34", "La personne qui se croit lésée par une décision rendue par la Société (SAAQ) peut, dans les 60 jours de sa notification, en demander la révision administrative, puis contester la décision en révision devant le Tribunal administratif du Québec (TAQ) dans les 60 jours.", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:83_34"),
    ("LAA", "83.57", "Les indemnités prévues au présent titre tiennent lieu de tous les droits et recours en raison d'un préjudice corporel et nulle action à ce sujet n'est admise devant un tribunal de droit commun (immunité civile no-fault).", "https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/A-25#se:83_57"),
]

_SEED_BENCHMARKS = [
    ("dol_restitution_prestation", "Dol contractuel / Marge ou profit caché (art. 1401, 1407 C.c.Q.)", 50.0, 58.0, 72.0, 2500.0, 5000.0, 10000.0, 12.0, "Le juge accorde la réduction de l'obligation (marge dolosive cachée) et 2 500 $ à 5 000 $ d'inconvénients, mais rejette dans 88 % des cas les honoraires extrajudiciaires (art. 51 C.p.c.) en l'absence d'abus procédural distinct.", "Robertson c. Murray (Maisons Paragon Homes inc.), 2022 QCCQ 10057 (CanLII)"),
    ("vice_cache_malfacon_toiture", "Vice caché / Malfaçons entrepreneuriales & Vétusté (art. 1726, 2100, 1607 C.c.Q.)", 55.0, 75.0, 85.0, 1000.0, 2500.0, 5000.0, 5.0, "Amputation systématique de 15 % à 35 % du coût de remplacement neuf au titre de la dépréciation pour vétusté / plus-value (art. 1607 et 1611 C.c.Q.) et rejet des soumissions non ventilées (art. 2803 C.c.Q.).", "Caron c. Toiture Allaire ; ABB Inc. c. Domtar Inc., [2007] 3 R.C.S. 461"),
    ("protection_consommateur_lpc_272", "Pratique interdite / Fausse représentation commerçant (art. 219, 228, 253, 272 L.p.c.)", 65.0, 82.0, 100.0, 1500.0, 3500.0, 8000.0, 18.0, "Présomption absolue de préjudice sous l'art. 253 L.p.c. Dommages punitifs sous l'art. 272 L.p.c. généralement fixés entre 1 000 $ et 10 000 $ en Cour du Québec selon la gravité de l'insouciance (arrêt Richard c. Time Inc.).", "Richard c. Time Inc., 2012 CSC 8"),
    ("congediement_injustifie_lnt_124", "Congédiement sans cause juste et suffisante / Délai de congé (art. 2091 C.c.Q., art. 124 L.n.t.)", 40.0, 60.0, 80.0, 2000.0, 7500.0, 20000.0, 10.0, "Barème jurisprudentiel québécois de 2 à 4 semaines d'indemnité par année d'ancienneté (plafonné à 24 mois), diminué des revenus gagnés durant la période (obligation de mitigation des dommages, art. 1479 C.c.Q.).", "Asphalte Desjardins inc. c. Québec (CNT), 2014 CSC 51"),
    ("saaq_irr_sequelles_taq", "Litige SAAQ devant le TAQ : Relation causale, IRR (art. 14, 45, 49 L.a.a.) & Séquelles permanentes (art. 73 L.a.a.)", 0.0, 45.0, 78.0, 0.0, 12500.0, 48000.0, 0.0, "En vertu du régime no-fault (art. 83.57 L.a.a.), le litige devant le TAQ repose sur : 1) la preuve médicale prépondérante du lien causal entre l'accident et la lésion vs l'état dégénératif préexistant asymptomatique (art. 2 L.a.a.) ; 2) la capacité d'exercer un emploi convenable déterminé (art. 45 et 49 L.a.a.) mettant fin à l'IRR ; et 3) la classe de gravité des unités fonctionnelles (SUTT, art. 73 L.a.a.).", "Productions Pram inc. c. Lemay, [1992] R.J.Q. 1738 (C.A.) ; J.L. c. SAAQ (TAQ SAS)"),
]


def _ensure_mcp_seed():
    if not os.path.exists(CCQ_CPC_DB):
        return
    try:
        conn = sqlite3.connect(CCQ_CPC_DB)
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS quantum_benchmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT UNIQUE,
            label TEXT,
            min_pct_claim REAL,
            median_pct_claim REAL,
            max_pct_claim REAL,
            troubles_inconvenients_min REAL,
            troubles_inconvenients_median REAL,
            troubles_inconvenients_max REAL,
            art51_cpc_grant_rate_pct REAL,
            key_rule TEXT,
            reference_case TEXT
        )
        """)
        for b in _SEED_BENCHMARKS:
            cur.execute("""
            INSERT OR REPLACE INTO quantum_benchmarks (
                category, label, min_pct_claim, median_pct_claim, max_pct_claim,
                troubles_inconvenients_min, troubles_inconvenients_median, troubles_inconvenients_max,
                art51_cpc_grant_rate_pct, key_rule, reference_case
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, b)
        for code, numero, texte, url in _SEED_STATUTES:
            cur.execute("SELECT id FROM articles WHERE code = ? AND numero = ?", (code, numero))
            if not cur.fetchone():
                cur.execute("INSERT INTO articles (code, numero, texte, url) VALUES (?, ?, ?, ?)", (code, numero, texte, url))
                rowid = cur.lastrowid
                try:
                    cur.execute("INSERT INTO articles_fts (rowid, code, numero, texte) VALUES (?, ?, ?, ?)", (rowid, code, numero, texte))
                except Exception:
                    pass
        conn.commit()
        conn.close()
    except Exception:
        pass


_ensure_mcp_seed()


def _query_article(code: str, numero: str) -> dict:
    if not os.path.exists(CCQ_CPC_DB):
        return {"found": False, "error": "ccq_cpc.db introuvable"}
    conn = sqlite3.connect(CCQ_CPC_DB)
    cur = conn.cursor()
    cur.execute(
        "SELECT code, numero, texte, url FROM articles WHERE code = ? AND numero = ? LIMIT 1",
        (code.upper().strip(), str(numero).strip())
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        return {"found": False, "code": code.upper(), "numero": str(numero)}
    return {"found": True, "code": row[0], "numero": row[1], "texte": row[2], "url": row[3]}


def _search_fts(keyword: str, code: str = "", limit: int = 5) -> list:
    if not os.path.exists(CCQ_CPC_DB):
        return []
    clean_kw = re.sub(r"[^a-zA-ZÀ-ÿ0-9\s]", " ", keyword or "").strip()
    if not clean_kw:
        return []
    conn = sqlite3.connect(CCQ_CPC_DB)
    cur = conn.cursor()
    try:
        if code:
            cur.execute(
                "SELECT code, numero, texte, url FROM articles WHERE id IN "
                "(SELECT rowid FROM articles_fts WHERE articles_fts MATCH ? AND code = ?) LIMIT ?",
                (f'"{clean_kw}"', code.upper().strip(), int(limit))
            )
        else:
            cur.execute(
                "SELECT code, numero, texte, url FROM articles WHERE id IN "
                "(SELECT rowid FROM articles_fts WHERE articles_fts MATCH ?) LIMIT ?",
                (f'"{clean_kw}"', int(limit))
            )
        rows = cur.fetchall()
    except Exception:
        rows = []
    conn.close()
    return [{"code": r[0], "numero": r[1], "texte": r[2], "url": r[3]} for r in rows]


def _get_quantum_benchmarks(category: str = "") -> list:
    if not os.path.exists(CCQ_CPC_DB):
        return []
    conn = sqlite3.connect(CCQ_CPC_DB)
    cur = conn.cursor()
    try:
        if category:
            cur.execute(
                "SELECT category, label, min_pct_claim, median_pct_claim, max_pct_claim, "
                "troubles_inconvenients_median, art51_cpc_grant_rate_pct, key_rule, reference_case "
                "FROM quantum_benchmarks WHERE category LIKE ?",
                (f"%{category}%",)
            )
        else:
            cur.execute(
                "SELECT category, label, min_pct_claim, median_pct_claim, max_pct_claim, "
                "troubles_inconvenients_median, art51_cpc_grant_rate_pct, key_rule, reference_case "
                "FROM quantum_benchmarks"
            )
        rows = cur.fetchall()
    except Exception:
        rows = []
    conn.close()
    return [
        {
            "category": r[0],
            "label": r[1],
            "min_pct_claim": r[2],
            "median_pct_claim": r[3],
            "max_pct_claim": r[4],
            "troubles_inconvenients_median": r[5],
            "art51_cpc_grant_rate_pct": r[6],
            "key_rule": r[7],
            "reference_case": r[8],
        }
        for r in rows
    ]


@mcp_bp.route("/tools", methods=["GET"])
def list_mcp_tools():
    """Retourne les statistiques de la base SQLite MCP et la liste des outils disponibles."""
    stats = {}
    quantum_count = 0
    if os.path.exists(CCQ_CPC_DB):
        conn = sqlite3.connect(CCQ_CPC_DB)
        cur = conn.cursor()
        for code, cnt in cur.execute("SELECT code, COUNT(*) FROM articles GROUP BY code").fetchall():
            stats[code] = cnt
        try:
            quantum_count = cur.execute("SELECT COUNT(*) FROM quantum_benchmarks").fetchone()[0]
        except Exception:
            quantum_count = 0
        conn.close()

    return jsonify({
        "status": "ok",
        "server": "lexior-normative-mcp",
        "version": "2.1.0",
        "indexed_statutes": stats,
        "quantum_benchmarks_count": quantum_count,
        "tools": [
            "get_law_article",
            "search_laws_fts",
            "get_quantum_benchmark",
            "scrape_legisquebec_article"
        ]
    })


@mcp_bp.route("/call", methods=["POST"])
def call_mcp_tool():
    """Exécute un outil MCP via HTTPS (compatible Lexior Notebook, agents externes et scripts R&D)."""
    payload = request.get_json(silent=True) or {}
    tool_name = payload.get("tool") or payload.get("name")
    args = payload.get("arguments") or payload.get("params") or {}

    if tool_name == "get_law_article":
        return jsonify(_query_article(args.get("code", "CCQ"), args.get("numero", "1457")))
    elif tool_name == "search_laws_fts":
        return jsonify({"results": _search_fts(args.get("keyword", ""), args.get("code", ""), args.get("limit", 5))})
    elif tool_name == "get_quantum_benchmark":
        return jsonify({"benchmarks": _get_quantum_benchmarks(args.get("category", ""))})
    elif tool_name == "scrape_legisquebec_article":
        chapter_id = args.get("chapter_id", "P-40.1")
        code_label = args.get("code_label", "LPC").upper()
        article_num = str(args.get("article_num", "272"))
        anchor_id = article_num.replace(".", "_")
        url = f"https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/{chapter_id}#se:{anchor_id}"
        try:
            resp = requests.get(f"https://www.legisquebec.gouv.qc.ca/fr/showdoc/cs/{chapter_id}", timeout=20)
            soup = BeautifulSoup(resp.content, "html.parser")
            anchor = soup.find(id=f"se:{anchor_id}")
            div = anchor.find_parent("div") if anchor else None
            if not div:
                return jsonify({"status": "not_found", "url": url}), 404
            text = re.sub(r"\s+", " ", div.get_text(separator=" ").strip())
            conn = sqlite3.connect(CCQ_CPC_DB)
            cur = conn.cursor()
            cur.execute("DELETE FROM articles WHERE code = ? AND numero = ?", (code_label, article_num))
            cur.execute("INSERT INTO articles (code, numero, texte, url) VALUES (?, ?, ?, ?)", (code_label, article_num, text, url))
            rowid = cur.lastrowid
            try:
                cur.execute("INSERT INTO articles_fts (rowid, code, numero, texte) VALUES (?, ?, ?, ?)", (rowid, code_label, article_num, text))
            except Exception:
                pass
            conn.commit()
            conn.close()
            return jsonify({"status": "indexed", "code": code_label, "numero": article_num, "texte": text, "url": url})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify({"error": f"Outil MCP inconnu : {tool_name}"}), 400

