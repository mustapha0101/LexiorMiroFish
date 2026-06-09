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

        # Si pas de graphe, on crée des nœuds fictifs basiques à partir de la description du projet
        if not nodes:
            if litigation_type == "civil":
                nodes = [
                    {"uuid": "n1", "name": "Infiltration d'eau", "summary": "Infiltration d'eau causée par un pontage pourri", "labels": ["Faits"]},
                    {"uuid": "n2", "name": "Devoir d'information", "summary": "Manque au devoir de conseil professionnel de l'entrepreneur", "labels": ["Concept"]},
                    {"uuid": "n3", "name": "France Caron", "summary": "Propriétaire victime du préjudice", "labels": ["Partie"]}
                ]
                edges = [
                    {"source_node_uuid": "n1", "target_node_uuid": "n2"},
                    {"source_node_uuid": "n2", "target_node_uuid": "n3"}
                ]
            else:
                nodes = [
                    {"uuid": "n1", "name": "Sac en nylon", "summary": "Sac souple contenant l'arme", "labels": ["Evidence"]},
                    {"uuid": "n2", "name": "Faux nom", "summary": "Identité Durocher fournie à l'arrestation", "labels": ["Concept"]},
                    {"uuid": "n3", "name": "Sergent Michon", "summary": "Policier qui a saisi le sac", "labels": ["Witness"]}
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
        top_nodes = sorted_nodes[:4]  # Prendre les 4 nœuds les plus centraux

        # 3. Préparer l'appel LLM pour générer la matrice tactique
        context_requirement = project.simulation_requirement or ""
        extracted_text = ""
        try:
            extracted_text = ProjectManager.get_extracted_text(project_id) or ""
        except Exception:
            pass

        # Construire le dossier d'analyse sémantique pour le LLM
        nodes_summary = ""
        for n in top_nodes:
            lbl = ", ".join(n.get("labels", []))
            nodes_summary += f"- Nœud : '{n.get('name')}' (Type: {lbl}) | Résumé : {n.get('summary')}\n"

        api_key = Config.LLM_API_KEY or "local-no-key"
        base_url = Config.LLM_BASE_URL
        model_name = getattr(Config, 'LLM_MODEL_NAME', 'gpt-4o-mini')

        if base_url:
            client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            client = OpenAI(api_key=api_key)

        # Dynamic prompt instructing the LLM to classify and adapt to any legal simulation
        role_instruction = (
            "Vous êtes un analyste tactique juridique et stratégique de haut niveau.\n"
            f"Votre rôle est d'analyser le dossier pour le camp représenté : {'DÉFENSE / ACCUSÉ / DÉFENDEUR' if client_side == 'defense' else 'DEMANDEUR / POURSUITE / ACCUSATION / REQUÉRANT'}.\n"
            "Vous devez analyser les nœuds sémantiques clés du dossier de la simulation juridique pour en extraire des opportunités tactiques ou des failles critiques.\n"
            "Analysez attentivement le contexte pour identifier la nature du litige (ex: criminel, pénal, civil, commercial, travail, administratif) et employez STRICTEMENT le vocabulaire juridique approprié."
        )

        system_prompt = f"""{role_instruction}
Voici le contexte de l'affaire :
{context_requirement[:1000]}

Extrait du jugement, pièces ou dossier :
{extracted_text[:2000]}

Voici les nœuds sémantiques centraux identifiés par centralité de degré :
{nodes_summary}

Votre tâche est de générer une analyse chirurgicale pour chacun des nœuds sémantiques ci-dessus, adaptée au camp représenté.
Pour chaque nœud, concevez une opportunité stratégique/tactique ou un angle d'attaque.

Renvoyez STRICTEMENT un tableau JSON valide contenant des opportunités tactiques pour chacun des nœuds ci-dessus.
Le format de sortie attendu doit être un tableau d'objets JSON avec exactement les clés suivantes :
- "node_name" : le nom exact du nœud ciblé (ex: "Sac en nylon" ou "Infiltration d'eau")
- "vector_name" : le titre professionnel et percutant de la tactique (ex: "Neutralisation Sensorielle" ou "Mise en demeure préalable")
- "impact" : l'impact estimé sous forme de chaîne textuelle claire, en utilisant le vocabulaire précis adapté à la nature du litige. Exemples :
  * Si Criminel / Pénal et Défense : "+45% de chances d'acquittement" ou "+35% d'exclusion de preuve"
  * Si Criminel / Pénal et Poursuite : "+40% de chances de condamnation" ou "+30% d'admissibilité de preuve"
  * Si Civil / Commercial / Travail et Défense : "+40% de chances de rejet de la demande" ou "+35% de réduction de responsabilité"
  * Si Civil / Commercial / Travail et Demandeur : "+45% de chances de succès" ou "+30% de probabilité de gain"
  * Si Administratif / Réglementaire : "+40% de chances d'annulation de la décision" ou "+35% de maintien de la décision"
- "impact_value" : un entier représentant le pourcentage d'impact (ex: 45)
- "match_plan" : la feuille de route actionnable en français rédigée sur un ton premium s'adressant à l'avocat ("Maître, ...") proposant une action concrète et des arguments juridiques précis.
- "request_type" : le type de requête, d'acte de procédure ou de document juridique associé (ex: "divulgation", "expertise", "exclusion", "production", "contestation", "amendement")

Ne renvoyez rien d'autre que du JSON valide, sans balises ```json ou de texte d'accompagnement.
"""

        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": system_prompt}],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            raw_content = response.choices[0].message.content.strip()
            # Parser le JSON
            data = json.loads(raw_content)
            # Si le JSON contient un dictionnaire avec une clé (ex: "opportunities"), extraire la liste
            if isinstance(data, dict):
                for val in data.values():
                    if isinstance(val, list):
                        return val
                # Si c'est juste un dict plat avec des nœuds
                if "node_name" in data or "opportunities" in data:
                    return [data]
            return data if isinstance(data, list) else []
        except Exception as err:
            logger.error(f"Error calling LLM for sensitivity analysis: {err}")
            # Renvoyer des données de secours adaptées
            if litigation_type == "civil":
                if client_side == "defense":
                    return [
                        {
                            "node_name": "Infiltration d'eau",
                            "vector_name": "Réfutation du Devoir d'Information",
                            "impact": "+40% de chances de rejet de la demande",
                            "impact_value": 40,
                            "match_plan": "Maître, préparez la preuve testimoniale montrant que la demanderesse a été informée verbalement des risques de poser les nouveaux bardeaux sur un support pourri, transférant ainsi la responsabilité à son refus d'assumer les coûts de remplacement.",
                            "request_type": "production"
                        },
                        {
                            "node_name": "France Caron",
                            "vector_name": "Limitation des Dommages",
                            "impact": "+30% de réduction de responsabilité",
                            "impact_value": 30,
                            "match_plan": "Contestez le quantum réclamé pour les troubles et inconvénients (1000 $) en montrant l'absence de pièces justificatives objectives. Proposez le dépôt d'une offre à l'amiable restreinte.",
                            "request_type": "divulgation"
                        }
                    ]
                else:
                    return [
                        {
                            "node_name": "Infiltration d'eau",
                            "vector_name": "Consolidation de l'Obligation de Résultat",
                            "impact": "+45% de probabilité de gain",
                            "impact_value": 45,
                            "match_plan": "Maître, invoquez l'article 2100 C.c.Q. L'entrepreneur est tenu à une obligation de résultat quant à l'étanchéité. Déposez le rapport d'expertise technique de M. Laforest démontrant le pontage pourri.",
                            "request_type": "expertise"
                        },
                        {
                            "node_name": "France Caron",
                            "vector_name": "Démonstration du Manquement Professionnel",
                            "impact": "+35% de chances de succès",
                            "impact_value": 35,
                            "match_plan": "Démontrez que Toiture Allaire inc. n'a produit aucun écrit (avenant ou refus de travaux signé) prouvant qu'elle a conseillé le remplacement du contreplaqué, violant ainsi son devoir d'information.",
                            "request_type": "production"
                        }
                    ]
            else: # criminal
                if client_side == "defense":
                    return [
                        {
                            "node_name": "Sac en nylon",
                            "vector_name": "Neutralisation Sensorielle",
                            "impact": "+45% de chances d'acquittement",
                            "impact_value": 45,
                            "match_plan": "Maître, commandez une expertise technique du sac saisi. Si vous prouvez la présence d'une doublure rigide, la théorie de la perception par le toucher du juge s'effondre.",
                            "request_type": "expertise"
                        },
                        {
                            "node_name": "Sergent Michon",
                            "vector_name": "Bris de Procédure Factuel",
                            "impact": "+35% de chances d'acquittement",
                            "impact_value": 35,
                            "match_plan": "Le témoin clé de la découverte de l'arme (Michon) n'a pas témoigné. Exigez la production des notes de calepin brutes de tous les policiers présents.",
                            "request_type": "divulgation"
                        }
                    ]
                else:
                    return [
                        {
                            "node_name": "Sac en nylon",
                            "vector_name": "Sécurisation Sensorielle",
                            "impact": "+40% d'admissibilité de preuve",
                            "impact_value": 40,
                            "match_plan": "Maître, préparez une déposition détaillée de l'officier de saisie décrivant la souplesse extrême du nylon et la forme distincte de l'arme pour contrer toute contestation sur la détection tactile.",
                            "request_type": "production"
                        },
                        {
                            "node_name": "Faux nom",
                            "vector_name": "Consolidation du Comportement Post-Facto",
                            "impact": "+25% de chances de condamnation",
                            "impact_value": 25,
                            "match_plan": "Démontrez que la fourniture d'une fausse identité coïncide précisément avec la question sur l'arme, écartant ainsi la thèse de la simple anxiété liée au couvre-feu.",
                            "request_type": "admissibilite"
                        }
                    ]

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

        # Build dynamic prompt context
        system_prompt = f"""Vous êtes un avocat ou rédacteur juridique chevronné membre du Barreau du Québec (ou de la juridiction correspondante indiquée dans le dossier).
Votre mission est de rédiger un projet de document de procédure judiciaire formel (ex: Requête, Avis, Demande, Contestation écrite, Mémoire) en français de niveau professionnel et d'une rigueur absolue.
Le document doit correspondre précisément à la demande suivante :
- Camp représenté : {"DÉFENSE / ACCUSÉ / DÉFENDEUR" if client_side == "defense" else "DEMANDEUR / POURSUITE / ACCUSATION / REQUÉRANT"}
- Élément ou nœud ciblé : {node_name}
- Ligne d'attaque ou tactique choisie : {vector_name}
- Type de document demandé : {request_type}

Déterminez intelligemment la juridiction appropriée (ex: Cour du Québec, Cour supérieure du Québec, Cour d'appel, Tribunal administratif, division civile, criminelle ou des petites créances) et le district judiciaire en vous basant sur les faits réels du dossier d'affaire ci-dessous.

Contexte du dossier :
{context_requirement[:1200]}

Extrait factuel officiel (dossier d'affaire, pièces ou jugement) :
{extracted_text[:3000]}

Instructions impératives de rédaction :
1. FORMALISME OFFICIEL : Respectez scrupuleusement la structure officielle d'une procédure devant les tribunaux de la juridiction (district judiciaire, parties avec leurs noms réels et numéro de dossier si mentionné dans le dossier d'origine ci-dessus).
2. PAS DE LISTE DE CHOIX : Ne proposez jamais de menu d'options ou d'hypothèses factuelles contradictoires. Choisissez UNE SEULE hypothèse factuelle logique, précise et réaliste découlant du dossier et rédigez-la de manière définitive comme si le fait était avéré.
3. ADHÉRENCE AUX FAITS RÉELS : Basez-vous en priorité sur les faits réels décrits dans le dossier d'affaire, les pièces ou le jugement ci-dessus.
4. DONNÉES SECONDAIRES CRÉDIBLES : Pour les détails obligatoires absents du dossier (comme les adresses ou les noms d'avocats), n'utilisez pas de placeholders génériques (ex: '[Votre Nom]'). Utilisez des noms ou adresses québécoises réalistes et sobres en adéquation avec les districts mentionnés (ex: Mont-Laurier, District de Labelle).
5. RIGUEUR ET PRÉCISION JURIDIQUE : 
   - Le document doit citer avec exactitude les lois, codes et articles applicables au litige (ex : Code civil du Québec (C.c.q.), Code de procédure civile (C.p.c.), Code criminel (C.cr.), etc.).
   - Les arguments et critères légaux doivent être rigoureusement appliqués.
   - Le vocabulaire juridique employé doit être précis, exact et typique de la juridiction.
6. Renvoyez uniquement le document rédigé en Markdown sans introduction, conclusion, ni texte explicatif en dehors du document lui-même.
"""

        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": system_prompt}],
                temperature=0.5
            )
            return response.choices[0].message.content.strip()
        except Exception as err:
            logger.error(f"Error generating legal draft: {err}")
            if litigation_type == "civil":
                if client_side == "defense":
                    return (
                        f"# PROJET DE CONTESTATION ÉCRITE / EXPOSÉ DE DÉFENSE\n\n"
                        f"**CANADA**\n"
                        f"**PROVINCE DE QUÉBEC**\n"
                        f"**DISTRICT DE MONTRÉAL**\n"
                        f"**COUR DU QUÉBEC (Division des petites créances)**\n\n"
                        f"**N° Dossier :** {project.name.replace('.pdf', '')}\n\n"
                        f"**DEMANDERESSE :** France Caron\n"
                        f"c.\n"
                        f"**DÉFENDERESSE :** Toiture Allaire inc.\n\n"
                        f"---\n\n"
                        f"### CONTESTATION DES RÉCLAMATIONS LIÉES À '{node_name}'\n"
                        f"*(Lié à l'élément de défense '{vector_name}')*\n\n"
                        f"À L'HONORABLE TRIBUNAL, LA DÉFENDERESSE EXPOSE CE QUI SUIT :\n\n"
                        f"1. La défenderesse a exécuté les travaux conformément aux règles de l'art pour les éléments commandés par la demanderesse;\n"
                        f"2. Concernant le support défectueux sous l'élément '{node_name}', la défenderesse a dûment averti la demanderesse de la nécessité de son remplacement, ce que cette dernière a expressément refusé pour des motifs d'économie financière;\n"
                        f"3. La défenderesse ne saurait être tenue responsable des infiltrations découlant directement de la décision de la demanderesse de ne pas procéder aux réparations structurales requises;\n\n"
                        f"**POUR CES MOTIFS, PLAISE À CE TRIBUNAL DE :**\n\n"
                        f"- **REJETER** la demande de la demanderesse;\n"
                        f"- **DÉCLARER** que la défenderesse a pleinement respecté son devoir de conseil et d'information;\n"
                        f"- **CONDAMNER** la demanderesse aux frais de justice.\n\n"
                        f"Montréal, le {datetime.now().strftime('%d %B %Y')}\n\n"
                        f"**Toiture Allaire inc., par ses représentants**"
                    )
                else:
                    return (
                        f"# PROJET DE DEMANDE INTRODUCTIVE D'INSTANCE (CIVIL)\n\n"
                        f"**CANADA**\n"
                        f"**PROVINCE DE QUÉBEC**\n"
                        f"**DISTRICT DE MONTRÉAL**\n"
                        f"**COUR DU QUÉBEC (Division des petites créances)**\n\n"
                        f"**N° Dossier :** {project.name.replace('.pdf', '')}\n\n"
                        f"**DEMANDERESSE :** France Caron\n"
                        f"c.\n"
                        f"**DÉFENDERESSE :** Toiture Allaire inc.\n\n"
                        f"---\n\n"
                        f"### DEMANDE INTRODUCTIVE D'INSTANCE EN REMBOURSEMENT DE TRAVAUX ET DOMMAGES-INTÉRÊTS\n"
                        f"*(Requête liée à l'élément '{node_name}' et la tactique '{vector_name}')*\n\n"
                        f"À L'HONORABLE TRIBUNAL, LA DEMANDERESSE EXPOSE CE QUI SUIT :\n\n"
                        f"1. En 2019, la demanderesse a confié à la défenderesse la réfection de sa toiture, couverte par une garantie de 5 ans sur la main-d'œuvre;\n"
                        f"2. Des infiltrations d'eau majeures sont survenues en raison du manquement professionnel de la défenderesse, qui a posé les bardeaux d'asphalte sur un support pourri, violant l'article 2100 C.c.Q.;\n"
                        f"3. La défenderesse n'a produit aucun écrit attestant d'un refus de travaux ou d'un avertissement de sa part, manquant ainsi à son devoir d'information;\n\n"
                        f"**POUR CES MOTIFS, PLAISE À CE TRIBUNAL DE :**\n\n"
                        f"- **ACCUEILLIR** la présente demande;\n"
                        f"- **CONDAMNER** la défenderesse à payer à la demanderesse la somme totale réclamée de 6 915,28 $ avec l'intérêt légal et l'indemnité additionnelle;\n"
                        f"- **DÉCLARER** le manquement professionnel de la défenderesse à son obligation de résultat et à son devoir de conseil.\n\n"
                        f"Montréal, le {datetime.now().strftime('%d %B %Y')}\n\n"
                        f"**France Caron, Demanderesse**"
                    )
            else:
                return (
                    f"# PROJET DE REQUÊTE EN EXCLUSION DE PREUVE (ARTICLE 24(2) CHARTE)\n\n"
                    f"**CANADA**\n"
                    f"**PROVINCE DE QUÉBEC**\n"
                    f"**DISTRICT DE MONTRÉAL**\n"
                    f"**COUR DU QUÉBEC (Chambre criminelle et pénale)**\n\n"
                    f"**N° Dossier :** {project.name.replace('.pdf', '')}\n\n"
                    f"**SA MAJESTÉ LA REINE**\n"
                    f"c.\n"
                    f"**LE PRÉVENU**\n\n"
                    f"---\n\n"
                    f"### REQUÊTE POUR L'EXCLUSION DU SAC ET DE SON CONTENU\n"
                    f"*(En vertu de l'article 24(2) de la Charte canadienne des droits et libertés et lié à l'élément '{node_name}')*\n\n"
                    f"À L'UN DES HONORABLES JUGES DE LA COUR DU QUÉBEC, LE REQUÉRANT EXPOSE CE QUI SUIT :\n\n"
                    f"1. L'arrestation et la saisie subséquente de l'élément '{node_name}' ont été effectuées en bris de l'article 8 de la Charte contre les fouilles abusives;\n"
                    f"2. Les officiers de police n'avaient aucun motif raisonnable et probable d'effectuer une fouille tactile intrusive du sac souple;\n"
                    f"3. L'admission de cette preuve déconsidérerait l'administration de la justice;\n\n"
                    f"**POUR CES MOTIFS, PLAISE À CE TRIBUNAL DE :**\n\n"
                    f"- **ACCUEILLIR** la présente requête;\n"
                    f"- **DÉCLARER** que les droits constitutionnels du requérant ont été violés;\n"
                    f"- **EXCLURE** de la preuve le sac en nylon et l'arme à feu saisie.\n\n"
                    f"Montréal, le {datetime.now().strftime('%d %B %Y')}\n\n"
                    f"**Avocats de la Défense**"
                )
