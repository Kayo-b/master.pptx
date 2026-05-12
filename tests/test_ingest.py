from __future__ import annotations

import unittest
from unittest.mock import patch

from pipeline.ingest import build_staging_document


class IngestPipelineTestCase(unittest.TestCase):
    @patch("pipeline.ingest.extract_graph_with_llm")
    @patch("pipeline.ingest.extract_wikipedia_evidence")
    @patch("pipeline.ingest.extract_insights")
    @patch("pipeline.ingest.clean_input")
    def test_build_staging_document_populates_graph_from_llm(
        self,
        clean_input_mock,
        extract_insights_mock,
        extract_wikipedia_evidence_mock,
        extract_graph_with_llm_mock,
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
        extract_graph_with_llm_mock.return_value = {
            "nos": [
                {"tipo_no": "Pessoa", "id": "pessoa_daniel_vorcaro", "nome": "Daniel Vorcaro"},
                {"tipo_no": "Organizacao", "id": "org_banco_master", "nome": "Banco Master", "tipo": "banco"},
            ],
            "arestas": [
                {
                    "tipo_relacao": "CONTROLA",
                    "origem_id": "pessoa_daniel_vorcaro",
                    "destino_id": "org_banco_master",
                    "desde": "2019",
                    "confianca": "confirmado",
                    "fonte_ids": ["f001"],
                }
            ],
            "fontes": [{"id": "f001", "url": "https://example.com/fonte", "tipo": "artigo"}],
        }

        payload = build_staging_document(url="https://pt.wikipedia.org/wiki/Escândalo_do_Banco_Master")

        self.assertEqual(len(payload["nos"]), 2)
        self.assertEqual(payload["arestas"][0]["tipo_relacao"], "CONTROLA")
        self.assertEqual(payload["fontes"][0]["id"], "f001")
        self.assertEqual(payload["metadata"]["extracao_grafo"]["status"], "concluida")


if __name__ == "__main__":
    unittest.main()
