from __future__ import annotations

import unittest

from core.models import ValidationError, build_node_id, slugify, validate_staging_payload


class ModelsTestCase(unittest.TestCase):
    def test_slugify_removes_accents(self) -> None:
        self.assertEqual(slugify("Escândalo do Banco Master"), "escandalo_do_banco_master")

    def test_build_node_id_uses_prefix(self) -> None:
        self.assertEqual(build_node_id("Pessoa", "Daniel Vorcaro"), "pessoa_daniel_vorcaro")

    def test_validate_staging_payload_generates_missing_node_ids(self) -> None:
        payload = validate_staging_payload(
            {
                "nos": [
                    {"tipo_no": "Pessoa", "nome": "Daniel Vorcaro"},
                    {"tipo_no": "Organizacao", "nome": "Banco Master", "tipo": "banco"},
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
                "fontes": [{"id": "f001", "url": "https://example.com", "tipo": "artigo"}],
            }
        )
        node_ids = {node["id"] for node in payload["nos"]}
        self.assertEqual(node_ids, {"pessoa_daniel_vorcaro", "org_banco_master"})

    def test_validate_staging_payload_rejects_invalid_confidence(self) -> None:
        with self.assertRaises(ValidationError):
            validate_staging_payload(
                {
                    "nos": [
                        {"tipo_no": "Pessoa", "id": "pessoa_a", "nome": "A"},
                        {"tipo_no": "Organizacao", "id": "org_b", "nome": "B", "tipo": "empresa"},
                    ],
                    "arestas": [
                        {
                            "tipo_relacao": "CONTROLA",
                            "origem_id": "pessoa_a",
                            "destino_id": "org_b",
                            "confianca": "alto",
                            "fonte_ids": ["f001"],
                        }
                    ],
                    "fontes": [{"id": "f001", "url": "https://example.com"}],
                }
            )

    def test_validate_staging_payload_rejects_edge_with_wrong_endpoint_types(self) -> None:
        with self.assertRaises(ValidationError):
            validate_staging_payload(
                {
                    "nos": [
                        {"tipo_no": "Organizacao", "id": "org_master", "nome": "Banco Master", "tipo": "banco"},
                        {"tipo_no": "Pessoa", "id": "pessoa_daniel_vorcaro", "nome": "Daniel Vorcaro"},
                    ],
                    "arestas": [
                        {
                            "tipo_relacao": "CONTROLA",
                            "origem_id": "org_master",
                            "destino_id": "pessoa_daniel_vorcaro",
                            "desde": "2019",
                            "confianca": "confirmado",
                            "fonte_ids": ["f001"],
                        }
                    ],
                    "fontes": [{"id": "f001", "url": "https://example.com", "tipo": "artigo"}],
                }
            )

    def test_validate_staging_payload_accepts_linked_wikipedia_references(self) -> None:
        payload = validate_staging_payload(
            {
                "referencias_wikipedia_vinculadas": [
                    {
                        "trecho_artigo": "A Amprev do Amapá investiu 400 milhões de reais no Banco Master.",
                        "numero_nota": "60",
                        "fonte_sugerida_id": "wikipedia_ref_60",
                        "referencia_correspondente": {
                            "id": "wikipedia_ref_60",
                            "url": "https://www.infomoney.com.br/noticia",
                            "titulo": "Banco Master recebeu investimentos de 18 fundos previdenciários",
                            "tipo": "artigo",
                        },
                        "claim_estruturada": {
                            "texto": "A Amprev do Amapá investiu 400 milhões de reais no Banco Master.",
                            "tipo": "investimento",
                            "entidades_mencionadas": ["Amprev do Amapá", "Banco Master"],
                            "valores_mencionados": ["400 milhões de reais"],
                            "datas_mencionadas": [],
                        },
                    }
                ]
            }
        )
        self.assertEqual(payload["referencias_wikipedia_vinculadas"][0]["numero_nota"], "60")
        self.assertEqual(payload["referencias_wikipedia_vinculadas"][0]["fonte_sugerida_id"], "wikipedia_ref_60")


if __name__ == "__main__":
    unittest.main()
