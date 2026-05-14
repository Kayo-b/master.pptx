from __future__ import annotations

import unittest
from unittest.mock import patch

from pipeline.ingest import build_staging_document


class IngestPipelineTestCase(unittest.TestCase):
    @patch("pipeline.ingest.extract_image_suggestions")
    @patch("pipeline.ingest.extract_wikipedia_evidence")
    @patch("pipeline.ingest.extract_insights")
    @patch("pipeline.ingest.clean_input")
    def test_build_staging_document_creates_manual_staging_without_llm(
        self,
        clean_input_mock,
        extract_insights_mock,
        extract_wikipedia_evidence_mock,
        extract_image_suggestions_mock,
    ) -> None:
        clean_input_mock.return_value = type(
            "CleanedDocument",
            (),
            {
                "source": "https://example.com/master",
                "source_kind": "url",
                "text": "Banco Master e Daniel Vorcaro aparecem no caso.",
            },
        )()
        extract_insights_mock.return_value = {
            "texto_resumido": "Daniel Vorcaro controla o Banco Master.",
            "entidades": [{"texto": "Daniel Vorcaro", "label": "PER", "inicio": 0, "fim": 14}],
            "frases_relevantes": ["Daniel Vorcaro controla o Banco Master."],
            "metodos": {"entidades": "spacy", "resumo": "sumy"},
        }
        extract_wikipedia_evidence_mock.return_value = {
            "fontes_sugeridas": [{"id": "f001", "url": "https://example.com/fonte", "tipo": "artigo"}],
            "referencias_vinculadas": [],
        }
        extract_image_suggestions_mock.return_value = {
            "imagens_sugeridas": [{"entidade": "Daniel Vorcaro", "imagem_url": "/assets/images/daniel.jpg"}],
            "erros": [],
        }

        payload = build_staging_document(url="https://pt.wikipedia.org/wiki/Escândalo_do_Banco_Master")

        self.assertEqual(payload["nos"], [])
        self.assertEqual(payload["arestas"], [])
        self.assertEqual(payload["fontes"][0]["url"], "https://example.com/master")
        self.assertEqual(payload["fontes_sugeridas"][0]["id"], "f001")
        self.assertEqual(payload["metadata"]["extracao_grafo"]["status"], "pendente")
        self.assertEqual(payload["metadata"]["extracao_grafo"]["modelo"], "manual_via_copilot_cli")
        self.assertEqual(payload["metadata"]["imagens_extraidas"], 1)
        self.assertEqual(payload["metadata"]["imagens_sugeridas"][0]["entidade"], "Daniel Vorcaro")


if __name__ == "__main__":
    unittest.main()
