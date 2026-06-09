import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure backend root is in the path
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from app.services.jurisprudence_grounding import JurisprudenceGrounding

class TestJurisprudenceGrounding(unittest.TestCase):

    def setUp(self):
        self.grounding = JurisprudenceGrounding()

    @patch('app.services.jurisprudence_grounding.JurisprudenceGrounding._call_ccq_mcp_tool')
    @patch('app.services.jurisprudence_grounding.JurisprudenceGrounding._verify_with_llm')
    def test_verify_argument_ccq_mcp(self, mock_verify, mock_mcp):
        # Setup mocks
        mock_mcp.return_value = "L'acheteur est tenu de dénoncer par écrit au vendeur le vice dans un délai raisonnable..."
        mock_verify.return_value = True

        argument = "Selon l'article 1726 C.c.Q., le vendeur est tenu de garantir l'acheteur contre les vices cachés."
        result = self.grounding.verify_argument(argument, role="prosecutor", litigation_type="civil")

        self.assertFalse(result["is_hallucination"])
        self.assertEqual(len(result["found_references"]), 1)
        ref = result["found_references"][0]
        self.assertEqual(ref["law_name"], "Code civil du Québec - Article 1726")
        self.assertIn("https://www.canlii.org", ref["url"])
        # Check that URL is embedded in the summary
        self.assertIn("Lien source pour validation :", ref["summary"])
        self.assertIn(ref["url"], ref["summary"])

    @patch('app.services.jurisprudence_grounding.JurisprudenceGrounding._query_a2aj_search')
    @patch('app.services.jurisprudence_grounding.JurisprudenceGrounding._verify_with_llm')
    def test_verify_argument_a2aj(self, mock_verify, mock_a2aj):
        # Setup mocks
        mock_a2aj.return_value = [{
            "citation_fr": "2021 QCCA 123",
            "url_fr": "https://www.canlii.org/fr/qc/qcca/doc/2021/2021qcca123/2021qcca123.html",
            "name_fr": "Caron c. Toiture Allaire inc.",
            "snippet": "La Cour d'appel confirme la responsabilité de l'entrepreneur."
        }]
        mock_verify.return_value = True

        argument = "Selon l'arrêt Caron c. Toiture Allaire, la responsabilité de l'entrepreneur est engagée pour le pontage pourri."
        result = self.grounding.verify_argument(argument, role="defense", litigation_type="civil")

        self.assertFalse(result["is_hallucination"])
        self.assertEqual(len(result["found_references"]), 1)
        ref = result["found_references"][0]
        self.assertEqual(ref["law_name"], "Caron c. Toiture Allaire inc.")
        self.assertEqual(ref["url"], "https://www.canlii.org/fr/qc/qcca/doc/2021/2021qcca123/2021qcca123.html")
        # Check that URL is embedded in the summary
        self.assertIn("Lien source pour validation :", ref["summary"])
        self.assertIn(ref["url"], ref["summary"])

if __name__ == '__main__':
    unittest.main()
