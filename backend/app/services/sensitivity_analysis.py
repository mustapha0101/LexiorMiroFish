import os
import json
import logging
import random
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from openai import OpenAI
from app.config import Config
from app.services.local_graph_database import LocalGraphDatabase
from app.models.project import ProjectManager

logger = logging.getLogger('mirofish.sensitivity_analysis')

class SensitivityAnalysisEngine:
    """
    Moteur de Sensibilité Inversée / Radar d'Anticipation Tactique.
    Calcule la centralité des nœuds et génère les failles / lignes de force.
    """

    @classmethod
    def analyze_case(cls, project_id: str, client_side: str, simulation_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Exécute l'analyse complète : centralité Kuzu DB + Stress-test LLM.
        """
        project = ProjectManager.get_project(project_id)
        if not project:
            raise ValueError("Projet non trouvé")

        # Get litigation_type (civil or criminal)
        litigation_type = "civil"
        if simulation_id:
            try:
                from app.services.simulation_runner import SimulationManager
                manager = SimulationManager()
                sim_dir = manager._get_simulation_dir(simulation_id)
                config_file = os.path.join(sim_dir, "simulation_config.json")
                if os.path.exists(config_file):
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                        litigation_type = config_data.get("litigation_type", "civil")
            except Exception as e:
                logger.warning(f"Could not load simulation config for litigation_type in analyze_case: {e}")
        else:
            txt = (project.simulation_requirement or "").lower() + " " + project.name.lower()
            if any(k in txt for k in ["criminel", "criminal", "meurtre", "vol", "drogue", "arrestation", "police", "accusation", "charte", "prévenu", "accusé"]):
                litigation_type = "criminal"

        # 1. Récupération du graphe Kuzu
        nodes = []
        edges = []
        if project.graph_id:
            try:
                with LocalGraphDatabase(project.graph_id, read_only=True) as db:
                    nodes = db.fetch_all_nodes()
                    edges = db.fetch_all_edges()
            except Exception as e:
                logger.error(f"Error fetching graph nodes/edges: {e}")

        # Si pas de graphe, on crée des nœuds génériques à partir de la description du projet (sans noms de dossiers tiers)
        if not nodes:
            if litigation_type == "civil":
                nodes = [
                    {"uuid": "n1", "name": "Exécution contractuelle et dol", "summary": "Analyse de la validité du consentement et de l'exécution des obligations (art. 1401, 1458, 1699 C.c.Q.)", "labels": ["Faits"]},
                    {"uuid": "n2", "name": "Causalité et Quantum des dommages", "summary": "Évaluation du préjudice direct et immédiat (art. 1607 et 1611 C.c.Q.)", "labels": ["Concept"]},
                    {"uuid": "n3", "name": "Frais et Abus de procédure", "summary": "Critères stricts de l'abus de procédure et des honoraires extrajudiciaires (art. 51 C.p.c.)", "labels": ["Procédure"]},
                    {"uuid": "n4", "name": "Responsabilité solidaire / in solidum", "summary": "Effet relatif des contrats (art. 1440 C.c.Q.) c. faute extracontractuelle (art. 1457 et 1526 C.c.Q.)", "labels": ["Concept"]}
                ]
                edges = [
                    {"source_node_uuid": "n1", "target_node_uuid": "n2"},
                    {"source_node_uuid": "n2", "target_node_uuid": "n3"},
                    {"source_node_uuid": "n3", "target_node_uuid": "n4"}
                ]
            else:
                nodes = [
                    {"uuid": "n1", "name": "Admissibilité de la preuve matérielle", "summary": "Examen de la légalité de la fouille et de la saisie (art. 8 et 24(2) Charte)", "labels": ["Evidence"]},
                    {"uuid": "n2", "name": "Crédibilité et fiabilité des témoignages", "summary": "Appréciation de la preuve testimoniale selon la grille W.(D.)", "labels": ["Concept"]},
                    {"uuid": "n3", "name": "Éléments essentiels de l'infraction", "summary": "Fardeau de la preuve hors de tout doute raisonnable (actus reus et mens rea)", "labels": ["Witness"]}
                ]
                edges = [
                    {"source_node_uuid": "n1", "target_node_uuid": "n2"},
                    {"source_node_uuid": "n2", "target_node_uuid": "n3"}
                ]

        # 2. Calcul de centralité (degré de connexion)
        node_degrees = {n["uuid"]: 0 for n in nodes}
        for e in edges:
            src = e.get("source_node_uuid")
            tgt = e.get("target_node_uuid")
            if src in node_degrees:
                node_degrees[src] += 1
            if tgt in node_degrees:
                node_degrees[tgt] += 1

        # Trier les nœuds par degré de centralité décroissant
        sorted_nodes = sorted(nodes, key=lambda n: node_degrees.get(n["uuid"], 0), reverse=True)
        top_nodes = sorted_nodes[:5]  # Prendre les 5 nœuds les plus centraux

        # 3. Préparer l'appel LLM pour générer la matrice tactique
        context_requirement = project.simulation_requirement or ""
        extracted_text = ""
        try:
            extracted_text = ProjectManager.get_extracted_text(project_id) or ""
        except Exception:
            pass

        # Pré-injection statutaire v2 (C.c.Q. / C.p.c.) depuis ccq_cpc.db
        statutory_block = ""
        try:
            from app.services.jurisprudence_grounding import JurisprudenceGroundingService
            grounder = JurisprudenceGroundingService()
            statutory_block = grounder.build_statutory_grounding_block(
                context_requirement + "\n" + extracted_text[:8000],
                litigation_type=litigation_type
            )
        except Exception as stat_err:
            logger.warning(f"Could not build statutory grounding block in Radar: {stat_err}")

        # Construire le dossier d'analyse sémantique pour le LLM
        nodes_summary = ""
        for n in top_nodes:
            lbl = ", ".join(n.get("labels", []))
            nodes_summary += f"- Nœud : '{n.get('name')}' (Centralité: {node_degrees.get(n['uuid'], 0)}, Type: {lbl}) | Résumé : {n.get('summary')}\n"

        api_key = Config.LLM_API_KEY or "local-no-key"
        base_url = Config.LLM_BASE_URL
        model_name = getattr(Config, 'LLM_MODEL_NAME', 'gpt-4o-mini')

        if base_url:
            client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            client = OpenAI(api_key=api_key)

        # Dynamic prompt instructing the LLM to classify and adapt to any legal simulation
        role_instruction = (
            "Vous êtes un analyste tactique juridique et actuariel de haut niveau du Barreau du Québec.\n"
            f"Votre rôle est d'analyser le dossier pour le camp représenté : {'DÉFENSE / DÉFENDEUR (ou ACCUSÉ)' if client_side == 'defense' else 'DEMANDEUR / POURSUITE / REQUÉRANT'}.\n"
            "Vous devez croiser les nœuds sémantiques centraux du graphe du dossier avec l'intégralité des postes financiers réclamés (demande principale, dommages moraux, honoraires extrajudiciaires art. 51 C.p.c., demande reconventionnelle, solidarité art. 1457/1526 C.c.Q.) pour identifier les « Planchers de Condamnation » (réductions du quantum des dommages) et les moyens de droit décisifs.\n"
            "Employez STRICTEMENT la terminologie juridique québécoise et canadienne authentique."
        )

        system_prompt = f"""{role_instruction}
Voici le contexte de l'affaire :
{context_requirement[:2000]}

Extrait complet du dossier, des pièces et des réclamations chiffrées :
{extracted_text[:12000]}
{statutory_block}

Voici les nœuds sémantiques centraux identifiés par centralité de degré dans le graphe Kuzu :
{nodes_summary}

Votre tâche est de générer une Matrice d'Anticipation Stratégique chirurgicale (4 à 5 vecteurs tactiques) couvrant à la fois les nœuds centraux ci-dessus ET les failles financières/procédurales critiques du dossier (ex: contestation des honoraires extrajudiciaires sous l'art. 51 C.p.c., nullité ab initio et restitution sous l'art. 1699 C.c.Q., solidarité in solidum sous l'art. 1457/1526 C.c.Q., rejet de la demande reconventionnelle).

Renvoyez STRICTEMENT un objet JSON valide de la forme {{"opportunities": [...]}} contenant un tableau d'objets avec exactement les clés suivantes :
- "node_name" : le nom du nœud ou poste financier ciblé (ex: le nom d'une partie, d'une pièce ou "Honoraires art. 51 C.p.c.")
- "vector_name" : le titre professionnel et percutant de la tactique (ex: "Amputation des Honoraires Extrajudiciaires (Art. 51 C.p.c.)")
- "impact" : l'impact estimé sous forme de chaîne textuelle claire (incluant l'impact en % ou en $ sur le quantum si applicable). Exemples :
  * Si Civil / Commercial et Défense : "+35% de réduction du quantum (-25 811 $ sous art. 51 C.p.c.)" ou "+30% de chances de rejet de la solidarité"
  * Si Civil / Commercial et Demandeur : "+45% de maintien de la restitution intégrale (41 117 $)" ou "+40% de rejet de la demande reconventionnelle"
  * Si Criminel / Pénal et Défense : "+45% de chances d'acquittement" ou "+35% d'exclusion de preuve"
  * Si Criminel / Pénal et Poursuite : "+40% de chances de condamnation" ou "+30% d'admissibilité de preuve"
- "impact_value" : un entier représentant le pourcentage d'impact (ex: 45)
- "match_plan" : la feuille de route actionnable en français rédigée sur un ton premium s'adressant à l'avocat ("Maître, ...") citant les articles exacts du C.c.Q. ou du C.p.c. et les pièces du dossier.
- "request_type" : le type de requête ou d'acte de procédure associé (ex: "contestation", "production", "divulgation", "expertise", "exclusion", "amendement")
"""

        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": system_prompt}],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            raw_content = (response.choices[0].message.content or "").strip()
            if raw_content.startswith("```json"):
                raw_content = raw_content[7:]
            elif raw_content.startswith("```"):
                raw_content = raw_content[3:]
            if raw_content.endswith("```"):
                raw_content = raw_content[:-3]
            data = json.loads(raw_content.strip())
            if isinstance(data, dict):
                for val in data.values():
                    if isinstance(val, list):
                        return val
                if "node_name" in data:
                    return [data]
            return data if isinstance(data, list) else []
        except Exception as err:
            logger.error(f"Error calling LLM for sensitivity analysis: {err}")
            fallback_opps = []
            for idx, n in enumerate(top_nodes[:4]):
                n_name = n.get("name", f"Élément {idx + 1}")
                fallback_opps.append({
                    "node_name": n_name,
                    "vector_name": "Analyse de Causalité et Force Probante (Art. 1607 & 2803 C.c.Q.)" if litigation_type == "civil" else "Vérification de la Preuve (Art. 24(2) Charte)",
                    "impact": "+30% de réduction de responsabilité" if client_side == "defense" else "+35% de probabilité de gain",
                    "impact_value": 30 if client_side == "defense" else 35,
                    "match_plan": f"Maître, concentrez votre argumentation sur '{n_name}' ({n.get('summary', 'élément central du dossier')}) en exigeant une preuve documentaire stricte conformément à l'article 2803 C.c.Q. et au principe de proportionnalité de l'article 18 C.p.c.",
                    "request_type": "contestation"
                })
            return fallback_opps

    @classmethod
    def generate_draft(cls, project_id: str, client_side: str, node_name: str, vector_name: str, request_type: str, simulation_id: Optional[str] = None) -> str:
        """
        Génère un projet de requête / avis juridique haut de gamme basé sur l'opportunité choisie.
        """
        project = ProjectManager.get_project(project_id)
        if not project:
            raise ValueError("Projet non trouvé")

        # Get litigation_type (civil or criminal)
        litigation_type = "civil"
        if simulation_id:
            try:
                from app.services.simulation_runner import SimulationManager
                manager = SimulationManager()
                sim_dir = manager._get_simulation_dir(simulation_id)
                config_file = os.path.join(sim_dir, "simulation_config.json")
                if os.path.exists(config_file):
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                        litigation_type = config_data.get("litigation_type", "civil")
            except Exception as e:
                logger.warning(f"Could not load simulation config for litigation_type in generate_draft: {e}")
        else:
            txt = (project.simulation_requirement or "").lower() + " " + project.name.lower()
            if any(k in txt for k in ["criminel", "criminal", "meurtre", "vol", "drogue", "arrestation", "police", "accusation", "charte", "prévenu", "accusé"]):
                litigation_type = "criminal"

        context_requirement = project.simulation_requirement or ""
        extracted_text = ""
        try:
            extracted_text = ProjectManager.get_extracted_text(project_id) or ""
        except Exception:
            pass

        api_key = Config.LLM_API_KEY or "local-no-key"
        base_url = Config.LLM_BASE_URL
        model_name = getattr(Config, 'LLM_MODEL_NAME', 'gpt-4o-mini')

        if base_url:
            client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            client = OpenAI(api_key=api_key)

        statutory_block = ""
        try:
            from app.services.jurisprudence_grounding import JurisprudenceGroundingService
            grounder = JurisprudenceGroundingService()
            statutory_block = grounder.build_statutory_grounding_block(
                context_requirement + "\n" + extracted_text[:8000],
                litigation_type=litigation_type
            )
        except Exception:
            pass

        # Build dynamic prompt context
        system_prompt = f"""Vous êtes un avocat plaideur chevronné membre du Barreau du Québec.
Votre mission est de rédiger un projet d'acte de procédure judiciaire formel (Requête, Avis, Demande, Contestation écrite, Mémoire) en français juridique québécois irréprochable.
Le document doit correspondre précisément à la demande suivante :
- Camp représenté : {"DÉFENSE / DÉFENDEUR (ou ACCUSÉ)" if client_side == "defense" else "DEMANDEUR / POURSUITE / REQUÉRANT"}
- Élément ou nœud ciblé : {node_name}
- Ligne d'attaque ou tactique choisie : {vector_name}
- Type de document demandé : {request_type}

Déterminez la juridiction appropriée (ex: Cour du Québec — Chambre civile, Cour supérieure du Québec) et le district judiciaire en vous basant sur les faits réels du dossier ci-dessous.

Contexte du dossier :
{context_requirement[:2000]}

Extrait factuel officiel (dossier d'affaire, pièces et réclamations) :
{extracted_text[:10000]}
{statutory_block}

Instructions impératives de rédaction :
1. FORMALISME OFFICIEL : Respectez scrupuleusement la structure officielle d'une procédure devant les tribunaux du Québec (district judiciaire, parties avec leurs noms réels et numéro de dossier si mentionné dans le dossier d'origine ci-dessus).
2. PAS DE LISTE DE CHOIX : Ne proposez jamais de menu d'options ou d'hypothèses factuelles contradictoires. Choisissez UNE SEULE hypothèse factuelle logique, précise et réaliste découlant du dossier et rédigez-la de manière définitive comme si le fait était avéré.
3. ADHÉRENCE AUX FAITS RÉELS : Basez-vous exclusivement sur les faits réels décrits dans le dossier d'affaire et les pièces ci-dessus.
4. ZÉRO PLACEHOLDER : N'utilisez jamais de crochets '[À insérer...]' ou '[Votre Nom]'.
5. RIGUEUR ET PRÉCISION JURIDIQUE :
   - Citez avec exactitude les articles pertinents du Code civil du Québec (C.c.Q.) et du Code de procédure civile (C.p.c.) pré-injectés ci-dessus.
6. Renvoyez uniquement le document rédigé en Markdown sans introduction, conclusion, ni texte explicatif en dehors du document lui-même.
"""

        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": system_prompt}],
                temperature=0.4
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as err:
            logger.error(f"Error generating legal draft: {err}")
            return (
                f"# ACTE DE PROCÉDURE ET MOYENS SUR « {node_name.upper()} »\n\n"
                f"**CANADA — PROVINCE DE QUÉBEC**\n"
                f"**COUR DU QUÉBEC**\n\n"
                f"**Dossier :** {project.name}\n\n"
                f"---\n\n"
                f"### EXPOSÉ DES MOYENS — {vector_name}\n\n"
                f"À L'HONORABLE TRIBUNAL, LA PARTIE EXPOSE CE QUI SUIT :\n\n"
                f"1. Eu égard aux pièces versées au dossier concernant **{node_name}**, il y a lieu d'appliquer rigoureusement les règles de preuve et de causalité prévues aux articles 1457, 1607, 1611 et 2803 du *Code civil du Québec* ainsi qu'aux articles 18 et 51 du *Code de procédure civile*;\n"
                f"2. La tactique **{vector_name}** commande d'écarter toute réclamation non appuyée par une preuve directe, prépondérante et contemporaine des faits;\n\n"
                f"**POUR CES MOTIFS, PLAISE AU TRIBUNAL :**\n\n"
                f"- **ACCUEILLIR** les présents moyens relatifs à *{node_name}*;\n"
                f"- **STATUER** conformément à la preuve documentaire versée au dossier, avec frais de justice.\n"
            )
