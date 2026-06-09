"""
Cognitive Memory Service
Gère la persistance de l'état des agents et de leurs fragments de mémoire autobiographique dans Kuzu.
"""

import os
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from .local_graph_database import LocalGraphDatabase
from .cognitive_engine import CognitiveAgentState

logger = logging.getLogger('mirofish.cognitive_memory')

class CognitiveMemoryService:
    """Service de gestion de la mémoire autobiographique et des états dans Kuzu DB."""

    @classmethod
    def _get_db(cls, simulation_id: str, read_only: bool = False) -> LocalGraphDatabase:
        """Retourne l'instance Kuzu DB pour la simulation."""
        return LocalGraphDatabase(simulation_id, read_only=read_only)

    @classmethod
    def _init_tables_if_needed(cls, db: LocalGraphDatabase):
        """Initialise les tables de nœuds et relations cognitives si elles n'existent pas."""
        tables = db._get_all_tables()
        
        # 1. Table des états cognitifs
        if "Node_CognitiveState" not in tables:
            try:
                db._execute(
                    "CREATE NODE TABLE Node_CognitiveState "
                    "(uuid STRING, name STRING, summary STRING, attributes STRING, PRIMARY KEY (uuid))"
                )
                logger.info("Table Node_CognitiveState créée avec succès dans Kuzu DB.")
            except Exception as e:
                logger.error(f"Erreur lors de la création de Node_CognitiveState: {e}")

        # 2. Table des fragments de mémoire
        if "Node_MemoryFragment" not in tables:
            try:
                db._execute(
                    "CREATE NODE TABLE Node_MemoryFragment "
                    "(uuid STRING, name STRING, summary STRING, attributes STRING, PRIMARY KEY (uuid))"
                )
                logger.info("Table Node_MemoryFragment créée avec succès dans Kuzu DB.")
            except Exception as e:
                logger.error(f"Erreur lors de la création de Node_MemoryFragment: {e}")

        # 3. Relation HAS_MEMORY
        # Remarque : Kuzu nécessite de spécifier explicitement les tables de départ et d'arrivée.
        if "Rel_HAS_MEMORY" not in tables and "Rel_HAS_MEMORY_CognitiveState_MemoryFragment" not in tables:
            try:
                db._execute(
                    "CREATE REL TABLE Rel_HAS_MEMORY "
                    "(FROM Node_CognitiveState TO Node_MemoryFragment, uuid STRING, fact STRING, attributes STRING)"
                )
                logger.info("Table relationnelle Rel_HAS_MEMORY créée avec succès.")
            except Exception as e:
                logger.debug(f"Erreur ou relation déjà existante pour Rel_HAS_MEMORY: {e}")
                
    @classmethod
    def save_agent_state(cls, simulation_id: str, agent_state: CognitiveAgentState):
        """Persiste l'état de l'agent (tensions, croyances, auto-narrations) dans Kuzu DB."""
        agent_id = agent_state.agent_id
        name = agent_state.name
        summary = agent_state.meta_narrative
        
        attributes = {
            "personality": agent_state.personality,
            "tensions": agent_state.tensions,
            "beliefs": agent_state.beliefs,
            "recent_reflection": agent_state.recent_reflection,
            "mood": agent_state.mood,
            "negative_interactions_count": agent_state.negative_interactions_count,
            "attention_budget": agent_state.attention_budget
        }
        
        # Write to local cache first to ensure multi-process cross-worker visibility on Render
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            cache_dir = os.path.join(base_dir, 'uploads', 'simulations', simulation_id)
            os.makedirs(cache_dir, exist_ok=True)
            cache_path = os.path.join(cache_dir, 'cognitive_states_cache.json')
            
            cache_data = {}
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, 'r', encoding='utf-8') as cf:
                        cache_data = json.load(cf)
                except Exception:
                    pass
            
            cache_data[agent_id] = {
                "agent_id": agent_id,
                "name": name,
                "meta_narrative": summary,
                "personality": attributes.get("personality", ""),
                "tensions": attributes.get("tensions", {}),
                "beliefs": attributes.get("beliefs", {}),
                "recent_reflection": attributes.get("recent_reflection", "")
            }
            
            with open(cache_path, 'w', encoding='utf-8') as cf:
                json.dump(cache_data, cf, ensure_ascii=False, indent=2)
        except Exception as cache_err:
            logger.warning(f"Failed to write cognitive states cache file: {cache_err}")

        with cls._get_db(simulation_id) as db:
            cls._init_tables_if_needed(db)
            attr_str = json.dumps(attributes, ensure_ascii=False)
            
            # Merge de l'état cognitif
            query = (
                "MERGE (n:Node_CognitiveState {uuid: $uuid}) "
                "ON MATCH SET n.name = $name, n.summary = $summary, n.attributes = $attributes "
                "ON CREATE SET n.name = $name, n.summary = $summary, n.attributes = $attributes"
            )
            try:
                db._execute(query, {
                    "uuid": agent_id,
                    "name": name,
                    "summary": summary,
                    "attributes": attr_str
                })
                logger.info(f"État cognitif de l'agent {name} ({agent_id}) sauvegardé dans Kuzu.")
            except Exception as e:
                logger.error(f"Impossible de sauvegarder l'état de l'agent {agent_id}: {e}")

    @classmethod
    def get_agent_state(cls, simulation_id: str, agent_id: str, agent_name: str = "") -> Optional[CognitiveAgentState]:
        """Récupère l'état d'un agent. Crée un état par défaut si aucun n'existe en base."""
        try:
            with cls._get_db(simulation_id, read_only=True) as db:
                query = "MATCH (n:Node_CognitiveState {uuid: $uuid}) RETURN n.name, n.summary, n.attributes"
                res = db._execute(query, {"uuid": agent_id})
                if res.has_next():
                    row = res.get_next()
                    name = row[0]
                    meta_narrative = row[1]
                    attr_data = json.loads(row[2]) if row[2] else {}
                    
                    return CognitiveAgentState(
                        agent_id=agent_id,
                        name=name,
                        personality=attr_data.get("personality", ""),
                        tensions=attr_data.get("tensions"),
                        beliefs=attr_data.get("beliefs"),
                        meta_narrative=meta_narrative,
                        recent_reflection=attr_data.get("recent_reflection", ""),
                        mood=attr_data.get("mood", "Neutre"),
                        negative_interactions_count=attr_data.get("negative_interactions_count", 0),
                        attention_budget=attr_data.get("attention_budget")
                    )
        except Exception as e:
            logger.warning(f"Erreur lors de la récupération de l'état pour l'agent {agent_id}: {e}")

        # État par défaut si non existant
        return CognitiveAgentState(
            agent_id=agent_id,
            name=agent_name or f"Agent_{agent_id}"
        )

    @classmethod
    def add_memory_fragment(cls, simulation_id: str, agent_id: str, event_desc: str, emotional_charge: float = 0.5):
        """Ajoute un fragment de mémoire autobiographique relié à l'état de l'agent."""
        with cls._get_db(simulation_id) as db:
            cls._init_tables_if_needed(db)
            
            fragment_id = f"frag_{uuid.uuid4().hex[:12]}"
            attributes = {
                "emotional_charge": emotional_charge,
                "strength": 1.0,  # Force initiale
                "created_at": datetime.now().isoformat()
            }
            attr_str = json.dumps(attributes)
            
            # 1. Créer le nœud de fragment
            query_node = (
                "CREATE (m:Node_MemoryFragment {uuid: $uuid, name: $name, summary: $summary, attributes: $attributes})"
            )
            # 2. Créer la relation HAS_MEMORY
            query_rel = (
                "MATCH (a:Node_CognitiveState {uuid: $agent_id}), (m:Node_MemoryFragment {uuid: $frag_id}) "
                "CREATE (a)-[r:Rel_HAS_MEMORY {uuid: $rel_id, fact: 'remembered', attributes: '{}'}]->(m)"
            )
            
            try:
                db._execute(query_node, {
                    "uuid": fragment_id,
                    "name": "MemoryFragment",
                    "summary": event_desc,
                    "attributes": attr_str
                })
                db._execute(query_rel, {
                    "agent_id": agent_id,
                    "frag_id": fragment_id,
                    "rel_id": f"rel_{uuid.uuid4().hex[:12]}"
                })
                logger.info(f"Fragment de mémoire '{event_desc[:30]}...' ajouté pour l'agent {agent_id}")
            except Exception as e:
                logger.error(f"Erreur lors de l'ajout de mémoire pour l'agent {agent_id}: {e}")

    @classmethod
    def get_active_memories(cls, simulation_id: str, agent_id: str, strength_threshold: float = 0.2) -> List[str]:
        """Récupère les descriptions des souvenirs actifs (dont la force est au-dessus du seuil)."""
        memories = []
        try:
            with cls._get_db(simulation_id, read_only=True) as db:
                query = (
                    "MATCH (a:Node_CognitiveState {uuid: $agent_id})-[r:Rel_HAS_MEMORY]->(m:Node_MemoryFragment) "
                    "RETURN m.summary, m.attributes"
                )
                res = db._execute(query, {"agent_id": agent_id})
                while res.has_next():
                    row = res.get_next()
                    summary = row[0]
                    attr_data = json.loads(row[1]) if row[1] else {}
                    strength = attr_data.get("strength", 1.0)
                    
                    if strength >= strength_threshold:
                        memories.append(summary)
        except Exception as e:
            logger.error(f"Erreur de lecture des souvenirs pour l'agent {agent_id}: {e}")
            
        return memories

    @classmethod
    def apply_memory_decay(cls, simulation_id: str, agent_id: str, decay_factor: float = 0.85):
        """Applique l'oubli sélectif en réduisant la force des souvenirs de l'agent. Supprime les souvenirs trop faibles."""
        with cls._get_db(simulation_id) as db:
            cls._init_tables_if_needed(db)
            
            # Récupérer les fragments reliés
            query = (
                "MATCH (a:Node_CognitiveState {uuid: $agent_id})-[r:Rel_HAS_MEMORY]->(m:Node_MemoryFragment) "
                "RETURN m.uuid, m.attributes"
            )
            
            fragments_to_update = []
            fragments_to_delete = []
            
            try:
                res = db._execute(query, {"agent_id": agent_id})
                while res.has_next():
                    row = res.get_next()
                    frag_id = row[0]
                    attr_data = json.loads(row[1]) if row[1] else {}
                    
                    # Réduction de la force
                    new_strength = attr_data.get("strength", 1.0) * decay_factor
                    
                    if new_strength < 0.15:
                        fragments_to_delete.append(frag_id)
                    else:
                        attr_data["strength"] = round(new_strength, 2)
                        fragments_to_update.append((frag_id, attr_data))
            except Exception as e:
                logger.error(f"Erreur de parcours des souvenirs à vieillir: {e}")
                return
                
            # Mettre à jour les souvenirs restants
            for frag_id, attr_data in fragments_to_update:
                update_query = "MATCH (m:Node_MemoryFragment {uuid: $uuid}) SET m.attributes = $attributes"
                try:
                    db._execute(update_query, {"uuid": frag_id, "attributes": json.dumps(attr_data)})
                except Exception:
                    pass
                    
            # Supprimer les souvenirs oubliés
            # En Kuzu, on supprime d'abord les relations puis le nœud
            for frag_id in fragments_to_delete:
                try:
                    # Supprimer la relation d'abord
                    db._execute(
                        "MATCH (a:Node_CognitiveState {uuid: $agent_id})-[r:Rel_HAS_MEMORY]->(m:Node_MemoryFragment {uuid: $frag_id}) "
                        "DELETE r", 
                        {"agent_id": agent_id, "frag_id": frag_id}
                    )
                    # Supprimer le nœud
                    db._execute("MATCH (m:Node_MemoryFragment {uuid: $uuid}) DELETE m", {"uuid": frag_id})
                    logger.info(f"Fragment de mémoire {frag_id} oublié et supprimé (strength < 0.15)")
                except Exception as e:
                    logger.debug(f"Impossible de supprimer le fragment {frag_id}: {e}")
