"""
Moteur de Simulation Juridique Principal
Orchestre l'Instruction, le Débat, et le Délibéré sur 50 itérations.
"""

import os
import sys
import json
import random
import logging
from datetime import datetime

# Ajouter le backend_dir pour les imports
_scripts_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.abspath(os.path.join(_scripts_dir, '..'))
sys.path.insert(0, _backend_dir)

from openai import OpenAI
from app.config import Config
from app.models.legal_agents import LegalAgents
from app.services.jurisprudence_grounding import JurisprudenceGrounding

logger = logging.getLogger('mirofish.run_legal_simulation')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class LegalSimulationRunner:
    def __init__(self, context: str, iterations: int = 50, litigation_type: str = "civil", judge_type: str = "single", selected_judge_personality: str = None, selected_judges_personalities: list = None):
        self.context = context
        self.iterations = iterations
        self.litigation_type = litigation_type
        self.grounding = JurisprudenceGrounding()
        self.judge_type = judge_type
        self.selected_judge_personality = selected_judge_personality
        self.selected_judges_personalities = selected_judges_personalities or []
        
        # Initialisation du client OpenAI pour les appels LLM (compatible LLM Local)
        api_key = Config.LLM_API_KEY or "local-no-key"
        base_url = Config.LLM_BASE_URL
        self.model_name = getattr(Config, 'LLM_MODEL_NAME', 'gpt-4o-mini')
        
        if base_url:
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self.client = OpenAI(api_key=api_key)
            
        self.processed_stimuli_count = context.count("[STIMULUS")
        self.judge_personality = None

    def filter_context(self, context: str, role: str) -> str:
        if not context:
            return ""
        lines = context.splitlines()
        filtered_lines = []
        for line in lines:
            if role == "defense":
                filtered_lines.append(line)
            elif role == "prosecutor":
                if "[STRATÉGIE EN DIRECT - AVOCAT]" not in line:
                    filtered_lines.append(line)
            elif role == "judge":
                if "[STRATÉGIE EN DIRECT - AVOCAT]" not in line and "[NÉGOCIATION EN DIRECT - ADVERSAIRE]" not in line:
                    filtered_lines.append(line)
            else:
                filtered_lines.append(line)
        return "\n".join(filtered_lines)

    def _call_llm(self, system_prompt: str, messages_history: list) -> str:
        messages = [{"role": "system", "content": system_prompt}] + messages_history
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Erreur d'appel LLM: {e}")
            return "Erreur technique, je passe mon tour."

    def run_single_simulation(self, iter_id: int, on_action_callback=None):
        # 1. Sélection aléatoire ou persistance d'une personnalité pour le juge
        if not getattr(self, 'judge_personality', None):
            if self.judge_type == "custom" and self.selected_judge_personality:
                self.judge_personality = self.selected_judge_personality
            elif self.judge_type == "collegiate":
                self.judge_personality = "Tribunal Collégial"
            elif self.selected_judge_personality:
                self.judge_personality = self.selected_judge_personality
            else:
                personalities = LegalAgents.get_judge_personalities()
                self.judge_personality = random.choice(personalities)
        current_personality = self.judge_personality
        logger.info(f"--- Itération {iter_id} | Juge: {current_personality} ---")
        
        agent1_name = "Le Procureur" if self.litigation_type == "criminal" else "Avocat du Demandeur"
        
        transcript = []
        debate_history_prosecutor = [
            {"role": "user", "content": f"Veuillez présenter votre réquisitoire initial et vos arguments principaux contre la défense en vous basant sur les faits du dossier."}
        ]
        debate_history_defense = []
        
        # 2. Phase de Débat (De base 2 tours, +1 tour de réplique si un stimulus est injecté)
        tour = 0
        max_tours = 2
        stimuli_checked_this_round = False
        
        while tour < max_tours:
            logger.info(f"Tour {tour+1}/{max_tours}...")
            
            # Détection de stimulus pour ajouter un round de réplique
            current_stimuli_count = self.context.count("[STIMULUS")
            if current_stimuli_count > self.processed_stimuli_count and not stimuli_checked_this_round:
                max_tours += 1
                self.processed_stimuli_count = current_stimuli_count
                stimuli_checked_this_round = True
                logger.info(f"Nouveau stimulus détecté au Tour {tour+1}. Ajout d'un tour de réplique supplémentaire (nouveau total : {max_tours}).")
                if on_action_callback:
                    on_action_callback("STIMULUS", "Système (Alerte)", 0, f"📢 Fait nouveau ou stimulus détecté à l'audience. Le tribunal autorise un tour de réplique supplémentaire.")
            
            # Procureur
            prosecutor_sys = LegalAgents.get_prosecutor_prompt(self.filter_context(self.context, "prosecutor"), self.litigation_type)
            msg_proc = self._call_llm(prosecutor_sys, debate_history_prosecutor)
            
            # Vérification Grounding Procureur avec boucle de régénération
            for attempt in range(3):
                check_proc = self.grounding.verify_argument(msg_proc, role="prosecutor", context=self.context, litigation_type=self.litigation_type)
                if not check_proc["is_hallucination"]:
                    break
                logger.info(f"Procureur Hallucination détectée (Essai {attempt+1}/3). Régénération en cours...")
                correction_prompt = (
                    f"ATTENTION : Votre plaidoyer précédent contenait une hallucination juridique ou une citation erronée.\n"
                    f"Erreur/Objection : {check_proc['objection_message']}\n"
                    f"Veuillez reformuler entièrement votre intervention. Assurez-vous d'utiliser uniquement "
                    f"des arrêts canadiens réels ou le code de loi approprié. "
                    f"Ne confondez pas le Code civil du Québec (C.c.Q.) avec des infractions de droit criminel."
                )
                retry_history = debate_history_prosecutor + [
                    {"role": "assistant", "content": msg_proc},
                    {"role": "user", "content": correction_prompt}
                ]
                msg_proc = self._call_llm(prosecutor_sys, retry_history)
            
            # Post-traitement final après les tentatives de correction
            check_proc = self.grounding.verify_argument(msg_proc, role="prosecutor", context=self.context, litigation_type=self.litigation_type)
            if check_proc["is_hallucination"]:
                if on_action_callback:
                    on_action_callback("STIMULUS", "Système (Alerte)", 0, f"⚠️ Erreur de Grounding : Hallucination de jurisprudence détectée pour {agent1_name}. Nettoyage automatique activé.")
                logger.warning(f"Procureur : Hallucination persistante détectée. Nettoyage du plaidoyer par le système.")
                clean_sys = (
                    "Tu es un assistant de réécriture juridique de Lexior.\n"
                    "Récris le plaidoyer suivant en retirant TOUTE citation d'article de loi, de code civil, de code criminel ou d'arrêt de jurisprudence.\n"
                    "Conserve intacts le sens, le ton et les arguments factuels ou techniques. Ne fais aucune mention d'articles ou de décisions de justice précis (ex: 'article 1726', 'arrêt R. c. X', 'Code civil')."
                )
                msg_proc = self._call_llm(clean_sys, [{"role": "user", "content": msg_proc}])
            else:
                refs = check_proc.get("found_references", [])
                if refs:
                    msg_proc += "\n\n**Sources officielles et citations :**\n"
                    for r in refs:
                        msg_proc += f"- **[{r['law_name']}]({r['url']})** (Citation: `{r['citation']}`)\n"
                        if r.get("summary"):
                            desc = r['summary'].replace('\n', '\n  ')
                            msg_proc += f"  *Description :* {desc}\n"
                
            transcript.append(f"PROCUREUR: {msg_proc}")
            if on_action_callback:
                on_action_callback("SPEECH_PROSECUTOR", agent1_name, 1, msg_proc)
                
            debate_history_prosecutor.append({"role": "assistant", "content": msg_proc})
            debate_history_defense.append({"role": "user", "content": f"{agent1_name} dit: {msg_proc}"})
            
            # Défense
            defense_sys = LegalAgents.get_defense_lawyer_prompt(self.filter_context(self.context, "defense"), self.litigation_type)
            msg_def = self._call_llm(defense_sys, debate_history_defense)
            
            # Vérification Grounding Défense avec boucle de régénération
            for attempt in range(3):
                check_def = self.grounding.verify_argument(msg_def, role="defense", context=self.context, litigation_type=self.litigation_type)
                if not check_def["is_hallucination"]:
                    break
                logger.info(f"Défense Hallucination détectée (Essai {attempt+1}/3). Régénération en cours...")
                correction_prompt = (
                    f"ATTENTION : Votre plaidoyer précédent contenait une hallucination juridique ou une citation erronée.\n"
                    f"Erreur/Objection : {check_def['objection_message']}\n"
                    f"Veuillez reformuler entièrement votre intervention. Assurez-vous d'utiliser uniquement "
                    f"des arrêts canadiens réels ou le code de loi approprié. "
                    f"Ne confondez pas le Code civil du Québec (C.c.Q.) avec des infractions de droit criminel."
                )
                retry_history = debate_history_defense + [
                    {"role": "assistant", "content": msg_def},
                    {"role": "user", "content": correction_prompt}
                ]
                msg_def = self._call_llm(defense_sys, retry_history)
                
            # Post-traitement final après les tentatives de correction
            check_def = self.grounding.verify_argument(msg_def, role="defense", context=self.context, litigation_type=self.litigation_type)
            if check_def["is_hallucination"]:
                if on_action_callback:
                    on_action_callback("STIMULUS", "Système (Alerte)", 0, "⚠️ Erreur de Grounding : Hallucination de jurisprudence détectée pour Avocat de la Défense. Nettoyage automatique activé.")
                logger.warning("Défense : Hallucination persistante détectée. Nettoyage du plaidoyer par le système.")
                clean_sys = (
                    "Tu es un assistant de réécriture juridique de Lexior.\n"
                    "Récris le plaidoyer suivant en retirant TOUTE citation d'article de loi, de code civil, de code criminel ou d'arrêt de jurisprudence.\n"
                    "Conserve intacts le sens, le ton et les arguments factuels ou techniques. Ne fais aucune mention d'articles ou de décisions de justice précis (ex: 'article 1726', 'arrêt R. c. X', 'Code civil')."
                )
                msg_def = self._call_llm(clean_sys, [{"role": "user", "content": msg_def}])
            else:
                refs = check_def.get("found_references", [])
                if refs:
                    msg_def += "\n\n**Sources officielles et citations :**\n"
                    for r in refs:
                        msg_def += f"- **[{r['law_name']}]({r['url']})** (Citation: `{r['citation']}`)\n"
                        if r.get("summary"):
                            desc = r['summary'].replace('\n', '\n  ')
                            msg_def += f"  *Description :* {desc}\n"
                
            transcript.append(f"DEFENSE: {msg_def}")
            if on_action_callback:
                on_action_callback("SPEECH_DEFENSE", "Avocat de la Défense", 2, msg_def)
                
            debate_history_defense.append({"role": "assistant", "content": msg_def})
            debate_history_prosecutor.append({"role": "user", "content": f"La Défense dit: {msg_def}"})
            
            tour += 1
 
        # 3. Phase de Délibéré
        import re
        
        def evaluate_verdict(verdict_text: str) -> bool:
            verdict_upper = verdict_text.upper()
            if self.litigation_type == "civil":
                has_responsible = "RESPONSABLE" in verdict_upper and not re.search(r'\bNON[- ]+RESPONSABLE\b', verdict_upper)
                has_condemnation = any(k in verdict_upper for k in ["CONDAMNE", "CONDAMNER"])
                if has_responsible or has_condemnation:
                    return False
                return any(k in verdict_upper for k in ["NON RESPONSABLE", "NON-RESPONSABLE", "REJETTE", "REJET", "DEBOUTE", "REFUSE", "SANS FONDEMENT"])
            else:
                has_guilty = "COUPABLE" in verdict_upper and not re.search(r'\bNON[- ]+COUPABLE\b', verdict_upper)
                has_condemnation = False
                if "CONDAMNE" in verdict_upper or "CONDAMNER" in verdict_upper:
                    if re.search(r'CONDAMNE(R)?\s+(?:[^.!?]*)(?:APEX|DÉFENDEUR|DÉFENDERESSE)', verdict_upper):
                        has_condemnation = True
                if has_guilty or has_condemnation:
                    return False
                return any(k in verdict_upper for k in ["NON COUPABLE", "RELAXE", "ACQUITTEMENT", "ACQUITTE", "NON-COUPABLE", "REJETTE", "REFUSE"])

        if self.judge_type == "collegiate":
            logger.info("Délibéré du Tribunal Collégial (3 Juges)...")
            judges_list = self.selected_judges_personalities if self.selected_judges_personalities else [
                "Formaliste strict (applique la loi à la lettre sans pitié).",
                "Sensible à l'équité (prend en compte les circonstances atténuantes et le contexte social).",
                "Conservateur (favorise souvent l'accusation et l'ordre public)."
            ]
            collegiate_results = []
            for idx, j_pers in enumerate(judges_list):
                logger.info(f"Délibération du Juge {idx+1} ({j_pers})...")
                judge_sys = LegalAgents.get_judge_prompt(self.filter_context(self.context, "judge"), j_pers, self.litigation_type)
                judge_history = [{"role": "user", "content": "Voici la transcription du débat:\n" + "\n".join(transcript) + "\n\nQuel est votre verdict ?"}]
                verdict_j = self._call_llm(judge_sys, judge_history)
                is_win_j = evaluate_verdict(verdict_j)
                collegiate_results.append({
                    "personality": j_pers,
                    "verdict": verdict_j,
                    "is_defense_win": is_win_j
                })
            
            wins_count = sum(1 for r in collegiate_results if r["is_defense_win"])
            is_defense_win = wins_count >= 2
            consensus_label = "Défense (Majorité)" if is_defense_win else (
                "Poursuite (Majorité)" if self.litigation_type == "criminal" else "Demandeur (Majorité)"
            )
            
            combined_verdict = f"[DÉCISION COLLÉGIALE - CONSENSUS : {consensus_label} ({wins_count}/3)]\n\n"
            for idx, r in enumerate(collegiate_results):
                j_name = r["personality"].split('(')[0].strip()
                combined_verdict += f"- Juge {idx+1} ({j_name}) : {r['verdict']}\n\n"
            
            verdict = combined_verdict
            transcript.append(f"JUGE: {verdict}")
            if on_action_callback:
                on_action_callback("VERDICT", "Le Tribunal Collégial", 0, verdict, result=verdict)
        else:
            logger.info("Délibéré du juge...")
            judge_sys = LegalAgents.get_judge_prompt(self.filter_context(self.context, "judge"), current_personality, self.litigation_type)
            judge_history = [{"role": "user", "content": "Voici la transcription du débat:\n" + "\n".join(transcript) + "\n\nQuel est votre verdict ?"}]
            verdict = self._call_llm(judge_sys, judge_history)
            transcript.append(f"JUGE: {verdict}")
            is_defense_win = evaluate_verdict(verdict)
            if on_action_callback:
                on_action_callback("VERDICT", "Le Juge", 0, verdict, result=verdict)
        
        # 4. Phase de Greffier (Analyste)
        clerk_sys = LegalAgents.get_clerk_prompt(self.litigation_type)
        clerk_history = [{"role": "user", "content": "Analyse du verdict et des arguments décisifs:\n" + "\n".join(transcript)}]
        clerk_analysis = self._call_llm(clerk_sys, clerk_history)
        if on_action_callback:
            on_action_callback("CLERK_ANALYSIS", "Le Greffier", 4, clerk_analysis, result="Analysis completed")
        
        return {
            "iteration": iter_id,
            "judge_personality": current_personality,
            "is_defense_win": is_defense_win,
            "transcript": transcript,
            "clerk_analysis": clerk_analysis,
            "verdict": verdict
        }

    def run_full_simulation(self):
        logger.info(f"Démarrage des {self.iterations} simulations de Monte-Carlo juridiques...")
        results = []
        defense_wins = 0
        
        for i in range(1, self.iterations + 1):
            res = self.run_single_simulation(i)
            results.append(res)
            if res["is_defense_win"]:
                defense_wins += 1
                
        win_rate = (defense_wins / self.iterations) * 100
        logger.info(f"FIN DE LA SIMULATION : La défense a gagné {defense_wins} fois sur {self.iterations} ({win_rate}% de succès).")
        
        # Sauvegarde des résultats
        output_dir = os.path.join(_backend_dir, 'uploads', 'legal_simulations')
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(output_dir, f"sim_{timestamp}.json")
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                "context": self.context,
                "iterations": self.iterations,
                "litigation_type": self.litigation_type,
                "win_rate": win_rate,
                "defense_wins": defense_wins,
                "details": results
            }, f, ensure_ascii=False, indent=2)
            
        return filename

if __name__ == "__main__":
    test_context = "Accusé de vol d'une bicyclette devant un supermarché. Preuves vidéo floues, l'accusé nie les faits et prétendait être chez sa mère."
    # On met 2 iterations pour les tests rapides
    runner = LegalSimulationRunner(context=test_context, iterations=2)
    outfile = runner.run_full_simulation()
    print(f"Simulation terminée. Résultats enregistrés dans {outfile}")
