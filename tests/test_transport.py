from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

from transport import (
    dump_json_file,
    dumps_record,
    emit_paths,
    ensure_regular_file,
    is_final_trailer_record,
    iter_records,
    load_json_file,
    load_json_object,
    loads_record,
    read_all_records,
    read_paths,
    read_text,
    require_single_final_trailer,
    split_final_trailer,
    write_record,
    write_records,
    write_text,
)


class NdjsonTests(unittest.TestCase):
    def test_parses_valid_single_line_object(self) -> None:
        self.assertEqual(loads_record('{"slug":"alpha"}'), {"slug": "alpha"})

    def test_parses_multi_line_stream_preserving_order(self) -> None:
        stream = io.StringIO('\n{"slug":"one"}\n{"slug":"two"}\n')
        self.assertEqual(
            read_all_records(stream),
            [{"slug": "one"}, {"slug": "two"}],
        )

    def test_rejects_malformed_json(self) -> None:
        with self.assertRaisesRegex(ValueError, "line 1"):
            list(iter_records(io.StringIO("{bad}\n")))

    def test_rejects_top_level_non_object(self) -> None:
        with self.assertRaisesRegex(ValueError, "JSON object"):
            loads_record('["not","an","object"]')

    def test_writes_compact_json_lines_with_newline_terminator(self) -> None:
        stream = io.StringIO()
        write_record(stream, {"slug": "alpha", "count": 1})
        self.assertEqual(stream.getvalue(), '{"slug":"alpha","count":1}\n')
        self.assertEqual(dumps_record({"slug": "alpha", "count": 1}), '{"slug":"alpha","count":1}')

    def test_write_records_writes_all_records_in_order(self) -> None:
        stream = io.StringIO()
        write_records(stream, [{"slug": "one"}, {"slug": "two"}])
        self.assertEqual(stream.getvalue(), '{"slug":"one"}\n{"slug":"two"}\n')


class TrailerTests(unittest.TestCase):
    def test_splits_payload_and_final_trailer_correctly(self) -> None:
        payload, trailer = split_final_trailer(
            [{"slug": "one"}, {"_op": "done", "record_count": 1}],
            predicate=lambda record: is_final_trailer_record(record, value="done"),
        )
        self.assertEqual(payload, [{"slug": "one"}])
        self.assertEqual(trailer, {"_op": "done", "record_count": 1})

    def test_rejects_no_trailer(self) -> None:
        with self.assertRaisesRegex(ValueError, "none were found"):
            require_single_final_trailer(
                [{"slug": "one"}],
                predicate=lambda record: is_final_trailer_record(record, value="done"),
            )

    def test_rejects_multiple_trailers(self) -> None:
        with self.assertRaisesRegex(ValueError, "multiple trailers"):
            require_single_final_trailer(
                [{"_op": "done"}, {"_op": "done"}],
                predicate=lambda record: is_final_trailer_record(record, value="done"),
            )

    def test_rejects_trailer_not_in_final_position(self) -> None:
        with self.assertRaisesRegex(ValueError, "final record"):
            require_single_final_trailer(
                [{"_op": "done"}, {"slug": "one"}],
                predicate=lambda record: is_final_trailer_record(record, value="done"),
            )

    def test_works_with_caller_supplied_predicate(self) -> None:
        payload, trailer = require_single_final_trailer(
            [{"slug": "one"}, {"kind": "trailer"}],
            predicate=lambda record: record.get("kind") == "trailer",
        )
        self.assertEqual(payload, [{"slug": "one"}])
        self.assertEqual(trailer, {"kind": "trailer"})


class FilesTests(unittest.TestCase):
    def test_read_text_write_text_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "note.txt"
            write_text(path, "hello")
            self.assertEqual(read_text(path), "hello")

    def test_write_text_fails_when_parent_dir_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "missing" / "note.txt"
            with self.assertRaises(FileNotFoundError):
                write_text(path, "hello")

    def test_emit_paths_writes_one_path_per_line(self) -> None:
        stream = io.StringIO()
        emit_paths([Path("/tmp/a.md"), Path("/tmp/b.md")], stream)
        self.assertEqual(stream.getvalue(), "/tmp/a.md\n/tmp/b.md\n")

    def test_read_paths_returns_expected_path_list(self) -> None:
        stream = io.StringIO("\n/tmp/a.md\n/tmp/b.md\n")
        self.assertEqual(read_paths(stream), [Path("/tmp/a.md"), Path("/tmp/b.md")])

    def test_ensure_regular_file_rejects_missing_path_and_non_file_path(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            with self.assertRaises(FileNotFoundError):
                ensure_regular_file(root / "missing.txt")
            with self.assertRaisesRegex(ValueError, "regular file"):
                ensure_regular_file(root)


class JsonFileTests(unittest.TestCase):
    def test_load_json_file_reads_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "data.json"
            path.write_text('{"slug":"alpha"}\n', encoding="utf-8")
            self.assertEqual(load_json_file(path), {"slug": "alpha"})

    def test_dump_json_file_writes_readable_json_with_trailing_newline(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "data.json"
            dump_json_file(path, {"beta": 2, "alpha": 1})
            self.assertEqual(
                path.read_text(encoding="utf-8"),
                '{\n  "alpha": 1,\n  "beta": 2\n}\n',
            )

    def test_load_json_file_rejects_malformed_json(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "data.json"
            path.write_text("{bad}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Malformed JSON file"):
                load_json_file(path)

    def test_load_json_object_rejects_non_object_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "data.json"
            path.write_text('["alpha"]\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "top-level object"):
                load_json_object(path)


if __name__ == "__main__":
    unittest.main()
