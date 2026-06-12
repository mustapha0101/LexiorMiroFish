import os
import json
import re
from datetime import datetime
import fitz
from ..config import Config

class SimulationPDFExporter:
    @classmethod
    def generate_pdf(cls, simulation_id: str) -> str:
        """
        Génère un rapport PDF complet de la simulation contenant :
        - Le contexte de l'affaire
        - La liste des agents (personas)
        - Le journal chronologique round par round
        - Le tableau de bord cognitif (tensions, croyances) de chaque agent à chaque round
        
        Retourne le chemin absolu du fichier PDF généré.
        """
        sim_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id)
        if not os.path.exists(sim_dir):
            raise FileNotFoundError(f"Simulation folder not found: {simulation_id}")
            
        pdf_path = os.path.join(sim_dir, "simulation_export.pdf")
        
        # 1. Charger la config et les profils
        config_path = os.path.join(sim_dir, "simulation_config.json")
        profiles_path = os.path.join(sim_dir, "reddit_profiles.json")
        twitter_profiles_path = os.path.join(sim_dir, "twitter_profiles.csv")
        state_path = os.path.join(sim_dir, "run_state.json")
        actions_path = os.path.join(sim_dir, "actions.jsonl")
        
        # Lecture de la config
        simulation_requirement = "N/A"
        litigation_type = "civil"
        run_mode = "courtroom"
        project_name = "Simulation Lexior"
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                    simulation_requirement = cfg.get("simulation_requirement", "N/A")
                    litigation_type = cfg.get("litigation_type", "civil")
                    run_mode = cfg.get("run_mode", "courtroom")
                    project_name = cfg.get("project_name", "Procès Lexior")
            except Exception as e:
                print(f"Error reading config: {e}")
                
        # Lecture des profils
        profiles = []
        if os.path.exists(profiles_path):
            try:
                with open(profiles_path, 'r', encoding='utf-8') as f:
                    profiles = json.load(f)
            except Exception as e:
                print(f"Error reading profiles: {e}")
        elif os.path.exists(twitter_profiles_path):
            try:
                import csv
                with open(twitter_profiles_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        profiles.append({
                            "name": row.get("name", ""),
                            "profession": "Public",
                            "persona": row.get("user_char", "")
                        })
            except Exception as e:
                print(f"Error reading twitter profiles: {e}")
                
        # Lecture du run_state (historique cognitif)
        cognitive_history = []
        if os.path.exists(state_path):
            try:
                with open(state_path, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                    cognitive_history = state_data.get("cognitive_history", [])
            except Exception as e:
                print(f"Error reading run_state: {e}")
                
        # Lecture des actions (chronologie)
        actions = []
        if os.path.exists(actions_path):
            try:
                with open(actions_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            actions.append(json.loads(line))
            except Exception as e:
                print(f"Error reading actions.jsonl: {e}")
        else:
            # Check for parallel simulation action logs (Twitter/Reddit)
            twitter_path = os.path.join(sim_dir, "twitter", "actions.jsonl")
            reddit_path = os.path.join(sim_dir, "reddit", "actions.jsonl")
            
            loaded_actions = []
            if os.path.exists(twitter_path):
                try:
                    with open(twitter_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                act = json.loads(line)
                                if "event_type" not in act:
                                    act["platform"] = "twitter"
                                    loaded_actions.append(act)
                except Exception as e:
                    print(f"Error reading twitter actions: {e}")
            if os.path.exists(reddit_path):
                try:
                    with open(reddit_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                act = json.loads(line)
                                if "event_type" not in act:
                                    act["platform"] = "reddit"
                                    loaded_actions.append(act)
                except Exception as e:
                    print(f"Error reading reddit actions: {e}")
            
            loaded_actions.sort(key=lambda x: (x.get("round", 0), x.get("timestamp", "")))
            actions = loaded_actions
                
        # 2. Initialiser le document PDF
        doc = fitz.open()
        
        # Marges et mise en page
        margin_left = 50
        margin_right = 545
        margin_top = 60
        margin_bottom = 780
        printable_width = margin_right - margin_left
        
        page = None
        y = 900  # Force la création de la première page
        
        # Charger les polices de base
        font_reg = fitz.Font("helvetica")
        font_bold = fitz.Font("helvetica-bold")
        font_italic = fitz.Font("helvetica-oblique")
        font_mono = fitz.Font("courier")
        
        def new_page():
            nonlocal page, y
            page = doc.new_page(width=595, height=842)
            y = margin_top
            
            # Dessiner le header
            page.insert_text((margin_left, 35), "LEXIOR SIMULATOR  |  RAPPORT OFFICIEL DU GREFFIER LEXIOR", fontsize=7.5, color=(0.45, 0.55, 0.72), fontname="helvetica-bold")
            page.draw_line((margin_left, 42), (margin_right, 42), color=(0.85, 0.88, 0.93), width=0.5)
            
            # Dessiner le footer
            page.draw_line((margin_left, 798), (margin_right, 798), color=(0.85, 0.88, 0.93), width=0.5)
            page.insert_text((margin_left, 812), f"Dossier : {project_name} ({litigation_type.upper()})", fontsize=7.5, color=(0.5, 0.5, 0.5), fontname="helvetica")
            page.insert_text((margin_right - 40, 812), f"Page {doc.page_count}", fontsize=7.5, color=(0.5, 0.5, 0.5), fontname="helvetica-bold")
            
        def wrap_text(text, font, fontsize, max_width):
            lines = []
            paragraphs = str(text).split('\n')
            for p in paragraphs:
                words = p.split(' ')
                current_line = []
                for word in words:
                    test_line = ' '.join(current_line + [word]) if current_line else word
                    width = font.text_length(test_line, fontsize=fontsize)
                    if width <= max_width:
                        current_line.append(word)
                    else:
                        lines.append(' '.join(current_line))
                        current_line = [word]
                if current_line:
                    lines.append(' '.join(current_line))
            return lines

        def draw_text(text, fontsize=9.5, color=(0.1, 0.1, 0.1), bold=False, line_spacing=13, italic=False):
            nonlocal page, y
            font = font_bold if bold else (font_italic if italic else font_reg)
            lines = wrap_text(text, font, fontsize, printable_width)
            for line in lines:
                if y + line_spacing > margin_bottom:
                    new_page()
                page.insert_text((margin_left, y), line, fontsize=fontsize, color=color, fontname="helvetica-bold" if bold else ("helvetica-oblique" if italic else "helvetica"))
                y += line_spacing
            y += 2 # petit espacement après paragraphe
 
        def draw_heading(text, level=1):
            nonlocal page, y
            font_size = 14 if level == 1 else 11.5
            spacing = 22 if level == 1 else 18
            color = (0.04, 0.09, 0.18) if level == 1 else (0.71, 0.54, 0.24) # Bleu Marine ou Or
            
            # Saut de page préventif pour les titres
            if y + spacing * 2 > margin_bottom:
                new_page()
                
            y += 5
            font = font_bold
            page.insert_text((margin_left, y), text, fontsize=font_size, color=color, fontname="helvetica-bold")
            y += spacing
            
            if level == 1:
                page.draw_line((margin_left, y - 8), (margin_left + 60, y - 8), color=(0.71, 0.54, 0.24), width=1.5)
                y += 5

        def draw_divider():
            nonlocal page, y
            if y + 15 > margin_bottom:
                new_page()
            y += 5
            page.draw_line((margin_left, y), (margin_right, y), color=(0.90, 0.92, 0.95), width=0.5)
            y += 10

        # --- PAGE DE COUVERTURE / EN-TÊTE ---
        new_page()
        y += 20
        
        # Titre Principal
        draw_text("RAPPORT OFFICIEL DU GREFFIER LEXIOR", fontsize=18, color=(0.04, 0.09, 0.18), bold=True, line_spacing=24)
        draw_text("JOURNAL DE BORD & CONTEXTE COGNITIF DES AGENTS", fontsize=11, color=(0.71, 0.54, 0.24), bold=False, line_spacing=15)
        y += 15
        
        # Boîte de métadonnées
        meta_height = 80
        page.draw_rect(fitz.Rect(margin_left, y, margin_right, y + meta_height), color=(0.85, 0.88, 0.93), fill=(0.96, 0.97, 0.99), width=0.5)
        
        ym = y + 18
        page.insert_text((margin_left + 15, ym), "Identifiant unique :", fontsize=9, color=(0.4, 0.4, 0.4), fontname="helvetica-bold")
        page.insert_text((margin_left + 130, ym), simulation_id, fontsize=9, color=(0.1, 0.1, 0.1), fontname="courier")
        
        ym += 15
        page.insert_text((margin_left + 15, ym), "Date d'exportation :", fontsize=9, color=(0.4, 0.4, 0.4), fontname="helvetica-bold")
        page.insert_text((margin_left + 130, ym), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), fontsize=9, color=(0.1, 0.1, 0.1), fontname="helvetica")
        
        ym += 15
        page.insert_text((margin_left + 15, ym), "Mode d'exécution :", fontsize=9, color=(0.4, 0.4, 0.4), fontname="helvetica-bold")
        mode_label = "Simulation d'Audience (Tribunal)" if run_mode == "courtroom" else "Simulation d'Opinion Publique (Oasis)"
        page.insert_text((margin_left + 130, ym), f"{mode_label} ({litigation_type.upper()})", fontsize=9, color=(0.1, 0.1, 0.1), fontname="helvetica")
        
        ym += 15
        page.insert_text((margin_left + 15, ym), "Total des itérations :", fontsize=9, color=(0.4, 0.4, 0.4), fontname="helvetica-bold")
        page.insert_text((margin_left + 130, ym), str(len(cognitive_history)), fontsize=9, color=(0.1, 0.1, 0.1), fontname="helvetica-bold")
        
        y += meta_height + 20
        
        # Contexte et exigences de la simulation
        draw_heading("Exigences et Contexte de l'Affaire", level=2)
        draw_text(simulation_requirement, fontsize=9.5, color=(0.2, 0.2, 0.2), bold=False, line_spacing=13.5, italic=True)
        y += 15
        
        # --- SECTION AGENTS ET PERSONAS ---
        if profiles:
            draw_heading("Profils des Acteurs de la Simulation", level=2)
            for profile in profiles:
                p_name = profile.get("name", profile.get("realname", "Nom inconnu"))
                p_prof = profile.get("profession", "N/A")
                p_persona = profile.get("persona", "")
                
                # Bloc de profil
                if y + 60 > margin_bottom:
                    new_page()
                
                page.draw_rect(fitz.Rect(margin_left, y, margin_right, y + 2), color=(0.71, 0.54, 0.24), fill=(0.71, 0.54, 0.24), width=0.5)
                y += 20
                
                draw_text(f"{p_name} ({p_prof})", fontsize=10.5, color=(0.04, 0.09, 0.18), bold=True, line_spacing=12)
                if p_persona:
                    draw_text(p_persona, fontsize=8.5, color=(0.3, 0.3, 0.3), bold=False, line_spacing=11.5, italic=True)
                y += 10
            
            draw_divider()

        # --- SECTION CHRONOLOGIE ET ÉTATS COGNITIFS ROUND PAR ROUND ---
        draw_heading("Déroulement Chronologique et Suivi Cognitif", level=1)
        
        # Organiser les actions par round
        rounds_actions = {}
        for action in actions:
            r_num = action.get("round_num", action.get("round", 0))
            if r_num not in rounds_actions:
                rounds_actions[r_num] = []
            rounds_actions[r_num].append(action)
            
        # Organiser l'historique cognitif par round
        rounds_cognitive = {rec.get("round"): rec for rec in cognitive_history if rec.get("round") is not None}
        
        # Boucler sur chaque round
        all_rounds = sorted(list(set(list(rounds_actions.keys()) + list(rounds_cognitive.keys()))))
        
        for r_num in all_rounds:
            # En-tête de round
            draw_heading(f"Itération / Round {r_num}", level=2)
            
            # A. Tableau de bord cognitif de ce round
            if r_num in rounds_cognitive:
                rec = rounds_cognitive[r_num]
                agents_data = rec.get("agents", {})
                
                # Calculer la hauteur requise pour le tableau cognitif
                card_height = 15 + len(agents_data) * 55
                
                if y + card_height > margin_bottom:
                    new_page()
                    
                # Dessiner le fond du tableau cognitif
                page.draw_rect(fitz.Rect(margin_left, y, margin_right, y + card_height), color=(0.8, 0.8, 0.8), fill=(0.95, 0.96, 0.98), width=0.5)
                
                # Titre de la carte
                page.insert_text((margin_left + 15, y + 12), f"TABLEAU DE BORD COGNITIF PIE (Entropie système : {rec.get('entropy', 0.0):.2f})", fontsize=7.5, color=(0.4, 0.4, 0.4), fontname="helvetica-bold")
                
                ya = y + 25
                for agent_key, a_data in agents_data.items():
                    a_name = a_data.get("name", f"Agent {agent_key}")
                    a_pers = a_data.get("personality", "N/A")
                    
                    # Nom & personnalité
                    page.insert_text((margin_left + 15, ya + 8), f"🧠 {a_name} ({a_pers})", fontsize=8.5, color=(0.04, 0.09, 0.18), fontname="helvetica-bold")
                    
                    # Déterminer si tensions courtroom ou social
                    is_courtroom = "procedure_vs_equite" in a_data or "offensive_vs_negociation" in a_data
                    
                    if is_courtroom:
                        t_pe = a_data.get("procedure_vs_equite", 0.5)
                        t_on = a_data.get("offensive_vs_negociation", 0.5)
                        t_pr = a_data.get("prudence_vs_rapidite", 0.5)
                        t_bc = a_data.get("belief_coupable")
                        
                        t_str = f"Procédure/Équité: {t_pe:.2f}  |  Offensif/Négociation: {t_on:.2f}  |  Prudence/Rapidité: {t_pr:.2f}"
                        if t_bc is not None:
                            t_str += f"  |  Croyance Culpabilité: {t_bc*100:.0f}%"
                            
                        page.insert_text((margin_left + 25, ya + 20), t_str, fontsize=7.5, color=(0.3, 0.3, 0.3), fontname="helvetica")
                        
                        bar_label = f"Tension Équité: {t_pe*100:.0f}%"
                        progress_val = t_pe
                    else:
                        t_es = a_data.get("exploration_vs_security", 0.5)
                        t_cd = a_data.get("cooperation_vs_domination", 0.5)
                        t_ts = a_data.get("truth_vs_social_survival", 0.5)
                        
                        t_str = f"Exploration/Sécurité: {t_es:.2f}  |  Coopération/Domination: {t_cd:.2f}  |  Vérité/Survie Sociale: {t_ts:.2f}"
                        page.insert_text((margin_left + 25, ya + 20), t_str, fontsize=7.5, color=(0.3, 0.3, 0.3), fontname="helvetica")
                        
                        bar_label = f"Vérité vs Survie Sociale: {t_ts*100:.0f}%"
                        progress_val = t_ts
                        
                    # Dessiner la barre
                    bar_x = margin_left + 25
                    bar_y = ya + 26
                    bar_w = 120
                    bar_h = 3
                    
                    page.draw_rect(fitz.Rect(bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), color=(0.85, 0.85, 0.85), fill=(0.85, 0.85, 0.85), width=0.5)
                    fill_w = int(bar_w * progress_val)
                    if fill_w > 0:
                        page.draw_rect(fitz.Rect(bar_x, bar_y, bar_x + fill_w, bar_y + bar_h), color=(0.71, 0.54, 0.24), fill=(0.71, 0.54, 0.24), width=0.5)
                        
                    page.insert_text((bar_x + bar_w + 10, bar_y + 3), bar_label, fontsize=6.5, color=(0.5, 0.5, 0.5), fontname="helvetica")
                    ya += 48
                    
                y += card_height + 15
                
            # B. Échanges de ce round
            if r_num in rounds_actions:
                draw_text("ÉCHANGES ET COMMUNICATIONS :", fontsize=8.5, color=(0.5, 0.5, 0.5), bold=True, line_spacing=12)
                
                for action in rounds_actions[r_num]:
                    a_type = action.get("action_type", "")
                    a_name = action.get("agent_name", "Système")
                    a_args = action.get("action_args", {})
                    content = a_args.get("content", "")
                    
                    if a_type in ["simulation_start", "simulation_end"]:
                        continue
                        
                    if a_type == "STIMULUS":
                        stim_text = content or a_args.get("stimulus", "")
                        font_inst = font_reg
                        lines_stim = wrap_text(f"⚡ STIMULUS INJECTÉ : {stim_text}", font_inst, 8.5, printable_width - 30)
                        stim_height = 20 + len(lines_stim) * 11
                        
                        if y + stim_height > margin_bottom:
                            new_page()
                            
                        page.draw_rect(fitz.Rect(margin_left, y, margin_right, y + stim_height), color=(0.88, 0.72, 0.38), fill=(0.99, 0.98, 0.94), width=1)
                        
                        ys = y + 14
                        for line in lines_stim:
                            page.insert_text((margin_left + 15, ys), line, fontsize=8.5, color=(0.62, 0.44, 0.05), fontname="helvetica-bold")
                            ys += 11
                            
                        y += stim_height + 12
                        continue
                        
                    role_color = (0.04, 0.09, 0.18)
                    role_label = a_name
                    
                    if "juge" in a_name.lower():
                        role_color = (0.64, 0.11, 0.11)
                        role_label = f"LE JUGE ({a_name})"
                    elif "procureur" in a_name.lower() or "demandeur" in a_name.lower():
                        role_color = (0.11, 0.38, 0.64)
                    elif "defense" in a_name.lower() or "défense" in a_name.lower() or "defendeur" in a_name.lower() or "défendeur" in a_name.lower():
                        role_color = (0.11, 0.64, 0.38)
                    else:
                        # Public social label
                        platform = action.get("platform", "")
                        platform_str = f" [{platform.upper()}]" if platform else ""
                        action_type_label = a_type.replace('_', ' ').title()
                        role_label = f"{a_name}{platform_str} - {action_type_label}"
                        if platform == 'twitter':
                            role_color = (0.11, 0.54, 0.85)
                        elif platform == 'reddit':
                            role_color = (0.85, 0.35, 0.11)
                        
                    if y + 25 > margin_bottom:
                        new_page()
                        
                    page.insert_text((margin_left, y), f"● {role_label}", fontsize=9, color=role_color, fontname="helvetica-bold")
                    y += 12
                    
                    is_verdict = (a_type == "VERDICT")
                    draw_text(content, fontsize=9, color=(0.15, 0.15, 0.15), bold=is_verdict, line_spacing=12.5, italic=is_verdict)
                    y += 5
                    
            draw_divider()
            
        doc.save(pdf_path)
        doc.close()
        return pdf_path


class ReportPDFExporter:
    @classmethod
    def _draw_risk_quadrant(cls, page, x, y, width, height, is_civil=True, client_side="defense", loss_prob=50.0, estimated_cost=250000.0):
        """
        Dessine un magnifique cadran vectoriel de risques (quadrant) directement sur la page du PDF.
        """
        import fitz
        # Dimensions du graphique lui-même
        chart_w = 320
        chart_h = 320
        chart_x = x + (width - chart_w) // 2
        chart_y = y + 20
        
        center_x = chart_x + chart_w // 2
        center_y = chart_y + chart_h // 2
        
        # 1. Dessiner le cadre extérieur
        page.draw_rect(
            fitz.Rect(chart_x, chart_y, chart_x + chart_w, chart_y + chart_h),
            color=(0.8, 0.8, 0.8),
            width=1.0
        )
        
        # 2. Dessiner la grille légère (tous les 10%)
        for i in range(1, 10):
            pct = i / 10.0
            gx = chart_x + pct * chart_w
            gy = chart_y + pct * chart_h
            # Lignes verticales
            page.draw_line((gx, chart_y), (gx, chart_y + chart_h), color=(0.94, 0.94, 0.94), width=0.5)
            # Lignes horizontales
            page.draw_line((chart_x, gy), (chart_x + chart_w, gy), color=(0.94, 0.94, 0.94), width=0.5)
            
        # 3. Écrire les étiquettes de fond des quadrants (Transfert, Éviter, Accepter, Atténuer)
        # On utilise des couleurs grises très claires
        quad_labels = [
            ("Transférer" if is_civil else "Transfer", center_x - 80, center_y - 80),
            ("Éviter" if is_civil else "Avoid", center_x + 80, center_y - 80),
            ("Accepter" if is_civil else "Accept", center_x - 80, center_y + 80),
            ("Atténuer" if is_civil else "Mitigate", center_x + 80, center_y + 80)
        ]
        
        for text, tx, ty in quad_labels:
            # Insérer le texte
            page.insert_text(
                (tx - 35, ty + 5),
                text,
                fontsize=16,
                color=(0.82, 0.85, 0.90),
                fontname="helvetica-bold"
            )
            
        # 4. Dessiner les axes principaux avec flèches
        # Axe horizontal (Y = center_y)
        page.draw_line((chart_x - 10, center_y), (chart_x + chart_w + 10, center_y), color=(0.75, 0.75, 0.75), width=2.0)
        # Flèche gauche
        page.draw_line((chart_x - 10, center_y), (chart_x - 5, center_y - 4), color=(0.75, 0.75, 0.75), width=2.0)
        page.draw_line((chart_x - 10, center_y), (chart_x - 5, center_y + 4), color=(0.75, 0.75, 0.75), width=2.0)
        # Flèche droite
        page.draw_line((chart_x + chart_w + 10, center_y), (chart_x + chart_w + 5, center_y - 4), color=(0.75, 0.75, 0.75), width=2.0)
        page.draw_line((chart_x + chart_w + 10, center_y), (chart_x + chart_w + 5, center_y + 4), color=(0.75, 0.75, 0.75), width=2.0)
        
        # Axe vertical (X = center_x)
        page.draw_line((center_x, chart_y + chart_h + 10), (center_x, chart_y - 10), color=(0.75, 0.75, 0.75), width=2.0)
        # Flèche haut
        page.draw_line((center_x, chart_y - 10), (center_x - 4, chart_y - 5), color=(0.75, 0.75, 0.75), width=2.0)
        page.draw_line((center_x, chart_y - 10), (center_x + 4, chart_y - 5), color=(0.75, 0.75, 0.75), width=2.0)
        # Flèche bas
        page.draw_line((center_x, chart_y + chart_h + 10), (center_x - 4, chart_y + chart_h + 5), color=(0.75, 0.75, 0.75), width=2.0)
        page.draw_line((center_x, chart_y + chart_h + 10), (center_x + 4, chart_y + chart_h + 5), color=(0.75, 0.75, 0.75), width=2.0)

        # 5. Dessiner les graduations et textes d'axes
        max_cost = estimated_cost if estimated_cost else 250000.0
        import math
        rounded_max = math.ceil(max_cost / 50000.0) * 50000.0
        if rounded_max < 50000.0:
            rounded_max = 50000.0

        if is_civil:
            y_vals = []
            step = rounded_max / 5.0
            for i in range(6):
                val = i * step
                if val == 0:
                    y_vals.append("$-")
                elif val >= 1000000.0:
                    y_vals.append(f"${val / 1000000.0:.1f}M")
                elif val >= 1000.0:
                    y_vals.append(f"${int(val / 1000.0)}k")
                else:
                    y_vals.append(f"${int(val)}")
        else:
            y_vals = ["$-", "$5k", "$10k", "$15k", "$20k", "$25k"]

        for i in range(6):
            gy = chart_y + chart_h - (i * chart_h // 5)
            page.insert_text(
                (chart_x - 38, gy + 3),
                y_vals[i],
                fontsize=8,
                color=(0.4, 0.4, 0.4),
                fontname="helvetica"
            )
            
        x_pcts = ["0%", "20%", "40%", "60%", "80%", "100%"]
        for i in range(6):
            gx = chart_x + (i * chart_w // 5)
            page.insert_text(
                (gx - 8, chart_y + chart_h + 14),
                x_pcts[i],
                fontsize=8,
                color=(0.4, 0.4, 0.4),
                fontname="helvetica"
            )
            
        # Titre des axes
        x_axis_title = "Probabilite de perte" if is_civil else "Probabilite d'occurrence"
        y_axis_title = "Impact financier potentiel" if is_civil else "Cout estime"
        
        page.insert_text(
            (center_x - 40, chart_y + chart_h + 28),
            x_axis_title,
            fontsize=9,
            color=(0.2, 0.2, 0.2),
            fontname="helvetica-bold"
        )
        
        page.insert_text(
            (chart_x - 45, chart_y - 18),
            y_axis_title,
            fontsize=9,
            color=(0.2, 0.2, 0.2),
            fontname="helvetica-bold"
        )

        # 6. Dessiner les bulles de risque
        core_y = min(85.0, max(20.0, (max_cost / rounded_max) * 80.0))

        if is_civil:
            items = [
                ("Obligation de resultat", min(95.0, max(5.0, loss_prob + 5.0)), core_y, 20, (0.92, 0.70, 0.03)),
                ("Devoir d'information", min(95.0, max(5.0, loss_prob - 10.0)), max(10.0, core_y * 0.7), 16, (0.39, 0.45, 0.55)),
                ("Frais de justice", min(95.0, max(5.0, loss_prob + 15.0)), min(95.0, max(10.0, (15000.0 / rounded_max) * 100.0)), 14, (0.23, 0.51, 0.96)),
                ("Dommages punitifs", min(95.0, max(5.0, loss_prob - 35.0)), max(10.0, core_y * 0.45), 15, (0.93, 0.28, 0.60)),
                ("Risque de reputation", min(95.0, max(5.0, loss_prob - 15.0)), max(10.0, core_y * 0.3), 12, (0.98, 0.45, 0.09))
            ]
        else:
            items = [
                ("Denial of service", 20.0, 80.0, 22, (0.96, 0.75, 0.06)),
                ("Ransomware", 40.0, 34.0, 18, (0.6, 0.6, 0.6)),
                ("Phishing", 80.0, 16.0, 14, (0.23, 0.51, 0.96)),
                ("Data leak (email)", 21.0, 8.0, 12, (0.98, 0.45, 0.09)),
                ("Imposter websites", 10.0, 8.0, 8, (0.23, 0.51, 0.96))
            ]
        
        for name, ix, iy, ir, fill in items:
            cx = chart_x + (ix / 100.0) * chart_w
            cy = chart_y + chart_h - (iy / 100.0) * chart_h
            
            # Bulle d'ombre
            page.draw_circle((cx, cy + 1.5), ir, color=(0.85, 0.85, 0.85), fill=(0.85, 0.85, 0.85), width=0.1)
            # Bulle de couleur
            page.draw_circle((cx, cy), ir, color=fill, fill=fill, width=1.0)
            
            # Écrire le nom au-dessus
            page.insert_text(
                (cx - len(name)*2.2, cy - ir - 4),
                name,
                fontsize=7.5,
                color=(0.15, 0.15, 0.15),
                fontname="helvetica-bold"
            )

    @classmethod
    def generate_pdf(cls, report_id: str) -> str:
        """
        Génère un rapport PDF d'analyse/prédiction complet et bien paginé.
        """
        from app.services.report_agent import ReportManager
        from app.services.simulation_manager import SimulationManager
        
        folder = ReportManager._get_report_folder(report_id)
        if not os.path.exists(folder):
            raise FileNotFoundError(f"Report folder not found: {report_id}")
            
        pdf_path = os.path.join(folder, "report_export.pdf")
        
        # 1. Charger les métadonnées et l'outline
        meta_path = ReportManager._get_report_path(report_id)
        outline_path = ReportManager._get_outline_path(report_id)
        
        title = "Rapport de Prédiction Lexior"
        summary = "Analyse prospective et prédictions basées sur la simulation"
        simulation_id = ""
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        run_mode = "courtroom"
        
        if os.path.exists(meta_path):
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    simulation_id = meta.get("simulation_id", "")
                    created_at = meta.get("created_at", created_at)
                    if "T" in created_at:
                        created_at = created_at.replace("T", " ").split(".")[0]
            except Exception:
                pass
                
        # Load simulation config for project_name and mode
        project_name = "Projet Lexior"
        litigation_type = "civil"
        simulation_requirement = "N/A"
        client_side = "defense"
        win_rate = 50.0
        estimated_cost = 250000.0
        
        if simulation_id:
            # Load project to get client_side
            try:
                from app.models.project import ProjectManager
                sim_manager = SimulationManager()
                state = sim_manager.get_simulation(simulation_id)
                if state:
                    project = ProjectManager.get_project(state.project_id)
                    if project:
                        client_side = getattr(project, "client_side", "defense")
            except Exception:
                pass

            # Load results to get win_rate and estimated_cost
            try:
                sim_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id)
                results_path = os.path.join(sim_dir, "legal_simulation_results.json")
                if os.path.exists(results_path):
                    with open(results_path, 'r', encoding='utf-8') as f:
                        res_data = json.load(f)
                        win_rate = res_data.get("win_rate", 50.0)
                        estimated_cost = res_data.get("estimated_cost", 250000.0)
            except Exception:
                pass

            sim_dir = os.path.join(Config.OASIS_SIMULATION_DATA_DIR, simulation_id)
            config_path = os.path.join(sim_dir, "simulation_config.json")
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        cfg = json.load(f)
                        project_name = cfg.get("project_name", "Procès Lexior")
                        litigation_type = cfg.get("litigation_type", litigation_type)
                        run_mode = cfg.get("run_mode", run_mode)
                        simulation_requirement = cfg.get("simulation_requirement", "N/A")
                except Exception:
                    pass

        # Calculate loss probability based on client_side and win_rate
        # win_rate in results is Defense win rate.
        # If client_side is plaintiff, User win rate = 100 - win_rate, User loss rate = win_rate.
        # If client_side is defense, User win rate = win_rate, User loss rate = 100 - win_rate.
        if client_side == "plaintiff":
            loss_prob = win_rate
        else:
            loss_prob = 100.0 - win_rate
                    
        # Load outline and sections
        sections_data = []
        if os.path.exists(outline_path):
            try:
                with open(outline_path, 'r', encoding='utf-8') as f:
                    outline = json.load(f)
                    title = outline.get("title", title)
                    summary = outline.get("summary", summary)
                    sections = outline.get("sections", [])
                    
                    for idx, sec in enumerate(sections, 1):
                        sec_file = ReportManager._get_section_path(report_id, idx)
                        content = ""
                        if os.path.exists(sec_file):
                            try:
                                with open(sec_file, 'r', encoding='utf-8') as sf:
                                    content = sf.read()
                            except Exception:
                                pass
                        sections_data.append({
                            "title": sec.get("title", f"Section {idx}"),
                            "index": idx,
                            "content": content
                        })
            except Exception:
                pass
                
        # Generate fitz PDF
        doc = fitz.open()
        
        margin_left = 54
        margin_right = 541
        margin_top = 60
        margin_bottom = 780
        printable_width = margin_right - margin_left
        
        font_reg = fitz.Font("helvetica")
        font_bold = fitz.Font("helvetica-bold")
        font_italic = fitz.Font("helvetica-oblique")
        
        page = None
        y = 900
        
        def new_page():
            nonlocal page, y
            page = doc.new_page(width=595, height=842)
            y = margin_top
            
            # Header
            page.insert_text((margin_left, 35), "LEXIOR SIMULATOR  |  RAPPORT D'ANALYSE ET DE PRÉDICTION", fontsize=7.5, color=(0.45, 0.55, 0.72), fontname="helvetica-bold")
            page.draw_line((margin_left, 42), (margin_right, 42), color=(0.85, 0.88, 0.93), width=0.5)
            
            # Footer
            page.draw_line((margin_left, 798), (margin_right, 798), color=(0.85, 0.88, 0.93), width=0.5)
            page.insert_text((margin_left, 812), f"Dossier : {project_name}", fontsize=7.5, color=(0.5, 0.5, 0.5), fontname="helvetica")
            page.insert_text((margin_right - 40, 812), f"Page {doc.page_count}", fontsize=7.5, color=(0.5, 0.5, 0.5), fontname="helvetica-bold")

        def get_clean_length(text, font, fontsize):
            clean = text.replace('**', '')
            return font.text_length(clean, fontsize=fontsize)

        def wrap_rich_text(text, font, fontsize, max_width):
            lines = []
            paragraphs = str(text).split('\n')
            for p in paragraphs:
                words = p.split(' ')
                current_line = []
                for word in words:
                    test_line = ' '.join(current_line + [word]) if current_line else word
                    width = get_clean_length(test_line, font, fontsize)
                    if width <= max_width:
                        current_line.append(word)
                    else:
                        lines.append(' '.join(current_line))
                        current_line = [word]
                if current_line:
                    lines.append(' '.join(current_line))
                # Add empty line between paragraphs
                lines.append("")
            return lines[:-1] # Remove last empty line

        def draw_rich_line(x, y, line, fontsize, color, is_bullet=False):
            start_x = x
            if is_bullet:
                page.insert_text((x, y), "•", fontsize=fontsize, color=(0.71, 0.54, 0.24), fontname="helvetica-bold")
                start_x += 12
                
            parts = re.split(r'(\*\*.*?\*\*)', line)
            current_x = start_x
            for part in parts:
                is_bold = part.startswith('**') and part.endswith('**')
                text = part[2:-2] if is_bold else part
                if not text:
                    continue
                fontname = "helvetica-bold" if is_bold else "helvetica"
                page.insert_text((current_x, y), text, fontsize=fontsize, color=color, fontname=fontname)
                font = font_bold if is_bold else font_reg
                current_x += font.text_length(text, fontsize=fontsize)

        def draw_rich_text(text, fontsize=9.5, color=(0.15, 0.15, 0.15), line_spacing=13, is_bullet=False):
            nonlocal page, y
            lines = wrap_rich_text(text, font_reg, fontsize, printable_width - (15 if is_bullet else 0))
            for line in lines:
                if y + line_spacing > margin_bottom:
                    new_page()
                if line == "":
                    y += 6 # Spacing between paragraphs
                    continue
                draw_rich_line(margin_left + (10 if is_bullet else 0), y, line, fontsize, color, is_bullet)
                y += line_spacing

        def draw_heading(text, level=1):
            nonlocal page, y
            font_size = 14 if level == 1 else (11.5 if level == 2 else 10)
            spacing = 22 if level == 1 else (18 if level == 2 else 14)
            color = (0.04, 0.09, 0.18) if level == 1 else (0.71, 0.54, 0.24) if level == 2 else (0.3, 0.3, 0.3)
            
            if y + spacing * 2 > margin_bottom:
                new_page()
                
            y += 8
            page.insert_text((margin_left, y), text, fontsize=font_size, color=color, fontname="helvetica-bold")
            y += spacing
            
            if level == 1:
                page.draw_line((margin_left, y - 8), (margin_left + 60, y - 8), color=(0.71, 0.54, 0.24), width=1.5)
                y += 5

        # 2. Cover Page
        new_page()
        y += 40
        
        # Cover header line
        page.draw_rect(fitz.Rect(margin_left, y, margin_right, y + 4), color=(0.71, 0.54, 0.24), fill=(0.71, 0.54, 0.24), width=1)
        y += 24
        
        # Document title
        draw_rich_text(f"**RAPPORT D'ANALYSE PRÉDICTIVE**", fontsize=18, color=(0.04, 0.09, 0.18), line_spacing=24)
        draw_rich_text(title, fontsize=12, color=(0.71, 0.54, 0.24), line_spacing=16)
        y += 10
        
        # Summary block
        draw_rich_text(f"*{summary}*", fontsize=9.5, color=(0.4, 0.4, 0.4), line_spacing=13)
        y += 20
        
        # Metadata block
        meta_height = 80
        page.draw_rect(fitz.Rect(margin_left, y, margin_right, y + meta_height), color=(0.85, 0.88, 0.93), fill=(0.96, 0.97, 0.99), width=0.5)
        
        ym = y + 18
        page.insert_text((margin_left + 15, ym), "Identifiant unique :", fontsize=9, color=(0.4, 0.4, 0.4), fontname="helvetica-bold")
        page.insert_text((margin_left + 130, ym), report_id, fontsize=9, color=(0.1, 0.1, 0.1), fontname="courier")
        
        ym += 15
        page.insert_text((margin_left + 15, ym), "Date d'exportation :", fontsize=9, color=(0.4, 0.4, 0.4), fontname="helvetica-bold")
        page.insert_text((margin_left + 130, ym), created_at, fontsize=9, color=(0.1, 0.1, 0.1), fontname="helvetica")
        
        ym += 15
        page.insert_text((margin_left + 15, ym), "Mode de simulation :", fontsize=9, color=(0.4, 0.4, 0.4), fontname="helvetica-bold")
        mode_label = "Simulation Judiciaire (Tribunal)" if run_mode == "courtroom" else "Analyse d'Opinion Publique (Oasis)"
        page.insert_text((margin_left + 130, ym), f"{mode_label} ({litigation_type.upper()})", fontsize=9, color=(0.1, 0.1, 0.1), fontname="helvetica")
        
        ym += 15
        page.insert_text((margin_left + 15, ym), "Dossier source :", fontsize=9, color=(0.4, 0.4, 0.4), fontname="helvetica-bold")
        page.insert_text((margin_left + 130, ym), project_name, fontsize=9, color=(0.1, 0.1, 0.1), fontname="helvetica-bold")
        
        y += meta_height + 25
        
        # Context requirement
        draw_heading("Contexte & Enjeux du Dossier", level=2)
        draw_rich_text(simulation_requirement, fontsize=9.5, color=(0.2, 0.2, 0.2), line_spacing=13.5)
        y += 20
        
        # 3. Render each section's content
        for sec in sections_data:
            draw_heading(f"{sec['index']}. {sec['title']}", level=1)
            
            content = sec['content']
            if not content.strip():
                draw_rich_text("*Contenu de la section en cours de génération ou indisponible.*", fontsize=9.5, color=(0.5, 0.5, 0.5))
                y += 10
                continue
                
            # Parse markdown blocks line-by-line
            lines = content.split('\n')
            p_block = []
            
            for line in lines:
                stripped = line.strip()
                if re.search(r'\[RISK[\s\\_]*QUAD(?:RANT)?[\s\\_]*CHART\]', stripped, re.IGNORECASE):
                    if p_block:
                        draw_rich_text('\n'.join(p_block))
                        p_block = []
                    # Check for page space (quadrant requires about 360 points)
                    if y + 370 > margin_bottom:
                        new_page()
                    cls._draw_risk_quadrant(
                        page, margin_left, y, printable_width, 320,
                        is_civil=(litigation_type == 'civil'),
                        client_side=client_side,
                        loss_prob=loss_prob,
                        estimated_cost=estimated_cost
                    )
                    y += 340
                    continue
                elif stripped.startswith('### '):
                    if p_block:
                        draw_rich_text('\n'.join(p_block))
                        p_block = []
                    draw_heading(stripped[4:], level=3)
                elif stripped.startswith('## '):
                    if p_block:
                        draw_rich_text('\n'.join(p_block))
                        p_block = []
                    draw_heading(stripped[3:], level=2)
                elif stripped.startswith('# '):
                    if p_block:
                        draw_rich_text('\n'.join(p_block))
                        p_block = []
                    draw_heading(stripped[2:], level=1)
                elif stripped.startswith('- ') or stripped.startswith('* '):
                    if p_block:
                        draw_rich_text('\n'.join(p_block))
                        p_block = []
                    draw_rich_text(stripped[2:], is_bullet=True)
                elif not stripped:
                    if p_block:
                        draw_rich_text('\n'.join(p_block))
                        p_block = []
                else:
                    p_block.append(line)
                    
            if p_block:
                draw_rich_text('\n'.join(p_block))
                
            y += 15
            
        doc.save(pdf_path)
        doc.close()
        return pdf_path
