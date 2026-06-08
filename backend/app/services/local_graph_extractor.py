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
You are an expert Graph DB Named Entity Recognition (NER) pipeline.
Your task is to extract all entities and their relationships from the provided text according to the target Ontology.

TARGET ONTOLOGY (Permitted Node Types):
{', '.join(entity_types) if entity_types else 'Any'}

TARGET EDGE TYPES (Permitted Relationship Types):
{', '.join(edge_types) if edge_types else 'Any'}

IMPORTANT ROLE-LABEL RULES:
1. Always use the most specific entity label from the TARGET ONTOLOGY. 
2. Do NOT use the generic 'Person' label if a more specific label applies. For example:
   - If a person is a witness or testifying, you MUST label them as 'Witness'.
   - If a person is the accused or defendant in a criminal context, you MUST label them as 'AccusedPerson'.
   - If a person is the prosecutor or crown, you MUST label them as 'Prosecutor'.
   - If a person is a judge presiding over a case, you MUST label them as 'Judge'.
   - If a person is a police officer or investigator, you MUST label them as 'PoliceOfficer'.
   - Only use 'Person' for individuals who do not fit any of these specific legal roles.

Return the data STRICTLY in the following JSON format without any markdown wrappers or text:
{{
  "nodes": [
     {{"uuid": "unique_string_1", "label": "Person", "name": "John Doe", "summary": "A developer."}}
  ],
  "edges": [
     {{"uuid": "edge_id_1", "source": "unique_string_1", "target": "unique_string_2", "source_label": "Person", "target_label": "Person", "label": "WORKS_WITH", "fact": "John works with Jane."}}
  ]
}}

IMPORTANT RULES:
1. Try to reuse uuids if the same entity appears multiple times.
2. Label MUST exactly match one of the permitted types if provided.
3. Your output must be purely valid JSON.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"TEXT TO PROCESS:\n{text}"}
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
