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

import re as _re_mod


def evaluate_verdict_is_defense_win(verdict_text: str, litigation_type: str = "civil") -> bool:
    """
    Détermine de manière déterministe si un délibéré judiciaire donne gain de cause
    à la Défense (acquittement / rejet de la demande principale) ou au Demandeur / Poursuite.
    Ignore explicitement le rejet d'une demande reconventionnelle afin de ne jamais
    confondre « REJETTE la demande reconventionnelle des défendeurs » avec un rejet de l'action principale.
    """
    if not verdict_text:
        return False
    verdict_upper = verdict_text.upper()

    # Si c'est un verdict collégial combiné contenant les votes individuels (- Juge 1 ...), évaluer chaque juge
    judge_splits = _re_mod.split(r'(?:^|\n)\s*-\s*JUGE\s+\d+\s*\([^)]*\)\s*:\s*', verdict_upper)
    if len(judge_splits) >= 3:
        individual_verdicts = [s.strip() for s in judge_splits[1:] if s.strip()]
        wins = sum(1 for jv in individual_verdicts if evaluate_verdict_is_defense_win(jv, litigation_type))
        return wins >= (len(individual_verdicts) // 2 + 1)

    # Isoler le dispositif final s'il est présent (après PAR CES MOTIFS ou DISPOSITIF)
    dispositif_match = _re_mod.search(r'(?:PAR\s+CES\s+MOTIFS|DISPOSITIF\s+FINAL|4\.\s*DISPOSITIF|\bDISPOSITIF\b)', verdict_upper)
    target_zone = verdict_upper[dispositif_match.start():] if dispositif_match else verdict_upper

    # Retirer toute phrase ou clause portant sur la demande reconventionnelle ou sur les seuls dépens/frais de justice
    cleaned_main = _re_mod.sub(r'[^.!?\n]*DEMANDE\s+RECONVENTIONNELLE[^.!?\n]*', '', target_zone)
    cleaned_main = _re_mod.sub(r'[^.!?\n]*\bCONDAMNE\b[^.!?\n]*\bAUX\s+(?:DÉPENS|DEPENS|FRAIS\s+DE\s+JUSTICE)\b[^.!?\n]*', '', cleaned_main)

    # Si le dispositif mentionne explicitement un total des condamnations en capital de 0,00 $ ou accueille l'irrecevabilité de la défense -> Victoire Défense
    if _re_mod.search(r'TOTAL(?:E)?\s+DES\s+CONDAMNATIONS[^$\n]{0,40}?\b0(?:[.,]00)?\s*\$', cleaned_main):
        return True
    if _re_mod.search(r'\bACCUEILLE\b[^.!?\n]*\bMOYEN\s+D[\'’]IRRECEVABILIT', cleaned_main) or _re_mod.search(r'\bD[ÉE]CLARE\b[^.!?\n]*\bIRRECEVABLE\b', cleaned_main):
        return True

    # Détecter l'accueil de la demande principale ou la condamnation pécuniaire des défendeurs
    cleaned_no_irrec = _re_mod.sub(r'[^.!?\n]*\bMOYEN\s+D[\'’]IRRECEVABILIT[^.!?\n]*', '', cleaned_main)
    has_main_welcome = bool(_re_mod.search(r'\bACCUEILLE\b[^.!?\n]*(?:DEMANDE|ACTION|RECOURS|REQUÊTE)', cleaned_no_irrec))
    has_condemnation = bool(_re_mod.search(r'\bCONDAMNE(?:R|NT|S)?\b', cleaned_main))
    has_main_reject = bool(_re_mod.search(
        r'\b(?:REJETTE|DÉBOUTE|DEBOUTE)\b[^.!?\n]*(?:INTÉGRALEMENT\s+LA\s+DEMANDE|DEMANDE\s+PRINCIPALE|DEMANDE\s+DES\s+DEMANDEURS|ACTION\s+EN\s+RESPONSABILIT|ACTION\s+PRINCIPALE|RECOURS\s+DE\s+MONSIEUR|RECOURS\s+DE\s+MADAME|LES\s+R[ÉE]CLAMATIONS\s+DE)',
        cleaned_main
    ))
    if has_main_reject and not has_main_welcome and not has_condemnation:
        return True
    has_responsible = ("RESPONSABLE" in cleaned_main and not _re_mod.search(r'\bNON[- ]+RESPONSABLE\b', cleaned_main))
    has_guilty = ("COUPABLE" in cleaned_main and not _re_mod.search(r'\bNON[- ]+COUPABLE\b', cleaned_main))

    if has_main_welcome or has_condemnation or has_responsible or has_guilty:
        return False

    return any(
        k in cleaned_main
        for k in [
            "NON RESPONSABLE", "NON-RESPONSABLE",
            "NON COUPABLE", "NON-COUPABLE",
            "RELAXE", "ACQUITTEMENT", "ACQUITTE",
            "REJETTE", "REJET", "DÉBOUTE", "DEBOUTE", "REFUSE", "SANS FONDEMENT"
        ]
    )


def extract_max_claim_amount(context_text: str) -> float:
    """
    Extrait le montant total de la demande principale (plafond de l'ultra petita, art. 10 C.p.c.)
    à partir du contexte du dossier ou de la requête de simulation.
    """
    if not context_text:
        return 0.0

    def _parse_money(s: str) -> float:
        cleaned = s.replace(' ', '').replace('\u00a0', '').replace(',', '.')
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    # Retirer les mentions de demande reconventionnelle ou de prix de vente du Kit/contrat pour isoler la demande principale
    patterns = [
        r'(?:demande\s+principale(?:\s+totale)?\s+de|demande\s+totale\s*[:de]*|réclame(?:nt)?\s+au\s+total|réclamant\s+un\s+total\s+de|montant\s+total\s+de\s+la\s+demande\s+principale|condamner[^\n$]{0,90}?payer\s+la\s+somme\s+totale\s+de|total\s+réclamé\s*[:de]*)\s*(\d{1,3}(?:[\s\u00a0]\d{3})*(?:[.,]\d{2})?|\d+(?:[.,]\d{2}))\s*\$',
        r'(?:somme\s+totale\s+réclamée\s+de|réclamation\s+principale\s+de)\s*(\d{1,3}(?:[\s\u00a0]\d{3})*(?:[.,]\d{2})?|\d+(?:[.,]\d{2}))\s*\$',
    ]
    for pat in patterns:
        matches = _re_mod.findall(pat, context_text, flags=_re_mod.IGNORECASE)
        vals = [_parse_money(m) for m in matches if _parse_money(m) > 100.0]
        if vals:
            return max(vals)
    return 0.0


def _single_judge_quantum(verdict_str: str, max_claim_amount: float = 0.0) -> float:
    if not verdict_str:
        return 0.0
    if evaluate_verdict_is_defense_win(verdict_str):
        return 0.0
    upper = verdict_str.upper()
    dispositif_match = _re_mod.search(r'(?:PAR\s+CES\s+MOTIFS|DISPOSITIF\s+FINAL|4\.\s*DISPOSITIF|\bDISPOSITIF\b)', upper)
    zone = verdict_str[dispositif_match.start():] if dispositif_match else verdict_str

    # Nettoyer les phrases/clauses qui mentionnent un rejet (ex: rejette la demande reconventionnelle de 51 646,53 $ ou rejette 25 811 $)
    zone_clean = _re_mod.sub(r'[^.!?\n;]*\b(?:REJETTE|DÉBOUTE|DEBOUTE|REFUSE|NON\s+FONDÉE?)\b[^.!?\n;]*', '', zone, flags=_re_mod.IGNORECASE)

    def _parse_money(s: str) -> float:
        cleaned = s.replace(' ', '').replace('\u00a0', '').replace(',', '.')
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def _is_valid_claim_val(v: float) -> bool:
        if v <= 50.0:
            return False
        # Écarter les montants manifestement hors demande principale (ex: prix global d'un contrat 223 223 $ > max_claim_amount)
        if max_claim_amount > 0 and v > max_claim_amount * 1.05:
            return False
        return True

    # 1. Chercher un montant total explicite dans le dispositif
    total_matches = _re_mod.findall(
        r'(?:TOTAL(?:E)?\s+DES\s+CONDAMNATIONS|SOMME\s+TOTALE\s+DE|MONTANT\s+TOTAL\s+DE|TOTAL\s+EN\s+CAPITAL\s*[:de]*|TOTAL\s*:\s*)[^$\n]{0,60}?(\d{1,3}(?:[\s\u00a0]\d{3})*(?:[.,]\d{2})?|\d+(?:[.,]\d{2}))\s*\$',
        zone_clean,
        flags=_re_mod.IGNORECASE,
    )
    if total_matches:
        t_vals = [_parse_money(m) for m in total_matches if _is_valid_claim_val(_parse_money(m))]
        if t_vals:
            res_q = max(t_vals)
            return round(min(res_q, max_claim_amount), 2) if max_claim_amount > 0 else round(res_q, 2)

    # 2. Chercher toutes les clauses de condamnation chiffrées (CONDAMNE ... à payer ... X $ [et Y $])
    condemn_segments = _re_mod.findall(
        r'\b(?:CONDAMNE(?:R|NT)?|ACCORDE(?:R)?|ORDONNE[^.!?\n;]{0,60}?PAYER)\b[^.!?\n;]{0,240}',
        zone_clean,
        flags=_re_mod.IGNORECASE,
    )
    if condemn_segments:
        c_vals = []
        for seg in condemn_segments:
            seg_amounts = _re_mod.findall(r'(\d{1,3}(?:[\s\u00a0]\d{3})*(?:[.,]\d{2})?|\d+(?:[.,]\d{2}))\s*\$', seg)
            for m in seg_amounts:
                v = _parse_money(m)
                if _is_valid_claim_val(v) and v not in c_vals:
                    c_vals.append(v)
        if c_vals:
            # Si un montant dans la liste est déjà la somme des autres, retourner le max; sinon additionner les chefs distincts
            if len(c_vals) > 1:
                max_v = max(c_vals)
                others_sum = sum(v for v in c_vals if v != max_v)
                if abs(max_v - others_sum) < 5.0:
                    res_q = max_v
                else:
                    res_q = sum(c_vals)
            else:
                res_q = c_vals[0]
            return round(min(res_q, max_claim_amount), 2) if max_claim_amount > 0 else round(res_q, 2)

    # 3. Fallback sur les montants restants de la zone nettoyée (filtrés par max_claim_amount)
    matches = _re_mod.findall(r'(\d{1,3}(?:[\s\u00a0]\d{3})*(?:[.,]\d{2})?|\d+(?:[.,]\d{2}))\s*\$', zone_clean)
    vals = [_parse_money(m) for m in matches if _is_valid_claim_val(_parse_money(m))]
    if not vals:
        return 0.0
    res_q = max(vals)
    return round(min(res_q, max_claim_amount), 2) if max_claim_amount > 0 else round(res_q, 2)


def extract_collegiate_quantums(verdict_text: str, max_claim_amount: float = 0.0) -> list:
    """
    Extrait les quantums individuels [q1, q2, q3] accordés par chacun des juges
    lorsqu'il s'agit d'un délibéré collégial (y compris 0,00 $ pour un juge ayant rejeté la demande).
    """
    if not verdict_text:
        return []
    judge_splits = _re_mod.split(r'(?:^|\n)\s*-\s*Juge\s+\d+\s*\([^)]*\)\s*:\s*', verdict_text, flags=_re_mod.IGNORECASE)
    if len(judge_splits) >= 3:
        q_list = []
        for jv in judge_splits[1:]:
            if jv.strip():
                q_j = _single_judge_quantum(jv, max_claim_amount=max_claim_amount)
                q_list.append(round(q_j, 2))
        return q_list
    return []


def extract_verdict_quantum(verdict_text: str, max_claim_amount: float = 0.0) -> float:
    """
    Extrait le quantum financier total accordé par le Tribunal (unique ou collégial),
    borné par le plafond de la demande principale (règle de l'ultra petita, art. 10 C.p.c.).
    - Si le banc collégial comporte une dissidence de rejet à 0,00 $ (ex: [0 $, 84 600 $, 3 200 $]),
      retourne l'espérance mathématique collégiale E[Q] (moyenne des 3 juges = 29 266,67 $).
    - Si tous les juges du banc collégial accueillent la demande (min > 0, ex: [46 117,15 $, 46 117,15 $, 41 117,15 $]),
      retourne le dispositif majoritaire (médiane collégiale = 46 117,15 $).
    """
    if not verdict_text:
        return 0.0
    q_list = extract_collegiate_quantums(verdict_text, max_claim_amount=max_claim_amount)
    if len(q_list) >= 2:
        if min(q_list) == 0.0:
            return round(sum(q_list) / len(q_list), 2)
        sorted_q = sorted(q_list)
        return round(sorted_q[len(sorted_q) // 2], 2)
    return _single_judge_quantum(verdict_text, max_claim_amount=max_claim_amount)


def normalize_legal_results_verdicts(res_data: dict) -> dict:
    """
    Recalibre dynamiquement les résultats de simulation juridique (y compris ceux déjà enregistrés sur disque)
    pour corriger toute inversion de verdict collégial due au rejet d'une demande reconventionnelle,
    appliquer le plafond de l'ultra petita (art. 10 C.p.c.), et corriger la détection civil/criminel.
    """
    if not isinstance(res_data, dict):
        return res_data
    ctx_text = res_data.get("context") or ""
    ctx_lower = ctx_text.lower()
    if any(m in ctx_lower for m in ["c.c.q.", "c.p.c.", "chambre civile", "demande reconventionnelle", "demandeurs"]):
        if not any(m in ctx_lower for m in ["code criminel", "dpcp", "acte d'accusation", "hors de tout doute raisonnable"]):
            res_data["litigation_type"] = "civil"

    max_claim = res_data.get("max_claim_amount") or extract_max_claim_amount(ctx_text)
    if max_claim > 0:
        res_data["max_claim_amount"] = max_claim

    lit_type = res_data.get("litigation_type", "civil")
    details = res_data.get("details")
    if not isinstance(details, list) or not details:
        return res_data

    defense_wins = 0
    for det in details:
        if not isinstance(det, dict):
            continue
        verdict_txt = det.get("verdict") or ""
        is_def_win = evaluate_verdict_is_defense_win(verdict_txt, lit_type)
        det["is_defense_win"] = is_def_win
        if is_def_win:
            defense_wins += 1

        q_list_col = extract_collegiate_quantums(verdict_txt, max_claim_amount=max_claim)
        if q_list_col:
            det["collegiate_quantums"] = q_list_col
            non_zero_col = [q for q in q_list_col if q > 0]
            det["min_positive_quantum"] = min(non_zero_col) if non_zero_col else 0.0
            det["max_collegiate_quantum"] = max(q_list_col)
            sorted_col = sorted(q_list_col)
            det["majority_executable_quantum"] = sorted_col[len(sorted_col) // 2]

        # Corriger l'en-tête collégial si présent
        judge_splits = _re_mod.split(r'(?:^|\n)\s*-\s*Juge\s+\d+\s*\([^)]*\)\s*:\s*', verdict_txt, flags=_re_mod.IGNORECASE)
        if len(judge_splits) >= 3:
            indiv = [s.strip() for s in judge_splits[1:] if s.strip()]
            total_j = len(indiv)
            def_j_wins = sum(1 for jv in indiv if evaluate_verdict_is_defense_win(jv, lit_type))
            winning_votes = def_j_wins if is_def_win else (total_j - def_j_wins)
            maj_q = det.get("majority_executable_quantum", 0.0)
            ref_max = max_claim if max_claim > 0 else (max(q_list_col) if q_list_col else 0.0)
            if not is_def_win and q_list_col and ref_max > 0 and 0 < maj_q < ref_max * 0.5:
                consensus_label = f"Accueil Partiel ({winning_votes}/{total_j}) — Dispositif Majoritaire Exécutoire : {maj_q:,.2f} $"
                header_str = f"[DÉCISION COLLÉGIALE - CONSENSUS : {consensus_label}]"
            else:
                consensus_label = "Défense (Majorité)" if is_def_win else (
                    "Poursuite (Majorité)" if lit_type == "criminal" else "Demandeur (Majorité)"
                )
                header_str = f"[DÉCISION COLLÉGIALE - CONSENSUS : {consensus_label} ({winning_votes}/{total_j})]"
            verdict_txt = _re_mod.sub(
                r'\[DÉCISION COLLÉGIALE - CONSENSUS\s*:[^\]]*\]',
                header_str,
                verdict_txt,
                count=1,
            )
            det["verdict"] = verdict_txt

        # Nettoyer le vocabulaire criminel résiduel dans la synthèse du greffier en matière civile
        if lit_type == "civil" and det.get("clerk_analysis"):
            ca = det["clerk_analysis"]
            ca = _re_mod.sub(r'\bverdict\s+de\s+culpabilité\b', 'jugement de responsabilité civile', ca, flags=_re_mod.IGNORECASE)
            ca = _re_mod.sub(r'\bculpabilité\b', 'responsabilité civile', ca, flags=_re_mod.IGNORECASE)
            ca = _re_mod.sub(r'\bcoupables?\b', 'responsables', ca, flags=_re_mod.IGNORECASE)
            det["clerk_analysis"] = ca

        q_val = extract_verdict_quantum(verdict_txt, max_claim_amount=max_claim)
        if q_val > 0 or is_def_win or q_list_col:
            det["awarded_quantum"] = q_val

    res_data["iterations"] = len(details)
    res_data["defense_wins"] = defense_wins
    res_data["win_rate"] = round((defense_wins / len(details)) * 100.0, 1)
    return res_data


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
        import re

        def _strip_meta_and_citations(text: str) -> str:
            if not text:
                return ""
            # 1. Couper tout bloc "Sources officielles et citations" généré spontanément par le LLM
            text = re.split(r'\n*\*\*Sources officielles et citations\s*:\*\*', text, flags=re.IGNORECASE)[0].strip()
            # 2. Supprimer les excuses méta-discursives liées au Grounding Guardrail en début de plaidoirie
            meta_patterns = [
                r"^(?:Monsieur le Juge,?\s*|Madame la Juge,?\s*|Votre Honneur,?\s*|Honorable Cour,?\s*|Le Tribunal,?\s*)?(?:J'ai pris note de l'objection[^.\n]*\.?\s*)",
                r"^(?:Je vous prie d'excuser[^.\n]*\.?\s*)",
                r"^(?:Je m'engage à reformuler[^.\n]*\.?\s*)",
                r"^(?:Suite à l'objection soulevée[^.\n]*\.?\s*)",
                r"^(?:Veuillez excuser cette imprécision[^.\n]*\.?\s*)",
            ]
            for pat in meta_patterns:
                text = re.sub(pat, "", text, flags=re.IGNORECASE).strip()
            # 3. Supprimer les espaces réservés (placeholders) résiduels
            text = re.sub(r'\[(?:À insérer|Date|Signature|Lieu|Nom)[^\]]*\]', '', text, flags=re.IGNORECASE)
            text = re.sub(r'Prononcé\s+à\s+[^\n.]*,\s+ce\s*\.?', '', text, flags=re.IGNORECASE)
            text = re.sub(r'\bRLRQ\s+c\.\s*A-(?!\d)', 'RLRQ c. A-25', text)
            return text.strip()

        def _format_dedup_refs(refs: list) -> str:
            if not refs:
                return ""
            seen = set()
            lines = ["\n\n**Sources officielles et citations :**"]
            for r in refs:
                key = (r.get("law_name", "").strip().lower(), r.get("citation", "").strip().lower())
                if key in seen:
                    continue
                seen.add(key)
                lines.append(f"- **[{r['law_name']}]({r['url']})** (Citation: `{r['citation']}`)")
                if r.get("summary"):
                    desc = r['summary'].replace('\n', '\n  ')
                    lines.append(f"  *Description :* {desc}")
            return "\n".join(lines) + "\n"
        
        transcript = []
        statutory_block = self.grounding.build_statutory_grounding_block(self.context, self.litigation_type)
        grounded_context = self.context + statutory_block

        is_admin_case = LegalAgents.is_administrative_tribunal(self.context)
        law_ref_label = "les dispositions statutaires vérifiées (ex: L.a.a., L.J.A.)" if is_admin_case else "les articles du C.c.Q. / C.p.c. vérifiés"
        if iter_id > 1 and "=== VERDICTS PRÉCÉDENTS" in self.context:
            initial_user_prompt = (
                f"Nous sommes au Round {iter_id} de l'audience contradictoire. "
                f"Sans répéter mot à mot votre exposé introductif du Round 1, répondez chirurgicalement aux points de friction et de dissidence soulevés lors du délibéré précédent "
                f"(notamment sur le lien de causalité de l'état préexistant, la ventilation poste par poste du quantum et {law_ref_label})."
            )
        else:
            initial_user_prompt = (
                f"Veuillez présenter votre plaidoirie principale et vos arguments déterminants contre la partie adverse en vous basant sur les faits du dossier et {law_ref_label}."
            )

        debate_history_prosecutor = [
            {"role": "user", "content": initial_user_prompt}
        ]
        debate_history_defense = []

        # Audition initiale du Témoin / Expert technique du dossier au Round 1 (ou à l'ouverture d'une nouvelle Chambre)
        if iter_id == 1 or getattr(self, 'is_new_chamber_opening', False):
            self.is_new_chamber_opening = False
            witness_sys = (
                "Tu es le Témoin Technique / Expert indépendant cité dans les pièces du dossier (ex: l'entrepreneur ou l'expert ayant inspecté les lieux et constaté les dommages).\n"
                "Présente à la barre du Tribunal, en 4 à 6 phrases factuelles, précises et neutres à la première personne, tes constatations techniques matérielles telles qu'elles ressortent strictement du contexte de l'affaire (état des lieux, cause technique des dégradations, estimés ou travaux correctifs constatés).\n"
                "Ne cite aucun article de loi et ne prends pas parti juridiquement : livre uniquement ton témoignage technique factuel sous serment.\n\n"
                f"Contexte de l'affaire :\n{self.filter_context(grounded_context, 'judge')}"
            )
            msg_witness = _strip_meta_and_citations(
                self._call_llm(witness_sys, [{"role": "user", "content": "Veuillez livrer votre déposition technique factuelle devant le Tribunal."}])
            )
            if msg_witness:
                transcript.append(f"TEMOIN_EXPERT: {msg_witness}")
                if on_action_callback:
                    on_action_callback("SPEECH_WITNESS", "Témoin / Expert Technique", 3, msg_witness)
                debate_history_prosecutor[0]["content"] += f"\n\nDéposition du Témoin / Expert Technique à la barre : {msg_witness}"
        
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
            
            # Procureur / Demandeur
            prosecutor_sys = LegalAgents.get_prosecutor_prompt(self.filter_context(grounded_context, "prosecutor"), self.litigation_type)
            msg_proc = _strip_meta_and_citations(self._call_llm(prosecutor_sys, debate_history_prosecutor))
            
            # Vérification Grounding Procureur avec boucle de régénération
            for attempt in range(3):
                check_proc = self.grounding.verify_argument(msg_proc, role="prosecutor", context=self.context, litigation_type=self.litigation_type)
                if not check_proc["is_hallucination"]:
                    break
                logger.info(f"Procureur Hallucination détectée (Essai {attempt+1}/3). Régénération en cours...")
                correction_prompt = (
                    f"INSTRUCTION SYSTÈME INTERNE : Votre brouillon précédent contenait une référence hors-graphe ({check_proc['objection_message']}).\n"
                    f"Reformulez directement votre plaidoirie depuis le début en utilisant uniquement les articles de loi et les faits du dossier.\n"
                    f"INTERDICTION ABSOLUE : Ne mentionnez JAMAIS qu'une objection, une erreur ou une reformulation a eu lieu (n'écrivez jamais 'J'ai pris note de l'objection', 'Je vous prie d'excuser' ou 'Je reformule'). Commencez directement votre plaidoirie devant le Tribunal."
                )
                retry_history = debate_history_prosecutor + [
                    {"role": "assistant", "content": msg_proc},
                    {"role": "user", "content": correction_prompt}
                ]
                msg_proc = _strip_meta_and_citations(self._call_llm(prosecutor_sys, retry_history))
            
            # Post-traitement final après les tentatives de correction
            check_proc = self.grounding.verify_argument(msg_proc, role="prosecutor", context=self.context, litigation_type=self.litigation_type)
            if check_proc["is_hallucination"]:
                if on_action_callback:
                    on_action_callback("STIMULUS", "Système (Alerte)", 0, f"⚠️ Erreur de Grounding : Hallucination de jurisprudence détectée pour {agent1_name}. Nettoyage automatique activé.")
                logger.warning(f"Procureur : Hallucination persistante détectée. Nettoyage du plaidoyer par le système.")
                clean_sys = (
                    "Tu es un assistant de réécriture juridique de Lexior.\n"
                    "Récris le plaidoyer suivant en retirant TOUTE citation d'article de loi, de code civil, de code criminel ou d'arrêt de jurisprudence non vérifié.\n"
                    "Conserve intacts le sens, le ton et les arguments factuels ou techniques. Ne mentionne jamais d'objection ni de correction."
                )
                msg_proc = _strip_meta_and_citations(self._call_llm(clean_sys, [{"role": "user", "content": msg_proc}]))
                msg_proc_display = msg_proc
            else:
                refs = check_proc.get("found_references", [])
                msg_proc_display = msg_proc + _format_dedup_refs(refs)
                
            transcript.append(f"PROCUREUR: {msg_proc_display}")
            if on_action_callback:
                on_action_callback("SPEECH_PROSECUTOR", agent1_name, 1, msg_proc_display)
                
            debate_history_prosecutor.append({"role": "assistant", "content": msg_proc})
            debate_history_defense.append({"role": "user", "content": f"{agent1_name} dit: {msg_proc}"})
            
            # Défense
            defense_sys = LegalAgents.get_defense_lawyer_prompt(self.filter_context(grounded_context, "defense"), self.litigation_type)
            msg_def = _strip_meta_and_citations(self._call_llm(defense_sys, debate_history_defense))
            
            # Vérification Grounding Défense avec boucle de régénération
            for attempt in range(3):
                check_def = self.grounding.verify_argument(msg_def, role="defense", context=self.context, litigation_type=self.litigation_type)
                if not check_def["is_hallucination"]:
                    break
                logger.info(f"Défense Hallucination détectée (Essai {attempt+1}/3). Régénération en cours...")
                correction_prompt = (
                    f"INSTRUCTION SYSTÈME INTERNE : Votre brouillon précédent contenait une référence hors-graphe ({check_def['objection_message']}).\n"
                    f"Reformulez directement votre plaidoirie depuis le début en utilisant uniquement les articles de loi et les faits du dossier.\n"
                    f"INTERDICTION ABSOLUE : Ne mentionnez JAMAIS qu'une objection, une erreur ou une reformulation a eu lieu (n'écrivez jamais 'J'ai pris note de l'objection', 'Je vous prie d'excuser' ou 'Je reformule'). Commencez directement votre plaidoirie devant le Tribunal."
                )
                retry_history = debate_history_defense + [
                    {"role": "assistant", "content": msg_def},
                    {"role": "user", "content": correction_prompt}
                ]
                msg_def = _strip_meta_and_citations(self._call_llm(defense_sys, retry_history))
                
            # Post-traitement final après les tentatives de correction
            check_def = self.grounding.verify_argument(msg_def, role="defense", context=self.context, litigation_type=self.litigation_type)
            if check_def["is_hallucination"]:
                if on_action_callback:
                    on_action_callback("STIMULUS", "Système (Alerte)", 0, "⚠️ Erreur de Grounding : Hallucination de jurisprudence détectée pour Avocat de la Défense. Nettoyage automatique activé.")
                logger.warning("Défense : Hallucination persistante détectée. Nettoyage du plaidoyer par le système.")
                clean_sys = (
                    "Tu es un assistant de réécriture juridique de Lexior.\n"
                    "Récris le plaidoyer suivant en retirant TOUTE citation d'article de loi, de code civil, de code criminel ou d'arrêt de jurisprudence non vérifié.\n"
                    "Conserve intacts le sens, le ton et les arguments factuels ou techniques. Ne mentionne jamais d'objection ni de correction."
                )
                msg_def = _strip_meta_and_citations(self._call_llm(clean_sys, [{"role": "user", "content": msg_def}]))
                msg_def_display = msg_def
            else:
                refs = check_def.get("found_references", [])
                msg_def_display = msg_def + _format_dedup_refs(refs)
                
            transcript.append(f"DEFENSE: {msg_def_display}")
            if on_action_callback:
                on_action_callback("SPEECH_DEFENSE", "Avocat de la Défense", 2, msg_def_display)
                
            debate_history_defense.append({"role": "assistant", "content": msg_def})
            debate_history_prosecutor.append({"role": "user", "content": f"La Défense dit: {msg_def}"})
            
            tour += 1
 
        # 3. Phase de Délibéré
        def evaluate_verdict(verdict_text: str) -> bool:
            return evaluate_verdict_is_defense_win(verdict_text, self.litigation_type)

        max_claim = extract_max_claim_amount(self.context)
        judge_grounded_ctx = self.filter_context(grounded_context, "judge")
        if max_claim > 0 and self.litigation_type == "civil":
            judge_grounded_ctx += (
                f"\n\n[PLAFOND IMPÉRATIF DE L'ULTRA PETITA (Art. 10 et 468 C.p.c.) : "
                f"Le montant total réclamé dans la demande principale est de {max_claim:,.2f} $. "
                f"Le quantum total accordé au dispositif ne peut EN AUCUN CAS dépasser {max_claim:,.2f} $. "
                f"Ne confondez jamais le prix global d'un contrat ou d'un bien mentionné dans les faits avec le montant réclamé.]\n"
            )

        if self.judge_type == "collegiate":
            logger.info("Délibéré du Tribunal Collégial (3 Juges)...")
            judges_list = self.selected_judges_personalities if self.selected_judges_personalities else [
                "Formaliste strict (applique la loi et les critères d'objectivité de la preuve à la lettre).",
                "Sensible à l'équité (prend en compte le contexte fonctionnel, social et la vulnérabilité de la partie lésée).",
                "Analytique et rigoureux sur le quantum (scrute l'état préexistant, la causalité poste par poste et écarte toute réclamation non prouvée)."
            ]
            collegiate_results = []
            for idx, j_pers in enumerate(judges_list):
                logger.info(f"Délibération du Juge {idx+1} ({j_pers})...")
                judge_sys = LegalAgents.get_judge_prompt(judge_grounded_ctx, j_pers, self.litigation_type)
                judge_history = [{"role": "user", "content": "Voici la transcription du débat:\n" + "\n".join(transcript) + "\n\nQuel est votre verdict ?"}]
                verdict_j = _strip_meta_and_citations(self._call_llm(judge_sys, judge_history))
                is_win_j = evaluate_verdict(verdict_j)
                collegiate_results.append({
                    "personality": j_pers,
                    "verdict": verdict_j,
                    "is_defense_win": is_win_j,
                    "quantum": _single_judge_quantum(verdict_j, max_claim_amount=max_claim)
                })
            
            wins_count = sum(1 for r in collegiate_results if r["is_defense_win"])
            total_judges = len(collegiate_results)
            is_defense_win = wins_count >= (total_judges // 2 + 1)
            majority_votes = wins_count if is_defense_win else (total_judges - wins_count)
            col_q_vals = [r["quantum"] for r in collegiate_results]
            sorted_col_q = sorted(col_q_vals)
            maj_exec_q = sorted_col_q[len(sorted_col_q) // 2] if sorted_col_q else 0.0
            if not is_defense_win and max_claim > 0 and 0 < maj_exec_q < max_claim * 0.5:
                consensus_header = f"[DÉCISION COLLÉGIALE - CONSENSUS : Accueil Partiel ({majority_votes}/{total_judges}) — Dispositif Majoritaire Exécutoire : {maj_exec_q:,.2f} $]"
            else:
                consensus_label = "Défense (Majorité)" if is_defense_win else (
                    "Poursuite (Majorité)" if self.litigation_type == "criminal" else "Demandeur (Majorité)"
                )
                consensus_header = f"[DÉCISION COLLÉGIALE - CONSENSUS : {consensus_label} ({majority_votes}/{total_judges})]"
            
            combined_verdict = f"{consensus_header}\n\n"
            for idx, r in enumerate(collegiate_results):
                j_name = r["personality"].split('(')[0].strip()
                combined_verdict += f"- Juge {idx+1} ({j_name}) : {r['verdict']}\n\n"
            
            verdict = combined_verdict
            transcript.append(f"JUGE: {verdict}")
            if on_action_callback:
                on_action_callback("VERDICT", "Le Tribunal Collégial", 0, verdict, result=verdict)
        else:
            logger.info("Délibéré du juge...")
            judge_sys = LegalAgents.get_judge_prompt(judge_grounded_ctx, current_personality, self.litigation_type)
            judge_history = [{"role": "user", "content": "Voici la transcription du débat:\n" + "\n".join(transcript) + "\n\nQuel est votre verdict ?"}]
            verdict = _strip_meta_and_citations(self._call_llm(judge_sys, judge_history))
            transcript.append(f"JUGE: {verdict}")
            is_defense_win = evaluate_verdict(verdict)
            if on_action_callback:
                on_action_callback("VERDICT", "Le Juge", 0, verdict, result=verdict)
        
        # 4. Phase de Greffier (Analyste)
        clerk_sys = LegalAgents.get_clerk_prompt(self.litigation_type)
        clerk_history = [{"role": "user", "content": "Analyse du verdict et des arguments décisifs:\n" + "\n".join(transcript)}]
        clerk_analysis = _strip_meta_and_citations(self._call_llm(clerk_sys, clerk_history))
        if self.litigation_type == "civil" and clerk_analysis:
            clerk_analysis = _re_mod.sub(r'\bverdict\s+de\s+culpabilité\b', 'jugement de responsabilité civile', clerk_analysis, flags=_re_mod.IGNORECASE)
            clerk_analysis = _re_mod.sub(r'\bculpabilité\b', 'responsabilité civile', clerk_analysis, flags=_re_mod.IGNORECASE)
            clerk_analysis = _re_mod.sub(r'\bcoupables?\b', 'responsables', clerk_analysis, flags=_re_mod.IGNORECASE)
        if on_action_callback:
            on_action_callback("CLERK_ANALYSIS", "Le Greffier", 4, clerk_analysis, result="Analysis completed")
        
        col_qs_out = extract_collegiate_quantums(verdict, max_claim_amount=max_claim)
        sorted_col_out = sorted(col_qs_out) if col_qs_out else []
        return {
            "iteration": iter_id,
            "judge_personality": current_personality,
            "is_defense_win": is_defense_win,
            "awarded_quantum": extract_verdict_quantum(verdict, max_claim_amount=max_claim),
            "collegiate_quantums": col_qs_out,
            "majority_executable_quantum": sorted_col_out[len(sorted_col_out) // 2] if sorted_col_out else None,
            "transcript": transcript,
            "clerk_analysis": clerk_analysis,
            "verdict": verdict
        }

    def run_full_simulation(self):
        logger.info(f"Démarrage des {self.iterations} simulations de Monte-Carlo juridiques...")
        results = []
        defense_wins = 0
        base_context = self.context
        chamber_archetypes = [
            "Formaliste strict (exige la preuve médicale et écrite rigoureuse sous l'art. 2803 C.c.Q. et applique la loi à la lettre).",
            "Imprévisible et analytique du quantum (scrute le lien de causalité art. 1607-1611 C.c.Q., l'état préexistant et la ventilation des chefs de dommages).",
            "Sensible à l'équité contractuelle et sociale (protège la partie vulnérable mais écarte les demandes accessoires ou abusives non prouvées)."
        ]

        for i in range(1, self.iterations + 1):
            # Si juge unique non fixé, faire tourner l'archétype ou maintenir la dialectique inter-rounds
            if self.judge_type != "collegiate" and not self.selected_judge_personality:
                self.judge_personality = chamber_archetypes[(i - 1) % len(chamber_archetypes)]

            if results:
                prev_summary = "\n\n=== VERDICTS PRÉCÉDENTS ET HISTORIQUE DU PROCÈS ===\n"
                for r_res in results:
                    prev_summary += (
                        f"[ROUND {r_res['iteration']} | {r_res.get('judge_personality', '')}] "
                        f"Quantum accordé : {r_res.get('awarded_quantum', 0.0):,.2f} $ | "
                        f"Analyse Greffier : {r_res.get('clerk_analysis', '')[:320]}...\n"
                    )
                prev_summary += (
                    "\nDirectives dialectiques (Moteur PIE) :\n"
                    "1. L'Avocat de la Défense doit cibler chirurgicalement les chefs de réclamation fragiles (ex: état dégénératif préexistant, capacité d'exercer un emploi convenable art. 45/49 L.a.a., classe de séquelles art. 73 L.a.a., frais non prescrits ou art. 51 C.p.c.) pour réduire le quantum accordé au round précédent.\n"
                    "2. Le Juge réévalue le quantum financier si la Défense démontre une faille sur le lien de causalité (art. 1607, 1611 C.c.Q.) ou le fardeau de preuve (art. 2803 C.c.Q.).\n"
                )
                self.context = base_context + prev_summary

            res = self.run_single_simulation(i)
            results.append(res)
            if res["is_defense_win"]:
                defense_wins += 1

        self.context = base_context
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
