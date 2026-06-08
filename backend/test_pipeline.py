import os
import sys
import uuid
import traceback

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.services.graph_builder import GraphBuilderService
from app.models.project import ProjectManager
from dotenv import load_dotenv

load_dotenv(".env")

try:
    project_id = "proj_0ee8b1efc429"
    project = ProjectManager.get_project(project_id)
    if not project:
        print("Project not found.")
        sys.exit(1)
        
    text = ProjectManager.get_extracted_text(project_id)
    print(f"Loaded {len(text)} characters.")
    
    # Take a tiny chunk for instant 1-batch test
    chunks = [text[:1000]]
    ontology = project.ontology
    
    builder = GraphBuilderService()
    graph_id = f"test_graph_{uuid.uuid4().hex[:8]}"
    print(f"Creating local graph {graph_id}...")
    builder.create_graph(graph_id)
    builder.set_ontology(graph_id, ontology)
    
    print("Sending chunk to LocalGraphExtractor...")
    builder.add_text_batches(graph_id, chunks, batch_size=1)
    
    graph_data = builder.get_graph_data(graph_id)
    print("\n--- GRAPH DATA ---")
    print(f"Nodes: {len(graph_data['nodes'])}")
    print(f"Edges: {len(graph_data['edges'])}")
    print("\nSUCCESS!")
except Exception as e:
    print("\n[CRITICAL ERROR]")
    traceback.print_exc()
