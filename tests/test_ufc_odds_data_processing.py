import csv
import importlib.util
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "UFC"
    / "Analysis"
    / "ufc_odds_data_processing_fightoddsio.py"
)
SPEC = importlib.util.spec_from_file_location("ufc_odds_processor", MODULE_PATH)
PROCESSOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROCESSOR)


class OddsProcessorTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.output = self.root / "movements.csv"
        self.state = self.root / "state.json"

    def tearDown(self):
        self.temporary_directory.cleanup()

    def write_snapshot(self, token, fieldnames, rows):
        path = self.source / f"ufc_odds_fightoddsio_{token}.csv"
        with path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def process(self, full=False, output=None, state=None):
        return PROCESSOR.process(
            self.source,
            output or self.output,
            state or self.state,
            force_full_rebuild=full,
        )

    def read_output(self, output=None):
        with (output or self.output).open(newline="", encoding="utf-8") as csv_file:
            return list(csv.DictReader(csv_file))

    def test_load_files_filters_and_sorts_snapshots(self):
        self.write_snapshot("20260102_0000", ["Fighters"], [{"Fighters": "B"}])
        self.write_snapshot("20260101_0000", ["Fighters"], [{"Fighters": "A"}])
        (self.source / "ufc_odds_movements_fightoddsio.csv").write_text("ignored")
        (self.source / ".temporary.csv").write_text("ignored")

        self.assertEqual(
            PROCESSOR.load_files(self.source),
            [
                "ufc_odds_fightoddsio_20260101_0000.csv",
                "ufc_odds_fightoddsio_20260102_0000.csv",
            ],
        )

    def test_full_rebuild_preserves_legacy_row_and_header_semantics(self):
        before_fields = ["Fighters", "Event", "book_b", "Event_URL", "book_a", "old_only"]
        after_fields = ["Fighters", "Event", "book_a", "Event_URL", "book_b", "new_only"]
        self.write_snapshot(
            "20260101_0000",
            before_fields,
            [
                {
                    "Fighters": "Alice",
                    "Event": "Card",
                    "book_b": "+100",
                    "Event_URL": "old-url",
                    "book_a": "-110",
                    "old_only": "x",
                },
                {
                    "Fighters": "Bob",
                    "Event": "Card",
                    "book_b": "+120",
                    "Event_URL": "same",
                    "book_a": "-130",
                    "old_only": "x",
                },
            ],
        )
        self.write_snapshot(
            "20260101_0006",
            after_fields,
            [
                {
                    "Fighters": "Alice",
                    "Event": "Card",
                    "book_a": "-105",
                    "Event_URL": "new-url",
                    "book_b": "100",
                    "new_only": "new",
                },
                {
                    "Fighters": "Charlie",
                    "Event": "Card",
                    "book_a": "-125",
                    "Event_URL": "same",
                    "book_b": "+125",
                    "new_only": "new",
                },
            ],
        )

        result = self.process(full=True)

        self.assertEqual(result["pairs_processed"], 1)
        self.assertEqual(
            [(row["sportsbook"], row["odds_before"], row["odds_after"]) for row in self.read_output()],
            [
                ("book_b", "+100", "100"),
                ("Event_URL", "old-url", "new-url"),
                ("book_a", "-110", "-105"),
            ],
        )
        output_bytes = self.output.read_bytes()
        self.assertTrue(output_bytes.startswith(b"file1,file2,fighter,sportsbook,odds_before,odds_after\r\n"))
        self.assertNotIn(b"\n", output_bytes.replace(b"\r\n", b""))

    def test_zero_byte_snapshot_is_a_valid_gap(self):
        self.write_snapshot(
            "20260101_0000", ["Fighters", "book"], [{"Fighters": "Alice", "book": "+100"}]
        )
        (self.source / "ufc_odds_fightoddsio_20260101_0006.csv").write_bytes(b"")
        self.write_snapshot(
            "20260101_0012", ["Fighters", "book"], [{"Fighters": "Alice", "book": "+200"}]
        )

        self.process(full=True)

        self.assertEqual(self.read_output(), [])
        self.assertEqual(self.output.read_bytes().count(b"\r\n"), 1)

    def test_single_snapshot_writes_header_only(self):
        self.write_snapshot(
            "20260101_0000", ["Fighters", "book"], [{"Fighters": "Alice", "book": "+100"}]
        )

        result = self.process()

        self.assertEqual(result["mode"], "full")
        self.assertEqual(result["pairs_processed"], 0)
        self.assertEqual(self.read_output(), [])

    def test_incremental_output_matches_full_rebuild_and_noop_is_stable(self):
        fields = ["Fighters", "book"]
        self.write_snapshot("20260101_0000", fields, [{"Fighters": "Alice", "book": "+100"}])
        self.write_snapshot("20260101_0006", fields, [{"Fighters": "Alice", "book": "+110"}])
        self.process(full=True)
        self.write_snapshot("20260101_0012", fields, [{"Fighters": "Alice", "book": "+120"}])
        self.write_snapshot("20260101_0018", fields, [{"Fighters": "Alice", "book": "+120"}])

        incremental_result = self.process()
        incremental_bytes = self.output.read_bytes()
        full_output = self.root / "full.csv"
        full_state = self.root / "full-state.json"
        full_result = self.process(full=True, output=full_output, state=full_state)

        self.assertEqual(incremental_result["pairs_processed"], 2)
        self.assertEqual(incremental_bytes, full_output.read_bytes())
        self.assertEqual(incremental_result["output_sha256"], full_result["output_sha256"])

        output_mtime = self.output.stat().st_mtime_ns
        state_mtime = self.state.stat().st_mtime_ns
        output_bytes = self.output.read_bytes()
        state_bytes = self.state.read_bytes()
        time.sleep(0.01)
        noop_result = self.process()

        self.assertEqual(noop_result["pairs_processed"], 0)
        self.assertEqual(self.output.read_bytes(), output_bytes)
        self.assertEqual(self.state.read_bytes(), state_bytes)
        self.assertEqual(self.output.stat().st_mtime_ns, output_mtime)
        self.assertEqual(self.state.stat().st_mtime_ns, state_mtime)

    def test_historical_change_fails_without_modifying_artifacts(self):
        first = self.write_snapshot(
            "20260101_0000", ["Fighters", "book"], [{"Fighters": "Alice", "book": "+100"}]
        )
        self.write_snapshot(
            "20260101_0006", ["Fighters", "book"], [{"Fighters": "Alice", "book": "+110"}]
        )
        self.process(full=True)
        output_bytes = self.output.read_bytes()
        state_bytes = self.state.read_bytes()
        first.write_text("Fighters,book\nAlice,+999\n", encoding="utf-8")

        with self.assertRaisesRegex(PROCESSOR.ProcessingError, "metadata changed"):
            self.process()

        self.assertEqual(self.output.read_bytes(), output_bytes)
        self.assertEqual(self.state.read_bytes(), state_bytes)

    def test_output_checksum_mismatch_fails_safely(self):
        self.write_snapshot(
            "20260101_0000", ["Fighters", "book"], [{"Fighters": "Alice", "book": "+100"}]
        )
        self.write_snapshot(
            "20260101_0006", ["Fighters", "book"], [{"Fighters": "Alice", "book": "+110"}]
        )
        self.process(full=True)
        self.output.write_bytes(self.output.read_bytes() + b"tampered\r\n")
        tampered_bytes = self.output.read_bytes()
        state_bytes = self.state.read_bytes()

        with self.assertRaisesRegex(PROCESSOR.ProcessingError, "output changed"):
            self.process()

        self.assertEqual(self.output.read_bytes(), tampered_bytes)
        self.assertEqual(self.state.read_bytes(), state_bytes)

    def test_malformed_new_snapshot_does_not_replace_output_or_state(self):
        self.write_snapshot(
            "20260101_0000", ["Fighters", "book"], [{"Fighters": "Alice", "book": "+100"}]
        )
        self.write_snapshot(
            "20260101_0006", ["Fighters", "book"], [{"Fighters": "Alice", "book": "+110"}]
        )
        self.process(full=True)
        output_bytes = self.output.read_bytes()
        state_bytes = self.state.read_bytes()
        (self.source / "ufc_odds_fightoddsio_20260101_0012.csv").write_text(
            "NotFighters,book\nAlice,+120\n", encoding="utf-8"
        )

        with self.assertRaisesRegex(PROCESSOR.ProcessingError, "missing the Fighters"):
            self.process()

        self.assertEqual(self.output.read_bytes(), output_bytes)
        self.assertEqual(self.state.read_bytes(), state_bytes)

    def test_corrupt_or_missing_checkpoint_requires_explicit_rebuild(self):
        self.write_snapshot(
            "20260101_0000", ["Fighters", "book"], [{"Fighters": "Alice", "book": "+100"}]
        )
        self.write_snapshot(
            "20260101_0006", ["Fighters", "book"], [{"Fighters": "Alice", "book": "+110"}]
        )
        self.process(full=True)
        self.state.write_text("not-json", encoding="utf-8")

        with self.assertRaisesRegex(PROCESSOR.ProcessingError, "Cannot read checkpoint"):
            self.process()

        recovered = self.process(full=True)
        self.assertEqual(recovered["mode"], "full")
        state_data = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual(state_data["version"], PROCESSOR.STATE_VERSION)
        self.state.unlink()
        with self.assertRaisesRegex(PROCESSOR.ProcessingError, "missing"):
            self.process()
        rebuilt = self.process(full=True)
        self.assertEqual(rebuilt["mode"], "full")

    def test_existing_checkpoint_without_output_fails_safely(self):
        self.write_snapshot(
            "20260101_0000", ["Fighters", "book"], [{"Fighters": "Alice", "book": "+100"}]
        )
        self.process(full=True)
        state_bytes = self.state.read_bytes()
        self.output.unlink()

        with self.assertRaisesRegex(PROCESSOR.ProcessingError, "Output or checkpoint is missing"):
            self.process()

        self.assertEqual(self.state.read_bytes(), state_bytes)
        rebuilt = self.process(full=True)
        self.assertEqual(rebuilt["mode"], "full")
        self.assertTrue(self.output.is_file())

    def test_structurally_invalid_checkpoint_is_controlled(self):
        self.write_snapshot(
            "20260101_0000", ["Fighters", "book"], [{"Fighters": "Alice", "book": "+100"}]
        )
        self.process(full=True)
        output_bytes = self.output.read_bytes()
        invalid_states = [
            [],
            True,
            {"version": PROCESSOR.STATE_VERSION, "processed_snapshot_count": True},
            {
                "version": PROCESSOR.STATE_VERSION,
                "processed_snapshot_count": 1,
                "last_snapshot": "invalid.csv",
                "prefix_metadata_sha256": "x",
                "output_sha256": "y",
            },
        ]

        for invalid_state in invalid_states:
            with self.subTest(invalid_state=invalid_state):
                self.state.write_text(json.dumps(invalid_state), encoding="utf-8")
                with self.assertRaises(PROCESSOR.ProcessingError):
                    self.process()
                self.assertEqual(self.output.read_bytes(), output_bytes)

    def test_ragged_and_malformed_csvs_fail_before_replacement(self):
        self.write_snapshot(
            "20260101_0000", ["Fighters", "book"], [{"Fighters": "Alice", "book": "+100"}]
        )
        second = self.source / "ufc_odds_fightoddsio_20260101_0006.csv"
        invalid_contents = [
            "Fighters,book\nAlice,+110,EXTRA\n",
            "Fighters,book\nAlice\n",
            'Fighters,book\n"Alice,+110\n',
        ]

        for contents in invalid_contents:
            with self.subTest(contents=contents):
                second.write_text(contents, encoding="utf-8")
                with self.assertRaises(PROCESSOR.ProcessingError):
                    self.process(full=True)
                self.assertFalse(self.output.exists())
                self.assertFalse(self.state.exists())

    def test_interrupted_commit_recovers_automatically(self):
        fields = ["Fighters", "book"]
        self.write_snapshot("20260101_0000", fields, [{"Fighters": "Alice", "book": "+100"}])
        self.write_snapshot("20260101_0006", fields, [{"Fighters": "Alice", "book": "+110"}])
        self.process(full=True)
        old_state = self.state.read_bytes()
        self.write_snapshot("20260101_0012", fields, [{"Fighters": "Alice", "book": "+120"}])
        original_write_state = PROCESSOR.write_state_atomic

        def fail_state_commit(path, state):
            if Path(path) == self.state:
                raise OSError("injected state commit failure")
            return original_write_state(path, state)

        with mock.patch.object(PROCESSOR, "write_state_atomic", side_effect=fail_state_commit):
            with self.assertRaisesRegex(OSError, "injected"):
                self.process()

        self.assertEqual(self.state.read_bytes(), old_state)
        self.assertTrue(PROCESSOR.transaction_path_for(self.state).is_file())
        recovered = self.process()
        self.assertEqual(recovered["pairs_processed"], 0)
        self.assertFalse(PROCESSOR.transaction_path_for(self.state).exists())
        full_output = self.root / "full-after-recovery.csv"
        full_state = self.root / "full-after-recovery-state.json"
        self.process(full=True, output=full_output, state=full_state)
        self.assertEqual(self.output.read_bytes(), full_output.read_bytes())

    def test_full_rebuild_discards_unrecoverable_transaction(self):
        self.write_snapshot(
            "20260101_0000", ["Fighters", "book"], [{"Fighters": "Alice", "book": "+100"}]
        )
        self.process(full=True)
        transaction_path = PROCESSOR.transaction_path_for(self.state)
        unrelated_file = self.output.parent / f".{self.output.name}.notes"
        unrelated_file.write_text("keep", encoding="utf-8")
        transaction_path.write_text(
            json.dumps(
                {
                    "version": PROCESSOR.STATE_VERSION,
                    "temporary_output": str(unrelated_file),
                    "state": json.loads(self.state.read_text(encoding="utf-8")),
                }
            ),
            encoding="utf-8",
        )

        recovered = self.process()
        self.assertEqual(recovered["pairs_processed"], 0)
        self.assertEqual(unrelated_file.read_text(encoding="utf-8"), "keep")
        transaction_path.write_text("not-json", encoding="utf-8")
        with self.assertRaisesRegex(PROCESSOR.ProcessingError, "Cannot recover transaction"):
            self.process()

        rebuilt = self.process(full=True)
        self.assertEqual(rebuilt["mode"], "full")
        self.assertFalse(transaction_path.exists())
        self.assertEqual(unrelated_file.read_text(encoding="utf-8"), "keep")

    def test_failure_before_journal_creation_removes_staged_output(self):
        self.write_snapshot(
            "20260101_0000", ["Fighters", "book"], [{"Fighters": "Alice", "book": "+100"}]
        )

        with mock.patch.object(PROCESSOR, "build_state", side_effect=OSError("injected digest failure")):
            with self.assertRaisesRegex(OSError, "injected"):
                self.process(full=True)

        staged_outputs = [
            path
            for path in self.output.parent.iterdir()
            if path.name.startswith(f".{self.output.name}.")
        ]
        self.assertEqual(staged_outputs, [])
        self.assertFalse(self.output.exists())
        self.assertFalse(self.state.exists())


if __name__ == "__main__":
    unittest.main()
