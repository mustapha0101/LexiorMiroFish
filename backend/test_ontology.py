import os
import sys
import traceback
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.project import ProjectManager
from app.services.ontology_generator import OntologyGenerator
from dotenv import load_dotenv

load_dotenv(".env")

try:
    project_id = "proj_688141b4ea83"
    project = ProjectManager.get_project(project_id)
    if not project:
        print(f"Project {project_id} not found!")
    else:
        text = ProjectManager.get_extracted_text(project_id)
        if not text:
            print("No text extracted!")
        else:
            print(f"Text length: {len(text)}")
            print(f"Simulation requirement: {project.simulation_requirement}")
            
            generator = OntologyGenerator()
            ontology = generator.generate(
                document_texts=[text],
                simulation_requirement=project.simulation_requirement,
                additional_context=""
            )
            print("SUCCESS")
            print(ontology)
except Exception as e:
    print("ERROR OCCURRED:")
    traceback.print_exc()
