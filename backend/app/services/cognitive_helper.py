"""
Cognitive Helper
Fournit les points d'ancrage pour injecter les invites dynamiques et traiter
les retours d'actions post-round dans les scripts de simulation.
"""

import os
import json
import sqlite3
import logging
from typing import List, Dict, Any, Tuple
from .cognitive_memory import CognitiveMemoryService
from .cognitive_engine import CognitiveEngine, CognitiveAgentState

logger = logging.getLogger('mirofish.cognitive_helper')

FILTERED_ACTIONS = {'refresh', 'sign_up'}

ACTION_TYPE_MAP = {
    'create_post': 'CREATE_POST',
    'like_post': 'LIKE_POST',
    'dislike_post': 'DISLIKE_POST',
    'repost': 'REPOST',
    'quote_post': 'QUOTE_POST',
    'follow': 'FOLLOW',
    'mute': 'MUTE',
    'create_comment': 'CREATE_COMMENT',
    'like_comment': 'LIKE_COMMENT',
    'dislike_comment': 'DISLIKE_COMMENT',
    'search_posts': 'SEARCH_POSTS',
    'search_user': 'SEARCH_USER',
    'trend': 'TREND',
    'do_nothing': 'DO_NOTHING',
    'interview': 'INTERVIEW',
}

def inject_cognitive_prompts(active_agents: List[Tuple[Any, Any]], config: Dict[str, Any], agent_names: Dict[int, str]):
    """
    Injecte les tensions cognitives, croyances et récits métacognitifs
    dans les messages système des agents actifs pour le round courant.
    """
    simulation_id = config.get("simulation_id", "unknown")
    is_legal = config.get("simulation_type") == "legal" or "legal" in simulation_id.lower()
    simulation_type = "legal" if is_legal else "social"
    
    logger.info(f"Injection des invites cognitives pour la simulation: {simulation_id} (Type: {simulation_type})")
    
    # Read injected stimuli
    injected_stimuli = []
    run_state_file = os.path.join(os.path.dirname(__file__), '../../uploads/simulations', simulation_id, "run_state.json")
    if os.path.exists(run_state_file):
        try:
            with open(run_state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
                injected_stimuli = state_data.get("injected_stimuli", [])
        except Exception as read_state_err:
            logger.error(f"Error reading injected stimuli from state file: {read_state_err}")

    stimuli_section = ""
    if injected_stimuli:
        stimuli_section = "\n# DÉBATS ET STIMULI RÉCENTS (OASIS JUDICIAIRE)\n"
        stimuli_section += "IMPORTANT : Les événements ou faits suivants se sont produits dans le cadre du dossier. Vous devez ABSOLUMENT en débattre, y réagir ou adapter votre stratégie/thèse en fonction :\n"
        for i, stim in enumerate(injected_stimuli, 1):
            stimuli_section += f"- Stimulus {i}: {stim}\n"
        stimuli_section += "\n"

    for agent_id, agent in active_agents:
        agent_str_id = str(agent_id)
        agent_name = agent_names.get(agent_id, f"Agent_{agent_id}")
        
        try:
            # Récupérer l'état actuel ou par défaut
            agent_state = CognitiveMemoryService.get_agent_state(simulation_id, agent_str_id, agent_name)
            
            # Récupérer les souvenirs en fonction du budget attentionnel à long terme
            strength_threshold = 0.2
            if agent_state.attention_budget.get("long_term", 0.2) < 0.20:
                strength_threshold = 0.6
                
            memories = CognitiveMemoryService.get_active_memories(simulation_id, agent_str_id, strength_threshold=strength_threshold)
            memories_str = "\n".join([f"- {m}" for m in memories]) if memories else "Aucun souvenir marquant."
            
            # Synthèse des croyances
            beliefs_summary = []
            for belief_key, distribution in agent_state.beliefs.items():
                if distribution:
                    max_key = max(distribution, key=distribution.get)
                    pct = distribution[max_key] * 100
                    beliefs_summary.append(f"{belief_key}: {max_key} ({pct:.0f}%)")
            beliefs_str = ", ".join(beliefs_summary) if beliefs_summary else "Aucune croyance ferme."
            
            # Formatage des tensions selon le type de simulation
            if simulation_type == "legal":
                tensions_str = f"""  * Prudence vs Rapidité: {agent_state.tensions.get('prudence_vs_rapidite', 0.5):.2f}
  * Offensive vs Négociation: {agent_state.tensions.get('offensive_vs_negociation', 0.5):.2f}
  * Procédure vs Équité: {agent_state.tensions.get('procedure_vs_equite', 0.5):.2f}"""
            else:
                tensions_str = f"""  * Exploration vs Security: {agent_state.tensions.get('exploration_vs_security', 0.5):.2f}
  * Cooperation vs Domination: {agent_state.tensions.get('cooperation_vs_domination', 0.5):.2f}
  * Truth vs Social Survival: {agent_state.tensions.get('truth_vs_social_survival', 0.5):.2f}"""

            # Introspection
            meta_narrative = agent_state.meta_narrative or 'Je commence à explorer cet environnement.'
            recent_reflection = agent_state.recent_reflection or "J'observe les premiers échanges."
            if agent_state.attention_budget.get("introspection", 0.2) < 0.20:
                meta_narrative = "Mon introspection est limitée par mon attention actuelle."
                recent_reflection = "Je me concentre sur l'action immédiate sans recul."

            # Prompt cognitif dynamique
            dynamic_section = f"""
# DYNAMIC COGNITIVE STATE (PIE)
Your internal state is constantly evolving. In this round:
- Current Mood: {agent_state.mood}
- Current Tensions: 
{tensions_str}
- Core Beliefs: {beliefs_str}
- Metacognitive Auto-Narration: {meta_narrative}
- Recent Reflection: {recent_reflection}
{stimuli_section}
# AUTOBIOGRAPHICAL MEMORIES (SELECTIVE)
You recall the following key events from your past:
{memories_str}

Keep these internal tensions, reflections, and beliefs in mind when choosing your next action and writing your content.
"""
            
            # Sauvegarder le message original au premier passage
            if not hasattr(agent, 'original_system_message'):
                agent.original_system_message = agent.system_message.content
            
            # Mettre à jour l'invite de l'agent
            agent.system_message.content = agent.original_system_message + dynamic_section
            
        except Exception as e:
            logger.error(f"Erreur d'injection cognitive pour l'agent {agent_id}: {e}")


async def update_cognitive_states(actual_actions: List[Dict[str, Any]], config: Dict[str, Any], round_num: int):
    """
    Met à jour l'état cognitif des agents après leurs actions (croyances bayésiennes, plasticité des tensions,
    génération de la réflexion métacognitive et ajout de souvenirs).
    """
    simulation_id = config.get("simulation_id", "unknown")
    is_legal = config.get("simulation_type") == "legal" or "legal" in simulation_id.lower()
    simulation_type = "legal" if is_legal else "social"
    
    logger.info(f"Mise à jour post-round des états cognitifs pour la simulation: {simulation_id} (Type: {simulation_type})")
    
    # Instance locale du moteur
    engine = CognitiveEngine()
    
    for action_data in actual_actions:
        agent_id = action_data.get('agent_id')
        if agent_id is None:
            continue
            
        agent_str_id = str(agent_id)
        agent_name = action_data.get('agent_name', f"Agent_{agent_id}")
        action_type = action_data.get('action_type', "DO_NOTHING")
        action_args = action_data.get('action_args', {})
        
        try:
            # Charger l'état cognitif
            agent_state = CognitiveMemoryService.get_agent_state(simulation_id, agent_str_id, agent_name)
            
            # Créer le stimulus d'action
            event_desc = f"J'ai effectué l'action {action_type} avec comme arguments: {json.dumps(action_args, ensure_ascii=False)}"
            
            # Mise à jour des croyances (décalage bayésien selon l'action)
            updated_beliefs = engine._update_beliefs_bayesian(agent_state, event_desc, action_type)
            agent_state.beliefs = updated_beliefs
            
            # Générer une métacognition asynchrone rapide
            meta_res = await engine._generate_metacognition(
                agent_state, 
                event_desc, 
                action_type, 
                f"Action effectuée au round {round_num}",
                simulation_type
            )
            agent_state.meta_narrative = meta_res.get("meta_narrative", agent_state.meta_narrative)
            agent_state.recent_reflection = meta_res.get("recent_reflection", agent_state.recent_reflection)
            
            # Appliquer la plasticité des tensions
            tension_to_drift = "prudence_vs_rapidite" if simulation_type == "legal" else "exploration_vs_security"
            engine._update_tensions_plasticity(agent_state, tension_to_drift)
            
            # Mettre à jour l'humeur de l'agent (drift identitaire)
            engine._update_mood_state(agent_state, action_type)
            
            # Sauvegarder l'état mis à jour
            CognitiveMemoryService.save_agent_state(simulation_id, agent_state)
            
            # Enregistrer comme fragment de mémoire autobiographique
            CognitiveMemoryService.add_memory_fragment(simulation_id, agent_str_id, event_desc, emotional_charge=0.5)
            
            # Vieillissement (decay) et oubli sélectif des souvenirs de cet agent
            CognitiveMemoryService.apply_memory_decay(simulation_id, agent_str_id)
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour post-action de l'agent {agent_id}: {e}")


async def fetch_and_update_cognitive_states(
    db_path: str,
    last_rowid: int,
    config: Dict[str, Any],
    round_num: int,
    agent_names: Dict[int, str]
) -> int:
    """
    Lit les nouvelles actions depuis la base de données SQLite de simulation,
    et déclenche la mise à jour cognitive correspondante.
    
    Retourne le nouveau last_rowid mis à jour.
    """
    if not os.path.exists(db_path):
        return last_rowid
        
    actual_actions = []
    new_last_rowid = last_rowid
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT rowid, user_id, action, info
            FROM trace
            WHERE rowid > ?
            ORDER BY rowid ASC
        """, (last_rowid,))
        
        for rowid, user_id, action, info_json in cursor.fetchall():
            new_last_rowid = rowid
            if action in FILTERED_ACTIONS:
                continue
                
            try:
                action_args = json.loads(info_json) if info_json else {}
            except json.JSONDecodeError:
                action_args = {}
                
            action_type = ACTION_TYPE_MAP.get(action, action.upper())
            actual_actions.append({
                'agent_id': user_id,
                'agent_name': agent_names.get(user_id, f'Agent_{user_id}'),
                'action_type': action_type,
                'action_args': action_args
            })
            
        conn.close()
        
        if actual_actions:
            await update_cognitive_states(actual_actions, config, round_num)
            
    except Exception as e:
        logger.error(f"Erreur lors de la lecture SQLite pour mise à jour cognitive: {e}")
        
    return new_last_rowid
