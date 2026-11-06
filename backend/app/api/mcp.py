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
