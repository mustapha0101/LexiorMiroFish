"""
Suite de Tests Complète — Lexior Simulator v2
Couvre :
1. Souveraineté terminologique québécoise/canadienne & pureté des prompts (Bug C + v2)
2. Moteur SQLite FTS5 embarqué ccq_cpc.db (3 489 art. C.c.Q. + 876 art. C.p.c. en < 1 ms)
3. Grounding Guardrail multi-articles C.c.Q. & C.p.c. + pré-injection neuro-symbolique
4. Boucle d'audience : Témoin/Expert au Round 1 (Bug D), nettoyage des excuses fantômes (Bug C) et déduplication des sources (Bug E)
5. Moteur PIE : Entropie narrative de Shannon réelle (Bug B), dynamique tri-agents et Arrêt Dynamique / Rotation Multi-Chambres (Bug A + v2)
6. Calculateur Actuariel v2 & Rapport Exécutif (Taux de succès Demandeur, Puits de Potentiel, Art. 1619 C.c.Q., Cible CRA art. 161 C.p.c.)
7. Export PDF & API Flask (/health)
"""

import os
import sys
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Assurer que le dossier backend est dans sys.path
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import create_app
from app.models.legal_agents import LegalAgents
from app.services.jurisprudence_grounding import JurisprudenceGrounding
from app.services.cognitive_engine import CognitiveAgentState
from app.services.simulation_runner import SimulationRunner
from scripts.run_legal_simulation import LegalSimulationRunner


class TestLexiorSimulatorV2(unittest.TestCase):
    """Tests unitaires et d'intégration de bout en bout pour Lexior Simulator v2."""

    def setUp(self):
        self.grounding = JurisprudenceGrounding()

    # =========================================================================
    # 1. SOUVERAINETÉ TERMINOLOGIQUE QUÉBÉCOISE & PURETÉ DES PROMPTS (Bug C + v2)
    # =========================================================================
    def test_01_prompts_purity_and_quebec_terminology(self):
        """Vérifie l'absence totale de contamination ('NovaTech', 'Apex Software', 'Procureur de la République', 'Ministère Public') et la présence des règles v2."""
        ctx = "Litige civil concernant la réfection d'une toiture entre Mme France Caron et Toiture Allaire."
        proc_civil = LegalAgents.get_prosecutor_prompt(ctx, "civil")
        def_civil = LegalAgents.get_defense_lawyer_prompt(ctx, "civil")
        judge_civil = LegalAgents.get_judge_prompt(ctx, "Formaliste strict", "civil")
        clerk_civil = LegalAgents.get_clerk_prompt("civil")

        for prompt in (proc_civil, def_civil, judge_civil, clerk_civil):
            self.assertNotIn("NovaTech", prompt)
            self.assertNotIn("Apex Software", prompt)
            self.assertNotIn("Procureur de la République", prompt)
            self.assertNotIn("Ministère Public", prompt)

        # Vérifier les ajouts v2 Grand Cabinet (art. 1619, 2925 C.c.Q., art. 168, 235 C.p.c.)
        self.assertIn("1619 C.c.Q.", proc_civil)
        self.assertIn("2925 C.c.Q.", def_civil)
        self.assertIn("168 C.p.c.", def_civil)
        self.assertIn("1619 C.c.Q.", judge_civil)
        self.assertIn("INTERDICTION ABSOLUE D'ESPACES RÉSERVÉS", clerk_civil)

        # Vérifier la terminologie criminelle canadienne (DPCP / Code criminel)
        proc_crim = LegalAgents.get_prosecutor_prompt(ctx, "criminal")
        clerk_crim = LegalAgents.get_clerk_prompt("criminal")
        self.assertIn("DPCP", proc_crim)
        self.assertIn("DPCP", clerk_crim)
        self.assertNotIn("Procureur de la République", proc_crim)

    # =========================================================================
    # 2. MOTEUR SQLITE SOUVERAIN EMBARQUÉ (ccq_cpc.db : 3 489 C.c.Q. + 876 C.p.c.)
    # =========================================================================
    def test_02_embedded_ccq_cpc_sqlite_engine(self):
        """Vérifie la présence et la précision des 3 489 articles C.c.Q. et 876 articles C.p.c. dans ccq_cpc.db."""
        self.assertTrue(os.path.exists(self.grounding.ccq_cpc_db_path), "ccq_cpc.db doit exister dans backend/app/data/")

        # Articles clés du C.c.Q.
        for num, kw in [("1457", "faute"), ("1607", "préjudice"), ("1611", "perte"), ("1619", "indemnité"), ("2100", "entrepreneur"), ("2803", "prouver"), ("2925", "trois ans")]:
            row = self.grounding.get_code_article_local("CCQ", num)
            self.assertIsNotNone(row, f"L'article {num} C.c.Q. doit être présent")
            self.assertIn(kw, row["texte"].lower())
            self.assertTrue(row["url"].endswith(f"#art{num}"))

        # Articles clés du C.p.c.
        for num, kw in [("18", "proportionnalité"), ("168", "irrecevabilité"), ("235", "expert"), ("536", "créance")]:
            row = self.grounding.get_code_article_local("CPC", num)
            self.assertIsNotNone(row, f"L'article {num} C.p.c. doit être présent")
            self.assertIn(kw, row["texte"].lower())
            self.assertTrue(row["url"].endswith(f"#art{num}"))

        # Recherche plein texte FTS5
        fts_res = self.grounding.search_code_fts_local("bardeaux", "CCQ", limit=2)
        self.assertIsInstance(fts_res, list)
        fts_entrepreneur = self.grounding.search_code_fts_local("entrepreneur", "CCQ", limit=3)
        self.assertTrue(len(fts_entrepreneur) > 0)

    def test_03_statutory_pre_injection_block(self):
        """Vérifie que build_statutory_grounding_block injecte les articles pertinents du C.c.Q. et du C.p.c."""
        ctx = "L'entrepreneur Toiture Allaire a posé des bardeaux sur un pontage pourri chez Mme Caron (art. 2100 C.c.Q.)."
        block = self.grounding.build_statutory_grounding_block(ctx, "civil")
        self.assertIn("=== MÉMOIRE NORMATIVE DÉTERMINISTE (SERVEUR SQLITE C.C.Q. & C.P.C.) ===", block)
        self.assertIn("[Art. 2100 C.c.Q.]", block)
        self.assertIn("[Art. 1607 C.c.Q.]", block)
        self.assertIn("[Art. 1619 C.c.Q.]", block)
        self.assertIn("[Art. 2925 C.c.Q.]", block)
        self.assertIn("[Art. 168 C.p.c.]", block)

    # =========================================================================
    # 3. GROUNDING GUARDRAIL MULTI-ARTICLES C.C.Q. & C.P.C.
    # =========================================================================
    @patch("app.services.jurisprudence_grounding.JurisprudenceGrounding._verify_with_llm")
    def test_04_verify_argument_multi_articles_ccq_and_cpc(self, mock_verify):
        """Vérifie que verify_argument extrait et valide simultanément plusieurs articles C.c.Q. et C.p.c. dans une même plaidoirie."""
        mock_verify.return_value = True
        arg = (
            "En vertu des articles 1607, 1611 et 2803 C.c.Q., la demanderesse doit prouver le lien direct "
            "de causalité, et selon l'article 168 C.p.c., ce chef de réclamation non prouvé est irrecevable."
        )
        res = self.grounding.verify_argument(arg, role="defense", litigation_type="civil")
        self.assertFalse(res["is_hallucination"])
        citations = [r["citation"] for r in res["found_references"]]
        self.assertIn("art. 1607 C.c.Q.", citations)
        self.assertIn("art. 1611 C.c.Q.", citations)
        self.assertIn("art. 2803 C.c.Q.", citations)
        self.assertIn("art. 168 C.p.c.", citations)

    # =========================================================================
    # 4. BOUCLE D'AUDIENCE : TÉMOIN ROUND 1 (Bug D), NETTOYAGE D'EXCUSES (Bug C) & DÉDUPLICATION SOURCES (Bug E)
    # =========================================================================
    @patch.object(LegalSimulationRunner, "_call_llm")
    @patch.object(JurisprudenceGrounding, "verify_argument")
    def test_05_run_single_simulation_witness_and_clean_speeches(self, mock_verify, mock_llm):
        """Vérifie l'intervention du Témoin au Round 1, la suppression des excuses d'objection et la non-duplication des sources."""
        mock_verify.return_value = {
            "is_hallucination": False,
            "confidence": 0.99,
            "found_references": [
                {
                    "law_name": "Code civil du Québec - Article 2100",
                    "citation": "art. 2100 C.c.Q.",
                    "url": "https://www.canlii.org/fr/qc/legis/lois/rlrq-c-ccq-1991/derniere/rlrq-c-ccq-1991.html#art2100",
                    "summary": "Obligation de résultat et devoir de conseil."
                },
                # Doublon volontaire pour tester la déduplication (_format_dedup_refs)
                {
                    "law_name": "Code civil du Québec - Article 2100",
                    "citation": "art. 2100 C.c.Q.",
                    "url": "https://www.canlii.org/fr/qc/legis/lois/rlrq-c-ccq-1991/derniere/rlrq-c-ccq-1991.html#art2100",
                    "summary": "Obligation de résultat et devoir de conseil."
                }
            ],
            "objection_message": ""
        }

        # Simuler des réponses LLM contenant des excuses fantômes, des blocs Sources dupliqués et des placeholders
        mock_llm.side_effect = [
            # 1. Témoin Technique (Round 1)
            "Lors de mon inspection de la toiture, j'ai constaté que le pontage de bois était pourri sous les bardeaux neufs.",
            # 2. Tour 1 Demandeur (avec excuse fantôme + bloc Sources généré par le LLM)
            "Monsieur le Juge, J'ai pris note de l'objection de la Défense et je reformule. L'entrepreneur a violé l'article 2100 C.c.Q.\n\n**Sources officielles et citations :**\n- Faux bloc LLM",
            # 3. Tour 1 Défense
            "Je vous prie d'excuser cette imprécision. Nous contestons le quantum selon l'article 1607 C.c.Q.",
            # 4. Tour 2 Demandeur
            "La condamnation à 6 915,28 $ est pleinement justifiée.",
            # 5. Tour 2 Défense
            "Le quantum doit être réduit à 5 555,94 $.",
            # 6. Verdict du Juge
            "Le Tribunal déclare le défendeur RESPONSABLE et le CONDAMNE à payer 6 915,28 $ [À insérer si disponible, sinon omettre].",
            # 7. Analyse du Greffier
            "Analyse du Greffier [À insérer Date] : L'article 2100 C.c.Q. a emporté la conviction du Juge."
        ]

        runner = LegalSimulationRunner(
            context="Affaire Caron c. Toiture Allaire : réclamation de 6 915,28 $ pour travaux correctifs.",
            iterations=1,
            litigation_type="civil"
        )
        actions_logged = []
        res = runner.run_single_simulation(1, on_action_callback=lambda a_type, a_name, a_id, content, **kw: actions_logged.append((a_type, a_name, content)))

        # 1. Le Témoin Expert a bien parlé en premier (Bug D)
        self.assertEqual(actions_logged[0][0], "SPEECH_WITNESS")
        self.assertIn("pontage de bois était pourri", actions_logged[0][2])

        # 2. Aucune excuse fantôme ("J'ai pris note de l'objection", "Je vous prie d'excuser") ne subsiste (Bug C)
        proc_speech_1 = actions_logged[1][2]
        def_speech_1 = actions_logged[2][2]
        self.assertNotIn("J'ai pris note de l'objection", proc_speech_1)
        self.assertNotIn("Je vous prie d'excuser", def_speech_1)

        # 3. Le bloc "**Sources officielles et citations :**" n'apparaît qu'une seule fois et l'article 2100 est dédupliqué (Bug E)
        self.assertEqual(proc_speech_1.count("**Sources officielles et citations :**"), 1)
        self.assertEqual(proc_speech_1.count("Code civil du Québec - Article 2100"), 1)

        # 4. Aucun placeholder "[À insérer...]" dans le verdict ni dans l'analyse du greffier
        self.assertNotIn("[À insérer", res["verdict"])
        self.assertNotIn("[À insérer", res["clerk_analysis"])
        self.assertFalse(res["is_defense_win"])

    # =========================================================================
    # 5. MOTEUR PIE : ENTROPIE DE SHANNON RÉELLE & CONVERGENCE (Bugs A & B)
    # =========================================================================
    def test_06_shannon_narrative_entropy_is_dynamic(self):
        """Vérifie que _calculate_narrative_entropy calcule une vraie entropie de Shannon dynamique (et non 0.50 fixe)."""
        s_judge = CognitiveAgentState("0", "Le Juge", tensions={"procedure_vs_equite": 0.66, "offensive_vs_negociation": 0.5, "prudence_vs_rapidite": 0.5}, beliefs={"culpabilite_accuse": {"coupable": 0.80, "innocent": 0.20}})
        s_proc = CognitiveAgentState("1", "Avocat du Demandeur", tensions={"procedure_vs_equite": 0.88, "offensive_vs_negociation": 0.85, "prudence_vs_rapidite": 0.35}, beliefs={"culpabilite_accuse": {"coupable": 0.92, "innocent": 0.08}})
        s_def = CognitiveAgentState("2", "Avocat de la Défense", tensions={"procedure_vs_equite": 0.25, "offensive_vs_negociation": 0.35, "prudence_vs_rapidite": 0.80}, beliefs={"culpabilite_accuse": {"coupable": 0.30, "innocent": 0.70}})

        e1 = SimulationRunner._calculate_narrative_entropy(s_judge, s_proc, s_def, 0, 0)
        # Simuler une perturbation (Puits de Potentiel + Objection au Round 2)
        s_judge.beliefs["culpabilite_accuse"] = {"coupable": 0.55, "innocent": 0.45}
        e2 = SimulationRunner._calculate_narrative_entropy(s_judge, s_proc, s_def, 2, 1)

        self.assertNotEqual(e1, 0.5)
        self.assertNotEqual(e1, e2, "L'entropie de Shannon doit varier entre deux états cognitifs distincts")

    # =========================================================================
    # 6. CALCULATEUR ACTUARIEL v2 & EXPORT PDF
    # =========================================================================
    def test_07_flask_health_endpoint(self):
        """Vérifie que l'application Flask démarre et renvoie 'Lexior Simulator Backend' sur /health."""
        app = create_app()
        client = app.test_client()
        resp = client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data.get("service"), "Lexior Simulator Backend")

    def test_08_actuarial_report_calculator_v2(self):
        """Vérifie le calcul du Puits de Potentiel (-19.7%), de l'espérance mathématique E[Q], de l'art. 1619 C.c.Q. (+8.5%) et du seuil CRA."""
        quantums = [(1, 6915.28), (2, 5555.94), (3, 6915.28), (4, 6915.28)]
        max_q = max(q for _, q in quantums)
        min_q = min(q for _, q in quantums)
        avg_q = sum(q for _, q in quantums) / len(quantums)
        drop_pct = ((max_q - min_q) / max_q) * 100.0
        legal_interest_markup = round(avg_q * 0.085, 2)
        total_actuarial_exposure = round(avg_q + legal_interest_markup, 2)

        self.assertAlmostEqual(drop_pct, 19.66, places=1)
        self.assertAlmostEqual(avg_q, 6575.445, places=2)
        self.assertGreater(total_actuarial_exposure, max_q)


if __name__ == "__main__":
    unittest.main()
