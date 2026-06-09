"""
Service de construction de graphes
Interface 2 : Construction de graphe à l'aide de Kuzu DB locale (Sovereign GraphRAG)
"""

import os
import uuid
import time
import threading
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

from ..config import Config
from ..models.task import TaskManager, TaskStatus
from .text_processor import TextProcessor
from ..utils.locale import t, get_locale, set_locale

from .local_graph_database import LocalGraphDatabase
from .local_graph_extractor import LocalGraphExtractor

logger = logging.getLogger("mirofish.graph_builder")


@dataclass
class GraphInfo:
    """Informations du graphe"""
    graph_id: str
    node_count: int
    edge_count: int
    entity_types: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "entity_types": self.entity_types,
        }


class GraphBuilderService:
    """
    Service de construction de graphes
    Responsable d'appeler le LLM local et Kuzu DB pour construire le graphe de connaissances
    """
    def __init__(self, api_key: Optional[str] = None):
        # api_key parameter is kept for backward compatibility with `api/graph.py` signature
        self.task_manager = TaskManager()
        self.extractor = LocalGraphExtractor()
        
    def build_graph_async(self, text: str, ontology: dict[str, Any], graph_name: str, chunk_size: int, chunk_overlap: int, batch_size: int):
        pass # Already managed in api/graph.py via direct threading approach

    def create_graph(self, name: str) -> str:
        """Créer le répertoire du graphe"""
        graph_id = f"lexior_{uuid.uuid4().hex[:16]}"
        with LocalGraphDatabase(graph_id) as db:
            pass
        # Keep db local directory ready
        return graph_id
    
    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]):
        """Configurer l'ontologie du graphe dans Kuzu DB"""
        with LocalGraphDatabase(graph_id) as db:
            db.set_ontology(ontology)
    
    def add_text_batches(
        self,
        graph_id: str,
        chunks: List[str],
        batch_size: int = 3,
        progress_callback: Optional[Callable] = None
    ) -> List[str]:
        """Extraire les entités à l'aide du LLM et les insérer dans Kuzu DB"""
        """Extraire les entités à l'aide du LLM et les insérer dans Kuzu DB"""
        with LocalGraphDatabase(graph_id) as db:
            # Determine ontology to pass to extractor by finding the corresponding project
            ontology = {"entity_types": [], "edge_types": []}
            try:
                from ..models.project import ProjectManager
                projects = ProjectManager.list_projects(limit=100)
                for p in projects:
                    if p.graph_id == graph_id:
                        ontology = p.ontology or ontology
                        break
            except Exception as ont_err:
                logger.error(f"Error fetching ontology for graph_id {graph_id}: {ont_err}")
            
            episode_uuids = []
            total_chunks = len(chunks)
            
            for i in range(0, total_chunks, batch_size):
                batch_chunks = chunks[i:i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (total_chunks + batch_size - 1) // batch_size
                
                if progress_callback:
                    progress = (i + len(batch_chunks)) / total_chunks
                    progress_callback(
                        t('progress.sendingBatch', current=batch_num, total=total_batches, chunks=len(batch_chunks)),
                        progress
                    )
                
                for chunk in batch_chunks:
                    try:
                        nodes, edges = self.extractor.extract_triplets(chunk, ontology)
                        if nodes or edges:
                            db.upsert_triplets(nodes, edges)
                        episode_uuids.append(uuid.uuid4().hex)
                    except Exception as e:
                        pass
            
            return episode_uuids
    
    def _wait_for_episodes(self, episode_uuids: List[str], progress_callback: Optional[Callable] = None):
        """Complété directement en local de manière synchrone, pas besoin d'attendre le traitement Cloud"""
        if progress_callback:
            progress_callback(t('progress.processingComplete', completed=len(episode_uuids), total=len(episode_uuids)), 1.0)
    
    def _get_graph_info(self, graph_id: str) -> GraphInfo:
        """Obtenir les informations du graphe"""
        with LocalGraphDatabase(graph_id, read_only=True) as db:
            nodes = db.fetch_all_nodes()
            edges = db.fetch_all_edges()

            entity_types = list(set([l for n in nodes for l in n.get("labels", [])]))

            return GraphInfo(
                graph_id=graph_id,
                node_count=len(nodes),
                edge_count=len(edges),
                entity_types=entity_types
            )
    
    _GRAPH_DATA_CACHE = {}

    def get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        """
        Obtenir les données complètes du graphe pour affichage dans l'interface utilisateur
        """
        try:
            with LocalGraphDatabase(graph_id, read_only=True) as db:
                nodes = db.fetch_all_nodes()
                edges = db.fetch_all_edges()
            
            # Remap to UI standards
            nodes_data = []
            node_map = {}
            for n in nodes:
                uuid_val = n.get("uuid", str(uuid.uuid4()))
                node_map[uuid_val] = n.get("name", "")
                nodes_data.append({
                    "uuid": uuid_val,
                    "name": n.get("name", ""),
                    "labels": n.get("labels", ["Entity"]),
                    "summary": n.get("summary", ""),
                    "attributes": n.get("attributes", {}),
                    "created_at": None,
                })
                
            edges_data = []
            for e in edges:
                src = e.get("source_node_uuid")
                tgt = e.get("target_node_uuid")
                edges_data.append({
                    "uuid": e.get("uuid", str(uuid.uuid4())),
                    "name": e.get("name", ""),
                    "fact": e.get("fact", ""),
                    "fact_type": e.get("name", ""),
                    "source_node_uuid": src,
                    "target_node_uuid": tgt,
                    "source_node_name": node_map.get(src, ""),
                    "target_node_name": node_map.get(tgt, ""),
                    "attributes": e.get("attributes", {}),
                    "episodes": [],
                })
                
            res = {
                "graph_id": graph_id,
                "nodes": nodes_data,
                "edges": edges_data,
                "node_count": len(nodes_data),
                "edge_count": len(edges_data),
            }
            self._GRAPH_DATA_CACHE[graph_id] = res
            return res
        except Exception as e:
            logger.warning(f"Error fetching graph data for {graph_id}: {e}. Returning cached version if available.")
            if graph_id in self._GRAPH_DATA_CACHE:
                return self._GRAPH_DATA_CACHE[graph_id]
            return {
                "graph_id": graph_id,
                "nodes": [],
                "edges": [],
                "node_count": 0,
                "edge_count": 0,
            }
    
    def delete_graph(self, graph_id: str):
        """Supprimer la base de données Kuzu locale"""
        with LocalGraphDatabase(graph_id) as db:
            db.delete_graph()
