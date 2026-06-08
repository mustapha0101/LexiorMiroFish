import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.project import ProjectManager
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(".env")

api_key = os.getenv("LLM_API_KEY")
base_url = os.getenv("LLM_BASE_URL")

client = OpenAI(
    api_key=api_key,
    base_url=base_url
)

project_id = "proj_688141b4ea83"
project = ProjectManager.get_project(project_id)
text = ProjectManager.get_extracted_text(project_id)

from app.services.ontology_generator import OntologyGenerator, ONTOLOGY_SYSTEM_PROMPT
generator = OntologyGenerator()
messages = [
    {"role": "system", "content": ONTOLOGY_SYSTEM_PROMPT},
    {"role": "user", "content": f"{generator._build_user_message([text], project.simulation_requirement, '')}"}
]

try:
    response = client.chat.completions.create(
        model="gemini-2.5-flash",
        messages=messages,
        max_tokens=8192,
        response_format={"type": "json_object"}
    )
    print("FINISH REASON:", response.choices[0].finish_reason)
    content = response.choices[0].message.content
    print("LENGTH:", len(content))
    print("LAST 200 CHARS:", content[-200:])
except Exception as e:
    print("ERROR:", e)
