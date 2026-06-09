"""
Local Entity Reader 服务 (Formerly ZepEntityReader)
从Kuzu DB读取图谱信息，对接原版MiroFish生态
"""

import time
import logging
from typing import Dict, Any, List, Optional, Set, Callable, TypeVar
from dataclasses import dataclass, field

from ..config import Config
from ..utils.logger import get_logger

from .local_graph_database import LocalGraphDatabase

logger = get_logger('mirofish.zep_entity_reader')

T = TypeVar('T')

@dataclass
class EntityNode:
    """实体节点数据结构"""
    uuid: str
    name: str
    labels: List[str]
    summary: str
    attributes: Dict[str, Any]
    related_edges: List[Dict[str, Any]] = field(default_factory=list)
    related_nodes: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "labels": self.labels,
            "summary": self.summary,
            "attributes": self.attributes,
            "related_edges": self.related_edges,
            "related_nodes": self.related_nodes,
        }
    
    def get_entity_type(self) -> Optional[str]:
        """获取实体类型（排除默认的Entity标签）"""
        for label in self.labels:
            if label not in ["Entity", "Node"]:
                return label
        return None

@dataclass
class FilteredEntities:
    """过滤后的实体集合"""
    entities: List[EntityNode]
    entity_types: Set[str]
    total_count: int
    filtered_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "entity_types": list(self.entity_types),
            "total_count": self.total_count,
            "filtered_count": self.filtered_count,
        }

class ZepEntityReader:
    """
    ZepEntityReader (Now backed by Kuzu DB)
    1. 从本地Kuzu读取节点
    2. 筛选
    """
    def __init__(self, api_key: Optional[str] = None):
        # We don't need Zep config anymore
        pass
        
    def _call_with_retry(self, func: Callable[[], T], operation_name: str, max_retries: int = 2, initial_delay: float = 1.0) -> T:
        try:
            return func()
        except Exception as e:
            logger.error(f"Local Kuzu DB Error during {operation_name}: {e}")
            raise e
            
    def get_all_nodes(self, graph_id: str) -> List[Dict[str, Any]]:
        with LocalGraphDatabase(graph_id, read_only=True) as db:
            return db.fetch_all_nodes()

    def get_all_edges(self, graph_id: str) -> List[Dict[str, Any]]:
        with LocalGraphDatabase(graph_id, read_only=True) as db:
            return db.fetch_all_edges()
        
    def get_node_edges(self, node_uuid: str, graph_id: str = None) -> List[Dict[str, Any]]:
        # In Kuzu, we need the graph_id to open the DB.
        # But this function signature misses graph_id in original MiroFish!
        # Usually it's called after getting graph_id. 
        # Modifying implementation to fetch from context if possible or returning []
        # Actually in filter_defined_entities, it reads from all_edges which avoids this issue.
        logger.warning(f"get_node_edges without graph_id is deprecated. Pass graph_id or get edges statically.")
        # If we really need this, we'd have to scan all kuzu DBs or pass graph_id.
        return []

    def filter_defined_entities(self, graph_id: str, defined_entity_types: Optional[List[str]] = None, enrich_with_edges: bool = True) -> FilteredEntities:
        with LocalGraphDatabase(graph_id, read_only=True) as db:
            all_nodes = db.fetch_all_nodes()
            total_count = len(all_nodes)
            all_edges = db.fetch_all_edges() if enrich_with_edges else []
        node_map = {n["uuid"]: n for n in all_nodes}
        
        filtered_entities = []
        entity_types_found = set()
        
        for node in all_nodes:
            labels = node.get("labels", [])
            custom_labels = [l for l in labels if l not in ["Entity", "Node"]]
            
            if not custom_labels:
                continue
                
            if defined_entity_types:
                matching_labels = [l for l in custom_labels if l in defined_entity_types]
                if not matching_labels:
                    continue
                entity_type = matching_labels[0]
            else:
                entity_type = custom_labels[0]
                
            entity_types_found.add(entity_type)
            
            entity = EntityNode(
                uuid=node["uuid"],
                name=node["name"],
                labels=labels,
                summary=node["summary"],
                attributes=node["attributes"],
            )
            
            if enrich_with_edges:
                related_edges = []
                related_node_uuids = set()
                
                for edge in all_edges:
                    if edge["source_node_uuid"] == node["uuid"]:
                        related_edges.append({
                            "direction": "outgoing",
                            "edge_name": edge["name"],
                            "fact": edge["fact"],
                            "target_node_uuid": edge["target_node_uuid"],
                        })
                        related_node_uuids.add(edge["target_node_uuid"])
                    elif edge["target_node_uuid"] == node["uuid"]:
                        related_edges.append({
                            "direction": "incoming",
                            "edge_name": edge["name"],
                            "fact": edge["fact"],
                            "source_node_uuid": edge["source_node_uuid"],
                        })
                        related_node_uuids.add(edge["source_node_uuid"])
                
                entity.related_edges = related_edges
                related_nodes = []
                for related_uuid in related_node_uuids:
                    if related_uuid in node_map:
                        related_node = node_map[related_uuid]
                        related_nodes.append({
                            "uuid": related_node["uuid"],
                            "name": related_node["name"],
                            "labels": related_node["labels"],
                            "summary": related_node.get("summary", ""),
                        })
                
                entity.related_nodes = related_nodes
            
            filtered_entities.append(entity)
            
        return FilteredEntities(
            entities=filtered_entities,
            entity_types=entity_types_found,
            total_count=total_count,
            filtered_count=len(filtered_entities),
        )

    def get_entity_with_context(self, graph_id: str, entity_uuid: str) -> Optional[EntityNode]:
        with LocalGraphDatabase(graph_id, read_only=True) as db:
            all_nodes = db.fetch_all_nodes()
        node_map = {n["uuid"]: n for n in all_nodes}
        node = node_map.get(entity_uuid)
        if not node:
            return None
            
        all_edges = db.fetch_all_edges()
        
        related_edges = []
        related_node_uuids = set()
        
        for edge in all_edges:
            if edge["source_node_uuid"] == entity_uuid:
                related_edges.append({
                    "direction": "outgoing",
                    "edge_name": edge["name"],
                    "fact": edge["fact"],
                    "target_node_uuid": edge["target_node_uuid"],
                })
                related_node_uuids.add(edge["target_node_uuid"])
            elif edge["target_node_uuid"] == entity_uuid:
                related_edges.append({
                    "direction": "incoming",
                    "edge_name": edge["name"],
                    "fact": edge["fact"],
                    "source_node_uuid": edge["source_node_uuid"],
                })
                related_node_uuids.add(edge["source_node_uuid"])
                
        related_nodes = []
        for related_uuid in related_node_uuids:
            if related_uuid in node_map:
                related_node = node_map[related_uuid]
                related_nodes.append({
                    "uuid": related_node["uuid"],
                    "name": related_node["name"],
                    "labels": related_node["labels"],
                    "summary": related_node.get("summary", ""),
                })
                
        return EntityNode(
            uuid=node["uuid"],
            name=node["name"],
            labels=node["labels"],
            summary=node["summary"],
            attributes=node["attributes"],
            related_edges=related_edges,
            related_nodes=related_nodes,
        )

    def get_entities_by_type(self, graph_id: str, entity_type: str, enrich_with_edges: bool = True) -> List[EntityNode]:
        result = self.filter_defined_entities(
            graph_id=graph_id,
            defined_entity_types=[entity_type],
            enrich_with_edges=enrich_with_edges
        )
        return result.entities
