"""
Jurisprudence Grounding Service
Vérifie les arguments juridiques générés par les agents contre le dataset local (anti-hallucination).
"""
import os
import json
import sqlite3
import logging
import re
from typing import List, Optional
from openai import OpenAI
from app.config import Config

logger = logging.getLogger('mirofish.jurisprudence_grounding')

class JurisprudenceGrounding:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(JurisprudenceGrounding, cls).__new__(cls)
            cls._instance._init_db()
            cls._instance._mcp_offline_until = 0.0
            cls._instance._a2aj_offline_until = 0.0
            cls._instance._verify_cache = {}
        return cls._instance

    def _init_db(self):
        """Initialise la base SQLite locale pour la recherche rapide (Jurisprudence + Serveur SQLite Souverain C.c.Q./C.p.c.)."""
        self.db_path = os.path.join(os.path.dirname(__file__), '../../uploads/jurisprudence.db')
        self.json_path = os.path.join(os.path.dirname(__file__), '../../uploads/jurisprudence.json')
        self.ccq_cpc_db_path = os.path.join(os.path.dirname(__file__), '../data/ccq_cpc.db')
        
        # Si la base SQLite n'existe pas mais le JSON oui, on construit l'index SQLite
        if not os.path.exists(self.db_path) and os.path.exists(self.json_path):
            logger.info("Construction de la base de données SQLite pour le Grounding...")
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Création de la table avec index sur le nom de loi et citation pour recherche rapide
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                law_name TEXT,
                citation TEXT,
                category TEXT,
                law_summary TEXT,
                section_text TEXT
            )
            ''')
            
            # Pour la recherche textuelle (FTS5) - optionnel mais très efficace
            try:
                cursor.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS cases_fts USING fts5(
                    law_name,
                    citation,
                    law_summary,
                    content='cases',
                    content_rowid='id'
                )
                ''')
            except sqlite3.OperationalError:
                logger.warning("FTS5 n'est pas supporté, recherche standard utilisée.")
            
            # Importation par lot
            logger.info(f"Lecture du fichier JSON : {self.json_path}")
            try:
                with open(self.json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                logger.info(f"Insertion de {len(data)} enregistrements...")
                batch = []
                for item in data:
                    batch.append((
                        item.get('law_name', ''),
                        item.get('citation', ''),
                        item.get('category', ''),
                        item.get('law_summary', ''),
                        item.get('section_text', '')
                    ))
                    
                    if len(batch) >= 10000:
                        cursor.executemany(
                            'INSERT INTO cases (law_name, citation, category, law_summary, section_text) VALUES (?, ?, ?, ?, ?)',
                            batch
                        )
                        conn.commit()
                        batch = []
                        
                if batch:
                    cursor.executemany(
                        'INSERT INTO cases (law_name, citation, category, law_summary, section_text) VALUES (?, ?, ?, ?, ?)',
                        batch
                    )
                    conn.commit()
                
                # Mise à jour de l'index FTS
                try:
                    cursor.execute("INSERT INTO cases_fts(cases_fts) VALUES('rebuild')")
                    conn.commit()
                except Exception as e:
                    logger.error(f"Error rebuilding FTS index in database init: {e}")
                    
                logger.info("Base de données initialisée avec succès.")
            except Exception as e:
                logger.error(f"Erreur lors de la création de la BDD : {e}")
            finally:
                conn.close()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def get_code_article_local(self, code: str, numero: str) -> Optional[dict]:
        """Recherche déterministe ultra-rapide (< 1 ms) d'un article du C.c.Q. ou du C.p.c. dans ccq_cpc.db."""
        if not hasattr(self, "ccq_cpc_db_path") or not os.path.exists(self.ccq_cpc_db_path):
            return None
        try:
            conn = sqlite3.connect(self.ccq_cpc_db_path)
            cur = conn.cursor()
            cur.execute(
                "SELECT code, numero, texte, url FROM articles WHERE code = ? AND numero = ? LIMIT 1",
                (code.upper(), str(numero).strip())
            )
            row = cur.fetchone()
            conn.close()
            if row:
                return {"code": row[0], "numero": row[1], "texte": row[2], "url": row[3]}
        except Exception as e:
            logger.error(f"Erreur lecture SQLite ccq_cpc.db ({code} {numero}): {e}")
        return None

    def search_code_fts_local(self, keyword: str, code: str = "CCQ", limit: int = 3) -> List[dict]:
        """Recherche plein texte FTS5 dans les 3 489 articles C.c.Q. et 876 articles C.p.c."""
        if not hasattr(self, "ccq_cpc_db_path") or not os.path.exists(self.ccq_cpc_db_path):
            return []
        results = []
        try:
            conn = sqlite3.connect(self.ccq_cpc_db_path)
            cur = conn.cursor()
            clean_kw = re.sub(r'[^a-zA-ZÀ-ÿ0-9]', '', keyword)
            if not clean_kw:
                conn.close()
                return []
            cur.execute(
                "SELECT code, numero, texte, url FROM articles WHERE id IN "
                "(SELECT rowid FROM articles_fts WHERE articles_fts MATCH ? AND code = ?) LIMIT ?",
                (f'"{clean_kw}"', code.upper(), limit)
            )
            for r in cur.fetchall():
                results.append({"code": r[0], "numero": r[1], "texte": r[2], "url": r[3]})
            conn.close()
        except Exception as e:
            logger.error(f"Erreur FTS5 ccq_cpc.db ({keyword}): {e}")
        return results

    def get_quantum_benchmarks_local(self, context: str = "") -> List[dict]:
        """Récupère les barèmes actuariels empiriques QCCQ/QCCS depuis la table quantum_benchmarks de ccq_cpc.db."""
        if not hasattr(self, "ccq_cpc_db_path") or not os.path.exists(self.ccq_cpc_db_path):
            return []
        ctx_lower = (context or "").lower()
        results = []
        try:
            conn = sqlite3.connect(self.ccq_cpc_db_path)
            cur = conn.cursor()
            cur.execute(
                "SELECT category, label, min_pct_claim, median_pct_claim, max_pct_claim, "
                "troubles_inconvenients_median, art51_cpc_grant_rate_pct, key_rule, reference_case "
                "FROM quantum_benchmarks"
            )
            rows = cur.fetchall()
            conn.close()
            for r in rows:
                cat = r[0]
                match = False
                if not context:
                    match = True
                elif cat == "dol_restitution_prestation" and any(k in ctx_lower for k in ["dol", "1401", "1407", "marge", "profit caché", "tromp"]):
                    match = True
                elif cat == "vice_cache_malfacon_toiture" and any(k in ctx_lower for k in ["vice", "toiture", "malfaçon", "1726", "2100", "vétusté"]):
                    match = True
                elif cat == "protection_consommateur_lpc_272" and any(k in ctx_lower for k in ["consommateur", "commerçant", "l.p.c", "lpc", "272", "punitif"]):
                    match = True
                elif cat == "congediement_injustifie_lnt_124" and any(k in ctx_lower for k in ["congédiement", "salarié", "employeur", "l.n.t", "cnesst", "124"]):
                    match = True
                elif cat == "saaq_irr_sequelles_taq" and any(k in ctx_lower for k in ["saaq", "assurance automobile", "l.a.a", "laa", "taq", "irr", "emploi convenable", "séquelle", "83.57"]):
                    match = True
                elif cat == "cnesst_latmp_lesion_professionnelle" and any(k in ctx_lower for k in ["lésion professionnelle", "accident du travail", "latmp", "l.a.t.m.p", "cnesst", "329", "326", "tat"]):
                    match = True
                elif cat == "harcelement_psychologique_lnt" and any(k in ctx_lower for k in ["harcèlement", "81.18", "81.19", "123.15", "conduite vexatoire"]):
                    match = True
                elif cat == "bail_logement_tal" and any(k in ctx_lower for k in ["bail", "locataire", "locateur", "logement", "loyer", "tal", "tribunal administratif du logement", "1854", "1863"]):
                    match = True
                elif cat == "fiscalite_cotisation_revenu_quebec" and any(k in ctx_lower for k in ["cotisation", "revenu québec", "tvq", "l.a.f", "laf", "l.t.v.q", "ltvq", "pénalité", "59.3", "1049"]):
                    match = True
                elif cat == "oppression_actionnaires_lsaq" and any(k in ctx_lower for k in ["actionnaire", "oppression", "450", "l.s.a.q", "lsaq", "société par actions", "administrateur"]):
                    match = True
                elif cat == "atteinte_reputation_vie_privee_charte_loi25" and any(k in ctx_lower for k in ["diffamation", "réputation", "vie privée", "loi 25", "renseignement personnel", "incident de confidentialité", "charte"]):
                    match = True
                if match:
                    results.append({
                        "category": r[0],
                        "label": r[1],
                        "min_pct_claim": r[2],
                        "median_pct_claim": r[3],
                        "max_pct_claim": r[4],
                        "troubles_inconvenients_median": r[5],
                        "art51_cpc_grant_rate_pct": r[6],
                        "key_rule": r[7],
                        "reference_case": r[8],
                    })
        except Exception as e:
            logger.error(f"Erreur lecture quantum_benchmarks: {e}")
        return results

    def build_statutory_grounding_block(self, context: str, litigation_type: str = "civil") -> str:
        """
        Pré-injecte de manière déterministe le texte officiel exact des articles du C.c.Q., du C.p.c.,
        des lois statutaires québécoises (L.p.c., L.n.t., L.a.t.m.p., L.s.a.Q., C.s.r., Loi 25)
        et des barèmes actuariels (`quantum_benchmarks`) pertinents au dossier.
        """
        if not hasattr(self, "ccq_cpc_db_path") or not os.path.exists(self.ccq_cpc_db_path):
            return ""
        ctx_lower = (context or "").lower()
        ccq_nums = []
        cpc_nums = []
        special_statutes = []  # tuples (code, numero)

        # 1. Extraire tous les articles explicitement mentionnés dans le dossier (en excluant ceux explicitement rattachés à LAA/CPC/LPC/LNT/CSR/LSAQ)
        non_ccq_statute_tag = r'(?:C\.p\.c\.|CPC|L\.p\.c\.|LPC|L\.n\.t\.|LNT|C\.s\.r\.|CSR|L\.s\.a\.Q\.|LSAQ|L\.a\.t\.m\.p\.|LATMP|L\.a\.a\.|LAA|Loi\s+sur\s+l\'assurance\s+automobile)'
        non_ccq_explicit = set()
        for span_match in re.finditer(
            r'(?:articles?|art\.?)\s*([\d\.,\s]+?(?:et\s+\d+(?:\.\d+)?)?)\s*(?:du\s+|de\s+la\s+)?' + non_ccq_statute_tag,
            context or "", re.IGNORECASE
        ):
            for num_tok in re.findall(r'\d+(?:\.\d+)?', span_match.group(1)):
                non_ccq_explicit.add(num_tok)
        # Si c'est un dossier SAAQ / L.a.a., exclure d'office les numéros typiques de la L.a.a. (1, 2, 14, 45, 49, 73, 83.34, 83.57) du C.c.Q.
        if any(k in ctx_lower for k in ["saaq", "l.a.a", "assurance automobile"]):
            non_ccq_explicit.update(["1", "2", "14", "15", "29", "45", "49", "73", "83.34", "83.57"])

        for m in re.findall(r'(?:articles?|art\.?)\s*(\d+(?:\.\d+)?)', context or "", re.IGNORECASE):
            if m not in ccq_nums and m not in non_ccq_explicit:
                ccq_nums.append(m)

        # 2. Ajouter le socle normatif québécois selon la nature du litige
        if any(k in ctx_lower for k in ["dol", "manoeuvre", "manœuvre", "1401", "1399", "erreur", "consentement"]):
            for n in ["1399", "1400", "1401", "1407"]:
                if n not in ccq_nums:
                    ccq_nums.append(n)
        if any(k in ctx_lower for k in ["entrepreneur", "toiture", "toit", "travaux", "contrat d'entreprise", "service", "2100"]):
            for n in ["2098", "2100", "2120"]:
                if n not in ccq_nums:
                    ccq_nums.append(n)
        if any(k in ctx_lower for k in ["vice", "caché", "acheteur", "vendeur", "immeuble", "1726"]):
            for n in ["1726", "1728", "1739"]:
                if n not in ccq_nums:
                    ccq_nums.append(n)
        if any(k in ctx_lower for k in ["bail", "locataire", "locateur", "logement"]):
            for n in ["1854", "1863", "1955"]:
                if n not in ccq_nums:
                    ccq_nums.append(n)

        # 2B. Lois statutaires spécialisées (LAA/LJA/SAAQ, LATMP/CNESST, LNT/TAT, LPC, LAF/LTVQ/LI, LSAQ, CHARTE/LOI25, LTAL, CSR, CCR)
        is_saaq_case = any(k in ctx_lower for k in ["saaq", "assurance automobile", "l.a.a", "laa", "remplacement du revenu", "irr", "emploi convenable", "83.57", "83.34"])
        if is_saaq_case:
            for num in ["1", "2", "5", "14", "45", "49", "73", "83.2", "83.32", "83.34", "83.57"]:
                special_statutes.append(("LAA", num))
            for num in ["15", "119", "120", "142"]:
                special_statutes.append(("LJA", num))
        if any(k in ctx_lower for k in ["consommateur", "commerçant", "l.p.c", "lpc", "représentation trompeuse", "272", "garantie légale"]):
            for num in ["8", "37", "38", "53", "219", "228", "253", "272"]:
                special_statutes.append(("LPC", num))
        if not is_saaq_case and any(k in ctx_lower for k in ["salarié", "congédiement", "harcèlement", "l.n.t", "lnt", "normes du travail", "81.18", "124"]):
            for num in ["81.18", "81.19", "82", "122", "123.15", "124", "128"]:
                special_statutes.append(("LNT", num))
        if not is_saaq_case and any(k in ctx_lower for k in ["lésion professionnelle", "accident du travail", "latmp", "l.a.t.m.p", "cnesst", "329", "326", "bem"]):
            for num in ["2", "7", "27", "28", "44", "49", "83", "212", "224.1", "326", "329", "438"]:
                special_statutes.append(("LATMP", num))
        if any(k in ctx_lower for k in ["cotisation", "revenu québec", "tvq", "l.a.f", "laf", "l.t.v.q", "ltvq", "impôt", "rti"]):
            for num in ["14", "21", "24.0.1", "28", "59", "59.2", "59.3", "93.1.1"]:
                special_statutes.append(("LAF", num))
            for num in ["16", "206.1", "323.1"]:
                special_statutes.append(("LTVQ", num))
            for num in ["1010", "1049"]:
                special_statutes.append(("LI", num))
        if any(k in ctx_lower for k in ["actionnaire", "administrateur", "oppression", "l.s.a.q", "lsaq", "société par actions", "450"]):
            for num in ["112", "119", "154", "214", "450", "451"]:
                special_statutes.append(("LSAQ", num))
        if any(k in ctx_lower for k in ["bail", "locataire", "locateur", "logement", "tal", "tribunal administratif du logement"]):
            for num in ["28", "56", "63", "91"]:
                special_statutes.append(("LTAL", num))
        if not is_saaq_case and any(k in ctx_lower for k in ["vitesse", "cinémomètre", "328", "sécurité routière", "c.s.r"]):
            for num in ["328", "359"]:
                special_statutes.append(("CSR", num))
        if any(k in ctx_lower for k in ["renseignement personnel", "confidentialité", "loi 25", "vie privée", "cai"]):
            for num in ["3.1", "3.5", "10", "14", "17", "93.1"]:
                special_statutes.append(("LOI25", num))
        if any(k in ctx_lower for k in ["charte", "dignité", "réputation", "diffamation", "discrimination", "atteinte illicite"]):
            for num in ["1", "4", "5", "10", "46", "49"]:
                special_statutes.append(("CHARTE", num))
        if litigation_type == "criminal" or any(k in ctx_lower for k in ["code criminel", "c.cr.", "voies de fait", "menaces", "vol", "fraude", "harcèlement criminel", "dpcp"]):
            for num in ["21", "34", "264", "264.1", "265", "266", "267", "322", "334", "348", "380", "718", "718.1"]:
                special_statutes.append(("CCR", num))

        # Socle transversal : Responsabilité, Causalité, Quantum, Intérêts légaux, Preuve et Prescription
        for core_ccq in ["1457", "1607", "1611", "1618", "1619", "2803", "2804", "2925"]:
            if core_ccq not in ccq_nums:
                ccq_nums.append(core_ccq)

        # Socle procédural C.p.c. (Proportionnalité, Abus art. 51, CRA, Irrecevabilité, Expertise)
        for core_cpc in ["18", "51", "54", "168", "235"]:
            if core_cpc not in cpc_nums:
                cpc_nums.append(core_cpc)

        lines = [
            "\n\n=== MÉMOIRE NORMATIVE DÉTERMINISTE (SERVEUR SQLITE C.C.Q. & C.P.C.) ===",
            "Utilise prioritairement les articles vérifiés ci-dessous (ne jamais inventer un numéro d'article) :"
        ]
        for num in ccq_nums[:12]:
            row = self.get_code_article_local("CCQ", num)
            if row:
                snippet = row["texte"].replace("\n", " ").strip()
                if len(snippet) > 320:
                    snippet = snippet[:320] + "..."
                lines.append(f"- [Art. {num} C.c.Q.] : {snippet}")
        for num in cpc_nums[:5]:
            row = self.get_code_article_local("CPC", num)
            if row:
                snippet = row["texte"].replace("\n", " ").strip()
                if len(snippet) > 260:
                    snippet = snippet[:260] + "..."
                lines.append(f"- [Art. {num} C.p.c.] : {snippet}")
        for code_lbl, num in special_statutes[:16]:
            row = self.get_code_article_local(code_lbl, num)
            if row:
                snippet = row["texte"].replace("\n", " ").strip()
                if len(snippet) > 260:
                    snippet = snippet[:260] + "..."
                lines.append(f"- [Art. {num} {code_lbl}] : {snippet}")

        # 3. Injecter les barèmes actuariels empiriques (quantum_benchmarks)
        q_benchmarks = self.get_quantum_benchmarks_local(context)
        if q_benchmarks:
            lines.append("\n=== BARÈMES ACTUARIELS EMPIRIQUES DE QUANTUM (QCCQ / QCCS) ===")
            for qb in q_benchmarks[:3]:
                lines.append(
                    f"- [{qb['label']}] : Fourchette historique de {qb['min_pct_claim']:.0f}% à {qb['max_pct_claim']:.0f}% "
                    f"(médiane {qb['median_pct_claim']:.0f}%), troubles médians {qb['troubles_inconvenients_median']:.0f} $, "
                    f"taux d'octroi art. 51 C.p.c. : {qb['art51_cpc_grant_rate_pct']:.0f}%. "
                    f"Règle : {qb['key_rule']} (Réf: {qb['reference_case']})"
                )
        return "\n".join(lines) + "\n"

    def _verify_with_llm(self, claim: str, source_text: str) -> bool:
        """
        Appelle le LLM pour vérifier si le texte officiel de la source soutient l'affirmation de l'agent.
        """
        cache_key = (claim, source_text)
        if hasattr(self, "_verify_cache") and cache_key in self._verify_cache:
            logger.info("Retrieved LLM verification from cache.")
            return self._verify_cache[cache_key]

        system_prompt = (
            "Vous êtes un assistant juridique rigoureux de Lexior.\n"
            "Votre tâche est de déterminer si le texte de loi ou l'arrêt officiel fourni "
            "valide et soutient l'affirmation juridique faite par l'agent (par exemple, s'il cite le bon article "
            "avec le bon sujet, et ne fait pas de confusion ou d'hallucination).\n"
            "Répondez strictement au format JSON suivant :\n"
            "{\n"
            "  \"supports\": true ou false,\n"
            "  \"reason\": \"Explication courte en français\"\n"
            "}"
        )
        user_content = (
            f"Affirmation de l'agent :\n{claim}\n\n"
            f"Texte officiel de la source :\n{source_text}\n\n"
            "Est-ce que la source officielle soutient et valide cette affirmation ?"
        )
        
        try:
            api_key = Config.LLM_API_KEY or "local-no-key"
            base_url = Config.LLM_BASE_URL
            model_name = getattr(Config, 'LLM_MODEL_NAME', 'gpt-4o-mini')
            
            if base_url:
                client = OpenAI(api_key=api_key, base_url=base_url)
            else:
                client = OpenAI(api_key=api_key)
                
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            res_data = json.loads(response.choices[0].message.content)
            logger.info(f"LLM verification result: {res_data}")
            supports = res_data.get("supports", False)
            if hasattr(self, "_verify_cache"):
                self._verify_cache[cache_key] = supports
            return supports
        except Exception as e:
            logger.error(f"Erreur de vérification LLM: {e}")
            # En cas d'erreur LLM, on considère par défaut que c'est bon pour ne pas bloquer
    def verify_argument(self, agent_argument: str, role: str = "prosecutor", context: Optional[str] = None, litigation_type: str = "civil") -> dict:
        """
        Vérifie si l'argument de l'agent est ancré dans la réalité juridique
        en interrogeant prioritairement le Serveur MCP du Code civil du Québec (pour tous les articles cités),
        puis le contexte des pièces du dossier et l'API A2AJ / SQLite local.
        """
        found_references = []
        is_hallucination = True

        # 1. Vérification Prioritaire CCQ (Code civil du Québec) et CPC (Code de procédure civile) sur TOUS les articles cités
        arg_lower = agent_argument.lower()
        is_cpc = any(term in arg_lower for term in ["cpc", "c.p.c.", "c.p.c", "procédure civile"])
        has_ccq_mention = any(term in arg_lower for term in ["ccq", "c.c.q.", "c.c.q", "code civil", "québec"])
        is_ccq = has_ccq_mention or (litigation_type == "civil" and not is_cpc and any(t in arg_lower for t in ["article", "art."]))

        # Détecter les articles explicitement rattachés au C.p.c. et aux lois spéciales québécoises / canadiennes
        cpc_explicit = re.findall(r'(?:articles?|art\.?)\s*(\d+(?:\.\d+)?)\s*(?:du\s+)?(?:C\.p\.c\.|CPC|Code de procédure civile)', agent_argument, re.IGNORECASE)
        laa_explicit = re.findall(r'(?:articles?|art\.?)\s*(\d+(?:\.\d+)?)\s*(?:de\s+la\s+|du\s+)?(?:L\.a\.a\.|LAA|Loi sur l\'assurance automobile)', agent_argument, re.IGNORECASE)
        lja_explicit = re.findall(r'(?:articles?|art\.?)\s*(\d+(?:\.\d+)?)\s*(?:de\s+la\s+|du\s+)?(?:L\.j\.a\.|LJA|Loi sur la justice administrative)', agent_argument, re.IGNORECASE)
        latmp_explicit = re.findall(r'(?:articles?|art\.?)\s*(\d+(?:\.\d+)?)\s*(?:de\s+la\s+|du\s+)?(?:L\.a\.t\.m\.p\.|LATMP|Loi sur les accidents du travail)', agent_argument, re.IGNORECASE)
        lpc_explicit = re.findall(r'(?:articles?|art\.?)\s*(\d+(?:\.\d+)?)\s*(?:de\s+la\s+|du\s+)?(?:L\.p\.c\.|LPC|Loi sur la protection du consommateur)', agent_argument, re.IGNORECASE)
        lnt_explicit = re.findall(r'(?:articles?|art\.?)\s*(\d+(?:\.\d+)?)\s*(?:de\s+la\s+|du\s+)?(?:L\.n\.t\.|LNT|Loi sur les normes du travail)', agent_argument, re.IGNORECASE)
        laf_explicit = re.findall(r'(?:articles?|art\.?)\s*(\d+(?:\.\d+)?)\s*(?:de\s+la\s+|du\s+)?(?:L\.a\.f\.|LAF|Loi sur l\'administration fiscale)', agent_argument, re.IGNORECASE)
        ltvq_explicit = re.findall(r'(?:articles?|art\.?)\s*(\d+(?:\.\d+)?)\s*(?:de\s+la\s+|du\s+)?(?:L\.t\.v\.q\.|LTVQ|Loi sur la taxe de vente du Québec)', agent_argument, re.IGNORECASE)
        li_explicit = re.findall(r'(?:articles?|art\.?)\s*(\d+(?:\.\d+)?)\s*(?:de\s+la\s+|du\s+)?(?:L\.i\.|LI|Loi sur les impôts)', agent_argument, re.IGNORECASE)
        lsaq_explicit = re.findall(r'(?:articles?|art\.?)\s*(\d+(?:\.\d+)?)\s*(?:de\s+la\s+|du\s+)?(?:L\.s\.a\.Q\.|LSAQ|Loi sur les sociétés par actions)', agent_argument, re.IGNORECASE)
        charte_explicit = re.findall(r'(?:articles?|art\.?)\s*(\d+(?:\.\d+)?)\s*(?:de\s+la\s+|du\s+)?(?:Charte|Charte des droits et libertés)', agent_argument, re.IGNORECASE)
        loi25_explicit = re.findall(r'(?:articles?|art\.?)\s*(\d+(?:\.\d+)?)\s*(?:de\s+la\s+|du\s+)?(?:Loi\s*25|L\.p\.r\.p\.s\.p\.|Loi sur la protection des renseignements personnels)', agent_argument, re.IGNORECASE)
        ltal_explicit = re.findall(r'(?:articles?|art\.?)\s*(\d+(?:\.\d+)?)\s*(?:de\s+la\s+|du\s+)?(?:L\.t\.a\.l\.|LTAL|Loi sur le Tribunal administratif du logement)', agent_argument, re.IGNORECASE)
        csr_explicit = re.findall(r'(?:articles?|art\.?)\s*(\d+(?:\.\d+)?)\s*(?:du\s+|de\s+la\s+)?(?:C\.s\.r\.|CSR|Code de la sécurité routière)', agent_argument, re.IGNORECASE)
        ccr_explicit = re.findall(r'(?:articles?|art\.?)\s*(\d+(?:\.\d+)?)\s*(?:du\s+)?(?:C\.cr\.|Code criminel)', agent_argument, re.IGNORECASE)

        art_matches = re.findall(r'(?:articles?|art\.?)\s*(\d+(?:\.\d+)?)', agent_argument, re.IGNORECASE)
        enum_matches = re.findall(r'(?:articles?|art\.?)\s*((?:\d+(?:\.\d+)?\s*(?:,\s*|\s+et\s+|\s+ou\s+))+\d+(?:\.\d+)?)', agent_argument, re.IGNORECASE)
        for em in enum_matches:
            for num_str in re.findall(r'\d+(?:\.\d+)?', em):
                if num_str not in art_matches:
                    art_matches.append(num_str)

        ccq_art_nums = []
        cpc_art_nums = [str(n) for n in cpc_explicit]
        laa_art_nums = [str(n) for n in laa_explicit]
        latmp_art_nums = [str(n) for n in latmp_explicit]
        if any(t in arg_lower for t in ["l.a.a", "laa", "saaq", "assurance automobile"]):
            for cand in ["1", "2", "5", "6", "14", "15", "19", "24", "29", "36", "45", "46", "47", "48", "49", "50", "57", "73", "74", "79", "83.1", "83.2", "83.22", "83.24", "83.30", "83.32", "83.34", "83.41", "83.49", "83.57"]:
                if cand in art_matches and cand not in laa_art_nums:
                    laa_art_nums.append(cand)
        if any(t in arg_lower for t in ["l.a.t.m.p", "latmp", "cnesst", "lésion professionnelle", "accident du travail"]):
            for cand in ["2", "7", "27", "28", "29", "30", "31", "44", "49", "53", "57", "83", "145", "179", "212", "224.1", "239", "326", "329", "358", "359", "438"]:
                if cand in art_matches and cand not in latmp_art_nums:
                    latmp_art_nums.append(cand)

        all_special_lists = (
            cpc_art_nums + laa_art_nums + latmp_art_nums
            + [str(n) for n in lja_explicit] + [str(n) for n in lpc_explicit]
            + [str(n) for n in lnt_explicit] + [str(n) for n in laf_explicit]
            + [str(n) for n in ltvq_explicit] + [str(n) for n in li_explicit]
            + [str(n) for n in lsaq_explicit] + [str(n) for n in charte_explicit]
            + [str(n) for n in loi25_explicit] + [str(n) for n in ltal_explicit]
            + [str(n) for n in csr_explicit] + [str(n) for n in ccr_explicit]
        )
        non_ccq_set = set(all_special_lists)
        for a_str in art_matches:
            if a_str in non_ccq_set:
                continue
            if is_cpc and not any(t in arg_lower for t in ["c.c.q", "ccq", "code civil"]):
                cpc_art_nums.append(a_str)
            elif '.' not in a_str:
                try:
                    n = int(a_str)
                    if 1 <= n <= 3500 and n not in ccq_art_nums:
                        ccq_art_nums.append(n)
                except ValueError:
                    pass

        # 1AA. Vérification déterministe de toutes les lois spéciales québécoises et canadiennes via SQLite ccq_cpc.db
        for stat_code, stat_name, stat_cite, stat_nums in [
            ("LAA", "Loi sur l'assurance automobile", "L.a.a.", laa_art_nums),
            ("LJA", "Loi sur la justice administrative", "L.J.A.", [str(n) for n in lja_explicit]),
            ("LATMP", "Loi sur les accidents du travail et les maladies professionnelles", "L.A.T.M.P.", latmp_art_nums),
            ("LPC", "Loi sur la protection du consommateur", "L.p.c.", [str(n) for n in lpc_explicit]),
            ("LNT", "Loi sur les normes du travail", "L.n.t.", [str(n) for n in lnt_explicit]),
            ("LAF", "Loi sur l'administration fiscale", "L.A.F.", [str(n) for n in laf_explicit]),
            ("LTVQ", "Loi sur la taxe de vente du Québec", "L.T.V.Q.", [str(n) for n in ltvq_explicit]),
            ("LI", "Loi sur les impôts", "L.I.", [str(n) for n in li_explicit]),
            ("LSAQ", "Loi sur les sociétés par actions", "L.S.A.Q.", [str(n) for n in lsaq_explicit]),
            ("CHARTE", "Charte des droits et libertés de la personne", "Charte", [str(n) for n in charte_explicit]),
            ("LOI25", "Loi sur la protection des renseignements personnels dans le secteur privé", "Loi 25", [str(n) for n in loi25_explicit]),
            ("LTAL", "Loi sur le Tribunal administratif du logement", "L.T.A.L.", [str(n) for n in ltal_explicit]),
            ("CSR", "Code de la sécurité routière", "C.s.r.", [str(n) for n in csr_explicit]),
            ("CCR", "Code criminel", "C.cr.", [str(n) for n in ccr_explicit]),
        ]:
            for art_num_str in stat_nums[:5]:
                local_stat = self.get_code_article_local(stat_code, str(art_num_str))
                if local_stat:
                    is_hallucination = False
                    url = local_stat["url"]
                    clean_snippet = local_stat["texte"].strip()
                    if len(clean_snippet) > 260:
                        clean_snippet = clean_snippet[:260] + "..."
                    found_references.append({
                        "law_name": f"{stat_name} - Article {art_num_str}",
                        "citation": f"art. {art_num_str} {stat_cite}",
                        "url": url,
                        "summary": f"{clean_snippet}\nLien source pour validation : {url}"
                    })

        # 1A. Vérification déterministe C.c.Q. (SQLite embarqué ccq_cpc.db en < 1ms, puis fallback MCP SSE)
        if is_ccq and ccq_art_nums:
            for art_num in ccq_art_nums[:5]:
                try:
                    local_art = self.get_code_article_local("CCQ", str(art_num))
                    articles_text = local_art["texte"] if local_art else self._call_ccq_mcp_tool("get_ccq_articles", {"start_article": art_num})
                    if articles_text and "Aucun article trouvé" not in articles_text:
                        if self._verify_with_llm(agent_argument, f"Article {art_num} C.c.Q. : {articles_text}"):
                            is_hallucination = False
                            url = local_art["url"] if local_art else f"https://www.canlii.org/fr/qc/legis/lois/rlrq-c-ccq-1991/derniere/rlrq-c-ccq-1991.html#art{art_num}"
                            clean_snippet = articles_text.strip()
                            if len(clean_snippet) > 260:
                                clean_snippet = clean_snippet[:260] + "..."
                            found_references.append({
                                "law_name": f"Code civil du Québec - Article {art_num}",
                                "citation": f"art. {art_num} C.c.Q.",
                                "url": url,
                                "summary": f"{clean_snippet}\nLien source pour validation : {url}"
                            })
                except Exception as e:
                    logger.error(f"Erreur lors de la vérification CCQ de l'article {art_num}: {e}")

        # 1B. Vérification déterministe C.p.c. (Code de procédure civile via SQLite embarqué ccq_cpc.db)
        if cpc_art_nums:
            for art_num_str in cpc_art_nums[:4]:
                try:
                    local_cpc = self.get_code_article_local("CPC", str(art_num_str))
                    if local_cpc and self._verify_with_llm(agent_argument, f"Article {art_num_str} C.p.c. : {local_cpc['texte']}"):
                        is_hallucination = False
                        url = local_cpc["url"]
                        clean_snippet = local_cpc["texte"].strip()
                        if len(clean_snippet) > 260:
                            clean_snippet = clean_snippet[:260] + "..."
                        found_references.append({
                            "law_name": f"Code de procédure civile - Article {art_num_str}",
                            "citation": f"art. {art_num_str} C.p.c.",
                            "url": url,
                            "summary": f"{clean_snippet}\nLien source pour validation : {url}"
                        })
                except Exception as e:
                    logger.error(f"Erreur lors de la vérification CPC de l'article {art_num_str}: {e}")

        # 2. Vérification par rapport au contexte (texte de la décision ou pièces téléversées)
        if context and (is_hallucination or not found_references):
            try:
                if self._verify_with_llm(agent_argument, context):
                    is_hallucination = False
                    # Si le MCP CCQ était hors-ligne mais que des articles CCQ sont cités et validés par le dossier, créer les références précises
                    if is_ccq and ccq_art_nums and not found_references:
                        for art_num in ccq_art_nums[:4]:
                            url = f"https://www.canlii.org/fr/qc/legis/lois/rlrq-c-ccq-1991/derniere/rlrq-c-ccq-1991.html#art{art_num}"
                            found_references.append({
                                "law_name": f"Code civil du Québec - Article {art_num}",
                                "citation": f"art. {art_num} C.c.Q.",
                                "url": url,
                                "summary": f"Disposition du Code civil du Québec validée par les pièces du dossier.\nLien source pour validation : {url}"
                            })
                    elif not found_references:
                        citation_match = re.search(r'(?:R\.\s+c\.\s+\w+,\s+\d{4}\s+QCCQ\s+\d+|article\s+\d+(?:\.\d+)?(?:(?:\(\d+\))?a\))?|art\.\s+\d+(?:\.\d+)?(?:(?:\(\d+\))?a\))?)', agent_argument, re.IGNORECASE)
                        citation_str = citation_match.group(0) if citation_match else "Pièces du dossier"
                        found_references.append({
                            "law_name": "Pièces et preuve versées au dossier",
                            "citation": citation_str,
                            "url": "https://www.canlii.org",
                            "summary": "Cette référence est directement validée par les pièces et faits admis au dossier."
                        })
            except Exception as context_check_err:
                logger.error(f"Erreur lors de la vérification de l'argument par rapport au contexte: {context_check_err}")

        # 3. Recherche par mots-clés CCQ si aucun numéro d'article explicite n'a été trouvé
        if is_hallucination and is_ccq and not ccq_art_nums:
            keywords = [w for w in re.findall(r'[a-zA-ZÀ-ÿ]+', agent_argument) if len(w) > 4]
            if keywords:
                search_kw = keywords[0]
                articles_text = self._call_ccq_mcp_tool("search_ccq_keywords", {"keyword": search_kw})
                if articles_text and "Aucun article trouvé" not in articles_text:
                    matches = re.findall(r'Article\s+(\d+)', articles_text)
                    for num in matches[:2]:
                        if not is_hallucination:
                            break
                        art_num = int(num)
                        single_art_text = self._call_ccq_mcp_tool("get_ccq_articles", {"start_article": art_num})
                        if single_art_text and self._verify_with_llm(agent_argument, single_art_text):
                            is_hallucination = False
                            url = f"https://www.canlii.org/fr/qc/legis/lois/rlrq-c-ccq-1991/derniere/rlrq-c-ccq-1991.html#art{art_num}"
                            found_references.append({
                                "law_name": f"Code civil du Québec - Article {art_num}",
                                "citation": f"art. {art_num} C.c.Q.",
                                "url": url,
                                "summary": f"Article {art_num} validé via le Serveur MCP C.c.Q.\nLien source pour validation : {url}"
                            })
   
        # 4. Vérification A2AJ (Jurisprudence et lois canadiennes)
        if is_hallucination:
            query_terms = self._extract_query_terms(agent_argument)
            if query_terms:
                try:
                    a2aj_results = self._query_a2aj_search(query_terms)
                    if a2aj_results:
                        for r in a2aj_results[:2]:
                            if not is_hallucination:
                                break
                            citation = r.get("citation_fr") or r.get("citation_en") or "Non disponible"
                            url = r.get("url_fr") or r.get("url_en") or "https://a2aj.ca"
                            name = r.get("name_fr") or r.get("name_en") or "Arrêt canadien"
                            snippet = r.get("snippet", "")
                            
                            # Validation par LLM
                            if self._verify_with_llm(agent_argument, f"Source: {name} ({citation})\nContenu: {snippet}"):
                                is_hallucination = False
                                found_references.append({
                                    "law_name": name,
                                    "citation": citation,
                                    "url": url,
                                    "summary": f"{snippet}\nLien source pour validation : {url}"
                                })
                except Exception as e:
                    logger.error(f"Erreur lors de la requête de recherche A2AJ : {e}")
   
        # 3. Fallback SQLite local si aucun résultat n'a été trouvé via les API
        if is_hallucination:
            local_check = self._verify_argument_local(agent_argument)
            if not local_check["is_hallucination"]:
                for r in local_check["found_references"]:
                    if not is_hallucination:
                        break
                    # Validation par LLM
                    if self._verify_with_llm(agent_argument, f"Source: {r['law_name']} ({r['citation']})\nContenu: {r['summary']}"):
                        is_hallucination = False
                        found_references.append(r)
 
        if is_hallucination:
            if role == "prosecutor":
                objection_msg = "OBJECTION DE LA DÉFENSE : La jurisprudence ou loi citée est inexistante ou inapplicable au dossier. Veuillez vous baser sur des textes réels."
            else:
                if litigation_type == "civil":
                    objection_msg = "OBJECTION DU DEMANDEUR : La jurisprudence ou loi citée est inexistante ou inapplicable au dossier. Veuillez vous baser sur des textes réels."
                else:
                    objection_msg = "OBJECTION DU PROCUREUR (DPCP) : La jurisprudence ou loi citée est inexistante ou inapplicable au dossier. Veuillez vous baser sur des textes réels."
                
            return {
                "is_hallucination": True,
                "confidence": 0.9,
                "found_references": [],
                "objection_message": objection_msg
            }
            
        return {
            "is_hallucination": False,
            "confidence": 0.95,
            "found_references": found_references,
            "objection_message": ""
        }

    def _verify_argument_local(self, agent_argument: str) -> dict:
        """Méthode de vérification interne sur la BDD SQLite locale."""
        if not os.path.exists(self.db_path):
            return {
                "is_hallucination": True,
                "found_references": []
            }
            
        query_terms = self._extract_query_terms(agent_argument)
        keywords = query_terms.split()
        if not keywords:
            return {
                "is_hallucination": True,
                "found_references": []
            }
            
        conn = self.get_connection()
        cursor = conn.cursor()
        matched_cases = []
        is_hallucination = True
        
        def process_local_results(rows):
            processed = []
            for r in rows:
                law_name = r[0]
                citation = r[1]
                summary = r[2]
                url = "https://www.canlii.org"
                
                # Check if CCQ
                if "c.c.q." in law_name.lower() or "c.c.q." in citation.lower() or "code civil" in law_name.lower():
                    art_match = re.search(r'(?:article|art\.?)\s*(\d+)', f"{law_name} {citation}", re.IGNORECASE)
                    if art_match:
                        art_num = art_match.group(1)
                        url = f"https://www.canlii.org/fr/qc/legis/lois/rlrq-c-ccq-1991/derniere/rlrq-c-ccq-1991.html#art{art_num}"
                
                processed.append({
                    "law_name": law_name,
                    "citation": citation,
                    "url": url,
                    "summary": f"{summary}\nLien source pour validation : {url}"
                })
            return processed

        try:
            fts_query = " OR ".join([f'"{k}"' for k in keywords[:5]])
            cursor.execute('''
                SELECT law_name, citation, law_summary 
                FROM cases_fts 
                WHERE cases_fts MATCH ? 
                LIMIT 3
            ''', (fts_query,))
            
            results = cursor.fetchall()
            if results:
                is_hallucination = False
                matched_cases = process_local_results(results)
                
        except Exception:
            like_query = f"%{keywords[0]}%"
            cursor.execute('''
                SELECT law_name, citation, law_summary 
                FROM cases 
                WHERE law_summary LIKE ? OR law_name LIKE ?
                LIMIT 3
            ''', (like_query, like_query))
            
            results = cursor.fetchall()
            if results:
                is_hallucination = False
                matched_cases = process_local_results(results)
        finally:
            conn.close()
            
        return {
            "is_hallucination": is_hallucination,
            "found_references": matched_cases
        }

    def _call_ccq_mcp_tool(self, tool_name: str, arguments: dict) -> Optional[str]:
        """Appelle le serveur MCP CCQ via le transport SSE."""
        import urllib.request
        import urllib.parse
        import json
        import threading
        import queue
        import time
        
        # Check circuit breaker
        if hasattr(self, "_mcp_offline_until") and time.time() < self._mcp_offline_until:
            logger.warning("CCQ MCP circuit breaker is active. Skipping call.")
            return None
        
        sse_url = os.environ.get('MCP_CCQ_SSE_URL', 'https://lexior-ccq-mcp.onrender.com/sse')
        req = urllib.request.Request(sse_url, headers={'User-Agent': 'Mozilla/5.0'})
        
        try:
            # Timeout adapté au cold-start Render (8s)
            response = urllib.request.urlopen(req, timeout=8)
            post_url = None
            response_queue = queue.Queue()
            
            def read_stream():
                nonlocal post_url
                current_event = None
                try:
                    while True:
                        line = response.readline().decode('utf-8')
                        if not line:
                            break
                        line = line.strip()
                        if not line:
                            continue
                        if line.startswith('event:'):
                            current_event = line[6:].strip()
                        elif line.startswith('data:'):
                            data_content = line[5:].strip()
                            if current_event == 'endpoint':
                                post_url = urllib.parse.urljoin(sse_url, data_content)
                            elif current_event == 'message':
                                msg = json.loads(data_content)
                                response_queue.put(msg)
                except Exception:
                    pass
                    
            t = threading.Thread(target=read_stream, daemon=True)
            t.start()
            
            for _ in range(50):
                if post_url:
                    break
                time.sleep(0.1)
                
            if not post_url:
                logger.warning("Failed to obtain post_url from CCQ MCP SSE stream. Triggering circuit breaker.")
                if hasattr(self, "_mcp_offline_until"):
                    self._mcp_offline_until = time.time() + 45
                return None
                
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                },
                "id": 1
            }
            
            post_req = urllib.request.Request(
                post_url,
                data=json.dumps(payload).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'Mozilla/5.0'
                },
                method='POST'
            )
            
            urllib.request.urlopen(post_req, timeout=6)
            
            for _ in range(80):
                try:
                    msg = response_queue.get(timeout=0.1)
                    if msg.get("id") == 1:
                        content_list = msg.get("result", {}).get("content", [])
                        if content_list and content_list[0].get("type") == "text":
                            return content_list[0].get("text", "")
                except queue.Empty:
                    continue
            return None
        except Exception as e:
            logger.error(f"Error querying CCQ MCP in grounding: {e}. Activating circuit breaker for 45 seconds.")
            if hasattr(self, "_mcp_offline_until"):
                self._mcp_offline_until = time.time() + 45
            return None

    def _query_a2aj_search(self, query: str) -> List[dict]:
        """Effectue une recherche jurisprudentielle sur l'API A2AJ."""
        import urllib.request
        import urllib.parse
        import json
        import time
        
        # Check circuit breaker
        if hasattr(self, "_a2aj_offline_until") and time.time() < self._a2aj_offline_until:
            logger.warning("A2AJ Search circuit breaker is active. Skipping search.")
            return []
            
        params = {
            "query": query,
            "size": 3,
            "search_language": "fr",
            "doc_type": "cases"
        }
        url = f"https://api.a2aj.ca/search?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        try:
            # Reduced timeout from 10 to 3
            res = urllib.request.urlopen(req, timeout=3)
            data = json.loads(res.read().decode('utf-8'))
            return data.get("results", [])
        except Exception as e:
            logger.error(f"Error querying A2AJ search in grounding: {e}. Activating circuit breaker for 5 minutes.")
            if hasattr(self, "_a2aj_offline_until"):
                self._a2aj_offline_until = time.time() + 300
            return []

    def _extract_query_terms(self, text: str) -> str:
        stop_words = {"selon", "l'arrêt", "la", "le", "les", "des", "dans", "pour", "par", "qui", "que", "une", "un", "code", "civil", "québec"}
        words = re.findall(r'[a-zA-ZÀ-ÿ\d]+(?:\.\d+)?', text)
        keywords = []
        for w in words:
            wl = w.lower()
            if len(wl) > 3 and wl not in stop_words:
                keywords.append(w)
        return " ".join(keywords[:5])
