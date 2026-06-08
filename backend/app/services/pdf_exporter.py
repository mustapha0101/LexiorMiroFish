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
            page.insert_text((margin_left, 35), "LEXIOR SIMULATOR  |  RAPPORT DE DÉROULEMENT DE SIMULATION", fontsize=7.5, color=(0.45, 0.55, 0.72), fontname="helvetica-bold")
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
        draw_text("RAPPORT DÉTAILLÉ DE SIMULATION", fontsize=18, color=(0.04, 0.09, 0.18), bold=True, line_spacing=24)
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
        mode_label = "Simulation d'Audience (Tribunal)" if run_mode == "courtroom" else "Simulation d'Opinion Publique"
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
                p_name = profile.get("name", "Nom inconnu")
                p_prof = profile.get("profession", "N/A")
                p_persona = profile.get("persona", "")
                
                # Bloc de profil
                if y + 60 > margin_bottom:
                    new_page()
                
                page.draw_rect(fitz.Rect(margin_left, y, margin_right, y + 2), color=(0.71, 0.54, 0.24), fill=(0.71, 0.54, 0.24), width=0.5)
                y += 8
                
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
            r_num = action.get("round_num", 0)
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
                # 3 agents maximum, environ 55 points par agent
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
                    
                    # Tensions
                    t_pe = a_data.get("procedure_vs_equite", 0.5)
                    t_on = a_data.get("offensive_vs_negociation", 0.5)
                    t_pr = a_data.get("prudence_vs_rapidite", 0.5)
                    t_bc = a_data.get("belief_coupable")
                    
                    t_str = f"Procédure/Équité: {t_pe:.2f}  |  Offensif/Négociation: {t_on:.2f}  |  Prudence/Rapidité: {t_pr:.2f}"
                    if t_bc is not None:
                        t_str += f"  |  Croyance Culpabilité: {t_bc*100:.0f}%"
                        
                    page.insert_text((margin_left + 25, ya + 20), t_str, fontsize=7.5, color=(0.3, 0.3, 0.3), fontname="helvetica")
                    
                    # Dessiner une petite barre de progression visuelle pour la tension principale (Procédure vs Équité)
                    bar_x = margin_left + 25
                    bar_y = ya + 26
                    bar_w = 120
                    bar_h = 3
                    
                    # Fond de la barre
                    page.draw_rect(fitz.Rect(bar_x, bar_y, bar_x + bar_w, bar_y + bar_h), color=(0.85, 0.85, 0.85), fill=(0.85, 0.85, 0.85), width=0.5)
                    # Remplissage
                    fill_w = int(bar_w * t_pe)
                    if fill_w > 0:
                        page.draw_rect(fitz.Rect(bar_x, bar_y, bar_x + fill_w, bar_y + bar_h), color=(0.71, 0.54, 0.24), fill=(0.71, 0.54, 0.24), width=0.5)
                        
                    # Libellé barre
                    page.insert_text((bar_x + bar_w + 10, bar_y + 3), f"Tension Équité: {t_pe*100:.0f}%", fontsize=6.5, color=(0.5, 0.5, 0.5), fontname="helvetica")
                    
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
                    
                    # Ignorer les événements de début/fin système non-informatifs
                    if a_type in ["simulation_start", "simulation_end"]:
                        continue
                        
                    # 1. Cas particulier : STIMULUS INJECTÉ
                    if a_type == "STIMULUS":
                        stim_text = content or a_args.get("stimulus", "")
                        
                        # Calculer la hauteur requise pour le bloc stimulus
                        font_inst = font_reg
                        lines_stim = wrap_text(f"⚡ STIMULUS INJECTÉ : {stim_text}", font_inst, 8.5, printable_width - 30)
                        stim_height = 20 + len(lines_stim) * 11
                        
                        if y + stim_height > margin_bottom:
                            new_page()
                            
                        # Dessiner un cadre jaune/doré pour le stimulus
                        page.draw_rect(fitz.Rect(margin_left, y, margin_right, y + stim_height), color=(0.88, 0.72, 0.38), fill=(0.99, 0.98, 0.94), width=1)
                        
                        ys = y + 14
                        for line in lines_stim:
                            page.insert_text((margin_left + 15, ys), line, fontsize=8.5, color=(0.62, 0.44, 0.05), fontname="helvetica-bold")
                            ys += 11
                            
                        y += stim_height + 12
                        continue
                        
                    # 2. Cas général : Discours ou Verdict d'agent
                    # Déterminer la couleur et le préfixe selon le rôle
                    role_color = (0.04, 0.09, 0.18)
                    role_label = a_name
                    
                    if "juge" in a_name.lower():
                        role_color = (0.64, 0.11, 0.11) # Rouge fonce pour le Juge
                        role_label = f"LE JUGE ({a_name})"
                    elif "procureur" in a_name.lower() or "demandeur" in a_name.lower():
                        role_color = (0.11, 0.38, 0.64) # Bleu pour la poursuite/demandeur
                    elif "defense" in a_name.lower() or "défense" in a_name.lower() or "defendeur" in a_name.lower() or "défendeur" in a_name.lower():
                        role_color = (0.11, 0.64, 0.38) # Vert pour la defense
                        
                    # Dessiner l'en-tête de l'intervention
                    if y + 25 > margin_bottom:
                        new_page()
                        
                    page.insert_text((margin_left, y), f"● {role_label}", fontsize=9, color=role_color, fontname="helvetica-bold")
                    y += 12
                    
                    # Le texte de l'intervention
                    # Si c'est un verdict ou une décision formelle, on la met en italique
                    is_verdict = (a_type == "VERDICT")
                    draw_text(content, fontsize=9, color=(0.15, 0.15, 0.15), bold=is_verdict, line_spacing=12.5, italic=is_verdict)
                    y += 5
                    
            draw_divider()
            
        # 3. Sauvegarder et fermer
        doc.save(pdf_path)
        doc.close()
        
        return pdf_path
