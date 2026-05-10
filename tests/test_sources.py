from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from db.sources import SourceStore


class SourceStoreTestCase(unittest.TestCase):
    def test_add_and_validate_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = SourceStore(Path(tmpdir) / "sources.db")
            first = store.add_source({"id": "f001", "url": "https://example.com/a", "tipo": "artigo"})
            second = store.add_source({"id": "f002", "url": "https://example.com/b", "tipo": "documento_oficial"})
            self.assertEqual(first["id"], "f001")
            self.assertEqual(len(store.list_sources()), 2)
            self.assertEqual(store.ensure_source_ids_exist(["f001", "f003"]), ["f003"])
            self.assertEqual(store.get_source(second["id"])["url"], "https://example.com/b")


if __name__ == "__main__":
    unittest.main()
