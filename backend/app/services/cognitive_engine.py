"""
Probabilistic Identity Engine (PIE) / Cognitive Engine
Gère l'intériorité dynamique des agents : tensions, croyances et arbitrage multi-perspectives.
"""

import os
import json
import logging
import random
from typing import Dict, Any, List, Optional
from openai import OpenAI
from ..config import Config

logger = logging.getLogger('mirofish.cognitive_engine')

class CognitiveAgentState:
    """Représente l'état mental dynamique d'un agent cognitif."""
    def __init__(
        self,
        agent_id: str,
        name: str,
        personality: str = "",
        tensions: Dict[str, float] = None,
        beliefs: Dict[str, Dict[str, float]] = None,
        meta_narrative: str = "",
        recent_reflection: str = "",
        mood: str = "Neutre",
        negative_interactions_count: int = 0,
        attention_budget: Dict[str, float] = None
    ):
        self.agent_id = agent_id
        self.name = name
        self.personality = personality
        
        # Tensions cognitives par défaut (0.0 à 1.0)
        default_tensions = {
            "exploration_vs_security": 0.5,
            "cooperation_vs_domination": 0.5,
            "truth_vs_social_survival": 0.5,
            "prudence_vs_rapidite": 0.5,
            "offensive_vs_negociation": 0.5,
            "procedure_vs_equite": 0.5
        }
        if tensions:
            default_tensions.update(tensions)
        self.tensions = default_tensions
        
        # Croyances sous forme de superposition probabiliste (somme = 1.0)
        default_beliefs = {
            "general_trust": {"high": 0.33, "medium": 0.34, "low": 0.33}
        }
        if beliefs:
            if "culpabilite_accuse" in beliefs:
                default_beliefs = {}
            default_beliefs.update(beliefs)
        self.beliefs = default_beliefs
        
        self.meta_narrative = meta_narrative
        self.recent_reflection = recent_reflection
        
        # Nouvelles propriétés d'état PIE
        self.mood = mood
        self.negative_interactions_count = negative_interactions_count
        self.attention_budget = attention_budget or {
            "social": 0.4,
            "introspection": 0.2,
            "risk": 0.2,
            "long_term": 0.2
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "personality": self.personality,
            "tensions": self.tensions,
            "beliefs": self.beliefs,
            "meta_narrative": self.meta_narrative,
            "recent_reflection": self.recent_reflection,
            "mood": self.mood,
            "negative_interactions_count": self.negative_interactions_count,
            "attention_budget": self.attention_budget
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CognitiveAgentState':
        return cls(
            agent_id=data.get("agent_id", ""),
            name=data.get("name", ""),
            personality=data.get("personality", ""),
            tensions=data.get("tensions"),
            beliefs=data.get("beliefs"),
            meta_narrative=data.get("meta_narrative", ""),
            recent_reflection=data.get("recent_reflection", ""),
            mood=data.get("mood", "Neutre"),
            negative_interactions_count=data.get("negative_interactions_count", 0),
            attention_budget=data.get("attention_budget")
        )


class CognitiveEngine:
    """Moteur cognitive gérant l'arbitrage interne et l'auto-narration."""
    
    def __init__(self, model_name: Optional[str] = None, base_url: Optional[str] = None, api_key: Optional[str] = None):
        # Possibilité de forcer un modèle local via Ollama ou d'utiliser le modèle global configuré
        self.base_url = base_url or Config.LLM_BASE_URL
        self.api_key = api_key or Config.LLM_API_KEY or "local"
        self.model = model_name or Config.LLM_MODEL_NAME
        
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            max_retries=2
        )

    def _call_llm(self, system_prompt: str, user_prompt: str, response_format: str = "text") -> str:
        """Méthode helper pour appeler le LLM configuré."""
        try:
            extra_args = {}
            if response_format == "json":
                # Certains modèles locaux ne supportent pas response_format={"type": "json_object"}
                # On force le format dans le prompt et on essaie de nettoyer la sortie.
                pass

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                **extra_args
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Erreur d'appel LLM dans CognitiveEngine: {e}")
            raise e

    async def run_cognitive_cycle(
        self,
        agent_state: CognitiveAgentState,
        environment_stimulus: str,
        memories: List[str],
        simulation_type: str = "social"
    ) -> Dict[str, Any]:
        """
        Exécute le cycle complet pour un round :
        1. Mixture of Perspectives (Analyste, Créatif, Protecteur)
        2. Arbitrage des tensions
        3. Mise à jour probabiliste des croyances
        4. Métacognition et Auto-narration
        5. Drift identitaire et plasticité
        """
        logger.info(f"Exécution du cycle cognitif pour l'agent {agent_state.name} ({agent_state.agent_id})")
        
        memory_context = "\n".join([f"- {m}" for m in memories]) if memories else "Aucun souvenir marquant."
        
        # 1. Mixture of Perspectives : générer 3 voix internes
        proposals = await self._generate_perspectives(agent_state, environment_stimulus, memory_context, simulation_type)
        
        # 2. Arbitrage selon les tensions de l'agent
        decision = await self._arbitrate_decision(agent_state, proposals, environment_stimulus, simulation_type)
        
        # 3. Évolution bayésienne/probabiliste des croyances
        updated_beliefs = self._update_beliefs_bayesian(agent_state, environment_stimulus, decision["action"])
        agent_state.beliefs = updated_beliefs
        
        # 4. Métacognition et Auto-narration (mise à jour de l'état)
        meta = await self._generate_metacognition(agent_state, environment_stimulus, decision["action"], decision["reasoning"], simulation_type)
        agent_state.meta_narrative = meta["meta_narrative"]
        agent_state.recent_reflection = meta["recent_reflection"]
        
        # 5. Ajuster légèrement les tensions selon la décision prise (effet de plasticité cognitive)
        self._update_tensions_plasticity(agent_state, decision["tension_used"])
        
        # 6. Mettre à jour l'humeur de l'agent (drift identitaire)
        self._update_mood_state(agent_state, decision["action"])
        
        return {
            "action": decision["action"],
            "reasoning": decision["reasoning"],
            "state": agent_state.to_dict()
        }

    async def _generate_perspectives(
        self,
        state: CognitiveAgentState,
        stimulus: str,
        memory_context: str,
        simulation_type: str = "social"
    ) -> Dict[str, Dict[str, Any]]:
        """Génère 3 propositions d'actions selon 3 facettes psychologiques."""
        
        if simulation_type == "legal":
            tensions_text = f"""- Prudence vs Rapidité : {state.tensions.get('prudence_vs_rapidite', 0.5):.2f}
- Offensive vs Négociation : {state.tensions.get('offensive_vs_negociation', 0.5):.2f}
- Procédure vs Équité : {state.tensions.get('procedure_vs_equite', 0.5):.2f}"""
        else:
            tensions_text = f"""- Exploration vs Sécurité : {state.tensions.get('exploration_vs_security', 0.5):.2f}
- Coopération vs Domination : {state.tensions.get('cooperation_vs_domination', 0.5):.2f}
- Vérité vs Survie Sociale : {state.tensions.get('truth_vs_social_survival', 0.5):.2f}"""

        system_prompt = f"""Tu es la conscience interne divisée de l'agent "{state.name}".
Voici son humeur actuelle : {state.mood}
Voici son profil de tensions courantes :
{tensions_text}

Voici sa mémoire résumée :
{memory_context}

Tu dois simuler séparément 3 facettes de sa psychologie :
1. L'Analyste (Pragmatique, logique, orienté données objectives).
2. L'Émotif/Créatif (Réaction passionnée, intuitive, artistique ou impulsive).
3. Le Protecteur (Orienté sécurité, survie sociale, évitement de conflits).

Pour le stimulus reçu, écris la réaction interne et la proposition d'action de chacune des 3 facettes.
Retourne STRICTEMENT un objet JSON sous cette forme :
{{
  "analyst": {{"thought": "Pensée logique...", "action": "Action proposée..."}},
  "creative": {{"thought": "Pensée intuitive...", "action": "Action proposée..."}},
  "protector": {{"thought": "Pensée de préservation...", "action": "Action proposée..."}}
}}
"""
        user_prompt = f"STIMULUS DE L'ENVIRONNEMENT :\n{stimulus}"
        
        raw_res = self._call_llm(system_prompt, user_prompt)
        
        # Nettoyage JSON
        if raw_res.startswith("```json"):
            raw_res = raw_res[7:]
        if raw_res.startswith("```"):
            raw_res = raw_res[3:]
        if raw_res.endswith("```"):
            raw_res = raw_res[:-3]
            
        try:
            return json.loads(raw_res.strip())
        except Exception as e:
            logger.warning(f"Erreur de parsing des perspectives, fallback par défaut : {e}")
            # Fallback simple en cas d'erreur de format JSON
            return {
                "analyst": {"thought": "Analyse logique de la situation.", "action": "DO_NOTHING"},
                "creative": {"thought": "Envie de s'exprimer librement.", "action": "CREATE_POST"},
                "protector": {"thought": "Mieux vaut rester discret.", "action": "DO_NOTHING"}
            }

    async def _arbitrate_decision(
        self,
        state: CognitiveAgentState,
        proposals: Dict[str, Dict[str, Any]],
        stimulus: str,
        simulation_type: str = "social"
    ) -> Dict[str, Any]:
        """Arbitre entre les 3 propositions en fonction des tensions de l'agent."""
        
        # Traduction des tensions en poids d'arbitrage
        if simulation_type == "legal":
            exp_weight = state.tensions.get("prudence_vs_rapidite", 0.5) # rapidité
            security_weight = 1.0 - exp_weight # prudence
        else:
            exp_weight = state.tensions.get("exploration_vs_security", 0.5)
            security_weight = 1.0 - exp_weight
        
        # Ajustement des poids en fonction de l'humeur (drift identitaire)
        if state.mood == "Paranoïaque":
            security_weight = min(1.0, security_weight + 0.2)
            exp_weight = max(0.0, exp_weight - 0.2)
        elif state.mood == "Isolé":
            security_weight = min(1.0, security_weight + 0.4)
            exp_weight = max(0.0, exp_weight - 0.4)
        elif state.mood == "Coopératif":
            exp_weight = min(1.0, exp_weight + 0.1)
            security_weight = max(0.0, security_weight - 0.1)
            
        if simulation_type == "legal":
            tensions_text = f"""- Prudence/Sécurité (Poids: {security_weight:.2f}) vs Rapidité/Action (Poids: {exp_weight:.2f})
- Offensive vs Négociation : {state.tensions.get('offensive_vs_negociation', 0.5):.2f}
- Procédure vs Équité : {state.tensions.get('procedure_vs_equite', 0.5):.2f}"""
            fallback_tension = "prudence_vs_rapidite"
        else:
            tensions_text = f"""- Exploration/Créativité (Poids: {exp_weight:.2f}) vs Sécurité/Protection (Poids: {security_weight:.2f})
- Coopération vs Domination : {state.tensions.get('cooperation_vs_domination', 0.5):.2f}
- Vérité vs Survie Sociale : {state.tensions.get('truth_vs_social_survival', 0.5):.2f}"""
            fallback_tension = "exploration_vs_security"
            
        system_prompt = f"""Tu es le Moteur d'Arbitrage Cognitif (PIE) de l'agent "{state.name}".
Ta mission est de choisir la meilleure action finale parmi les propositions de ses voix internes en fonction de ses tensions courantes et de son humeur.

HUMEUR ACTUELLE : {state.mood}

TENSIONS COURANTES (AJUSTÉES PAR SON HUMEUR) :
{tensions_text}

PROPOSITIONS INTERNES :
1. L'Analyste :
   - Pensée : {proposals.get('analyst', {}).get('thought')}
   - Action : {proposals.get('analyst', {}).get('action')}
2. L'Émotif/Créatif :
   - Pensée : {proposals.get('creative', {}).get('thought')}
   - Action : {proposals.get('creative', {}).get('action')}
3. Le Protecteur :
   - Pensée : {proposals.get('protector', {}).get('thought')}
   - Action : {proposals.get('protector', {}).get('action')}

Prends une décision finale. L'action doit être valide (par exemple : CREATE_POST, LIKE_POST, FOLLOW, DO_NOTHING ou CREATE_COMMENT).
Retourne STRICTEMENT un objet JSON de cette forme :
{{
  "action": "ACTION_FINALE",
  "reasoning": "Explication synthétique du choix montrant comment les tensions ont été résolues.",
  "tension_used": "exploration_vs_security"
}}
"""
        user_prompt = f"STIMULUS :\n{stimulus}"
        
        raw_res = self._call_llm(system_prompt, user_prompt)
        
        if raw_res.startswith("```json"):
            raw_res = raw_res[7:]
        if raw_res.startswith("```"):
            raw_res = raw_res[3:]
        if raw_res.endswith("```"):
            raw_res = raw_res[:-3]
            
        try:
            return json.loads(raw_res.strip())
        except Exception:
            # Fallback
            return {
                "action": proposals.get("analyst", {}).get("action", "DO_NOTHING"),
                "reasoning": "Décision de compromis par l'analyste.",
                "tension_used": fallback_tension
            }

    def _update_beliefs_bayesian(
        self,
        state: CognitiveAgentState,
        stimulus: str,
        action: str
    ) -> Dict[str, Dict[str, float]]:
        """
        Met à jour de manière pseudo-bayésienne les distributions de croyances de l'agent.
        En fonction du stimulus et de l'action choisie, la confiance glisse.
        """
        updated = {}
        for belief_key, distribution in state.beliefs.items():
            # distribution = {"high": 0.33, "medium": 0.34, "low": 0.33}
            # Simulation d'un impact bayésien simple :
            # Si l'action est affirmative (ex: CREATE_POST/LIKE_POST) et que le social_survival est haut,
            # on augmente la croyance positive.
            impact = 0.0
            if "trust" in belief_key:
                if action in ["CREATE_POST", "LIKE_POST", "FOLLOW"]:
                    impact = 0.05
                elif action in ["DISLIKE_POST", "MUTE"]:
                    impact = -0.05
            
            # Appliquer le décalage et renormaliser
            new_dist = {}
            total = 0.0
            for k, val in distribution.items():
                if k == "high" or k == "yes" or k == "true":
                    new_val = max(0.01, val + impact)
                elif k == "low" or k == "no" or k == "false":
                    new_val = max(0.01, val - impact)
                else:
                    new_val = val
                new_dist[k] = new_val
                total += new_val
            
            # Renormalisation
            renormalized = {k: round(v / total, 2) for k, v in new_dist.items()}
            # S'assurer que la somme fait exactement 1.0
            diff = 1.0 - sum(renormalized.values())
            if diff != 0:
                first_key = list(renormalized.keys())[0]
                renormalized[first_key] = round(renormalized[first_key] + diff, 2)
                
            updated[belief_key] = renormalized
            
        return updated

    async def _generate_metacognition(
        self,
        state: CognitiveAgentState,
        stimulus: str,
        action: str,
        reasoning: str,
        simulation_type: str = "social"
    ) -> Dict[str, str]:
        """Génère l'auto-narration (le récit interne) et la réflexion métacognitive de l'agent."""
        
        if simulation_type == "legal":
            tensions_val = {
                "prudence_vs_rapidite": state.tensions.get("prudence_vs_rapidite", 0.5),
                "offensive_vs_negociation": state.tensions.get("offensive_vs_negociation", 0.5),
                "procedure_vs_equite": state.tensions.get("procedure_vs_equite", 0.5)
            }
        else:
            tensions_val = {
                "exploration_vs_security": state.tensions.get("exploration_vs_security", 0.5),
                "cooperation_vs_domination": state.tensions.get("cooperation_vs_domination", 0.5),
                "truth_vs_social_survival": state.tensions.get("truth_vs_social_survival", 0.5)
            }
            
        system_prompt = f"""Tu es la voix métacognitive introspective de l'agent "{state.name}".
Ton travail est de rédiger un court journal intime interne décrivant l'état psychologique de l'agent suite à sa décision.

DÉCISION PRISE : {action}
RAISONNEMENT : {reasoning}
HUMEUR ACTUELLE : {state.mood}
TENSIONS COURANTES : {tensions_val}

Rédige :
1. "meta_narrative" : Une réflexion globale à la première personne du singulier sur l'évolution de son identité et sa perception du monde (max 2 phrases).
2. "recent_reflection" : Une note d'auto-analyse sur pourquoi il a agi ainsi face au stimulus (max 1 phrase).

Retourne STRICTEMENT un objet JSON :
{{
  "meta_narrative": "Je commence à me rendre compte que...",
  "recent_reflection": "J'ai agi par prudence car..."
}}
"""
        user_prompt = f"STIMULUS REÇU :\n{stimulus}"
        
        raw_res = self._call_llm(system_prompt, user_prompt)
        
        if raw_res.startswith("```json"):
            raw_res = raw_res[7:]
        if raw_res.startswith("```"):
            raw_res = raw_res[3:]
        if raw_res.endswith("```"):
            raw_res = raw_res[:-3]
            
        try:
            return json.loads(raw_res.strip())
        except Exception:
            return {
                "meta_narrative": f"Je continue à naviguer dans cet environnement complexe en restant fidèle à mes valeurs de {state.name}.",
                "recent_reflection": f"J'ai pris la décision d'effectuer l'action {action} pour répondre aux sollicitations."
            }

    def _update_tensions_plasticity(self, state: CognitiveAgentState, tension_used: str):
        """Ajuste légèrement les tensions de l'agent après une décision (plasticité cognitive)."""
        # Si une tension a été fortement mobilisée, elle dévie légèrement (±0.02)
        if tension_used in state.tensions:
            # Petite déviation aléatoire pour simuler l'adaptation ou la fatigue psychologique
            drift = random.choice([-0.02, 0.02])
            state.tensions[tension_used] = max(0.05, min(0.95, state.tensions[tension_used] + drift))

    def _update_mood_state(self, state: CognitiveAgentState, action: str):
        """Met à jour l'humeur de l'agent en fonction de son action (drift identitaire)."""
        # Actions hostiles ou d'évitement
        hostile_actions = {"MUTE", "DISLIKE_POST", "DISLIKE_COMMENT", "DO_NOTHING"}
        social_actions = {"CREATE_POST", "CREATE_COMMENT", "LIKE_POST", "LIKE_COMMENT", "FOLLOW"}
        
        if action in hostile_actions:
            state.negative_interactions_count += 1
        elif action in social_actions:
            state.negative_interactions_count = max(0, state.negative_interactions_count - 1)
            
        # Machine d'états d'humeur
        if state.negative_interactions_count >= 3:
            state.mood = "Isolé"
        elif state.negative_interactions_count == 2:
            state.mood = "Paranoïaque"
        elif state.negative_interactions_count == 1:
            state.mood = "Méfiant"
        else:
            if action in ["LIKE_POST", "FOLLOW", "LIKE_COMMENT"]:
                state.mood = "Coopératif"
            else:
                state.mood = "Neutre"

    def generate_legal_courtroom_metacognition(
        self,
        agent_name: str,
        state: CognitiveAgentState,
        round_idx: int,
        prosecutor_speech: str,
        defense_speech: str,
        verdict: str,
        clerk_analysis: str,
        last_stim: str = None
    ) -> Dict[str, str]:
        """
        Génère de manière dynamique la continuité subjective (l'auto-narration et la réflexion métacognitive)
        d'un agent du procès (Juge, Procureur ou Avocat) en fin de round, en fonction des plaidoiries,
        du verdict, de l'analyse du greffier et d'éventuels stimuli injectés.
        """
        # Rôle de l'acteur descriptif dynamique
        role_desc_agent = ""
        if "Juge" in agent_name:
            role_desc_agent = "Le Juge : Impartial, à l'écoute des arguments juridiques et factuels, cherche à forger son intime conviction en pesant le doute raisonnable et les preuves de vice caché."
        elif "Demandeur" in agent_name or "Procureur" in agent_name:
            role_desc_agent = f"{agent_name} : Ferme, soutient la poursuite/l'accusation, veut démontrer le vice caché technique, l'inadéquation de la diligence raisonnable et réclame 10 millions de dollars."
        else:
            role_desc_agent = f"{agent_name} : Allié du client, combatif, cherche le doute raisonnable, insiste sur la diligence de l'acquéreur, la proportionnalité des dommages et l'absence de vice caché juridique."

        system_prompt = f"""Tu es la voix métacognitive introspective et le flux de conscience de l'acteur du procès "{agent_name}" (nommé "{state.name}").
Ton travail est de rédiger les pensées internes intimes, réalistes et sincères de cet acteur à la fin du round {round_idx} du procès.

Rôle de l'acteur :
- {role_desc_agent}

État cognitif actuel de l'acteur :
- Humeur : {state.mood}
- Tensions psychologiques actuelles :
  * Prudence vs Rapidité: {state.tensions.get('prudence_vs_rapidite', 0.5):.2f} (un taux élevé indique une prudence extrême dans les conclusions)
  * Offensive vs Négociation: {state.tensions.get('offensive_vs_negociation', 0.5):.2f} (un taux élevé indique une posture de combat sans concession, un taux faible indique une ouverture aux deals)
  * Procédure vs Équité: {state.tensions.get('procedure_vs_equite', 0.5):.2f} (un taux élevé indique un attachement strict à la lettre du contrat, un taux faible indique une recherche d'équité)
- Croyance actuelle en la culpabilité/responsabilité de la Défense (coupable vs innocent) : {state.beliefs.get('culpabilite_accuse', {})}

Directives d'écriture :
1. Rédige STRICTEMENT à la première personne du singulier ("Je", "Moi", "Mon").
2. Sois extrêmement réaliste, humain et contextuel. Évite les phrases répétitives et génériques. Tes pensées doivent refléter précisément ce qui s'est passé dans ce round.
3. Intègre ses doutes, sa posture par rapport à son humeur et ses tensions.
4. Reste professionnel mais exprime des réflexions sincères d'avocat/procureur/juge en train de vivre un procès de 10 millions de dollars.

Tu dois obligatoirement répondre sous la forme d'un objet JSON contenant exactement ces deux clés :
{{
  "meta_narrative": "Une réflexion globale à la première personne sur l'évolution de mon opinion, de ma stratégie ou de mon humeur face au déroulement de ce procès (max 2 phrases).",
  "recent_reflection": "Une auto-analyse précise à la première personne de ma réaction face aux derniers arguments, verdicts ou stimuli du round (max 1 phrase)."
}}
Assure-toi que la réponse est uniquement un objet JSON valide, sans formatage markdown de bloc de code (ne mets pas de ```json ou ```).
"""
        user_prompt = f"""DÉROULEMENT DU ROUND {round_idx} DU PROCÈS :
- Argumentations de l'Accusation (Procureur) : {prosecutor_speech or "Non spécifié"}
- Argumentations de la Défense : {defense_speech or "Non spécifié"}
- Verdict/Décision du Juge pour ce round : {verdict or "Délibérations en cours"}
- Analyse globale du Greffier : {clerk_analysis or "Non spécifiée"}
"""
        if last_stim:
            user_prompt += f"\n- Stimulus/Événement de dernière minute injecté dans le procès : {last_stim}\n"

        raw_res = self._call_llm(system_prompt, user_prompt)
        
        # Clean markdown formatting if any
        if raw_res.startswith("```json"):
            raw_res = raw_res[7:]
        if raw_res.startswith("```"):
            raw_res = raw_res[3:]
        if raw_res.endswith("```"):
            raw_res = raw_res[:-3]
            
        try:
            return json.loads(raw_res.strip())
        except Exception as e:
            logger.error(f"Failed to parse legal metacognition JSON: {e}. Raw content: {raw_res}")
            return {}

