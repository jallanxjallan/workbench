from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from intake.materialize import MaterializeError, materialize_ndjson


class IntakeMaterializeTests(unittest.TestCase):
    def test_materialize_ndjson_moves_tmp_file_to_destination(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir).resolve()
            tmp_path = root / "tmp.md"
            destination = root / "final.md"
            tmp_path.write_text("body\n", encoding="utf-8")

            written = materialize_ndjson(
                f'{{"tmp_path":"{tmp_path}","destination":"{destination}"}}\n'
            )

            self.assertEqual(written, [destination])
            self.assertFalse(tmp_path.exists())
            self.assertEqual(destination.read_text(encoding="utf-8"), "body\n")

    def test_materialize_ndjson_surfaces_transport_ndjson_error(self) -> None:
        with self.assertRaisesRegex(MaterializeError, "line 1"):
            materialize_ndjson("{bad}\n")


if __name__ == "__main__":
    unittest.main()
