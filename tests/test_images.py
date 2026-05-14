from __future__ import annotations

import unittest
from unittest.mock import patch

from pipeline.images import (
    apply_suggested_images_to_nodes,
    backfill_node_images_from_wikipedia,
    extract_image_suggestions,
)


class ImagesPipelineTestCase(unittest.TestCase):
    @patch("pipeline.images._download_image")
    def test_extract_image_suggestions_downloads_matching_image(self, download_image_mock) -> None:
        download_image_mock.return_value = "/assets/images/daniel-vorcaro.jpg"
        result = extract_image_suggestions(
            source="https://example.com/article",
            source_kind="url",
            raw_html="""
                <html><head>
                <meta property="og:image" content="https://cdn.example.com/hero.jpg">
                </head><body>
                <img src="https://cdn.example.com/daniel-vorcaro.jpg" alt="Daniel Vorcaro em evento" />
                </body></html>
            """,
            entities=[{"texto": "Daniel Vorcaro", "label": "PER"}],
        )

        self.assertEqual(result["imagens_sugeridas"][0]["entidade"], "Daniel Vorcaro")
        self.assertEqual(result["imagens_sugeridas"][0]["imagem_url"], "/assets/images/daniel-vorcaro.jpg")
        download_image_mock.assert_called_once_with("https://cdn.example.com/daniel-vorcaro.jpg", "Daniel Vorcaro")

    def test_apply_suggested_images_to_nodes_sets_missing_image_url(self) -> None:
        payload = {
            "metadata": {
                "imagens_sugeridas": [
                    {"entidade": "Daniel Vorcaro", "imagem_url": "/assets/images/daniel-vorcaro.jpg"}
                ]
            },
            "nos": [
                {"tipo_no": "Pessoa", "id": "pessoa_daniel_vorcaro", "nome": "Daniel Vorcaro", "imagem_url": None}
            ],
        }

        result = apply_suggested_images_to_nodes(payload)

        self.assertEqual(result["nos"][0]["imagem_url"], "/assets/images/daniel-vorcaro.jpg")

    @patch("pipeline.images._download_image")
    @patch("pipeline.images.fetch_wikipedia_image")
    def test_backfill_node_images_from_wikipedia_updates_missing_images(
        self,
        fetch_wikipedia_image_mock,
        download_image_mock,
    ) -> None:
        fetch_wikipedia_image_mock.return_value = {
            "title": "Daniel Vorcaro",
            "source": "https://upload.wikimedia.org/daniel-vorcaro.jpg",
        }
        download_image_mock.return_value = "/assets/images/daniel-vorcaro.jpg"
        nodes = [
            {"tipo_no": "Pessoa", "id": "pessoa_daniel_vorcaro", "nome": "Daniel Vorcaro", "imagem_url": None}
        ]

        result = backfill_node_images_from_wikipedia(nodes)

        self.assertEqual(result["updated_count"], 1)
        self.assertEqual(nodes[0]["imagem_url"], "/assets/images/daniel-vorcaro.jpg")


if __name__ == "__main__":
    unittest.main()
