"""
Script pour ingérer le dataset de jurisprudence de HuggingFace.
Télécharge le dataset et le stocke localement sous format JSON.
"""

import os
import json
import logging
from datasets import load_dataset

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('ingest_jurisprudence')

DATASET_ID = "intelliwork/lexiorgpt-raw-32b-full-fr"
HF_TOKEN = os.environ.get("HF_TOKEN", "")
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), '../uploads')
OUTPUT_FILE = os.path.join(UPLOADS_DIR, 'jurisprudence.json')

def ingest_dataset():
    logger.info(f"Début du téléchargement du dataset {DATASET_ID}...")
    
    # Assurez-vous que le répertoire existe
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    
    try:
        # Configuration stream=False pour tout télécharger
        ds = load_dataset(DATASET_ID, split='train', token=HF_TOKEN)
        
        cas_juridiques = []
        for row in ds:
            cas_juridiques.append({
                "law_name": row.get("law_name", ""),
                "citation": row.get("citation", ""),
                "section_id": row.get("section_id", ""),
                "category": row.get("category", ""),
                "question": row.get("question", ""),
                "answer": row.get("answer", ""),
                "law_summary": row.get("law_summary", ""),
                "section_text": row.get("section_text", "")
            })
            
        # Sauvegarde en JSON
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(cas_juridiques, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Ingestion réussie ! {len(cas_juridiques)} cas sauvegardés dans {OUTPUT_FILE}")
        
    except Exception as e:
        logger.error(f"Erreur lors de l'ingestion: {e}")

if __name__ == "__main__":
    # We may need to install 'datasets' package first
    print("Veuillez vous assurer que 'datasets' est installé: pip install datasets huggingface_hub")
    ingest_dataset()
