import os
import sys
import unittest
import shutil
from unittest.mock import MagicMock, patch

# Ensure backend root is in the path
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from app.services.sensitivity_analysis import SensitivityAnalysisEngine
from app.models.project import Project, ProjectStatus, ProjectManager

class TestSensitivityAnalysis(unittest.TestCase):

    def setUp(self):
        self.project_id = "test_project_sensitivity"
        self.db_path = os.path.join(base_dir, 'uploads', 'projects', self.project_id)
        if os.path.exists(self.db_path):
            shutil.rmtree(self.db_path, ignore_errors=True)

        # Create a mock project
        self.project = ProjectManager.create_project(name="R. c. Gauthier", project_id=self.project_id)
        self.project.simulation_requirement = "Accusation d'arme à feu dans un sac souple."
        ProjectManager.save_project(self.project)

    def tearDown(self):
        # Clean up
        if os.path.exists(self.db_path):
            shutil.rmtree(self.db_path, ignore_errors=True)

    @patch('app.services.sensitivity_analysis.OpenAI')
    def test_analyze_case_defense(self, mock_openai):
        # Mock OpenAI response
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_response = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json_data = """
        [
            {
                "node_name": "Sac en nylon",
                "vector_name": "Neutralisation Sensorielle",
                "impact": "+45% de chances d'acquittement",
                "impact_value": 45,
                "match_plan": "Maître, commandez une expertise technique du sac Adidas.",
                "request_type": "expertise"
            }
        ]
        """
        
        opportunities = SensitivityAnalysisEngine.analyze_case(self.project_id, "defense")
        self.assertEqual(len(opportunities), 1)
        self.assertEqual(opportunities[0]["node_name"], "Sac en nylon")
        self.assertEqual(opportunities[0]["impact_value"], 45)

    @patch('app.services.sensitivity_analysis.OpenAI')
    def test_generate_draft(self, mock_openai):
        # Mock OpenAI response
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_response = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "PROJET DE REQUÊTE FORMEL"

        draft = SensitivityAnalysisEngine.generate_draft(
            project_id=self.project_id,
            client_side="defense",
            node_name="Sac en nylon",
            vector_name="Neutralisation Sensorielle",
            request_type="expertise"
        )
        self.assertEqual(draft, "PROJET DE REQUÊTE FORMEL")

if __name__ == '__main__':
    unittest.main()
