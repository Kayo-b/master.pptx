from __future__ import annotations

import unittest

from pipeline import llm


class LlmPipelineTestCase(unittest.TestCase):
    def test_extract_json_payload_accepts_fenced_json(self) -> None:
        payload = llm._extract_json_payload(
            """```json
            {"nos": [], "arestas": []}
            ```"""
        )
        self.assertEqual(payload, {"nos": [], "arestas": []})

    def test_build_candidate_sources_keeps_primary_source_available(self) -> None:
        candidates, by_id = llm._build_candidate_sources(
            "https://example.com/artigo",
            "url",
            [],
            [{"id": "f001", "url": "https://example.com/fonte", "titulo": "Fonte", "tipo": "artigo"}],
        )

        candidate_ids = {item["id"] for item in candidates}
        self.assertIn("f001", candidate_ids)
        self.assertIn(llm._primary_source_id("https://example.com/artigo"), candidate_ids)
        self.assertIn("f001", by_id)

    def test_normalize_edges_resolves_aliases_and_deduplicates(self) -> None:
        aliases = {
            "pessoa_daniel_vorcaro": "pessoa_daniel_vorcaro",
            "daniel vorcaro": "pessoa_daniel_vorcaro",
            "org_banco_master": "org_banco_master",
            "banco master": "org_banco_master",
        }

        edges = llm._normalize_edges(
            [
                {
                    "tipo_relacao": "CONTROLA",
                    "origem": "Daniel Vorcaro",
                    "destino": "Banco Master",
                    "desde": "2019",
                    "confianca": "confirmado",
                    "fonte_ids": ["f001"],
                },
                {
                    "tipo_relacao": "CONTROLA",
                    "origem_id": "pessoa_daniel_vorcaro",
                    "destino_id": "org_banco_master",
                    "desde": "2019",
                    "confianca": "confirmado",
                    "fonte_ids": ["f001"],
                },
            ],
            aliases,
            {"f001"},
        )

        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]["origem_id"], "pessoa_daniel_vorcaro")
        self.assertEqual(edges[0]["destino_id"], "org_banco_master")


if __name__ == "__main__":
    unittest.main()
