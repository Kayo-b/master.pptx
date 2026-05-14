from __future__ import annotations

import unittest
from datetime import UTC, datetime

from pipeline.bootstrap import bootstrap_news_payload
from pipeline.news import parse_google_news_feed


RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<item>
  <title>PF prende pai de Daniel Vorcaro - G1</title>
  <link>https://news.google.com/rss/articles/test1</link>
  <pubDate>Thu, 14 May 2026 10:56:40 GMT</pubDate>
  <source url="https://g1.globo.com">G1</source>
</item>
</channel></rss>
"""


class NewsPipelineTestCase(unittest.TestCase):
    def test_parse_google_news_feed_filters_and_decodes(self) -> None:
        items = parse_google_news_feed(
            RSS,
            limit=5,
            min_published_at=datetime(2026, 5, 14, 9, 0, tzinfo=UTC),
            decode_url=lambda url: "https://g1.globo.com/noticia",
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "PF prende pai de Daniel Vorcaro")
        self.assertEqual(items[0].article_url, "https://g1.globo.com/noticia")

    def test_bootstrap_news_payload_creates_nodes_and_edges(self) -> None:
        payload = {
            "metadata": {"extracao_grafo": {"modelo": "manual_via_copilot_cli", "status": "pendente"}},
            "entidades": [
                {"texto": "Daniel Vorcaro", "label": "PER"},
                {"texto": "Banco Master", "label": "ORG"},
                {"texto": "PL", "label": "LOC"},
                {"texto": "PF", "label": "LOC"},
                {"texto": "Minas Gerais", "label": "LOC"},
            ],
            "texto_resumido": "Nesta quarta-feira, a PF prendeu Henrique Vorcaro no contexto das apuracoes sobre o Banco Master.",
            "frases_relevantes": [
                "Nesta quarta-feira, a PF prendeu Henrique Vorcaro no contexto das apuracoes sobre o Banco Master."
            ],
            "fontes": [{"id": "f001", "titulo": "PF prende pai de Daniel Vorcaro", "data": "2026-05-14"}],
            "nos": [],
            "arestas": [],
        }

        result = bootstrap_news_payload(payload, "PF prende pai de Daniel Vorcaro")

        event_node = next(node for node in result["nos"] if node["tipo_no"] == "Evento")
        self.assertEqual(
            event_node["nome"],
            "Nesta quarta-feira, a PF prendeu Henrique Vorcaro no contexto das apuracoes sobre o Banco Master",
        )
        self.assertTrue(any(edge["tipo_relacao"] == "PARTICIPOU_DE" for edge in result["arestas"]))
        self.assertTrue(any(node["id"] == "orgao_pf" for node in result["nos"]))
        self.assertFalse(any(node["id"] == "org_minas_gerais" for node in result["nos"]))
        self.assertFalse(any(edge.get("origem_id") == "org_minas_gerais" for edge in result["arestas"]))
        self.assertEqual(result["metadata"]["extracao_grafo"]["modelo"], "heuristica_news")

    def test_bootstrap_news_payload_skips_non_event_headline(self) -> None:
        payload = {
            "metadata": {"extracao_grafo": {"modelo": "manual_via_copilot_cli", "status": "pendente"}},
            "entidades": [
                {"texto": "Henrique Vorcaro", "label": "PER"},
                {"texto": "Daniel Vorcaro", "label": "PER"},
                {"texto": "Banco Master", "label": "ORG"},
            ],
            "texto_resumido": "Perfil sobre Henrique Vorcaro e sua relacao com Daniel Vorcaro e o Banco Master.",
            "frases_relevantes": [
                "Quem e Henrique Vorcaro, pai de Daniel Vorcaro do Banco Master.",
                "Perfil sobre Henrique Vorcaro e sua relacao com Daniel Vorcaro e o Banco Master.",
            ],
            "fontes": [
                {
                    "id": "f002",
                    "titulo": "Quem e Henrique Vorcaro, pai de Daniel Vorcaro do Banco Master",
                    "data": "2026-05-14",
                }
            ],
            "nos": [],
            "arestas": [],
        }

        result = bootstrap_news_payload(payload, "Quem e Henrique Vorcaro, pai de Daniel Vorcaro do Banco Master")

        self.assertEqual(result["nos"], [])
        self.assertEqual(result["arestas"], [])
        self.assertEqual(result["metadata"]["extracao_grafo"]["status"], "pendente")


if __name__ == "__main__":
    unittest.main()
