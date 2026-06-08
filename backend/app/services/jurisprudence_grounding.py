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
        """Initialise la base SQLite locale pour la recherche rapide."""
        self.db_path = os.path.join(os.path.dirname(__file__), '../../uploads/jurisprudence.db')
        self.json_path = os.path.join(os.path.dirname(__file__), '../../uploads/jurisprudence.json')
        
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
        en interrogeant d'abord le contexte de la décision téléversée,
        puis en interrogeant l'API A2AJ et le MCP du Code Civil du Québec.
        """
        found_references = []
        is_hallucination = True

        # 0. Vérification par rapport au contexte (notamment le texte de la décision téléversée)
        if context:
            try:
                # Si le contexte (le texte du jugement réel) valide l'affirmation, ce n'est pas une hallucination
                if self._verify_with_llm(agent_argument, context):
                    is_hallucination = False
                    
                    # Tenter d'extraire une citation ou l'article mentionné dans l'argument
                    citation_match = re.search(r'(?:R\.\s+c\.\s+\w+,\s+\d{4}\s+QCCQ\s+\d+|article\s+\d+(?:\.\d+)?(?:(?:\(\d+\))?a\))?|art\.\s+\d+(?:\.\d+)?(?:(?:\(\d+\))?a\))?)', agent_argument, re.IGNORECASE)
                    citation_str = citation_match.group(0) if citation_match else "Décision téléversée"
                    
                    found_references.append({
                        "law_name": "Pièces et texte de la décision téléversée",
                        "citation": citation_str,
                        "url": "https://www.canlii.org",
                        "summary": "Cette référence/citation est directement validée par les pièces et le texte du jugement téléversé dans le dossier."
                    })
            except Exception as context_check_err:
                logger.error(f"Erreur lors de la vérification de l'argument par rapport au contexte: {context_check_err}")
        
        # 1. Vérification CCQ (Code Civil du Québec)
        is_ccq = any(term in agent_argument.lower() for term in ["ccq", "code civil", "québec"])
        
        art_match = re.search(r'(?:article|art\.?)\s*(\d+(?:\.\d+)?)', agent_argument, re.IGNORECASE)
        art_str = art_match.group(1) if art_match else ""
        
        # S'il y a un point décimal dans le numéro de l'article (ex: 718.1), ce n'est pas du CCQ mais probablement le Code criminel
        if is_ccq and '.' in art_str:
            is_ccq = False
            
        if is_hallucination and is_ccq:
            if art_match:
                try:
                    art_num = int(float(art_str))
                    articles_text = self._call_ccq_mcp_tool("get_ccq_articles", {"start_article": art_num})
                    if articles_text and "Aucun article trouvé" not in articles_text:
                        # Validation par LLM
                        if self._verify_with_llm(agent_argument, articles_text):
                            is_hallucination = False
                            found_references.append({
                                "law_name": f"Code civil du Québec - Article {art_num}",
                                "citation": f"art. {art_num} C.c.Q.",
                                "url": f"https://www.canlii.org/fr/qc/legis/lois/rlrq-c-ccq-1991/derniere/rlrq-c-ccq-1991.html#art{art_num}",
                                "summary": articles_text[:200] + "..." if len(articles_text) > 200 else articles_text
                            })
                except Exception as e:
                    logger.error(f"Erreur lors de la vérification CCQ de l'article {art_str}: {e}")
            else:
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
                            # Validation par LLM
                            single_art_text = self._call_ccq_mcp_tool("get_ccq_articles", {"start_article": art_num})
                            if single_art_text and self._verify_with_llm(agent_argument, single_art_text):
                                is_hallucination = False
                                found_references.append({
                                    "law_name": f"Code civil du Québec - Article {art_num}",
                                    "citation": f"art. {art_num} C.c.Q.",
                                    "url": f"https://www.canlii.org/fr/qc/legis/lois/rlrq-c-ccq-1991/derniere/rlrq-c-ccq-1991.html#art{art_num}",
                                    "summary": f"Article {art_num} trouvé par recherche du mot-clé '{search_kw}'"
                                })
   
        # 2. Vérification A2AJ (Jurisprudence et lois canadiennes)
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
                                    "summary": snippet
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
                    objection_msg = "OBJECTION DU MINISTÈRE PUBLIC : La jurisprudence ou loi citée est inexistante ou inapplicable au dossier. Veuillez vous baser sur des textes réels."
                
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
                matched_cases = [{"law_name": r[0], "citation": r[1], "url": "https://www.canlii.org", "summary": r[2]} for r in results]
                
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
                matched_cases = [{"law_name": r[0], "citation": r[1], "url": "https://www.canlii.org", "summary": r[2]} for r in results]
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
        
        sse_url = 'https://lexior-ccq-mcp.onrender.com/sse'
        req = urllib.request.Request(sse_url, headers={'User-Agent': 'Mozilla/5.0'})
        
        try:
            # Reduced timeout from 10 to 3
            response = urllib.request.urlopen(req, timeout=3)
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
                    self._mcp_offline_until = time.time() + 300
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
            
            # Reduced timeout from 5 to 3
            urllib.request.urlopen(post_req, timeout=3)
            
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
            logger.error(f"Error querying CCQ MCP in grounding: {e}. Activating circuit breaker for 5 minutes.")
            if hasattr(self, "_mcp_offline_until"):
                self._mcp_offline_until = time.time() + 300
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
