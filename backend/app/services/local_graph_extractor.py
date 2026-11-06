import os
import json
import uuid
import logging
from typing import Dict, Any, List, Optional
from openai import OpenAI
from ..config import Config

logger = logging.getLogger('mirofish.extractor')

class LocalGraphExtractor:
    """
    Replaces Zep's NLP extraction pipeline.
    Connects to the local LLM (Ollama/Mistral) and runs a custom Prompt to extract Entities & Relations (GraphRAG approach).
    """
    def __init__(self):
        # We use the config's LLM_BASE_URL (which is pointing to localhost:11434/v1 for Ollama usually)
        self.client = OpenAI(
            base_url=Config.LLM_BASE_URL,
            api_key=Config.LLM_API_KEY or "local",
            max_retries=2
        )
        self.model = Config.LLM_MODEL_NAME
        
    def extract_triplets(self, text: str, ontology: Dict[str, Any]) -> tuple[List[Dict], List[Dict]]:
        """
        Input: Text block + Ontology schema
        Output: Parsed nodes and edges
        """
        # Build prompt from ontology
        entity_types = [e["name"] for e in ontology.get("entity_types", [])]
        edge_types = [e["name"] for e in ontology.get("edge_types", [])]
        
        system_prompt = f"""
Tu es un pipeline expert d'extraction d'entités nommées (NER) et de graphes de connaissances juridiques québécois (GraphRAG).
Ta mission est d'extraire toutes les entités pertinentes et leurs relations à partir du texte fourni, conformément à l'ontologie cible.

ONTOLOGIE CIBLE (Types de nœuds autorisés) :
{', '.join(entity_types) if entity_types else 'Tout type pertinent'}

TYPES DE RELATIONS AUTORISÉS (Edge Types) :
{', '.join(edge_types) if edge_types else 'Toute relation pertinente'}

RÈGLES IMPÉRATIVES DE QUALIFICATION DES RÔLES ET DE LANGUE :
1. Utilise toujours le type d'entité le plus précis de l'ONTOLOGIE CIBLE.
2. N'inclus PAS dans les nœuds d'acteurs les noms de causes jurisprudentielles citées uniquement à titre de précédents (ex: 'Productions Pram inc.', 'Lemay', 'Biron') — classe les arrêts sous le type 'Jurisprudence' uniquement s'il est autorisé.
3. Rédige OBLIGATOIREMENT tous les champs 'summary' (résumé du rôle) et 'fact' (description de la relation) en FRANÇAIS juridique clair et précis. N'utilise jamais l'anglais dans les résumés.

Retourne les données STRICTEMENT au format JSON suivant, sans balises Markdown ni texte explicatif :
{{
  "nodes": [
     {{"uuid": "unique_string_1", "label": "Person", "name": "Jean Tremblay", "summary": "Demandeur dans le litige civil, charpentier-menuisier de 48 ans."}}
  ],
  "edges": [
     {{"uuid": "edge_id_1", "source": "unique_string_1", "target": "unique_string_2", "source_label": "Person", "target_label": "Company", "label": "SUES", "fact": "Jean Tremblay réclame une indemnité à la défenderesse."}}
  ]
}}

RÈGLES TECHNIQUES :
1. Réutilise le même 'uuid' si la même entité apparaît plusieurs fois.
2. Le champ 'label' DOIT correspondre exactement à l'un des types permis.
3. Ta réponse doit être uniquement du JSON valide.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"TEXTE DU DOSSIER À ANALYSER :\n{text}"}
                ],
                temperature=0.0
            )
            
            raw_content = response.choices[0].message.content.strip()
            
            # Clean up potential markdown formatting block
            if raw_content.startswith("```json"):
                raw_content = raw_content[7:]
            if raw_content.startswith("```"):
                raw_content = raw_content[3:]
            if raw_content.endswith("```"):
                raw_content = raw_content[:-3]
                
            parsed = json.loads(raw_content)
            
            # Post-process nodes to inject random uuids explicitly if they don't have them
            return parsed.get("nodes", []), parsed.get("edges", [])
            
        except Exception as e:
            logger.error(f"Extraction failed for chunk. Error: {e}")
            return [], []
