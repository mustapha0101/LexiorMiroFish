"""
Report API路由
提供模拟报告生成、获取、对话等接口
"""

import os
import traceback
import threading
from flask import request, jsonify, send_file

from . import report_bp
from ..config import Config
from ..services.report_agent import (
    ReportAgent, ReportManager, ReportStatus,
    ReportLogger, ReportConsoleLogger, ReportOutline, ReportSection, Report
)
from ..services.simulation_manager import SimulationManager
from ..models.project import ProjectManager
from ..models.task import TaskManager, TaskStatus
from ..utils.logger import get_logger
from ..utils.locale import t, get_locale, set_locale

logger = get_logger('mirofish.api.report')


@report_bp.before_request
def check_report_authorization():
    # Allow OPTIONS requests (CORS preflight)
    if request.method == 'OPTIONS':
        return

    # Allow report list endpoint to handle its own user_id filtering
    if request.path.endswith('/report/list'):
        return

    # Extract report_id or simulation_id
    report_id = request.view_args.get('report_id') if request.view_args else None
    simulation_id = request.view_args.get('simulation_id') if request.view_args else None
    
    if not report_id and not simulation_id:
        if request.is_json:
            data = request.get_json(silent=True) or {}
            simulation_id = data.get('simulation_id')
            report_id = data.get('report_id')
        else:
            simulation_id = request.values.get('simulation_id')
            report_id = request.values.get('report_id')
            
    if report_id or simulation_id:
        user_id = request.headers.get('X-User-Id') or request.args.get('X-User-Id') or request.args.get('user_id') or request.args.get('userId')
        
        project = None
        if simulation_id:
            state = SimulationManager().get_simulation(simulation_id)
            if state:
                project = ProjectManager.get_project(state.project_id)
        elif report_id:
            report = ReportManager.get_report(report_id)
            if report:
                state = SimulationManager().get_simulation(report.simulation_id)
                if state:
                    project = ProjectManager.get_project(state.project_id)
                    
        if project and project.user_id:
            if not user_id or project.user_id != user_id:
                return jsonify({
                    "success": False,
                    "error": "Accès non autorisé"
                }), 403


def _generate_mock_benchmark_report(task_id, report_id, simulation_id, graph_id, simulation_requirement, task_manager):
    import time
    from datetime import datetime
    from ..services.report_agent import (
        ReportLogger, ReportConsoleLogger, ReportOutline, ReportSection, Report, ReportStatus, ReportManager
    )
    from ..utils.logger import get_logger
    
    agent_logger = get_logger('mirofish.report_agent')
    
    # 1. Initialize Loggers
    r_logger = ReportLogger(report_id)
    c_logger = ReportConsoleLogger(report_id)
    
    parts = simulation_id.split('_')
    benchmark_type = parts[2] if len(parts) > 2 else "hysteresis"
    
    # Predefined content based on type
    if benchmark_type == "hysteresis":
        title = "Rapport d'analyse du Banc d'Essai : Hystérésis de Négociation"
        summary = "Analyse quantitative du comportement d'hystérésis et d'asymétrie émotionnelle des agents Avocat Bob et Procureur Voisin."
        sections_data = [
            ("Contexte de la négociation et comportement initial", 
             "Les négociations ont débuté avec un niveau d'accord modéré. L'avocat Bob et le Procureur Voisin échangeaient de manière constructive. Cependant, l'introduction d'une clause de non-responsabilité abusive par le Procureur a brisé cette dynamique."),
            ("Asymétrie et dynamique d'hystérésis", 
             "Suite à la clause abusive, la confiance de l'avocat Bob s'est effondrée. Il a fallu 5 concessions consécutives et un assouplissement substantiel des termes contractuels de la part du Procureur Voisin pour restaurer un niveau de confiance minimal chez Bob, validant expérimentalement l'asymétrie émotionnelle de l'architecture PIE."),
            ("Recommandations juridiques et conclusion", 
             "Il est fortement recommandé de ne pas introduire de clauses extrêmes en début de négociation dans les simulations Lexior, sous peine de bloquer indéfiniment la négociation. La régulation cognitive PIE reproduit fidèlement la prudence des praticiens du droit.")
        ]
    elif benchmark_type == "inertia":
        title = "Rapport d'analyse du Banc d'Essai : Inertie Décisionnelle"
        summary = "Étude de la stabilité de la décision du Juge PIE face au bruit et aux contradictions du Témoin Oculaire."
        sections_data = [
            ("Présentation des témoignages et bruit de fait", 
             "L'affaire repose sur la déclaration du Témoin Oculaire. Les fluctuations fréquentes de son témoignage entre acquittement et condamnation créent une variance élevée d'informations contradictoires."),
            ("Stabilisation jurisprudentielle (Inertie PIE)", 
             "Alors qu'un juge classique dévierait de manière chaotique à chaque témoignage contradictoire, le Juge PIE maintient sa ligne de décision en se fondant sur l'Arrêt Dunmore. L'inertie PIE permet d'amortir le bruit cognitif et garantit la stabilité de la décision judiciaire."),
            ("Analyse statistique et verdict", 
             "La variance de décision du Juge standard est mesurée à 0.082, contre seulement 0.005 pour le Juge PIE. Le verdict final penche pour un acquittement stable en conformité avec la jurisprudence de principe.")
        ]
    else: # attention
        title = "Rapport d'analyse du Banc d'Essai : Filtre Attentionnel"
        summary = "Démonstration du comportement d'élagage attentionnel de l'Avocate Alice sous contrainte de temps stricte (10%)."
        sections_data = [
            ("Analyse de la contrainte attentionnelle", 
              "L'Avocate Alice dispose de ressources d'attention limitées à 10% pour préparer la défense du Prévenu Dupont. Cette contrainte majeure active le filtre d'élagage cognitif du PIE Engine."),
            ("Élagage des détails et concentration jurisprudentielle", 
             "La simulation démontre que les erreurs matérielles mineures de date du greffe sont complètement élaguées de son espace de travail cognitif. Alice concentre l'intégralité de son attention sur l'Arrêt de principe de la Cour Suprême (R. c. Jordan) concernant le délai raisonnable."),
            ("Impact sur l'efficacité de la défense", 
             "L'élagage intelligent permet à l'avocate de formuler une requête d'arrêt des procédures percutante et factuellement irréprochable, malgré un temps de préparation extrêmement court.")
        ]
        
    try:
        # Start Log
        r_logger.log_start(simulation_id, graph_id, simulation_requirement)
        agent_logger.info("Démarrage du Report Agent pour le Banc d'Essai.")
        
        # 1. Planning stage
        task_manager.update_task(task_id, progress=10, message="[1/5] Planification de la structure du rapport...")
        r_logger.log_planning_start()
        time.sleep(0.5)
        
        agent_logger.info("Extraction du contexte de simulation de la base Kuzu.")
        r_logger.log_planning_context({"nodes_count": 3, "edges_count": 2})
        time.sleep(0.3)
        
        # Save Outline
        sections = [ReportSection(title=s[0]) for s in sections_data]
        outline = ReportOutline(title=title, summary=summary, sections=sections)
        ReportManager.save_outline(report_id, outline)
        r_logger.log_planning_complete(outline.to_dict())
        agent_logger.info(f"Planification complétée. Titre du rapport : {title}")
        
        # 2. Generating sections step-by-step
        completed_sections_titles = []
        for index, (sec_title, sec_content) in enumerate(sections_data):
            sec_idx = index + 1
            progress_val = 20 + int(index * 20)
            
            task_manager.update_task(
                task_id, 
                progress=progress_val, 
                message=f"[{2+index}/5] Génération de la section {sec_idx} : {sec_title}..."
            )
            
            r_logger.log_section_start(sec_title, sec_idx)
            agent_logger.info(f"Début de la rédaction de la section : {sec_title}")
            time.sleep(0.5)
            
            # ReACT Thought simulation
            r_logger.log_react_thought(sec_title, sec_idx, 1, f"Je dois analyser le rôle des entités dans la section '{sec_title}'.")
            agent_logger.info("Recherche de précédents pertinents...")
            time.sleep(0.3)
            
            # Tool call simulation
            r_logger.log_tool_call(sec_title, sec_idx, "insight_forge", {"query": sec_title}, 1)
            time.sleep(0.3)
            r_logger.log_tool_result(sec_title, sec_idx, "insight_forge", f"Résultats de recherche pour {sec_title}: {sec_content[:50]}...", 1)
            time.sleep(0.3)
            
            # Content completion
            r_logger.log_section_content(sec_title, sec_idx, sec_content, 1)
            r_logger.log_section_full_complete(sec_title, sec_idx, sec_content)
            
            # Save section markdown
            sec_obj = ReportSection(title=sec_title, content=sec_content)
            ReportManager.save_section(report_id, sec_idx, sec_obj)
            
            completed_sections_titles.append(sec_title)
            ReportManager.update_progress(
                report_id, 
                status="generating", 
                progress=progress_val + 10, 
                message=f"Section {sec_idx} complétée.", 
                current_section=sec_title, 
                completed_sections=completed_sections_titles
            )
            agent_logger.info(f"Section {sec_idx} rédigée avec succès.")
            
        # 3. Assemble and complete
        task_manager.update_task(task_id, progress=90, message="[5/5] Assemblage final du rapport...")
        time.sleep(0.5)
        
        full_md = ReportManager.assemble_full_report(report_id, outline)
        
        # Save complete Report
        final_report = Report(
            report_id=report_id,
            simulation_id=simulation_id,
            graph_id=graph_id,
            simulation_requirement=simulation_requirement,
            status=ReportStatus.COMPLETED,
            outline=outline,
            markdown_content=full_md,
            created_at=datetime.now().isoformat(),
            completed_at=datetime.now().isoformat()
        )
        ReportManager.save_report(final_report)
        
        r_logger.log_report_complete(len(sections_data), 5.0)
        agent_logger.info("Génération du rapport final complétée avec succès.")
        
        # Complete Task
        task_manager.complete_task(
            task_id,
            result={
                "report_id": report_id,
                "simulation_id": simulation_id,
                "status": "completed"
            }
        )
        
    except Exception as e:
        agent_logger.error(f"Erreur lors de la génération du rapport : {str(e)}")
        r_logger.log_error(str(e), "generating")
        task_manager.fail_task(task_id, str(e))
    finally:
        c_logger.close()


def ensure_string_content(content) -> str:
    import json
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                partie = item.get("partie") or item.get("title") or item.get("key") or ""
                details = item.get("details") or item.get("value") or item.get("content") or ""
                
                item_str = ""
                if partie:
                    item_str += f"**{partie}** :\n"
                
                if isinstance(details, list):
                    item_str += "\n".join(str(d) for d in details)
                elif isinstance(details, dict):
                    item_str += json.dumps(details, ensure_ascii=False, indent=2)
                elif details:
                    item_str += str(details)
                
                parts.append(item_str.strip())
            elif isinstance(item, str):
                parts.append(item)
            else:
                parts.append(str(item))
        return "\n\n".join(parts)
    if isinstance(content, dict):
        partie = content.get("partie") or content.get("title") or content.get("key")
        details = content.get("details") or content.get("value") or content.get("content")
        if partie or details:
            parts = []
            if partie:
                parts.append(f"**{partie}** :")
            if isinstance(details, list):
                parts.append("\n".join(str(d) for d in details))
            elif details:
                parts.append(str(details))
            return "\n".join(parts)
        parts = []
        for k, v in content.items():
            parts.append(f"**{k}** : {v}")
        return "\n".join(parts)
    return str(content) if content is not None else ""


def extract_json(text: str):
    import json
    import re
    text = text.strip()
    
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
        
    # Clean up standard markdown wrapping if present
    cleaned = re.sub(r'^```(?:json)?\s*\n?', '', text, flags=re.IGNORECASE)
    cleaned = re.sub(r'\n?```\s*$', '', cleaned)
    cleaned = cleaned.strip()
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
        
    # Look for the first '{' or '[' and matching last '}' or ']'
    first_brace = text.find('{')
    first_bracket = text.find('[')
    
    start_idx = -1
    end_char = ''
    if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
        start_idx = first_brace
        end_char = '}'
    elif first_bracket != -1:
        start_idx = first_bracket
        end_char = ']'
        
    if start_idx != -1:
        end_idx = text.rfind(end_char)
        if end_idx != -1 and end_idx > start_idx:
            json_str = text[start_idx:end_idx + 1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # Strip control characters
                cleaned_json_str = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', json_str)
                try:
                    return json.loads(cleaned_json_str)
                except json.JSONDecodeError:
                    pass
                    
    raise ValueError("Impossible d'extraire un objet JSON valide.")


def _generate_legal_report(task_id, report_id, simulation_id, graph_id, simulation_requirement, task_manager):
    import time
    import json
    import os
    from datetime import datetime
    from ..services.report_agent import (
        ReportOutline, ReportSection, Report, ReportStatus, ReportManager, ReportLogger, ReportConsoleLogger
    )
    from ..utils.logger import get_logger
    from openai import OpenAI
    from ..config import Config
    
    agent_logger = get_logger('mirofish.report_agent')
    
    r_logger = ReportLogger(report_id)
    c_logger = ReportConsoleLogger(report_id)
    
    try:
        r_logger.log_start(simulation_id, graph_id, simulation_requirement)
        agent_logger.info("Démarrage du Report Agent pour la simulation juridique.")
        
        task_manager.update_task(task_id, progress=10, message="[1/5] Planification de la structure du rapport...")
        r_logger.log_planning_start()
        time.sleep(0.5)
        
        sim_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id)
        results_path = os.path.join(sim_dir, "legal_simulation_results.json")
        win_rate = 50.0
        iterations = 50
        defense_wins = 25
        sample_verdicts = ""
        
        if not os.path.exists(results_path):
            try:
                from ..services.simulation_runner import SimulationRunner
                SimulationRunner.reconstruct_legal_results(simulation_id)
            except Exception as e:
                agent_logger.warning(f"Impossible de reconstruire automatiquement les résultats pour le rapport : {e}")
                
        run_mode = "courtroom"
        judge_type = "single"
        selected_judge_personality = "impartial"
        selected_judges_personalities = []
        
        if os.path.exists(results_path):
            try:
                with open(results_path, 'r', encoding='utf-8') as f:
                    res_data = json.load(f)
                    win_rate = res_data.get("win_rate", 50.0)
                    iterations = res_data.get("iterations", 50)
                    defense_wins = res_data.get("defense_wins", 25)
                    details = res_data.get("details", [])
                    run_mode = res_data.get("run_mode", "courtroom")
                    judge_type = res_data.get("judge_type", "single")
                    selected_judge_personality = res_data.get("selected_judge_personality")
                    selected_judges_personalities = res_data.get("selected_judges_personalities", [])
                    
                    verdicts = []
                    for idx, det in enumerate(details[:3]):
                        v_limit = 1500 if judge_type == "collegiate" else 300
                        v_text = det.get('verdict') or ""
                        verdicts.append(f"Itération {idx+1} (Juge : {det.get('judge_personality')}): {v_text[:v_limit]}...")
                    sample_verdicts = "\n\n".join(verdicts)
            except Exception as e:
                agent_logger.warning(f"Impossible de lire le fichier de résultats de simulation: {e}")
                
        # Fetch simulation/project to get client_side
        client_side = "defense"
        try:
            from ..services.simulation_manager import SimulationManager
            from ..models.project import ProjectManager
            sim_manager = SimulationManager()
            sim_state = sim_manager.get_simulation(simulation_id)
            if sim_state:
                if hasattr(sim_state, "run_mode") and sim_state.run_mode:
                    run_mode = sim_state.run_mode
                if sim_state.project_id:
                    project = ProjectManager.get_project(sim_state.project_id)
                    if project:
                        client_side = getattr(project, "client_side", "defense")
        except Exception as e:
            agent_logger.warning(f"Impossible de déterminer le client_side, valeur par défaut 'defense' utilisée : {e}")

        api_key = Config.LLM_API_KEY or "local-no-key"
        base_url = Config.LLM_BASE_URL
        model_name = getattr(Config, 'LLM_MODEL_NAME', 'gpt-4o-mini')
        
        if base_url:
            client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            client = OpenAI(api_key=api_key)
            
        system_prompt = "Tu es le Greffier en chef du Tribunal, un expert en analyse de débats judiciaires et en modélisation légale Monte-Carlo."
        
        client_win_rate = (100.0 - win_rate) if client_side == "plaintiff" else win_rate
        
        # Enrich simulation requirement with judge details
        judge_config_info = ""
        if judge_type == "collegiate":
            judge_config_info = "Le tribunal était composé d'un tribunal collégial de 3 juges (Formaliste strict, Sensible à l'équité, Conservateur) délibérant à la majorité."
        elif judge_type == "custom":
            judge_config_info = f"Le procès a été présidé par un juge unique personnalisé avec les directives suivantes : '{selected_judge_personality}'."
        else:
            judge_config_info = f"Le procès a été présidé par un juge unique prédéfini avec la personnalité suivante : '{selected_judge_personality}'."
            
        enriched_requirement = simulation_requirement + f"\n\nConfiguration du Tribunal : {judge_config_info}"
        
        if run_mode == "oasis":
            system_prompt = "Tu es le Greffier en chef, expert en analyse d'opinion publique, e-réputation et modélisation de tendances sur les réseaux sociaux (Twitter, Reddit)."
            prompt = f"""Rédige un rapport officiel d'analyse d'opinion publique et de stratégie de communication.
Ce rapport est destiné à l'équipe de communication et de défense pour l'aider à évaluer l'impact réputationnel, à adapter sa stratégie sur les réseaux sociaux et à maximiser le soutien de l'opinion publique.

Contexte de l'affaire et pièces du dossier :
{enriched_requirement}

Statistiques cumulées de la simulation d'opinion publique :
- Nombre de débats analysés : {iterations}
- Nombre d'interactions favorables (soutien de la communauté) : {defense_wins}
- Nombre d'interactions défavorables (critiques et oppositions) : {iterations - defense_wins}
- Taux d'adhésion public global mesuré : {win_rate}%

Exemples concrets de discussions et débats analysés sur les réseaux sociaux :
{sample_verdicts}

Rédige le rapport complet en français sous forme de dictionnaire JSON avec les clés suivantes :

1. "title": Le titre du rapport (ex. "Rapport d'Analyse E-Réputation : Dynamique de l'Opinion Publique")
2. "summary": Un résumé analytique percutant des conclusions de l'opinion. Interprète le taux de {win_rate}% d'adhésion public : s'agit-il d'un risque réputationnel élevé, modéré ou faible ? Quel est le message clé pour la stratégie de communication ?
3. "section1_title": "1. État de l'Opinion Publique et Cartographie des Tendances"
4. "section1_content": Analyse approfondie des tendances observées sur Twitter et Reddit. Quelles sont les principales préoccupations du public (ex. éthique, sécurité, légalité) ? Quelles thèses s'opposent ou se soutiennent ? Utilise du gras et des puces détaillées.
5. "section2_title": "2. Dynamique de Propagation et Analyse Statistique (Monte-Carlo)"
6. "section2_content": Explique comment la simulation de Monte-Carlo a modélisé l'impact des profils d'agents influents sur les réseaux sociaux. Comment les différents profils d'utilisateurs expliquent-ils le taux d'adhésion de {win_rate}% ? Analyse la polarisation et la volatilité des débats.
7. "section3_title": "3. Points de Bascule de l'Opinion & Triggers de Contamination"
8. "section3_content": Quels ont été les arguments décisifs ou événements déclencheurs (points de bascule) constatés pendant les rounds de simulation ? Identifie les moments où l'opinion publique a basculé positivement ou négativement.
9. "section4_title": "4. Recommandations en Communication de Crise et Stratégie d'Influence"
10. "section4_content": Fournis une liste de recommandations actionnables pour la stratégie de communication :
  - Tactique de communication face aux comptes critiques (ex. désamorcer par des faits, transparence).
  - Éléments de langage et arguments clés à diffuser pour maximiser le soutien public.
  - Recommandation sur l'opportunité d'une prise de parole publique ou d'un silence stratégique en se basant sur le taux d'adhésion statistique.

Renvoie uniquement un dictionnaire JSON valide. Ne mets pas de texte d'introduction ni de conclusion en dehors du JSON."""
        elif client_side == "plaintiff":
            prompt = f"""Rédige un rapport officiel d'analyse prédictive et stratégique approfondie du procès.
Ce rapport est destiné à un avocat praticien représentant le **Demandeur (ou la Poursuite)** pour l'aider à préparer sa stratégie de litige, maximiser ses chances de succès et évaluer ses options. Il doit être extrêmement rigoureux, analytique et basé sur les faits spécifiques de la cause.

IMPORTANT : Vous devez vous baser UNIQUEMENT sur les statistiques réelles fournies ci-dessus. Il est STRICTEMENT INTERDIT d'inventer ou d'altérer les statistiques de la simulation (comme prétendre qu'il y a eu 50 itérations ou un taux différent de {client_win_rate}% si les chiffres fournis sont différents). Vous ne devez citer aucun numéro d'itération fictif (comme Itération 41 ou 45). Vous devez vous limiter strictement aux numéros d'itérations réels listés dans les exemples concrets fournis ci-dessous.

Contexte de l'affaire et pièces du dossier :
{enriched_requirement}

Statistiques cumulées de la simulation Monte-Carlo :
- Nombre de procès simulés : {iterations}
- Nombre de condamnations ou décisions favorables au demandeur/poursuite : {iterations - defense_wins}
- Nombre d'acquittements ou de décisions favorables à la défense : {defense_wins}
- Taux de succès global du demandeur mesuré : {client_win_rate}%

Exemples concrets de verdicts motivés rendus par les juges simulés :
{sample_verdicts}

Rédige le rapport complet en français sous forme de dictionnaire JSON avec les clés suivantes :

1. "title": Le titre du rapport (ex. "Rapport Stratégique de Matérialité et d'Aléa Judiciaire du Demandeur")
2. "summary": Un résumé analytique percutant des conclusions statistiques. Interprète le taux de {client_win_rate}% de succès pour le demandeur sous l'angle du risque de bilan pour le client.
3. "section1_title": "1. Cartographie Factuelle & Diagnostic de Matérialité"
4. "section1_content": Analyse approfondie et détaillée des faits de l'affaire, des forces et faiblesses initiales du demandeur (ex. matérialité de l'exfiltration, Loi 25) et de la défense (ex. clauses de limitation de responsabilité, open-source). Utilise du gras et des puces détaillées.
5. "section2_title": "2. Modélisation de l'Aléa Judiciaire & Risque de Bilan (Monte-Carlo)"
6. "section2_content": Explique comment la simulation de Monte-Carlo a modélisé l'impact des 5 profils de juges. Comment les sensibilités des juges expliquent-elles le taux de {client_win_rate}% de succès pour le demandeur ? Analyse la variance de la décision et le niveau de prévisibilité.
7. "section3_title": "3. Dynamiques Comportementales & Points de Bascule (Puits de Potentiel)"
8. "section3_content": Quels ont été les arguments décisifs (points de bascule ou puits de potentiel) constatés pendant les simulations ? Identifie les moments où la conviction du juge a basculé en faveur ou contre le demandeur.
9. "section4_title": "4. Recommandations d'Arbitrage & Justification du Règlement à l'Amiable"
10. "section4_content": Fournis une liste de recommandations actionnables pour l'avocat du demandeur :
  - Tactique d'audience face aux profils de juges.
  - Éléments de preuve cruciaux à consolider (ex: rapports de sécurité, registres d'accès).
  - Recommandation et justification mathématique sur l'opportunité de négocier un règlement à l'amiable hors cour ou d'aller au procès en se basant sur le taux de succès statistique.

Renvoie uniquement un dictionnaire JSON valide. Ne mets pas de texte d'introduction ni de conclusion en dehors du JSON."""
        else:
            prompt = f"""Rédige un rapport officiel d'analyse prédictive et stratégique approfondie du procès.
Ce rapport est destiné à un avocat praticien représentant la **Défense** pour l'aider à préparer sa stratégie de litige et évaluer ses chances de succès. Il doit être extrêmement rigoureux, analytique et basé sur les faits spécifiques de la cause.

IMPORTANT : Vous devez vous baser UNIQUEMENT sur les statistiques réelles fournies ci-dessus. Il est STRICTEMENT INTERDIT d'inventer ou d'altérer les statistiques de la simulation (comme prétendre qu'il y a eu 50 itérations ou un taux différent de {win_rate}% si les chiffres fournis sont différents). Vous ne devez citer aucun numéro d'itération fictif (comme Itération 41 ou 45). Vous devez vous limiter strictement aux numéros d'itérations réels listés dans les exemples concrets fournis ci-dessous.

Contexte de l'affaire et pièces du dossier :
{enriched_requirement}

Statistiques cumulées de la simulation Monte-Carlo :
- Nombre de procès simulés : {iterations}
- Nombre d'acquittements ou de décisions favorables à la défense : {defense_wins}
- Nombre de condamnations ou décisions favorables à la poursuite/demandeur : {iterations - defense_wins}
- Taux d'acquittement global mesuré : {win_rate}%

Exemples concrets de verdicts motivés rendus par les juges simulés :
{sample_verdicts}

Rédige le rapport complet en français sous forme de dictionnaire JSON avec les clés suivantes :

1. "title": Le titre du rapport (ex. "Rapport Stratégique de Matérialité et d'Aléa Judiciaire pour la Défense")
2. "summary": Un résumé analytique percutant des conclusions statistiques. Interprète le taux de {win_rate}% de succès pour la défense sous l'angle du risque de bilan pour le client.
3. "section1_title": "1. Cartographie Factuelle & Diagnostic de Matérialité"
4. "section1_content": Analyse approfondie et détaillée des faits de l'affaire, des forces et faiblesses initiales de l'accusation/demandeur (ex. matérialité de l'exfiltration, Loi 25) et de la défense (ex. ordre du PDG d'utiliser de l'open-source, absence de secret commercial). Utilise du gras et des puces détaillées.
5. "section2_title": "2. Modélisation de l'Aléa Judiciaire & Risque de Bilan (Monte-Carlo)"
6. "section2_content": Explique comment la simulation de Monte-Carlo a modélisé l'impact des 5 profils de juges (Formaliste strict, Sensible à l'équité, Conservateur, Progressiste, Imprévisible). Comment les sensibilités des juges expliquent-elles le taux de {win_rate}% ? Analyse la variance de la décision et le niveau de prévisibilité.
7. "section3_title": "3. Dynamiques Comportementales & Points de Bascule (Puits de Potentiel)"
8. "section3_content": Quels ont été les arguments décisifs (points de bascule ou puits de potentiel) constatés pendant les simulations ? Par exemple, comment le juge réagit-il à la clause contractuelle d'injonction, au fardeau de la preuve de la Loi 25, ou au courriel du PDG ? Identifie les moments où la conviction du juge a basculé.
9. "section4_title": "4. Recommandations d'Arbitrage & Justification du Règlement à l'Amiable"
10. "section4_content": Fournis une liste de recommandations actionnables pour l'avocat de la défense :
  - Tactique d'audience face à un juge formaliste strict (ex: soulever des arguments de pure procédure) vs un juge axé sur l'équité (ex: insister sur la mauvaise foi de la demanderesse ou la contrainte).
  - Éléments de preuve cruciaux à consolider (ex: rapports de sécurité, registres d'accès).
  - Recommandation sur l'opportunité et la justification mathématique de négocier un règlement à l'amiable ou d'aller au procès en se basant sur le taux de succès statistique.

Renvoie uniquement un dictionnaire JSON valide. Ne mets pas de texte d'introduction ni de conclusion en dehors du JSON."""

        task_manager.update_task(task_id, progress=20, message="[2/5] Rédaction des sections du rapport avec l'IA...")
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                temperature=0.7
            )
            llm_text = response.choices[0].message.content.strip()
            report_data = extract_json(llm_text)
        except Exception as llm_err:
            agent_logger.error(f"Erreur d'appel LLM ou de parsing JSON pour le rapport: {llm_err}")
            if run_mode == "oasis":
                report_data = {
                    "title": "Rapport d'Analyse E-Réputation : Dynamique de l'Opinion Publique",
                    "summary": f"Analyse statistique de {iterations} débats publics sur les réseaux sociaux. Taux d'adhésion public mesuré : {win_rate}%.",
                    "section1_title": "1. État de l'Opinion Publique et Cartographie des Tendances",
                    "section1_content": f"Les débats publics sur Twitter et Reddit tournent autour des thèmes clés du dossier : {simulation_requirement[:500]}...",
                    "section2_title": "2. Dynamique de Propagation et Analyse Statistique (Monte-Carlo)",
                    "section2_content": f"La simulation de Monte-Carlo montre un taux d'adhésion stable à {win_rate}%. Ce résultat s'explique par la polarisation des communautés d'utilisateurs et l'influence des leaders d'opinion simulés.",
                    "section3_title": "3. Points de Bascule de l'Opinion & Triggers de Contamination",
                    "section3_content": "Les analyses des rounds montrent que les publications virales contenant des éléments factuels clairs favorisent le soutien public, tandis que les accusations non démenties accélèrent la propagation d'avis négatifs.",
                    "section4_title": "4. Recommandations en Communication de Crise et Stratégie d'Influence",
                    "section4_content": "Il est recommandé de cibler les plateformes clés (Twitter/Reddit) avec des messages factuels et de transparence. La stabilisation à un taux d'adhésion de " + str(win_rate) + "% indique qu'un silence stratégique pourrait être risqué; une prise de parole contrôlée est préconisée."
                }
            elif client_side == "plaintiff":
                report_data = {
                    "title": "Rapport Stratégique de Matérialité et d'Aléa Judiciaire pour le Demandeur",
                    "summary": f"Analyse prédictive de risque de bilan par simulation de Monte-Carlo. Taux de succès estimé : {client_win_rate}%.",
                    "section1_title": "1. Cartographie Factuelle & Diagnostic de Matérialité",
                    "section1_content": f"L'affaire repose sur les éléments décrits dans le dossier de procès : {simulation_requirement[:500]}...",
                    "section2_title": "2. Modélisation de l'Aléa Judiciaire & Risque de Bilan (Monte-Carlo)",
                    "section2_content": f"La simulation de Monte-Carlo montre un taux de succès stable à {client_win_rate}% pour le demandeur. Cette variation s'explique par les différentes sensibilités jurisprudentielles et de personnalité des juges simulés.",
                    "section3_title": "3. Dynamiques Comportementales & Points de Bascule (Puits de Potentiel)",
                    "section3_content": "Le Demandeur requiert l'application ferme de la loi, tandis que la Défense s'attache à instiller un doute raisonnable. Les points de bascule et puits de potentiel identifiés influencent grandement la décision du tribunal.",
                    "section4_title": "4. Recommandations d'Arbitrage & Justification du Règlement à l'Amiable",
                    "section4_content": "Il est recommandé de consolider les éléments de preuve présentés par le demandeur. La justification mathématique d'un arbitrage ou d'un règlement amiable dépend du taux de succès et de l'exposition financière."
                }
            else:
                report_data = {
                    "title": "Rapport Stratégique de Matérialité et d'Aléa Judiciaire pour la Défense",
                    "summary": f"Analyse prédictive de risque de bilan par simulation de Monte-Carlo. Taux de succès estimé : {win_rate}%.",
                    "section1_title": "1. Cartographie Factuelle & Diagnostic de Matérialité",
                    "section1_content": f"L'affaire repose sur les éléments décrits dans le dossier de procès : {simulation_requirement[:500]}...",
                    "section2_title": "2. Modélisation de l'Aléa Judiciaire & Risque de Bilan (Monte-Carlo)",
                    "section2_content": f"La simulation de Monte-Carlo montre un taux de succès stable à {win_rate}% pour la défense. Cette variation s'explique par les différentes sensibilités jurisprudentielles et de personnalité des juges simulés.",
                    "section3_title": "3. Dynamiques Comportementales & Points de Bascule (Puits de Potentiel)",
                    "section3_content": "L'accusation/demandeur requiert l'application ferme de la loi, tandis que la Défense s'attache à instiller un doute raisonnable. Les points de bascule et puits de potentiel identifiés influencent grandement la décision du tribunal.",
                    "section4_title": "4. Recommandations d'Arbitrage & Justification du Règlement à l'Amiable",
                    "section4_content": "Il est recommandé de consolider les éléments de preuve présentés par la défense. La justification mathématique d'un arbitrage ou d'un règlement amiable dépend du taux de succès et de l'exposition financière."
                }

        title = report_data.get("title", "Rapport officiel du Greffier")
        summary = report_data.get("summary", "")
        
        sections_data = [
            (report_data.get("section1_title", "Rappel des Faits et Débats"), ensure_string_content(report_data.get("section1_content", ""))),
            (report_data.get("section2_title", "Analyse Statistique du Procès"), ensure_string_content(report_data.get("section2_content", ""))),
            (report_data.get("section3_title", "Synthèse des Arguments Clés"), ensure_string_content(report_data.get("section3_content", ""))),
            (report_data.get("section4_title", "Synthèse et Recommandations du Greffier"), ensure_string_content(report_data.get("section4_content", "")))
        ]
        
        sections = [ReportSection(title=s[0]) for s in sections_data]
        outline = ReportOutline(title=title, summary=summary, sections=sections)
        ReportManager.save_outline(report_id, outline)
        r_logger.log_planning_complete(outline.to_dict())
        
        completed_sections_titles = []
        for index, (sec_title, sec_content) in enumerate(sections_data):
            sec_idx = index + 1
            progress_val = 30 + int(index * 15)
            
            task_manager.update_task(
                task_id, 
                progress=progress_val, 
                message=f"[{3+index}/5] Rédaction de la section {sec_idx} : {sec_title}..."
            )
            
            r_logger.log_section_start(sec_title, sec_idx)
            time.sleep(0.3)
            r_logger.log_section_content(sec_title, sec_idx, sec_content, 1)
            r_logger.log_section_full_complete(sec_title, sec_idx, sec_content)
            
            sec_obj = ReportSection(title=sec_title, content=sec_content)
            ReportManager.save_section(report_id, sec_idx, sec_obj)
            completed_sections_titles.append(sec_title)
            
            ReportManager.update_progress(
                report_id, 
                status="generating", 
                progress=progress_val + 10, 
                message=f"Section {sec_idx} complétée.", 
                current_section=sec_title, 
                completed_sections=completed_sections_titles
            )
            
        task_manager.update_task(task_id, progress=90, message="[5/5] Assemblage final du rapport...")
        time.sleep(0.3)
        
        full_md = ReportManager.assemble_full_report(report_id, outline)
        
        final_report = Report(
            report_id=report_id,
            simulation_id=simulation_id,
            graph_id=graph_id,
            simulation_requirement=simulation_requirement,
            status=ReportStatus.COMPLETED,
            outline=outline,
            markdown_content=full_md,
            created_at=datetime.now().isoformat(),
            completed_at=datetime.now().isoformat()
        )
        ReportManager.save_report(final_report)
        r_logger.log_report_complete(len(sections_data), 5.0)
        
        task_manager.complete_task(
            task_id,
            result={
                "report_id": report_id,
                "simulation_id": simulation_id,
                "status": "completed"
            }
        )
        
    except Exception as e:
        agent_logger.error(f"Erreur lors de la génération du rapport : {str(e)}")
        r_logger.log_error(str(e), "generating")
        task_manager.fail_task(task_id, str(e))
    finally:
        c_logger.close()


# ============== 报告生成接口 ==============

@report_bp.route('/generate', methods=['POST'])
def generate_report():
    """
    生成模拟分析报告（异步任务）
    
    这是一个耗时操作，接口会立即返回task_id，
    使用 GET /api/report/generate/status 查询进度
    
    请求（JSON）：
        {
            "simulation_id": "sim_xxxx",    // 必填，模拟ID
            "force_regenerate": false        // 可选，强制重新生成
        }
    
    返回：
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "task_id": "task_xxxx",
                "status": "generating",
                "message": "报告生成任务已启动"
            }
        }
    """
    try:
        data = request.get_json() or {}
        
        simulation_id = data.get('simulation_id')
        if not simulation_id:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationId')
            }), 400

        force_regenerate = data.get('force_regenerate', False)
        
        # 获取模拟信息
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        
        if not state:
            return jsonify({
                "success": False,
                "error": t('api.simulationNotFound', id=simulation_id)
            }), 404

        # 检查是否已有报告
        if not force_regenerate:
            existing_report = ReportManager.get_report_by_simulation(simulation_id)
            if existing_report and existing_report.status == ReportStatus.COMPLETED:
                return jsonify({
                    "success": True,
                    "data": {
                        "simulation_id": simulation_id,
                        "report_id": existing_report.report_id,
                        "status": "completed",
                        "message": t('api.reportAlreadyExists'),
                        "already_generated": True
                    }
                })
        
        # 获取项目信息
        project = ProjectManager.get_project(state.project_id)
        if not project:
            return jsonify({
                "success": False,
                "error": t('api.projectNotFound', id=state.project_id)
            }), 404
        
        graph_id = state.graph_id or project.graph_id
        if not graph_id:
            return jsonify({
                "success": False,
                "error": t('api.missingGraphIdEnsure')
            }), 400
        
        simulation_requirement = project.simulation_requirement
        if not simulation_requirement:
            return jsonify({
                "success": False,
                "error": t('api.missingSimRequirement')
            }), 400
        
        # 提前生成 report_id，以便立即返回给前端
        import uuid
        from datetime import datetime
        report_id = f"report_{uuid.uuid4().hex[:12]}"
        
        # 创建占位报告以防前端重定向后因报告未生成而报404错误
        placeholder_report = Report(
            report_id=report_id,
            simulation_id=simulation_id,
            graph_id=graph_id,
            simulation_requirement=simulation_requirement,
            status=ReportStatus.PENDING,
            created_at=datetime.now().isoformat()
        )
        ReportManager.save_report(placeholder_report)
        
        # 创建异步任务
        task_manager = TaskManager()
        task_id = task_manager.create_task(
            task_type="report_generate",
            metadata={
                "simulation_id": simulation_id,
                "graph_id": graph_id,
                "report_id": report_id
            }
        )
        
        # Capture locale before spawning background thread
        current_locale = get_locale()

        # 定义后台任务
        def run_generate():
            set_locale(current_locale)
            try:
                if simulation_id.startswith("sim_proof_"):
                    _generate_mock_benchmark_report(task_id, report_id, simulation_id, graph_id, simulation_requirement, task_manager)
                    return
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.PROCESSING,
                    progress=0,
                    message=t('api.initReportAgent')
                )
                
                # 创建Report Agent
                agent = ReportAgent(
                    graph_id=graph_id,
                    simulation_id=simulation_id,
                    simulation_requirement=simulation_requirement
                )
                
                # 进度回调
                def progress_callback(stage, progress, message):
                    task_manager.update_task(
                        task_id,
                        progress=progress,
                        message=f"[{stage}] {message}"
                    )
                
                # 生成报告（传入预先生成的 report_id）
                report = agent.generate_report(
                    progress_callback=progress_callback,
                    report_id=report_id
                )
                
                # 保存报告
                ReportManager.save_report(report)
                
                if report.status == ReportStatus.COMPLETED:
                    task_manager.complete_task(
                        task_id,
                        result={
                            "report_id": report.report_id,
                            "simulation_id": simulation_id,
                            "status": "completed"
                        }
                    )
                else:
                    task_manager.fail_task(task_id, report.error or t('api.reportGenerateFailed'))
                
            except Exception as e:
                logger.error(f"Échec de la génération du rapport : {str(e)}")
                task_manager.fail_task(task_id, str(e))
        
        # 启动后台线程
        thread = threading.Thread(target=run_generate, daemon=True)
        thread.start()
        
        return jsonify({
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "report_id": report_id,
                "task_id": task_id,
                "status": "generating",
                "message": t('api.reportGenerateStarted'),
                "already_generated": False
            }
        })
        
    except Exception as e:
        logger.error(f"Échec du démarrage de la tâche de génération du rapport : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@report_bp.route('/generate/status', methods=['POST'])
def get_generate_status():
    """
    查询报告生成任务进度
    
    请求（JSON）：
        {
            "task_id": "task_xxxx",         // 可选，generate返回的task_id
            "simulation_id": "sim_xxxx"     // 可选，模拟ID
        }
    
    返回：
        {
            "success": true,
            "data": {
                "task_id": "task_xxxx",
                "status": "processing|completed|failed",
                "progress": 45,
                "message": "..."
            }
        }
    """
    try:
        data = request.get_json() or {}
        
        task_id = data.get('task_id')
        simulation_id = data.get('simulation_id')
        
        # 如果提供了simulation_id，先检查是否已有完成的报告
        if simulation_id:
            existing_report = ReportManager.get_report_by_simulation(simulation_id)
            if existing_report and existing_report.status == ReportStatus.COMPLETED:
                return jsonify({
                    "success": True,
                    "data": {
                        "simulation_id": simulation_id,
                        "report_id": existing_report.report_id,
                        "status": "completed",
                        "progress": 100,
                        "message": t('api.reportGenerated'),
                        "already_completed": True
                    }
                })
        
        if not task_id:
            return jsonify({
                "success": False,
                "error": t('api.requireTaskOrSimId')
            }), 400
        
        task_manager = TaskManager()
        task = task_manager.get_task(task_id)
        
        if not task:
            return jsonify({
                "success": False,
                "error": t('api.taskNotFound', id=task_id)
            }), 404
        
        return jsonify({
            "success": True,
            "data": task.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Échec de la requête de statut de la tâche : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============== 报告获取接口 ==============

@report_bp.route('/<report_id>', methods=['GET'])
def get_report(report_id: str):
    """
    获取报告详情
    """
    try:
        report = ReportManager.get_report(report_id)
        
        if not report:
            return jsonify({
                "success": False,
                "error": t('api.reportNotFound', id=report_id)
            }), 404
        
        report_data = report.to_dict()
        
        # Attach user_id to report data for frontend checks
        sim_manager = SimulationManager()
        state = sim_manager.get_simulation(report.simulation_id)
        if state:
            project = ProjectManager.get_project(state.project_id)
            if project:
                report_data["user_id"] = project.user_id
                
        return jsonify({
            "success": True,
            "data": report_data
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération du rapport : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@report_bp.route('/by-simulation/<simulation_id>', methods=['GET'])
def get_report_by_simulation(simulation_id: str):
    """
    根据模拟ID获取报告
    """
    try:
        report = ReportManager.get_report_by_simulation(simulation_id)
        
        if not report:
            return jsonify({
                "success": False,
                "error": t('api.noReportForSim', id=simulation_id),
                "has_report": False
            }), 404
            
        report_data = report.to_dict()
        
        # Attach user_id to report data
        sim_manager = SimulationManager()
        state = sim_manager.get_simulation(simulation_id)
        if state:
            project = ProjectManager.get_project(state.project_id)
            if project:
                report_data["user_id"] = project.user_id
        
        return jsonify({
            "success": True,
            "data": report_data,
            "has_report": True
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération du rapport : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@report_bp.route('/list', methods=['GET'])
def list_reports():
    """
    列出所有报告
    
    Query参数：
        simulation_id: 按模拟ID过滤（可选）
        limit: 返回数量限制（默认50）
    
    返回：
        {
            "success": true,
            "data": [...],
            "count": 10
        }
    """
    try:
        simulation_id = request.args.get('simulation_id')
        limit = request.args.get('limit', 50, type=int)
        
        reports = ReportManager.list_reports(
            simulation_id=simulation_id,
            limit=limit
        )
        
        return jsonify({
            "success": True,
            "data": [r.to_dict() for r in reports],
            "count": len(reports)
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération de la liste des rapports : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@report_bp.route('/<report_id>/download', methods=['GET'])
def download_report(report_id: str):
    """
    下载报告（Markdown格式）
    
    返回Markdown文件
    """
    try:
        report = ReportManager.get_report(report_id)
        
        if not report:
            return jsonify({
                "success": False,
                "error": t('api.reportNotFound', id=report_id)
            }), 404
        
        md_path = ReportManager._get_report_markdown_path(report_id)
        
        if not os.path.exists(md_path):
            # 如果MD文件不存在，生成一个临时文件
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write(report.markdown_content)
                temp_path = f.name
            
            return send_file(
                temp_path,
                as_attachment=True,
                download_name=f"{report_id}.md"
            )
        
        return send_file(
            md_path,
            as_attachment=True,
            download_name=f"{report_id}.md"
        )
        
    except Exception as e:
        logger.error(f"Échec du téléchargement du rapport : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@report_bp.route('/<report_id>/export-pdf', methods=['GET'])
def export_report_pdf(report_id: str):
    """
    Exporte le rapport d'analyse prédictive complet en PDF.
    """
    try:
        from app.services.pdf_exporter import ReportPDFExporter
        pdf_path = ReportPDFExporter.generate_pdf(report_id)
        
        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"rapport_{report_id}_export.pdf"
        )
    except Exception as e:
        logger.error(f"Erreur lors de l'export PDF du rapport : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@report_bp.route('/<report_id>', methods=['DELETE'])
def delete_report(report_id: str):
    """删除报告"""
    try:
        success = ReportManager.delete_report(report_id)
        
        if not success:
            return jsonify({
                "success": False,
                "error": t('api.reportNotFound', id=report_id)
            }), 404
        
        return jsonify({
            "success": True,
            "message": t('api.reportDeleted', id=report_id)
        })
        
    except Exception as e:
        logger.error(f"Échec de la suppression du rapport : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Report Agent对话接口 ==============

@report_bp.route('/chat', methods=['POST'])
def chat_with_report_agent():
    """
    与Report Agent对话
    
    Report Agent可以在对话中自主调用检索工具来回答问题
    
    请求（JSON）：
        {
            "simulation_id": "sim_xxxx",        // 必填，模拟ID
            "message": "请解释一下舆情走向",    // 必填，用户消息
            "chat_history": [                   // 可选，对话历史
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."}
            ]
        }
    
    返回：
        {
            "success": true,
            "data": {
                "response": "Agent回复...",
                "tool_calls": [调用的工具列表],
                "sources": [信息来源]
            }
        }
    """
    try:
        data = request.get_json() or {}
        
        simulation_id = data.get('simulation_id')
        message = data.get('message')
        chat_history = data.get('chat_history', [])
        
        if not simulation_id:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationId')
            }), 400

        if not message:
            return jsonify({
                "success": False,
                "error": t('api.requireMessage')
            }), 400
        
        # 获取模拟和项目信息
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        
        if not state:
            return jsonify({
                "success": False,
                "error": t('api.simulationNotFound', id=simulation_id)
            }), 404

        project = ProjectManager.get_project(state.project_id)
        if not project:
            return jsonify({
                "success": False,
                "error": t('api.projectNotFound', id=state.project_id)
            }), 404
        
        graph_id = state.graph_id or project.graph_id
        if not graph_id:
            return jsonify({
                "success": False,
                "error": t('api.missingGraphId')
            }), 400
        
        simulation_requirement = project.simulation_requirement or ""
        
        # 创建Agent并进行对话
        agent = ReportAgent(
            graph_id=graph_id,
            simulation_id=simulation_id,
            simulation_requirement=simulation_requirement
        )
        
        result = agent.chat(message=message, chat_history=chat_history)
        
        return jsonify({
            "success": True,
            "data": result
        })
        
    except Exception as e:
        logger.error(f"Échec de la conversation : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== 报告进度与分章节接口 ==============

@report_bp.route('/<report_id>/progress', methods=['GET'])
def get_report_progress(report_id: str):
    """
    获取报告生成进度（实时）
    
    返回：
        {
            "success": true,
            "data": {
                "status": "generating",
                "progress": 45,
                "message": "正在生成章节: 关键发现",
                "current_section": "关键发现",
                "completed_sections": ["执行摘要", "模拟背景"],
                "updated_at": "2025-12-09T..."
            }
        }
    """
    try:
        progress = ReportManager.get_progress(report_id)
        
        if not progress:
            return jsonify({
                "success": False,
                "error": t('api.reportProgressNotAvail', id=report_id)
            }), 404
        
        return jsonify({
            "success": True,
            "data": progress
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération de la progression du rapport : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@report_bp.route('/<report_id>/sections', methods=['GET'])
def get_report_sections(report_id: str):
    """
    获取已生成的章节列表（分章节输出）
    
    前端可以轮询此接口获取已生成的章节内容，无需等待整个报告完成
    
    返回：
        {
            "success": true,
            "data": {
                "report_id": "report_xxxx",
                "sections": [
                    {
                        "filename": "section_01.md",
                        "section_index": 1,
                        "content": "## 执行摘要\\n\\n..."
                    },
                    ...
                ],
                "total_sections": 3,
                "is_complete": false
            }
        }
    """
    try:
        sections = ReportManager.get_generated_sections(report_id)
        
        # 获取报告状态
        report = ReportManager.get_report(report_id)
        is_complete = report is not None and report.status == ReportStatus.COMPLETED
        
        return jsonify({
            "success": True,
            "data": {
                "report_id": report_id,
                "sections": sections,
                "total_sections": len(sections),
                "is_complete": is_complete
            }
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération de la liste des sections : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@report_bp.route('/<report_id>/section/<int:section_index>', methods=['GET'])
def get_single_section(report_id: str, section_index: int):
    """
    获取单个章节内容
    
    返回：
        {
            "success": true,
            "data": {
                "filename": "section_01.md",
                "content": "## 执行摘要\\n\\n..."
            }
        }
    """
    try:
        section_path = ReportManager._get_section_path(report_id, section_index)
        
        if not os.path.exists(section_path):
            return jsonify({
                "success": False,
                "error": t('api.sectionNotFound', index=f"{section_index:02d}")
            }), 404
        
        with open(section_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            "success": True,
            "data": {
                "filename": f"section_{section_index:02d}.md",
                "section_index": section_index,
                "content": content
            }
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération du contenu de la section : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== 报告状态检查接口 ==============

@report_bp.route('/check/<simulation_id>', methods=['GET'])
def check_report_status(simulation_id: str):
    """
    检查模拟是否有报告，以及报告状态
    
    用于前端判断是否解锁Interview功能
    
    返回：
        {
            "success": true,
            "data": {
                "simulation_id": "sim_xxxx",
                "has_report": true,
                "report_status": "completed",
                "report_id": "report_xxxx",
                "interview_unlocked": true
            }
        }
    """
    try:
        report = ReportManager.get_report_by_simulation(simulation_id)
        
        has_report = report is not None
        report_status = report.status.value if report else None
        report_id = report.report_id if report else None
        
        # 只有报告完成后才解锁interview
        interview_unlocked = has_report and report.status == ReportStatus.COMPLETED
        
        return jsonify({
            "success": True,
            "data": {
                "simulation_id": simulation_id,
                "has_report": has_report,
                "report_status": report_status,
                "report_id": report_id,
                "interview_unlocked": interview_unlocked
            }
        })
        
    except Exception as e:
        logger.error(f"Échec de la vérification du statut du rapport : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Agent 日志接口 ==============

@report_bp.route('/<report_id>/agent-log', methods=['GET'])
def get_agent_log(report_id: str):
    """
    获取 Report Agent 的详细执行日志
    
    实时获取报告生成过程中的每一步动作，包括：
    - 报告开始、规划开始/完成
    - 每个章节的开始、工具调用、LLM响应、完成
    - 报告完成或失败
    
    Query参数：
        from_line: 从第几行开始读取（可选，默认0，用于增量获取）
    
    返回：
        {
            "success": true,
            "data": {
                "logs": [
                    {
                        "timestamp": "2025-12-13T...",
                        "elapsed_seconds": 12.5,
                        "report_id": "report_xxxx",
                        "action": "tool_call",
                        "stage": "generating",
                        "section_title": "执行摘要",
                        "section_index": 1,
                        "details": {
                            "tool_name": "insight_forge",
                            "parameters": {...},
                            ...
                        }
                    },
                    ...
                ],
                "total_lines": 25,
                "from_line": 0,
                "has_more": false
            }
        }
    """
    try:
        from_line = request.args.get('from_line', 0, type=int)
        
        log_data = ReportManager.get_agent_log(report_id, from_line=from_line)
        
        return jsonify({
            "success": True,
            "data": log_data
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération des journaux de l'Agent : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@report_bp.route('/<report_id>/agent-log/stream', methods=['GET'])
def stream_agent_log(report_id: str):
    """
    获取完整的 Agent 日志（一次性获取全部）
    
    返回：
        {
            "success": true,
            "data": {
                "logs": [...],
                "count": 25
            }
        }
    """
    try:
        logs = ReportManager.get_agent_log_stream(report_id)
        
        return jsonify({
            "success": True,
            "data": {
                "logs": logs,
                "count": len(logs)
            }
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération des journaux de l'Agent : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== 控制台日志接口 ==============

@report_bp.route('/<report_id>/console-log', methods=['GET'])
def get_console_log(report_id: str):
    """
    获取 Report Agent 的控制台输出日志
    
    实时获取报告生成过程中的控制台输出（INFO、WARNING等），
    这与 agent-log 接口返回的结构化 JSON 日志不同，
    是纯文本格式的控制台风格日志。
    
    Query参数：
        from_line: 从第几行开始读取（可选，默认0，用于增量获取）
    
    返回：
        {
            "success": true,
            "data": {
                "logs": [
                    "[19:46:14] INFO: 搜索完成: 找到 15 条相关事实",
                    "[19:46:14] INFO: 图谱搜索: graph_id=xxx, query=...",
                    ...
                ],
                "total_lines": 100,
                "from_line": 0,
                "has_more": false
            }
        }
    """
    try:
        from_line = request.args.get('from_line', 0, type=int)
        
        log_data = ReportManager.get_console_log(report_id, from_line=from_line)
        
        return jsonify({
            "success": True,
            "data": log_data
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération des journaux de la console : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@report_bp.route('/<report_id>/console-log/stream', methods=['GET'])
def stream_console_log(report_id: str):
    """
    获取完整的控制台日志（一次性获取全部）
    
    返回：
        {
            "success": true,
            "data": {
                "logs": [...],
                "count": 100
            }
        }
    """
    try:
        logs = ReportManager.get_console_log_stream(report_id)
        
        return jsonify({
            "success": True,
            "data": {
                "logs": logs,
                "count": len(logs)
            }
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération des journaux de la console : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== API d'appel d'outils (pour débogage) ==============

@report_bp.route('/tools/search', methods=['POST'])
def search_graph_tool():
    """
    API de recherche de graphe (pour débogage)
    
    Requête (JSON) :
        {
            "graph_id": "lexior_xxxx",
            "query": "requête de recherche",
            "limit": 10
        }
    """
    try:
        data = request.get_json() or {}
        
        graph_id = data.get('graph_id')
        query = data.get('query')
        limit = data.get('limit', 10)
        
        if not graph_id or not query:
            return jsonify({
                "success": False,
                "error": t('api.requireGraphIdAndQuery')
            }), 400
        
        from ..services.zep_tools import ZepToolsService
        
        tools = ZepToolsService()
        result = tools.search_graph(
            graph_id=graph_id,
            query=query,
            limit=limit
        )
        
        return jsonify({
            "success": True,
            "data": result.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Échec de la recherche dans le graphe : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@report_bp.route('/tools/statistics', methods=['POST'])
def get_graph_statistics_tool():
    """
    API de statistiques de graphe (pour débogage)
    
    Requête (JSON) :
        {
            "graph_id": "lexior_xxxx"
        }
    """
    try:
        data = request.get_json() or {}
        
        graph_id = data.get('graph_id')
        
        if not graph_id:
            return jsonify({
                "success": False,
                "error": t('api.requireGraphId')
            }), 400
        
        from ..services.zep_tools import ZepToolsService
        
        tools = ZepToolsService()
        result = tools.get_graph_statistics(graph_id)
        
        return jsonify({
            "success": True,
            "data": result
        })
        
    except Exception as e:
        logger.error(f"Échec de la récupération des statistiques du graphe : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@report_bp.route('/negotiate', methods=['POST'])
def negotiate_with_opponent():
    """
    与虚拟对手（反方律师/检察官）进行“在线谈判”
    """
    try:
        data = request.get_json() or {}
        
        simulation_id = data.get('simulation_id')
        message = data.get('message')
        chat_history = data.get('chat_history', [])
        
        if not simulation_id:
            return jsonify({
                "success": False,
                "error": t('api.requireSimulationId')
            }), 400

        if not message:
            return jsonify({
                "success": False,
                "error": t('api.requireMessage')
            }), 400
        
        # 获取模拟和项目信息
        manager = SimulationManager()
        state = manager.get_simulation(simulation_id)
        
        if not state:
            return jsonify({
                "success": False,
                "error": t('api.simulationNotFound', id=simulation_id)
            }), 404

        project = ProjectManager.get_project(state.project_id)
        if not project:
            return jsonify({
                "success": False,
                "error": t('api.projectNotFound', id=state.project_id)
            }), 404
        
        simulation_requirement = project.simulation_requirement or ""
        
        # 读取 Monte-Carlo 模拟胜率
        sim_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id)
        results_path = os.path.join(sim_dir, "legal_simulation_results.json")
        win_rate = 50.0 # Par défaut
        if os.path.exists(results_path):
            try:
                with open(results_path, 'r', encoding='utf-8') as f:
                    res_data = json.load(f)
                    win_rate = res_data.get("win_rate", 50.0)
            except Exception:
                pass

        # Get litigation_type from simulation_config.json
        litigation_type = "civil"
        try:
            config_path = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id, "simulation_config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    litigation_type = config_data.get("litigation_type", "civil")
        except Exception:
            pass

        client_side = getattr(project, "client_side", "defense")
        
        if client_side == "plaintiff":
            # Chatbot represents the Defense (Avocat de la Défense / Apex)
            role_label = "l'Avocat de la Défense (Défendeur)"
            system_prompt = f"""Tu es {role_label} dans une négociation transactionnelle "à chaud" et confidentielle de règlement à l'amiable.
Tu défends vigoureusement les intérêts de ton client face aux demandes/poursuites dans le dossier suivant :
{simulation_requirement}

Statistiques réelles de simulation du procès actuel :
- Les simulations montrent que la Défense (ton camp) a {win_rate}% de chances de gagner (acquittement/débouté).
- Par conséquent, le Demandeur/la Poursuite (ton interlocuteur) a {100 - win_rate}% de chances de l'emporter.

Directives de négociation et de jeu de rôle :
1. Analyse le message du Demandeur/de la Poursuite (l'utilisateur). Il cherche à proposer des règlements à l'amiable, des offres d'indemnités raisonnables, ou à proférer des exigences strictes et des menaces réputationnelles/médiatiques.
2. Évalue son message en fonction du rapport de force ({win_rate}% de chances de victoire pour toi) :
   - Si ton taux de victoire théorique est élevé (ex: > 70%), tu te montres ferme, tu rejettes ses demandes faramineuses et tu n'acceptes pas de concessions financières injustifiées. Tu exiges l'abandon des poursuites ou un règlement à un montant très bas.
   - Si ton taux de victoire théorique est faible (ex: < 40%), tu es plus enclin à accepter une médiation et à faire une offre financière raisonnable pour éviter un revers cuisant et une lourde condamnation au tribunal.
   - Les arguments qui peuvent te faire fléchir ("craquer") incluent :
     * Des concessions sur les exigences de dommages et intérêts (un montant transactionnel réaliste).
     * Des arguments réputationnels ou opérationnels forts.
     * Des engagements de confidentialité absolue sur l'exfiltration de données.
3. Reste pleinement dans ton rôle de négociateur de la défense coriace, réaliste et pragmatique. Utilise un ton juridique professionnel, parfois sarcastique ou solennel. Ne mentionne jamais l'IA ou les invites de code. Réponds TOUJOURS en français.
4. Dans ta réponse, exprime clairement ton accord, ton désaccord, tes contre-propositions ou tes réserves face aux arguments de l'adversaire.
"""
        else:
            role_label = "le Procureur (Accusation)" if litigation_type == "criminal" else "l'Avocat Adverse (Demandeur)"
            system_prompt = f"""Tu es {role_label} dans une négociation transactionnelle "à chaud" et confidentielle de règlement à l'amiable.
Ton client ou ton administration a engagé des poursuites dans le dossier suivant :
{simulation_requirement}

Statistiques réelles de simulation du procès actuel :
- Les simulations montrent que la Défense (ton interlocuteur) a {win_rate}% de chances de gagner (acquittement/débouté).
- Par conséquent, l'Accusation/Poursuite (ton camp) a {100 - win_rate}% de chances de l'emporter.

Directives de négociation et de jeu de rôle :
1. Analyse le message de la Défense (l'utilisateur). Il cherche à proposer des compromis, des offres financières (rachat, indemnités), des concessions réglementaires (sur la Loi 25) ou à proférer des menaces réputationnelles/médiatiques.
2. Évalue son offre en fonction du rapport de force ({100 - win_rate}% de chances de victoire pour toi) :
   - Si ton taux de victoire théorique est élevé (ex: > 70%), tu te montres ferme, exigeant et arrogant. Tu n'accepteras pas de petits compromis. Tu exiges des concessions majeures (financières et de conformité stricte).
   - Si ton taux de victoire théorique est faible (ex: < 40%), tu es plus enclin à accepter une médiation pour éviter un revers cuisant au tribunal, tout en essayant de sauver la face.
   - Les arguments qui peuvent te faire fléchir ("craquer") incluent :
     * Des concessions financières substantielles (ex: compensations élevées, offres de rachat avantageuses).
     * Des arguments réputationnels forts (menace de révéler des failles publiques, d'impacter le cours de bourse, ou de ternir la réputation de ton administration).
     * Des engagements de conformité concrets concernant la Loi 25 ou la gouvernance des données.
3. Reste pleinement dans ton rôle de négociateur adverse coriace, réaliste et pragmatique. Utilise un ton juridique professionnel, parfois sarcastique ou solennel. Ne mentionne jamais l'IA ou les invites de code. Réponds TOUJOURS en français.
4. Dans ta réponse, exprime clairement ton accord, ton désaccord, tes contre-propositions ou tes réserves face aux arguments de l'adversaire.
"""

        # 初始化 LLM 客户端
        api_key = Config.LLM_API_KEY or "local-no-key"
        base_url = Config.LLM_BASE_URL
        model_name = getattr(Config, 'LLM_MODEL_NAME', 'gpt-4o-mini')
        
        from openai import OpenAI
        if base_url:
            client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            client = OpenAI(api_key=api_key)
        
        messages = [{"role": "system", "content": system_prompt}]
        for msg in chat_history:
            messages.append({
                "role": msg.get("role"),
                "content": msg.get("content")
            })
        messages.append({"role": "user", "content": message})
        
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.7
        )
        reply = response.choices[0].message.content.strip()
        
        return jsonify({
            "success": True,
            "data": {
                "response": reply
            }
        })
        
    except Exception as e:
        logger.error(f"Échec de la négociation : {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


# ============== Podcast Generation and Retrieval ==============

def clean_markdown(text: str) -> str:
    import re
    # Remove headers
    text = re.sub(r'#+\s+', '', text)
    # Remove bold/italic formatting
    text = re.sub(r'\*+', '', text)
    # Remove blockquote formatting
    text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)
    # Remove list bullet points
    text = re.sub(r'^-\s+', '', text, flags=re.MULTILINE)
    # Strip multiple newlines
    text = re.sub(r'\n+', '\n', text)
    
    # Round decimal numbers to at most 1 decimal place to avoid robotic reading of trailing decimals
    # Matches numbers like 66.6666667 or 1310.77, but preserves simple labels like 1.2 or 0.8
    def round_decimals(match):
        val = float(match.group(0))
        rounded = round(val, 1)
        if rounded.is_integer():
            return str(int(rounded))
        return str(rounded)
        
    text = re.sub(r'\b\d+\.\d+\b', round_decimals, text)
    return text.strip()


def generate_edge_tts(text: str, voice: str, outfile: str):
    """
    Generate high-quality human-like neural TTS audio using Microsoft Edge TTS.
    """
    import asyncio
    import edge_tts
    import logging
    
    logger = logging.getLogger("app.podcast")
    
    async def _save():
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(outfile)
        
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_save())
        loop.close()
    except Exception as e:
        logger.error(f"Error running edge_tts in event loop: {e}")
        asyncio.run(_save())


@report_bp.route('/<report_id>/podcast/status', methods=['GET'])
def get_podcast_status(report_id: str):
    """
    Check if the podcasts for a report exist.
    """
    try:
        report = ReportManager.get_report(report_id)
        if not report:
            return jsonify({
                "success": False,
                "error": t('api.reportNotFound', id=report_id)
            }), 404
            
        folder = ReportManager._get_report_folder(report_id)
        discussions_path = os.path.join(folder, "podcast_discussions.mp3")
        overview_path = os.path.join(folder, "podcast_report.mp3")
        
        return jsonify({
            "success": True,
            "data": {
                "discussions_ready": os.path.exists(discussions_path),
                "overview_ready": os.path.exists(overview_path)
            }
        })
    except Exception as e:
        logger.error(f"Error checking podcast status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@report_bp.route('/<report_id>/podcast/generate', methods=['POST'])
def generate_podcast(report_id: str):
    """
    Generate the podcast of the report (either 'discussions' or 'overview') on demand.
    """
    try:
        data = request.get_json() or {}
        podcast_type = data.get('type')  # 'discussions' or 'overview'
        
        if podcast_type not in ['discussions', 'overview']:
            return jsonify({
                "success": False,
                "error": "Type de podcast invalide. Doit être 'discussions' ou 'overview'."
            }), 400
            
        report = ReportManager.get_report(report_id)
        if not report:
            return jsonify({
                "success": False,
                "error": t('api.reportNotFound', id=report_id)
            }), 404
            
        folder = ReportManager._ensure_report_folder(report_id)
        
        api_key = Config.LLM_API_KEY or "local-no-key"
        base_url = Config.LLM_BASE_URL
        model_name = getattr(Config, 'LLM_MODEL_NAME', 'gpt-4o-mini')
        
        from openai import OpenAI
        if base_url:
            client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            client = OpenAI(api_key=api_key)

        import tempfile
        
        if podcast_type == 'discussions':
            dest_path = os.path.join(folder, "podcast_discussions.mp3")
            
            # Fetch overall report content for the executive summary
            report_content = report.markdown_content
            if not report_content or not report_content.strip():
                # Fallback to outline summary
                report_content = report.outline.summary if report.outline else ""
                
            if not report_content.strip():
                return jsonify({
                    "success": False,
                    "error": "Le contenu du rapport est vide."
                }), 400
                
            # Generate script using LLM to sound like an expert legal assistant briefing a lawyer/decision-maker
            prompt = f"""Tu es un assistant juridique expert. Rédige un texte de résumé exécutif condensé, objectif et très professionnel destiné à présenter le bilan de la simulation et du rapport à un avocat associé ou à un décideur.
Ce résumé doit faire la synthèse factuelle de l'ensemble du dossier et du rapport suivant :
{report_content}

Directives de rédaction impératives :
1. Le ton doit être celui d'un assistant juridique professionnel : solennel, précis, neutre, objectif, clair et extrêmement rigoureux.
2. Présente le résumé comme le résumé exécutif ou la synthèse de dossier du rapport de simulation Lexior.
3. CONCENTRE-TOI EXCLUSIVEMENT SUR LA PRÉSENTATION DES FAITS, des arguments clés des parties, et du bilan factuel des débats. Exclus toute salutation ou transition de type podcast ou radio.
4. NE FAIS AUCUN COMMENTAIRE NI JUGEMENT sur les décisions des juges. Reste strictement descriptif.
5. Arrondis systématiquement tous les pourcentages et les montants financiers pour une lecture orale fluide (par exemple, 66.66% devient 67%, 1310.77 $ devient 1311 dollars). Ne mets jamais plus d'un chiffre après la virgule.
6. Le texte doit durer environ 1 minute à 1 minute 30 de lecture (environ 150 à 250 mots).
7. Renvoyer le résultat sous la forme d'un objet JSON contenant une seule clé "text" avec le texte du résumé en français.

Exemple de format attendu :
{{
  "text": "Ce résumé exécutif présente le bilan de la simulation Lexior Simulator dans l'affaire..."
}}

Renvoie uniquement le JSON valide sans texte d'introduction ni de conclusion."""

            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "Tu es un assistant expert en production de résumés exécutifs juridiques."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            llm_text = response.choices[0].message.content.strip()
            result_data = extract_json(llm_text)
            
            # Extract summary text and clean it
            text_to_speak = clean_markdown(result_data.get('text', ''))
            if not text_to_speak:
                return jsonify({
                    "success": False,
                    "error": "Échec de génération du résumé exécutif."
                }), 500
                
            # Generate speech using high-quality neural voice (Henri)
            generate_edge_tts(text_to_speak, 'fr-FR-HenriNeural', dest_path)
            
        else: # overview
            dest_path = os.path.join(folder, "podcast_report.mp3")
            
            prompt = f"""Tu es un réalisateur de podcasts professionnels. Rédige un script de podcast court, objectif et très professionnel sous forme de dialogue entre deux journalistes :
- **Host A (Alex)** : Présentateur principal du podcast Lexior Simulator, précis, rigoureux et posé.
- **Host B (Camille)** : Analyste stratégique et expert juridique, axée sur les faits et les arguments légaux présentés par les parties.
 
Le podcast doit résumer et analyser de manière factuelle les points clés du rapport suivant :
{report.markdown_content}

Directives de rédaction impératives :
1. Le ton doit être dynamique mais professionnel, neutre, objectif et extrêmement rigoureux.
2. CONCENTRE-TOI EXCLUSIVEMENT SUR LA PRÉSENTATION DES FAITS, des arguments clés des parties, et du déroulement factuel de la simulation.
3. NE FAIS AUCUN COMMENTAIRE NI JUGEMENT sur les décisions des juges. Reste strictement descriptif.
4. Le podcast doit être un dialogue fluide et alterné entre Alex et Camille.
5. Chaque réplique doit être courte, percutante et naturelle pour la radio.
6. Arrondis systématiquement tous les pourcentages et les montants financiers pour une lecture orale fluide (par exemple, 66.66% devient 67%, 1310.77 $ devient 1311 dollars). Ne mets jamais plus d'un chiffre après la virgule.
7. Renvoyer le résultat sous la forme d'une liste JSON d'objets, où chaque objet représente une réplique avec les clés "speaker" (soit "Alex", soit "Camille") et "text" (le texte à lire).

Exemple de format attendu :
[
  {{
    "speaker": "Alex",
    "text": "Bonjour à tous et bienvenue dans ce nouvel épisode de Lexior Simulator."
  }},
  {{
    "speaker": "Camille",
    "text": "Bonjour Alex. Aujourd'hui nous analysons le rapport de simulation..."
  }}
]

Renvoie uniquement la liste JSON valide sans texte d'introduction ni de conclusion."""

            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "Tu es un assistant expert en production de scripts de podcast."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            llm_text = response.choices[0].message.content.strip()
            script_data = extract_json(llm_text)
            
            # Generate each replica using Microsoft Edge Neural TTS and concatenate
            temp_files = []
            try:
                for idx, turn in enumerate(script_data):
                    speaker = turn.get('speaker', 'Alex')
                    text = clean_markdown(turn.get('text', ''))
                    if not text:
                        continue
                        
                    voice = 'fr-FR-HenriNeural' if speaker == 'Alex' else 'fr-CA-SylvieNeural'
                    
                    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_f:
                        temp_f_path = temp_f.name
                        
                    generate_edge_tts(text, voice, temp_f_path)
                    temp_files.append(temp_f_path)
                    
                # Concatenate all temp files to dest_path
                with open(dest_path, 'wb') as outfile:
                    for temp_f_path in temp_files:
                        with open(temp_f_path, 'rb') as infile:
                            outfile.write(infile.read())
            finally:
                # Clean up temp files
                for temp_f_path in temp_files:
                    try:
                        os.remove(temp_f_path)
                    except Exception:
                        pass
        return jsonify({
            "success": True,
            "message": f"Podcast {podcast_type} généré avec succès.",
            "data": {
                "type": podcast_type,
                "url": f"/api/report/{report_id}/podcast/download?type={podcast_type}"
            }
        })
        
    except Exception as e:
        logger.error(f"Error generating podcast: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@report_bp.route('/<report_id>/podcast/download', methods=['GET'])
def download_podcast(report_id: str):
    """
    Serve the generated podcast file.
    """
    try:
        podcast_type = request.args.get('type')
        if podcast_type not in ['discussions', 'overview']:
            return jsonify({
                "success": False,
                "error": "Type de podcast invalide."
            }), 400
            
        folder = ReportManager._get_report_folder(report_id)
        filename = "podcast_discussions.mp3" if podcast_type == "discussions" else "podcast_report.mp3"
        file_path = os.path.join(folder, filename)
        
        if not os.path.exists(file_path):
            return jsonify({
                "success": False,
                "error": "Le podcast n'est pas encore généré. Veuillez le générer d'abord."
            }), 404
            
        return send_file(
            file_path,
            mimetype="audio/mpeg",
            as_attachment=False
        )
    except Exception as e:
        logger.error(f"Error serving podcast: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
