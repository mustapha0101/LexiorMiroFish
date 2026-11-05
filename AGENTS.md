# AGENTS.md — Lexior Simulator (Moteur PIE & Chambre d'Essai Judiciaire Souveraine)

> **Règle de nomenclature impérative** : Bien que le dossier racine sur le disque porte historiquement le nom `/Users/mustaphaberrabaa/Documents/MiroFish`, ce projet s'appelle exclusivement **Lexior Simulator** (`LexiorSimulator`). Toute référence dans le code, les prompts, les rapports PDF, les documents R&D et la documentation technique doit utiliser **Lexior Simulator**.

---

## 1. Rôle de Lexior Simulator dans la Fonderie Lexior

**Lexior Simulator** est le moteur de simulation contradictoire multi-agents et d'homologation neuro-symbolique de l'écosystème Lexior (**Lexior Notebook** + **Lexior Simulator / PIE** + **Serveur MCP SQLite 3 471 art. C.c.Q. / 871 art. C.p.c.** + **Modèle local distillé `LexiorGPT` 7B/32B-AWQ**).

### Positionnement Stratégique
> **« La première fonderie d'intelligence décisionnelle et juridique 100 % souveraine, qui garantit zéro hallucination normative et calcule mathématiquement le risque de litige avant l'audience. »**

Lexior Simulator remplit simultanément les **Fonctions 2 et 3** de la triple boucle souveraine :
1. **Chambre de Stress-Test Actuariel de Dossier (Axe Commercial Court Terme)** : Confrontation d'un dossier réel au jumeau numérique du juge et de la partie adverse pour détecter le **« Puits de Potentiel »** (ex. l'amputation de 19,7 % du quantum au Round 2 de *Caron c. Toiture Allaire* via les art. 1607, 1611 et 2803 C.c.Q., et la contre-attaque chirurgicale du Round 3 permettant de récupérer 100 % de la réclamation).
2. **Playground d'Homologation et de Gouvernance IA (Axe Institutionnel)** : Banc d'essai (*Red-Teaming & Eval Sandbox*) permettant aux ministères, sociétés d'État, banques et assureurs de stresser leurs processus décisionnels et agents IA face aux normes québécoises (C.c.Q., C.p.c., Loi 25).
3. **Usine de Données Synthétiques DPO (Axe DeepTech / RS&DE)** : Extraction des trajectoires dialectiques gagnantes (`chosen`) et perdantes (`rejected`) corrélées aux variations du vecteur cognitif PIE du juge ($\Delta\text{PIE}$) et du montant accordé ($\Delta\text{Quantum}$) pour entraîner `LexiorGPT` en DPO.

---

## 2. Architecture Technique & Garanties du Moteur (`backend/`)

### 2.1 Moteur Cognitif PIE (*Persona-Intent-Emotion*) & Arrêt Dynamique (*Early Stopping*)
- **Fichier clé** : `backend/app/services/simulation_runner.py`
- **Dynamique tri-partite** : À chaque round d'audience, les vecteurs de tensions (`procedure_vs_equite`, `offensive_vs_negociation`, `prudence_vs_rapidite`) et les croyances bayésiennes (`culpabilite_accuse`) des **trois acteurs principaux** (`state_judge`, `state_proc`, `state_def`) sont recalculés dynamiquement selon l'issue du délibéré, les variations du quantum accordé et les objections soulevées.
- **Entropie de Shannon Réelle** : L'entropie narrative du système est calculée dynamiquement à chaque round via `_calculate_narrative_entropy(...)` (et non figée à une constante statique).
- **Arrêt Dynamique par Convergence (*PIE Early Stopping*)** : Pour éviter le gaspillage de tokens dans une boucle séquentielle lorsque le débat juridique a convergé (ex. après les Rounds 1 à 4), la boucle s'arrête automatiquement lorsque :
  1. Le round minimal dialectique est atteint (`round >= 4`), ET
  2. La variation du vecteur PIE du juge et du quantum accordé est quasi nulle sur 2 rounds consécutifs ($\Delta\text{PIE} < 0.01$ et $\Delta\text{Quantum} = 0$) sans nouveau stimulus injecté, OU la Défense concède explicitement le quantum et le Tribunal déclare sa décision finale et irrévocable.

### 2.2 Garde-Fou d'Ancrage (*Grounding Guardrail*) & Pureté Dialectique
- **Fichiers clés** : `backend/app/models/legal_agents.py`, `backend/scripts/run_legal_simulation.py`, `backend/app/services/jurisprudence_grounding.py`
- **Zéro contamination inter-dossiers** : Les prompts systèmes des agents juridiques (`legal_agents.py`) sont strictement génériques et ancrés uniquement dans les faits du dossier actif (aucune référence codée en dur à d'anciens cas tests).
- **Reformulation Transparente sans Excuse Méta-Discursive** : Lorsqu'une plaidoirie initiale est interceptée par le *Grounding Guardrail* pour citation hors-contexte, l'avocat reformule directement son argumentaire de fond **sans jamais s'excuser ni mentionner l'objection de filtrage** (suppression stricte des préambules du type *« J'ai pris note de l'objection... »*).
- **Témoins et Experts Actifs** : Les acteurs secondaires identifiés dans le dossier (témoins factuels, experts techniques comme l'entrepreneur ou l'inspecteur) interviennent activement lors de la phase d'instruction (Round 1) via l'action `SPEECH_WITNESS`.
- **Déduplication des Sources** : Le bloc `**Sources officielles et citations :**` est généré et dédupliqué une seule fois par intervention finale, sans polluer l'historique conversationnel des tours suivants.

### 2.3 Génération du Rapport Actuariel & Export PDF Officiel
- **Fichiers clés** : `backend/app/services/report_agent.py`, `backend/app/services/pdf_exporter.py`
- **Calcul Exact du Taux de Succès et de la Trajectoire du Quantum** : `report_agent.py` extrait le gagnant réel de chaque round (Demandeur vs Défense) ainsi que la trajectoire exacte des montants accordés par le juge (ex. $6\,915,28\ \$ \rightarrow 5\,555,94\ \$ \rightarrow 6\,915,28\ \$$) et passe le délibéré complet du juge au rédacteur exécutif (sans troncature à 300 caractères).
- **Nettoyage Typographique PDF** : `pdf_exporter.py` nettoie les balises Markdown/LaTeX résiduelles (`**$...$**`) et supprime tout espace réservé non résolu avant le rendu ReportLab.

