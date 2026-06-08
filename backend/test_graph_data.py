import os
import sys
import traceback
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.graph_builder import GraphBuilderService

try:
    builder = GraphBuilderService()
    graph_data = builder.get_graph_data("mirofish_be1b9fd606994b95")
    print("Success. Graph nodes:", len(graph_data["nodes"]), "edges:", len(graph_data["edges"]))
except Exception as e:
    print("ERROR:")
    traceback.print_exc()
