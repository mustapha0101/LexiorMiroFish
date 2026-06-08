import os
import kuzu
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger('mirofish.kuzu')

class LocalGraphDatabase:
    """
    Wrapper for Kuzu DB to replicate Zep's Graph functionality entirely locally.
    Each graph gets its own directory to maintain isolation.
    """
    import threading
    _KUZU_DATABASES = {}

    def __init__(self, graph_id: str, base_path: str = None, read_only: bool = False):
        if base_path is None:
            # Default to uploads/kuzu
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            base_path = os.path.join(base_dir, 'uploads', 'kuzu')
            
        self.graph_dir = os.path.join(base_path, graph_id)
        os.makedirs(self.graph_dir, exist_ok=True)
        self.graph_id = graph_id
        self.read_only = read_only
        self.db = None
        self.conn = None
        
        import time
        import random

        max_attempts = 15
        for attempt in range(max_attempts):
            try:
                # If read_only is requested, try opening read_only first
                if self.read_only:
                    self.db = kuzu.Database(self.graph_dir, read_only=True, max_db_size=1024 * 1024 * 1024)
                else:
                    self.db = kuzu.Database(self.graph_dir, read_only=False, max_db_size=1024 * 1024 * 1024)
                break
            except RuntimeError as e:
                err_str = str(e).lower()
                if "lock" in err_str or "descriptor" in err_str:
                    if attempt < max_attempts - 1:
                        # Sleep a random short interval before retrying
                        time.sleep(0.1 + random.random() * 0.2)
                        continue
                    else:
                        # Fallback to read-only if we cannot acquire the lock
                        try:
                            self.db = kuzu.Database(self.graph_dir, read_only=True, max_db_size=1024 * 1024 * 1024)
                            break
                        except RuntimeError:
                            raise e
                elif "wal" in err_str or "recovery" in err_str or "corrupt" in err_str:
                    logger.warning(f"Corrupted Kuzu WAL/DB detected! Resetting directory {self.graph_dir}")
                    import shutil
                    shutil.rmtree(self.graph_dir, ignore_errors=True)
                    os.makedirs(self.graph_dir, exist_ok=True)
                    try:
                        self.db = kuzu.Database(self.graph_dir, read_only=False, max_db_size=1024 * 1024 * 1024)
                        break
                    except RuntimeError:
                        if attempt < max_attempts - 1:
                            time.sleep(0.1 + random.random() * 0.2)
                            continue
                        raise e
                else:
                    raise e
            
        self.conn = kuzu.Connection(self.db)
        self._results = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        if hasattr(self, '_results') and self._results:
            for res in self._results:
                try:
                    res.close()
                except Exception:
                    pass
            self._results.clear()
        try:
            if hasattr(self, 'conn') and self.conn:
                self.conn.close()
                self.conn = None
        except Exception:
            pass
        try:
            if hasattr(self, 'db') and self.db:
                self.db.close()
                self.db = None
        except Exception:
            pass
        
    def _execute(self, query: str, parameters: dict = None):
        if parameters is None:
            parameters = {}
        try:
            res = self.conn.execute(query, parameters)
            self._results.append(res)
            return res
        except Exception as e:
            logger.error(f"Kuzu execution error on query: {query}\nError: {e}")
            raise e

    def _get_all_tables(self) -> List[str]:
        tables = []
        try:
            res = self._execute("CALL show_tables() RETURN *")
            while res.has_next():
                row = res.get_next()
                if len(row) > 1:
                    tables.append(row[1])
        except Exception as e:
            logger.warning(f"Failed to fetch tables: {e}")
        return tables

    def set_ontology(self, ontology: Dict[str, Any]):
        """
        Dynamically generates Kuzu Schema based on the generated Ontology.
        """
        logger.info(f"Setting Kuzu ontology for graph {self.graph_id}")
        
        # 1. Create Node Tables
        # All entities get a generic 'uuid', 'name', 'summary' plus whatever attributes were defined
        for entity_def in ontology.get("entity_types", []):
            name = entity_def.get("name")
            if not name:
                logger.warning(f"Skipping entity definition without a valid name: {entity_def}")
                continue
            # To avoid Cypher reserved word clashes, we namespace node tables
            table_name = f"Node_{name}"
            
            # Check if table exists
            tables = self._get_all_tables()
            
            if table_name not in tables:
                # Build schema: We store attributes as JSON strings if they are dynamic
                query = f"CREATE NODE TABLE {table_name} (uuid STRING, name STRING, summary STRING, attributes STRING, PRIMARY KEY (uuid))"
                self._execute(query)

        # 2. Create Rel Tables
        for edge_def in ontology.get("edge_types", []):
            name = edge_def.get("name")
            if not name:
                logger.warning(f"Skipping edge definition without a valid name: {edge_def}")
                continue
            table_name = f"Rel_{name}"
            
            # Check if table exists
            tables = self._get_all_tables()
            
            if table_name not in tables:
                source_targets = edge_def.get("source_targets", [])
                if not source_targets:
                    continue
                
                # In Kuzu, Relationships can have multiple FROM/TO definitions
                for st in source_targets:
                    src = f"Node_{st.get('source', 'Entity')}"
                    tgt = f"Node_{st.get('target', 'Entity')}"
                    
                    try:
                        query = f"CREATE REL TABLE {table_name} (FROM {src} TO {tgt}, uuid STRING, fact STRING, attributes STRING)"
                        self._execute(query)
                        break # Simplification: Kuzu generally wants uniform rels or multigraph definitions. 
                    except Exception as e:
                        # Table might already exist from previous iteration or src/tgt node might not exist dynamically
                        logger.warning(f"Could not create rel {table_name} FROM {src} TO {tgt}: {e}")

    def upsert_triplets(self, nodes: List[Dict], edges: List[Dict]):
        """
        Takes LLM extracted nodes/edges and inserts them into Kuzu.
        nodes = [{"uuid": "1", "label": "Person", "name": "Alice", "summary": "...", "attributes": {}}]
        edges = [{"uuid": "e1", "label": "KNOWS", "source": "1", "target": "2", "fact": "..."}]
        """
        existing_tables = self._get_all_tables()
        node_labels = {}
        
        # Upsert Nodes
        for n in nodes:
            label = n.get("label", "Entity")
            uuid_val = n.get("uuid")
            if uuid_val:
                node_labels[uuid_val] = label
                
            table_name = f"Node_{label}"
            
            # Dinamically create table if it doesn't exist
            if table_name not in existing_tables:
                try:
                    self._execute(f"CREATE NODE TABLE {table_name} (uuid STRING, name STRING, summary STRING, attributes STRING, PRIMARY KEY (uuid))")
                    existing_tables.append(table_name)
                except Exception as e:
                    logger.debug(f"Failed to create new node table {table_name}: {e}")
                    continue
            
            name = n.get("name", "")
            summary = n.get("summary", "")
            attributes = json.dumps(n.get("attributes", {}))
            
            query = "MERGE (n:" + table_name + " {uuid: $uuid}) ON MATCH SET n.name = $name, n.summary = $summary, n.attributes = $attributes ON CREATE SET n.name = $name, n.summary = $summary, n.attributes = $attributes"
            try:
                self._execute(query, {"uuid": uuid_val, "name": name, "summary": summary, "attributes": attributes})
            except Exception as e:
                # Don't log spam for data errors
                pass

        # Upsert Edges
        for e in edges:
            label = e.get("label", "RELATION")
            table_name = f"Rel_{label}"
            uuid_val = e.get("uuid")
            fact = e.get("fact", "")
            attributes = json.dumps(e.get("attributes", {}))
            
            src_uuid = e.get("source")
            tgt_uuid = e.get("target")
            
            src_label = e.get("source_label") or node_labels.get(src_uuid, "Entity")
            tgt_label = e.get("target_label") or node_labels.get(tgt_uuid, "Entity")
            
            src_table = f"Node_{src_label}"
            tgt_table = f"Node_{tgt_label}"
            
            # Ensure src and tgt node tables actually exist!
            if src_table not in existing_tables or tgt_table not in existing_tables:
                continue

            # Ensure strict relation tables per src_label/tgt_label to avoid schema combo errors
            combo_table_name = f"Rel_{label}_{src_label}_{tgt_label}"
            if combo_table_name not in existing_tables:
                try:
                    self._execute(f"CREATE REL TABLE {combo_table_name} (FROM {src_table} TO {tgt_table}, uuid STRING, fact STRING, attributes STRING)")
                    existing_tables.append(combo_table_name)
                except Exception:
                    pass
            
            query = "MATCH (a:" + src_table + " {uuid: $src_uuid}), (b:" + tgt_table + " {uuid: $tgt_uuid}) CREATE (a)-[r:" + combo_table_name + " {uuid: $uuid, fact: $fact, attributes: $attributes}]->(b)"
            try:
                self._execute(query, {"src_uuid": src_uuid, "tgt_uuid": tgt_uuid, "uuid": uuid_val, "fact": fact, "attributes": attributes})
            except Exception:
                pass

    def fetch_all_nodes(self):
        nodes_data = []
        all_tables = self._get_all_tables()
        tables = [t for t in all_tables if t.startswith("Node_")]
        
        for table in tables:
            actual_label = table.replace("Node_", "")
            query = f"MATCH (n:{table}) RETURN n.uuid, n.name, n.summary, n.attributes"
            try:
                results = self._execute(query)
                while results.has_next():
                    row = results.get_next()
                    nodes_data.append({
                        "uuid": row[0],
                        "name": row[1],
                        "summary": row[2],
                        "labels": [actual_label],
                        "attributes": json.loads(row[3]) if row[3] else {}
                    })
            except Exception:
                pass
        return nodes_data

    def fetch_all_edges(self):
        edges_data = []
        all_tables = self._get_all_tables()
        node_tables = [t for t in all_tables if t.startswith("Node_")]
        rel_tables = [t for t in all_tables if t.startswith("Rel_")]
        
        for rel in rel_tables:
            actual_label = rel.replace("Rel_", "")
            for src in node_tables:
                for tgt in node_tables:
                    query = f"MATCH (a:{src})-[r:{rel}]->(b:{tgt}) RETURN r.uuid, r.fact, a.uuid, b.uuid, r.attributes"
                    try:
                        results = self._execute(query)
                        while results.has_next():
                            row = results.get_next()
                            edges_data.append({
                                "uuid": row[0],
                                "fact": row[1],
                                "source_node_uuid": row[2],
                                "target_node_uuid": row[3],
                                "name": actual_label,
                                "attributes": json.loads(row[4]) if row[4] else {}
                            })
                    except Exception:
                        pass
        return edges_data

    def delete_graph(self):
        try:
            self.close()
        except Exception:
            pass
        import shutil
        if os.path.exists(self.graph_dir):
            shutil.rmtree(self.graph_dir, ignore_errors=True)

