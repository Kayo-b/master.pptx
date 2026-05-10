from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from db.graph import GraphStore


class GraphStorePathTestCase(unittest.TestCase):
    def test_prepare_db_path_removes_empty_legacy_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "graph.kuzu"
            db_path.mkdir()
            (db_path / ".gitkeep").write_text("", encoding="utf-8")

            store = GraphStore(db_path)

            already_exists = store._prepare_db_path()

            self.assertFalse(already_exists)
            self.assertFalse(db_path.exists())

    def test_prepare_db_path_ignores_missing_legacy_directory_on_remove(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "graph.kuzu"
            db_path.mkdir()
            (db_path / ".gitkeep").write_text("", encoding="utf-8")

            store = GraphStore(db_path)
            original_rmdir = Path.rmdir

            def flaky_rmdir(path: Path) -> None:
                original_rmdir(path)
                raise FileNotFoundError(path)

            with patch.object(Path, "rmdir", flaky_rmdir):
                already_exists = store._prepare_db_path()

            self.assertFalse(already_exists)
            self.assertFalse(db_path.exists())


if __name__ == "__main__":
    unittest.main()
