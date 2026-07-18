import importlib.util
import csv
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "UFC" / "Scraping" / "supabase_odds_publisher.py"
BULK_MODULE_PATH = REPO_ROOT / "UFC" / "Scraping" / "supabase_odds_bulk_import.py"


def load_module():
    spec = importlib.util.spec_from_file_location("supabase_odds_publisher", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_bulk_module():
    scraping_dir = str(BULK_MODULE_PATH.parent)
    if scraping_dir not in sys.path:
        sys.path.insert(0, scraping_dir)
    spec = importlib.util.spec_from_file_location("supabase_odds_bulk_import", BULK_MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    def __init__(self, status_code=201, payload=None, text="ok"):
        self.status_code = status_code
        self._payload = payload if payload is not None else []
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}: {self.text}")

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, get_payloads=None):
        self.posts = []
        self.gets = []
        self.get_payloads = list(get_payloads or [])

    def post(self, url, **kwargs):
        self.posts.append({"url": url, **kwargs})
        return FakeResponse()

    def get(self, url, **kwargs):
        self.gets.append({"url": url, **kwargs})
        payload = self.get_payloads.pop(0) if self.get_payloads else []
        return FakeResponse(payload=payload)


class EnvGuard:
    def __init__(self, *keys):
        self.keys = keys
        self.original = {}

    def __enter__(self):
        for key in self.keys:
            self.original[key] = os.environ.get(key)
            os.environ.pop(key, None)
        return self

    def __exit__(self, exc_type, exc, tb):
        for key in self.keys:
            os.environ.pop(key, None)
            if self.original[key] is not None:
                os.environ[key] = self.original[key]


class SupabaseOddsPublisherTests(unittest.TestCase):
    def test_parses_american_odds_values(self):
        module = load_module()

        self.assertEqual(module.parse_american_odds("-150"), -150)
        self.assertEqual(module.parse_american_odds("+120"), 120)
        self.assertEqual(module.parse_american_odds(-115.0), -115)
        self.assertIsNone(module.parse_american_odds(""))
        self.assertIsNone(module.parse_american_odds("-"))
        self.assertIsNone(module.parse_american_odds("RmlnaHROb2RlOjEyMw=="))

    def test_converts_fightodds_wide_dataframe_to_latest_odds_rows(self):
        module = load_module()
        dataframe = pd.DataFrame(
            [
                {
                    "Event": "UFC 320: Example MAY 26\n12",
                    "Event_URL": "https://fightodds.io/odds/ufc-320-example",
                    "FightOdds_Fight_ID": "RmlnaHROb2RlOjEyMw==",
                    "Fighters": "Fighter One",
                    "draftkings": "-150",
                    "fanduel": "+120",
                    "betonline_URL": "https://betonline.example/fight",
                },
                {
                    "Event": "UFC 320: Example MAY 26\n12",
                    "Event_URL": "https://fightodds.io/odds/ufc-320-example",
                    "FightOdds_Fight_ID": "RmlnaHROb2RlOjEyMw==",
                    "Fighters": "Fighter Two",
                    "draftkings": "",
                    "fanduel": -110.0,
                    "betonline_URL": "https://betonline.example/fight",
                },
            ]
        )

        rows = module.rows_from_dataframe(
            dataframe,
            source_file="ufc_odds_fightoddsio_20260526_1953.csv",
        )

        self.assertEqual(
            rows,
            [
                {
                    "source": "fightoddsio",
                    "market": "moneyline",
                    "event_name": "UFC 320: Example MAY 26",
                    "fight_id": "RmlnaHROb2RlOjEyMw==",
                    "event_raw": "UFC 320: Example MAY 26\n12",
                    "event_url": "https://fightodds.io/odds/ufc-320-example",
                    "fighter": "Fighter One",
                    "sportsbook": "draftkings",
                    "odds_american": -150,
                    "scraped_at": "2026-05-26T19:53:00+00:00",
                    "source_file": "ufc_odds_fightoddsio_20260526_1953.csv",
                },
                {
                    "source": "fightoddsio",
                    "market": "moneyline",
                    "event_name": "UFC 320: Example MAY 26",
                    "fight_id": "RmlnaHROb2RlOjEyMw==",
                    "event_raw": "UFC 320: Example MAY 26\n12",
                    "event_url": "https://fightodds.io/odds/ufc-320-example",
                    "fighter": "Fighter One",
                    "sportsbook": "fanduel",
                    "odds_american": 120,
                    "scraped_at": "2026-05-26T19:53:00+00:00",
                    "source_file": "ufc_odds_fightoddsio_20260526_1953.csv",
                },
                {
                    "source": "fightoddsio",
                    "market": "moneyline",
                    "event_name": "UFC 320: Example MAY 26",
                    "fight_id": "RmlnaHROb2RlOjEyMw==",
                    "event_raw": "UFC 320: Example MAY 26\n12",
                    "event_url": "https://fightodds.io/odds/ufc-320-example",
                    "fighter": "Fighter Two",
                    "sportsbook": "fanduel",
                    "odds_american": -110,
                    "scraped_at": "2026-05-26T19:53:00+00:00",
                    "source_file": "ufc_odds_fightoddsio_20260526_1953.csv",
                },
            ],
        )

    def test_preserves_source_and_sherdog_fighter_identity_columns(self):
        module = load_module()
        dataframe = pd.DataFrame(
            [
                {
                    "Event": "UFC 320: Example MAY 26\n12",
                    "Event_URL": "https://fightodds.io/odds/ufc-320-example",
                    "FightOdds_Fight_ID": "fight-123",
                    "FightOdds_Fighter_ID": "fighter-456",
                    "Sherdog_Fighter_ID": "229309",
                    "Sherdog_Fighter_URL": "https://www.sherdog.com/fighter/Tommy-McMillen-229309",
                    "Fighters": "Tommy McMillen",
                    "draftkings": "-150",
                }
            ]
        )

        rows = module.rows_from_dataframe(
            dataframe,
            source_file="ufc_odds_fightoddsio_20260526_1953.csv",
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source_fighter_id"], "fighter-456")
        self.assertEqual(rows[0]["sherdog_fighter_id"], "229309")
        self.assertEqual(rows[0]["fighter_identity_key"], "sherdog:229309")
        self.assertEqual(rows[0]["fighter"], "Tommy McMillen")

    def test_derives_sherdog_identity_from_profile_url_when_id_is_missing(self):
        module = load_module()
        dataframe = pd.DataFrame(
            [
                {
                    "Event": "UFC 320: Example MAY 26\n12",
                    "FightOdds_Fight_ID": "fight-123",
                    "FightOdds_Fighter_ID": "fighter-456",
                    "Sherdog_Fighter_ID": "",
                    "Sherdog_Fighter_URL": "https://www.sherdog.com/fighter/Tommy-McMillen-229309",
                    "Fighters": "Tommy McMillen",
                    "draftkings": "-150",
                }
            ]
        )

        rows = module.rows_from_dataframe(
            dataframe,
            source_file="ufc_odds_fightoddsio_20260526_1953.csv",
        )

        self.assertEqual(rows[0]["sherdog_fighter_id"], "229309")
        self.assertEqual(rows[0]["fighter_identity_key"], "sherdog:229309")

    def test_preserves_future_fight_rows_with_same_fighter_and_different_fight_ids(self):
        module = load_module()
        dataframe = pd.DataFrame(
            [
                {
                    "Event": "Future Fights DECEMBER 31\n27",
                    "Event_URL": "https://fightodds.io/odds/future-fights",
                    "FightOdds_Fight_ID": "fight-a",
                    "Fighters": "Alex Pereira",
                    "betonline": "+145",
                },
                {
                    "Event": "Future Fights DECEMBER 31\n27",
                    "Event_URL": "https://fightodds.io/odds/future-fights",
                    "FightOdds_Fight_ID": "fight-b",
                    "Fighters": "Alex Pereira",
                    "betonline": "-175",
                },
            ]
        )

        rows = module.rows_from_dataframe(
            dataframe,
            source_file="ufc_odds_fightoddsio_20260526_1953.csv",
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual({row["fight_id"] for row in rows}, {"fight-a", "fight-b"})

    def test_find_latest_csv_uses_timestamped_fightodds_files(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tempdir:
            data_dir = Path(tempdir)
            older = data_dir / "ufc_odds_fightoddsio_20260526_1900.csv"
            newer = data_dir / "ufc_odds_fightoddsio_20260526_1953.csv"
            unrelated = data_dir / "other.csv"
            older.write_text("older")
            newer.write_text("newer")
            unrelated.write_text("unrelated")

            self.assertEqual(module.find_latest_csv(data_dir), newer)

    def test_find_all_csvs_returns_timestamped_fightodds_files_in_order(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tempdir:
            data_dir = Path(tempdir)
            newest = data_dir / "ufc_odds_fightoddsio_20260527_0724.csv"
            oldest = data_dir / "ufc_odds_fightoddsio_20260526_1953.csv"
            unrelated = data_dir / "ufc_odds_movements_fightoddsio.csv"
            newest.write_text("newest")
            oldest.write_text("oldest")
            unrelated.write_text("unrelated")

            self.assertEqual(module.find_all_csvs(data_dir), [oldest, newest])

    def test_publish_rows_dry_run_never_posts_to_supabase(self):
        module = load_module()
        session = FakeSession()
        config = module.SupabaseConfig(
            url="https://example.supabase.co",
            service_role_key="service-key",
        )

        result = module.publish_rows(
            config,
            [{"source_file": "latest.csv", "scraped_at": "2026-05-26T19:53:00+00:00"}],
            session=session,
            dry_run=True,
        )

        self.assertTrue(result["dry_run"])
        self.assertEqual(result["row_count"], 1)
        self.assertEqual(session.posts, [])

    def test_publish_rows_upserts_history_odds_and_records_ingest_runs(self):
        module = load_module()
        session = FakeSession()
        config = module.SupabaseConfig(
            url="https://example.supabase.co/",
            service_role_key="service-key",
        )
        rows = [
            {
                "source": "fightoddsio",
                "market": "moneyline",
                "source_file": "latest.csv",
                "scraped_at": "2026-05-26T19:53:00+00:00",
            },
            {
                "source": "fightoddsio",
                "market": "moneyline",
                "source_file": "latest.csv",
                "scraped_at": "2026-05-26T19:53:00+00:00",
            },
            {
                "source": "fightoddsio",
                "market": "moneyline",
                "source_file": "latest.csv",
                "scraped_at": "2026-05-26T19:53:00+00:00",
            },
        ]

        result = module.publish_rows(
            config,
            rows,
            session=session,
            dry_run=False,
            chunk_size=2,
        )

        self.assertFalse(result["dry_run"])
        self.assertEqual(result["row_count"], 3)
        self.assertEqual(len(session.posts), 3)
        self.assertEqual(
            session.posts[0]["url"],
            "https://example.supabase.co/rest/v1/ufc_odds_history",
        )
        self.assertEqual(session.posts[0]["params"], {"on_conflict": module.HISTORY_ON_CONFLICT})
        self.assertEqual(len(session.posts[0]["json"]), 2)
        self.assertEqual(len(session.posts[1]["json"]), 1)
        self.assertEqual(
            session.posts[2]["url"],
            "https://example.supabase.co/rest/v1/ufc_odds_ingest_runs",
        )
        self.assertEqual(
            session.posts[2]["json"],
            [
                {
                    "source": "fightoddsio",
                    "market": "moneyline",
                    "source_file": "latest.csv",
                    "row_count": 3,
                    "scraped_at": "2026-05-26T19:53:00+00:00",
                }
            ],
        )
        self.assertIn("Bearer service-key", session.posts[0]["headers"]["Authorization"])
        self.assertIn("resolution=merge-duplicates", session.posts[0]["headers"]["Prefer"])

    def test_publish_rows_seeds_fighter_maps_and_source_fight_before_odds(self):
        module = load_module()
        session = FakeSession()
        config = module.SupabaseConfig(
            url="https://example.supabase.co/",
            service_role_key="service-key",
        )
        rows = [
            {
                "source": "fightoddsio",
                "market": "moneyline",
                "source_file": "latest.csv",
                "scraped_at": "2026-05-26T19:53:00+00:00",
                "event_name": "UFC 320",
                "source_event_id": "9103",
                "fight_id": "fight-a",
                "fighter": "Tommy McMillen",
                "source_fighter_id": "fighter-tommy",
                "sherdog_fighter_id": "229309",
                "fighter_identity_key": "sherdog:229309",
                "sportsbook": "draftkings",
                "odds_american": -150,
            },
            {
                "source": "fightoddsio",
                "market": "moneyline",
                "source_file": "latest.csv",
                "scraped_at": "2026-05-26T19:53:00+00:00",
                "event_name": "UFC 320",
                "source_event_id": "9103",
                "fight_id": "fight-a",
                "fighter": "Alberto Montes",
                "source_fighter_id": "fighter-alberto",
                "sherdog_fighter_id": "257203",
                "fighter_identity_key": "sherdog:257203",
                "sportsbook": "draftkings",
                "odds_american": 130,
            },
        ]

        module.publish_rows(config, rows, session=session, dry_run=False)

        self.assertEqual(
            [post["url"].rsplit("/", 1)[-1] for post in session.posts],
            [
                "ufc_fighters",
                "ufc_fighter_source_map",
                "ufc_source_fights",
                "ufc_odds_history",
                "ufc_odds_ingest_runs",
            ],
        )
        self.assertEqual(session.posts[0]["json"][0]["sherdog_fighter_id"], 229309)
        self.assertEqual(session.posts[1]["json"][0]["resolution_status"], "resolved")
        self.assertEqual(session.posts[2]["json"][0]["resolution_status"], "resolved")

    def test_publish_rows_preserves_existing_seen_order_on_source_map_upsert(self):
        module = load_module()
        session = FakeSession(
            get_payloads=[
                [
                    {
                        "source": "fightoddsio",
                        "source_fighter_id": "fighter-tommy",
                        "sherdog_fighter_id": 229309,
                        "resolution_status": "resolved",
                        "first_seen_at": "2026-05-26T09:00:00+00:00",
                        "last_seen_at": "2026-05-26T10:30:00+00:00",
                    }
                ]
            ]
        )
        config = module.SupabaseConfig(
            url="https://example.supabase.co/",
            service_role_key="service-key",
        )
        rows = [
            {
                "source": "fightoddsio",
                "market": "moneyline",
                "source_file": "latest.csv",
                "scraped_at": "2026-05-26T10:00:00+00:00",
                "event_name": "UFC 320",
                "source_event_id": "9103",
                "fight_id": "fight-a",
                "fighter": "Tommy McMillen",
                "source_fighter_id": "fighter-tommy",
                "sherdog_fighter_id": "229309",
                "fighter_identity_key": "sherdog:229309",
                "sportsbook": "draftkings",
                "odds_american": -150,
            }
        ]

        module.publish_rows(config, rows, session=session, dry_run=False)

        source_map_post = next(
            post for post in session.posts if post["url"].endswith("/ufc_fighter_source_map")
        )
        payload = source_map_post["json"][0]
        self.assertEqual(payload["first_seen_at"], "2026-05-26T09:00:00+00:00")
        self.assertEqual(payload["last_seen_at"], "2026-05-26T10:30:00+00:00")

    def test_publish_line_rows_extends_active_segments_and_inserts_changes(self):
        module = load_module()
        session = FakeSession(
            get_payloads=[
                [{"last_seen_at": "2026-05-26T10:00:00+00:00"}],
                [
                    {
                        "source": "fightoddsio",
                        "market": "moneyline",
                        "event_name": "UFC 320",
                        "fight_id": "fight-a",
                        "fighter": "Fighter One",
                        "sportsbook": "draftkings",
                        "odds_american": -150,
                        "valid_from": "2026-05-26T10:00:00+00:00",
                        "last_seen_at": "2026-05-26T10:00:00+00:00",
                        "first_source_file": "ufc_odds_fightoddsio_20260526_1000.csv",
                    }
                ],
            ]
        )
        config = module.SupabaseConfig(
            url="https://example.supabase.co/",
            service_role_key="service-key",
        )
        rows = [
            {
                "source": "fightoddsio",
                "market": "moneyline",
                "event_name": "UFC 320",
                "fight_id": "fight-a",
                "event_raw": "UFC 320\n12",
                "event_url": "https://fightodds.io/odds/ufc-320",
                "fighter": "Fighter One",
                "sportsbook": "draftkings",
                "odds_american": -150,
                "scraped_at": "2026-05-26T10:10:00+00:00",
                "source_file": "ufc_odds_fightoddsio_20260526_1010.csv",
            },
            {
                "source": "fightoddsio",
                "market": "moneyline",
                "event_name": "UFC 320",
                "fight_id": "fight-a",
                "event_raw": "UFC 320\n12",
                "event_url": "https://fightodds.io/odds/ufc-320",
                "fighter": "Fighter Two",
                "sportsbook": "draftkings",
                "odds_american": 130,
                "scraped_at": "2026-05-26T10:10:00+00:00",
                "source_file": "ufc_odds_fightoddsio_20260526_1010.csv",
            },
        ]

        result = module.publish_line_rows(
            config,
            rows,
            session=session,
            dry_run=False,
            chunk_size=500,
        )

        self.assertEqual(result["line_segment_count"], 2)
        self.assertEqual(session.gets[0]["params"]["order"], "last_seen_at.desc")
        self.assertEqual(session.gets[1]["params"]["last_seen_at"], "eq.2026-05-26T10:00:00+00:00")
        self.assertEqual(
            session.posts[0]["url"],
            "https://example.supabase.co/rest/v1/ufc_odds_line_history",
        )
        payload_by_fighter = {row["fighter"]: row for row in session.posts[0]["json"]}
        self.assertEqual(payload_by_fighter["Fighter One"]["valid_from"], "2026-05-26T10:00:00+00:00")
        self.assertEqual(payload_by_fighter["Fighter One"]["last_seen_at"], "2026-05-26T10:10:00+00:00")
        self.assertEqual(payload_by_fighter["Fighter One"]["first_source_file"], "ufc_odds_fightoddsio_20260526_1000.csv")
        self.assertEqual(payload_by_fighter["Fighter Two"]["valid_from"], "2026-05-26T10:10:00+00:00")

    def test_build_publish_result_reports_backfill_totals_and_duplicates(self):
        module = load_module()
        rows = [
            {
                "source": "fightoddsio",
                "market": "moneyline",
                "source_file": "one.csv",
                "event_name": "UFC 320",
                "fight_id": "fight-1",
                "fighter": "Fighter One",
                "sportsbook": "draftkings",
                "scraped_at": "2026-05-26T19:53:00+00:00",
            },
            {
                "source": "fightoddsio",
                "market": "moneyline",
                "source_file": "one.csv",
                "event_name": "UFC 320",
                "fight_id": "fight-1",
                "fighter": "Fighter One",
                "sportsbook": "draftkings",
                "scraped_at": "2026-05-26T19:53:00+00:00",
            },
            {
                "source": "fightoddsio",
                "market": "moneyline",
                "source_file": "two.csv",
                "event_name": "UFC 321",
                "fight_id": "fight-2",
                "fighter": "Fighter Two",
                "sportsbook": "fanduel",
                "scraped_at": "2026-05-27T07:24:00+00:00",
            },
        ]

        result = module.build_publish_result(
            dry_run=True,
            rows=rows,
            csv_paths=[Path("one.csv"), Path("two.csv")],
            history_table="ufc_odds_history",
            ingest_table="ufc_odds_ingest_runs",
        )

        self.assertTrue(result["dry_run"])
        self.assertEqual(result["file_count"], 2)
        self.assertEqual(result["row_count"], 3)
        self.assertEqual(result["duplicate_key_count"], 1)
        self.assertEqual(result["min_scraped_at"], "2026-05-26T19:53:00+00:00")
        self.assertEqual(result["max_scraped_at"], "2026-05-27T07:24:00+00:00")

    def test_load_rows_from_csvs_skips_empty_files_when_requested(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tempdir:
            data_dir = Path(tempdir)
            valid_csv = data_dir / "ufc_odds_fightoddsio_20260526_1953.csv"
            empty_csv = data_dir / "ufc_odds_fightoddsio_20260527_0724.csv"
            valid_csv.write_text(
                "Event,Event_URL,FightOdds_Fight_ID,Fighters,betonline\n"
                "UFC 320: Example MAY 26,https://fightodds.io/odds/ufc-320,fight-1,Fighter One,-150\n"
            )
            empty_csv.write_text("")

            rows, skipped_files = module.load_rows_from_csvs(
                [valid_csv, empty_csv],
                skip_invalid=True,
            )

            self.assertEqual(len(rows), 1)
            self.assertEqual(skipped_files, [{"csv_path": str(empty_csv), "reason": "empty_csv"}])

    def test_load_rows_from_csvs_raises_for_empty_latest_file_by_default(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tempdir:
            empty_csv = Path(tempdir) / "ufc_odds_fightoddsio_20260527_0724.csv"
            empty_csv.write_text("")

            with self.assertRaisesRegex(RuntimeError, "empty CSV"):
                module.load_rows_from_csvs([empty_csv])

    def test_build_config_from_env_requires_service_role_key(self):
        module = load_module()

        with EnvGuard("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
            os.environ["SUPABASE_URL"] = "https://example.supabase.co"

            with self.assertRaisesRegex(RuntimeError, "SUPABASE_SERVICE_ROLE_KEY"):
                module.build_config_from_env()

    def test_bulk_compile_writes_copy_parts_manifest_and_movement_samples(self):
        module = load_bulk_module()

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            data_dir = root / "data"
            output_dir = root / "bulk"
            data_dir.mkdir()
            self.write_fightodds_csv(
                data_dir / "ufc_odds_fightoddsio_20260526_1000.csv",
                [
                    ["UFC 320: Example MAY 26\n12", "fight-a", "Fighter One", "-150", "+120"],
                    ["UFC 320: Example MAY 26\n12", "fight-a", "Fighter Two", "+130", "-110"],
                    ["UFC 321: Other MAY 27\n8", "fight-b", "Fighter Three", "-200", ""],
                    ["UFC 321: Other MAY 27\n8", "fight-b", "Fighter Four", "+160", ""],
                ],
            )
            self.write_fightodds_csv(
                data_dir / "ufc_odds_fightoddsio_20260526_1010.csv",
                [
                    ["UFC 320: Example MAY 26\n12", "fight-a", "Fighter One", "-145", "+115"],
                    ["UFC 320: Example MAY 26\n12", "fight-a", "Fighter Two", "+125", "-105"],
                    ["UFC 321: Other MAY 27\n8", "fight-b", "Fighter Three", "-210", ""],
                    ["UFC 321: Other MAY 27\n8", "fight-b", "Fighter Four", "+170", ""],
                ],
            )
            self.write_fightodds_csv(
                data_dir / "ufc_odds_fightoddsio_20260526_1020.csv",
                [
                    ["UFC 320: Example MAY 26\n12", "fight-a", "Fighter One", "-140", "+110"],
                    ["UFC 320: Example MAY 26\n12", "fight-a", "Fighter Two", "+120", "-100"],
                ],
            )

            manifest = module.compile_bulk_import(
                data_dir=data_dir,
                output_dir=output_dir,
                rows_per_file=5,
                sample_fight_count=2,
                progress_every=0,
            )

            self.assertEqual(manifest["source_file_count"], 3)
            self.assertEqual(manifest["processed_file_count"], 3)
            self.assertEqual(manifest["compiled_row_count"], 16)
            self.assertEqual(manifest["part_count"], 4)
            self.assertEqual(manifest["min_scraped_at"], "2026-05-26T10:00:00+00:00")
            self.assertEqual(manifest["max_scraped_at"], "2026-05-26T10:20:00+00:00")

            sample_by_fight = {sample["fight_id"]: sample for sample in manifest["matchup_samples"]}
            self.assertEqual(sample_by_fight["fight-a"]["scraped_at_count"], 3)
            self.assertEqual(sample_by_fight["fight-a"]["source_file_count"], 3)
            self.assertEqual(sample_by_fight["fight-b"]["scraped_at_count"], 2)
            self.assertEqual(sample_by_fight["fight-b"]["source_file_count"], 2)

            manifest_file = json.loads((output_dir / module.MANIFEST_NAME).read_text())
            self.assertEqual(manifest_file["compiled_row_count"], 16)
            self.assertIn("load_command", manifest_file)
            self.assertIn("verify_command", manifest_file)
            self.assertEqual(len(list(output_dir.glob("ufc_odds_history_part_*.csv"))), 4)
            load_sql = (output_dir / module.LOAD_SQL_NAME).read_text()
            verify_sql = (output_dir / module.VERIFY_SQL_NAME).read_text()
            self.assertIn("\\copy ufc_odds_history_stage", load_sql)
            self.assertIn("on conflict (source,market,source_file,event_name,fight_id,fighter,sportsbook)", load_sql)
            self.assertIn("loaded_all_compiled_history", verify_sql)
            self.assertIn("fight-a", verify_sql)
            self.assertIn("fight-b", verify_sql)
            self.assertIn("expected_fighters", verify_sql)

    def test_bulk_compile_samples_matchups_without_fight_ids(self):
        module = load_bulk_module()

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            data_dir = root / "data"
            output_dir = root / "bulk"
            data_dir.mkdir()
            self.write_fightodds_csv(
                data_dir / "ufc_odds_fightoddsio_20260401_1000.csv",
                [
                    ["UFC 300: Example APRIL 1\n12", "", "Fighter One", "-150", "+120"],
                    ["UFC 300: Example APRIL 1\n12", "", "Fighter Two", "+130", "-110"],
                ],
            )
            self.write_fightodds_csv(
                data_dir / "ufc_odds_fightoddsio_20260401_1010.csv",
                [
                    ["UFC 300: Example APRIL 1\n12", "", "Fighter One", "-145", "+115"],
                    ["UFC 300: Example APRIL 1\n12", "", "Fighter Two", "+125", "-105"],
                ],
            )

            manifest = module.compile_bulk_import(
                data_dir=data_dir,
                output_dir=output_dir,
                progress_every=0,
            )

            self.assertEqual(len(manifest["matchup_samples"]), 1)
            sample = manifest["matchup_samples"][0]
            self.assertEqual(sample["fight_id"], "")
            self.assertEqual(sample["fighters"], ["Fighter One", "Fighter Two"])
            self.assertEqual(sample["scraped_at_count"], 2)
            self.assertEqual(sample["source_file_count"], 2)
            self.assertEqual(sample["compiled_row_count"], 8)
            verify_sql = (output_dir / module.VERIFY_SQL_NAME).read_text()
            self.assertIn("'Fighter One'", verify_sql)
            self.assertIn("'Fighter Two'", verify_sql)

    def test_bulk_compile_skips_empty_csvs_and_deduplicates_keys(self):
        module = load_bulk_module()

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            data_dir = root / "data"
            output_dir = root / "bulk"
            data_dir.mkdir()
            self.write_fightodds_csv(
                data_dir / "ufc_odds_fightoddsio_20260526_1000.csv",
                [
                    ["UFC 320: Example MAY 26\n12", "fight-a", "Fighter One", "-150", ""],
                    ["UFC 320: Example MAY 26\n12", "fight-a", "Fighter One", "-150", ""],
                ],
            )
            (data_dir / "ufc_odds_fightoddsio_20260526_1010.csv").write_text("")

            manifest = module.compile_bulk_import(
                data_dir=data_dir,
                output_dir=output_dir,
                rows_per_file=100,
                progress_every=0,
            )

            self.assertEqual(manifest["compiled_row_count"], 1)
            self.assertEqual(manifest["duplicate_key_count"], 1)
            self.assertEqual(manifest["skipped_file_count"], 1)
            self.assertEqual(manifest["skipped_files"][0]["reason"], "empty_csv")

    def test_compact_compile_collapses_unchanged_odds_and_records_changes(self):
        module = load_bulk_module()

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            data_dir = root / "data"
            output_dir = root / "compact"
            data_dir.mkdir()
            self.write_fightodds_csv(
                data_dir / "ufc_odds_fightoddsio_20260526_1000.csv",
                [
                    ["UFC 320: Example MAY 26\n12", "fight-a", "Fighter One", "-150", ""],
                    ["UFC 320: Example MAY 26\n12", "fight-a", "Fighter Two", "+130", ""],
                ],
            )
            self.write_fightodds_csv(
                data_dir / "ufc_odds_fightoddsio_20260526_1010.csv",
                [
                    ["UFC 320: Example MAY 26\n12", "fight-a", "Fighter One", "-150", ""],
                    ["UFC 320: Example MAY 26\n12", "fight-a", "Fighter Two", "+130", ""],
                ],
            )
            self.write_fightodds_csv(
                data_dir / "ufc_odds_fightoddsio_20260526_1020.csv",
                [
                    ["UFC 320: Example MAY 26\n12", "fight-a", "Fighter One", "-140", ""],
                    ["UFC 320: Example MAY 26\n12", "fight-a", "Fighter Two", "+130", ""],
                ],
            )

            manifest = module.compile_compact_bulk_import(
                data_dir=data_dir,
                output_dir=output_dir,
                rows_per_file=100,
                progress_every=0,
            )

            self.assertEqual(manifest["input_row_count"], 6)
            self.assertEqual(manifest["segment_row_count"], 3)
            self.assertEqual(manifest["changed_quote_count"], 1)
            self.assertEqual(manifest["unchanged_quote_count"], 3)
            self.assertEqual(manifest["duplicate_input_key_count"], 0)
            self.assertEqual(manifest["duplicate_key_count"], 0)
            self.assertEqual(manifest["compression_ratio"], 2.0)
            self.assertEqual(manifest["part_count"], 1)
            manifest_file = json.loads((output_dir / module.LINE_MANIFEST_NAME).read_text())
            self.assertIn("load_command", manifest_file)
            self.assertIn("verify_command", manifest_file)

            with Path(manifest["part_files"][0]).open(newline="", encoding="utf-8") as handle:
                segments = list(csv.DictReader(handle))
            f1_segments = [row for row in segments if row["fighter"] == "Fighter One"]
            self.assertEqual([row["odds_american"] for row in f1_segments], ["-150", "-140"])
            self.assertEqual(f1_segments[0]["valid_from"], "2026-05-26T10:00:00+00:00")
            self.assertEqual(f1_segments[0]["last_seen_at"], "2026-05-26T10:10:00+00:00")
            self.assertIn("\\copy ufc_odds_line_history_stage", (output_dir / module.LINE_LOAD_SQL_NAME).read_text())

    def test_compact_compile_starts_new_segment_after_disappearance(self):
        module = load_bulk_module()

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            data_dir = root / "data"
            output_dir = root / "compact"
            data_dir.mkdir()
            self.write_fightodds_csv(
                data_dir / "ufc_odds_fightoddsio_20260526_1000.csv",
                [["UFC 320: Example MAY 26\n12", "fight-a", "Fighter One", "-150", ""]],
            )
            self.write_fightodds_csv(
                data_dir / "ufc_odds_fightoddsio_20260526_1010.csv",
                [["UFC 320: Example MAY 26\n12", "fight-a", "Fighter Two", "+130", ""]],
            )
            self.write_fightodds_csv(
                data_dir / "ufc_odds_fightoddsio_20260526_1020.csv",
                [["UFC 320: Example MAY 26\n12", "fight-a", "Fighter One", "-150", ""]],
            )

            manifest = module.compile_compact_bulk_import(
                data_dir=data_dir,
                output_dir=output_dir,
                rows_per_file=100,
                progress_every=0,
            )

            with Path(manifest["part_files"][0]).open(newline="", encoding="utf-8") as handle:
                segments = list(csv.DictReader(handle))
            f1_segments = [row for row in segments if row["fighter"] == "Fighter One"]
            self.assertEqual(len(f1_segments), 2)
            self.assertEqual(f1_segments[0]["last_seen_at"], "2026-05-26T10:00:00+00:00")
            self.assertEqual(f1_segments[1]["valid_from"], "2026-05-26T10:20:00+00:00")

    def test_compact_compile_reports_duplicate_input_keys_separately(self):
        module = load_bulk_module()

        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            data_dir = root / "data"
            output_dir = root / "compact"
            data_dir.mkdir()
            self.write_fightodds_csv(
                data_dir / "ufc_odds_fightoddsio_20260526_1000.csv",
                [
                    ["UFC 320: Example MAY 26\n12", "fight-a", "Fighter One", "-150", ""],
                    ["UFC 320: Example MAY 26\n12", "fight-a", "Fighter One", "-150", ""],
                ],
            )

            manifest = module.compile_compact_bulk_import(
                data_dir=data_dir,
                output_dir=output_dir,
                rows_per_file=100,
                progress_every=0,
            )

            with Path(manifest["part_files"][0]).open(newline="", encoding="utf-8") as handle:
                segments = list(csv.DictReader(handle))
            self.assertEqual(len(segments), 1)
            self.assertEqual(manifest["input_row_count"], 1)
            self.assertEqual(manifest["duplicate_input_key_count"], 1)
            self.assertEqual(manifest["duplicate_key_count"], 0)

    @staticmethod
    def write_fightodds_csv(path, rows):
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "Event",
                    "Event_URL",
                    "FightOdds_Fight_ID",
                    "Fighters",
                    "draftkings",
                    "fanduel",
                    "betonline_URL",
                ]
            )
            for event, fight_id, fighter, draftkings, fanduel in rows:
                writer.writerow(
                    [
                        event,
                        "https://fightodds.io/odds/example",
                        fight_id,
                        fighter,
                        draftkings,
                        fanduel,
                        "https://sportsbook.example",
                    ]
                )


if __name__ == "__main__":
    unittest.main()
