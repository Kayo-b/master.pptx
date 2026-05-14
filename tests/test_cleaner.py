from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pipeline.cleaner import clean_file


class CleanerTestCase(unittest.TestCase):
    def test_clean_file_strips_html_from_txt_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "article.txt"
            path.write_text(
                "<html><body><script>var x = 1;</script><p>Daniel Vorcaro negociou com Flávio Bolsonaro.</p></body></html>",
                encoding="utf-8",
            )

            cleaned = clean_file(path)

            self.assertIn("Daniel Vorcaro negociou com Flávio Bolsonaro.", cleaned.text)
            self.assertNotIn("<p>", cleaned.text)
            self.assertNotIn("var x = 1", cleaned.text)


if __name__ == "__main__":
    unittest.main()
