from __future__ import annotations

import importlib.util
import io
import inspect
import json
import sys
import tempfile
import time
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

import requests


MODULE_PATH = Path(__file__).with_name("superset_query.py")
SPEC = importlib.util.spec_from_file_location("superset_query_under_test", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ReadOnlyValidationTests(unittest.TestCase):
    def test_allows_select_with_and_explain(self):
        accepted = [
            "SELECT 1;",
            "WITH x AS (SELECT 1 AS n) SELECT n FROM x",
            "EXPLAIN SELECT * FROM some_table",
            "-- comment\nSELECT ';' AS semicolon_in_string",
        ]
        for sql in accepted:
            with self.subTest(sql=sql):
                self.assertTrue(MODULE.validate_readonly_sql(sql))

    def test_rejects_writes_metadata_commands_and_multiple_statements(self):
        rejected = [
            "CREATE TABLE x AS SELECT 1",
            "WITH x AS (SELECT 1) DELETE FROM y",
            "SHOW TABLES",
            "DESCRIBE some_table",
            "SELECT 1; SELECT 2",
            "VALUES (1)",
            "SELECT * INTO copied_table FROM source_table",
            "SELECT set_config('search_path','public',false)",
            "SELECT pg_advisory_lock(1)",
            "SELECT nextval('sequence_name')",
            "SELECT 1 FROM source LOCK IN SHARE MODE",
        ]
        for sql in rejected:
            with self.subTest(sql=sql):
                with self.assertRaises(ValueError):
                    MODULE.validate_readonly_sql(sql)

    def test_ignores_keywords_inside_strings_and_comments(self):
        sql = "SELECT 'DROP TABLE x' AS message /* DELETE is documentation */"
        self.assertEqual(MODULE.validate_readonly_sql(sql), sql)


class ExportSafetyTests(unittest.TestCase):
    def test_csv_prefixes_spreadsheet_formula_cells(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "result.csv"
            MODULE._write_csv(
                target,
                [{"value": '=HYPERLINK("https://example.invalid")'}, {"value": "+1+1"}],
                ["value"],
            )
            text = target.read_text(encoding="utf-8-sig")
        self.assertIn("'=HYPERLINK", text)
        self.assertIn("'+1+1", text)

    def test_csv_protects_headers_and_control_prefixed_formulas(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "result.csv"
            MODULE._write_csv(
                target,
                [{"=unsafe_header": "\t=1+1"}],
                ["=unsafe_header"],
            )
            text = target.read_text(encoding="utf-8-sig")
        self.assertTrue(text.startswith("'=unsafe_header"))
        self.assertIn("'\t=1+1", text)


class ErrorClassificationTests(unittest.TestCase):
    def test_policy_error_keeps_query_id(self):
        info = MODULE.classify_error(500, {"query_id": 123, "error": "Only SELECT statements are allowed against this database"})
        self.assertEqual(info.category, "policy")
        self.assertEqual(info.query_id, 123)
        self.assertFalse(info.retryable)

    def test_object_and_permission_are_distinct(self):
        self.assertEqual(MODULE.classify_error(500, {"error": "Table a.b does not exist"}).category, "object")
        self.assertEqual(MODULE.classify_error(500, {"error": "Access Denied: cannot select"}).category, "permission")

    def test_only_transient_server_status_is_retryable(self):
        self.assertTrue(MODULE.classify_error(503, {}, "unavailable").retryable)
        self.assertFalse(MODULE.classify_error(500, {}, "internal error").retryable)


class RetryLimitTests(unittest.TestCase):
    def test_execute_never_retries_more_than_once(self):
        profile = MODULE.Profile(
            base_url="https://example.invalid", username="user", database_id="1", schema="default"
        )
        client = MODULE.SupersetClient(profile=profile, password_loader=lambda: "unused")
        client._ensure_session = lambda: None
        attempts = 0

        def fail_query(_sql):
            nonlocal attempts
            attempts += 1
            raise requests.ConnectionError("temporary network failure")

        client._post_query = fail_query
        with patch.object(MODULE.time, "sleep", return_value=None):
            with self.assertRaises(MODULE.SupersetServerError):
                client.execute("SELECT 1", max_retries=999)
        self.assertEqual(attempts, 2)


class QueryLifecycleTests(unittest.TestCase):
    def test_query_transport_accepts_dynamic_timeout(self):
        execute_parameters = inspect.signature(
            MODULE.SupersetClient.execute
        ).parameters
        post_parameters = inspect.signature(
            MODULE.SupersetClient._post_query
        ).parameters
        self.assertIn("timeout_seconds", execute_parameters)
        self.assertIn("timeout_seconds", post_parameters)
        if (
            "timeout_seconds" not in execute_parameters
            or "timeout_seconds" not in post_parameters
        ):
            return
        profile = MODULE.Profile(
            base_url="https://example.invalid",
            username="user",
            database_id="1",
            schema="default",
        )
        client = MODULE.SupersetClient(
            profile=profile,
            password_loader=lambda: "unused",
        )
        client._session = requests.Session()
        response = type(
            "Response",
            (),
            {
                "status_code": 200,
                "headers": {"content-type": "application/json"},
                "json": lambda _self: {
                    "data": [{"value": 1}],
                    "columns": [{"name": "value"}],
                },
                "text": '{"data":[{"value":1}]}',
            },
        )()
        post = Mock(return_value=response)
        client._session.post = post
        client._observe_query_status = lambda *_args: None

        client._post_query("SELECT 1", timeout_seconds=77)

        self.assertEqual((15, 77), post.call_args.kwargs["timeout"])
        self.assertEqual("10000", post.call_args.kwargs["data"]["queryLimit"])

    def test_execute_blocks_response_above_local_row_limit(self):
        profile = MODULE.Profile(
            base_url="https://example.invalid",
            username="user",
            database_id="1",
            schema="default",
            max_result_rows=2,
        )
        client = MODULE.SupersetClient(profile=profile, password_loader=lambda: "unused")
        client._ensure_session = lambda: None
        response = type("Response", (), {
            "status_code": 200,
            "headers": {"content-type": "application/json"},
            "text": "",
            "url": "https://example.invalid/superset/sql_json/",
        })()
        client._post_query = lambda _sql: (response, {"data": [{"n": 1}, {"n": 2}, {"n": 3}]})
        with self.assertRaises(MODULE.SupersetSQLError) as caught:
            client.execute("SELECT n FROM source", max_retries=0)
        self.assertEqual("resource", caught.exception.info.category)
        self.assertEqual(2, caught.exception.info.details["max_result_rows"])

    def test_query_transport_waits_for_final_observer_snapshot(self):
        profile = MODULE.Profile(
            base_url="https://example.invalid",
            username="user",
            database_id="1",
            schema="default",
        )
        client = MODULE.SupersetClient(
            profile=profile,
            password_loader=lambda: "unused",
        )
        client._session = requests.Session()
        response = type(
            "Response",
            (),
            {
                "status_code": 200,
                "headers": {"content-type": "application/json"},
                "json": lambda _self: {"data": [], "columns": []},
                "text": '{"data":[]}',
            },
        )()
        client._session.post = Mock(return_value=response)

        def append_when_stopped(
            _client_id,
            _since_ms,
            stop_event,
            timeline,
            _started,
        ):
            stop_event.wait(1)
            timeline.append(
                {
                    "observed_at_seconds": 0.1,
                    "record": {"state": "success"},
                }
            )

        client._observe_query_status = append_when_stopped

        transport = client._post_query("SELECT 1")

        self.assertTrue(transport[3])
        if not transport[3]:
            return
        self.assertEqual(
            "success",
            transport[3][-1]["record"]["state"],
        )

    def test_find_sqllab_query_returns_only_requested_client(self):
        finder = getattr(MODULE, "find_sqllab_query", None)
        self.assertIsNotNone(finder)
        if finder is None:
            return
        payload = {
            "one": {
                "id": "other00001",
                "serverId": 10,
                "state": "success",
                "sql": "SELECT secret_that_must_not_be_copied",
            },
            "two": {
                "id": "target0001",
                "serverId": 11,
                "state": "running",
                "progress": 40,
                "rows": 0,
                "errorMessage": None,
            },
        }

        record = finder(payload, "target0001")

        self.assertEqual("target0001", record["id"])
        self.assertEqual(11, record["serverId"])
        self.assertEqual("running", record["state"])
        self.assertNotIn("sql", record)

    def test_execute_preserves_superset_query_lifecycle(self):
        profile = MODULE.Profile(
            base_url="https://example.invalid",
            username="user",
            database_id="1",
            schema="default",
        )
        client = MODULE.SupersetClient(
            profile=profile,
            password_loader=lambda: "unused",
        )
        client._ensure_session = lambda: None
        payload = {
            "data": [{"value": 1}],
            "columns": [{"name": "value"}],
            "query_id": 319773,
            "status": "success",
            "query": {
                "id": "target0001",
                "serverId": 319773,
                "state": "success",
                "progress": 100,
                "startDttm": 1_000,
                "endDttm": 4_250,
                "rows": 1,
                "resultsKey": None,
                "errorMessage": None,
                "limit_reached": False,
            },
        }
        response = type(
            "Response",
            (),
            {
                "status_code": 200,
                "headers": {"content-type": "application/json"},
                "text": "",
                "url": "https://example.invalid/superset/sql_json/",
            },
        )()
        client._post_query = lambda _sql: (response, payload)

        result = client.execute("SELECT 1", max_retries=0)

        self.assertEqual("target0001", result.get("client_id"))
        self.assertEqual(319773, result.get("server_query_id"))
        self.assertEqual("success", result.get("query_state"))
        self.assertEqual(3.25, result.get("superset_lifecycle_seconds"))
        self.assertEqual(100, result.get("query_progress"))

    def test_poll_sqllab_status_once_uses_known_client_id(self):
        poll = getattr(MODULE, "poll_sqllab_status_once", None)
        self.assertIsNotNone(poll)
        if poll is None:
            return
        session = requests.Session()
        response = type(
            "Response",
            (),
            {
                "status_code": 200,
                "json": lambda _self: {
                    "one": {
                        "id": "target0001",
                        "serverId": 319773,
                        "state": "running",
                        "progress": 0,
                    }
                },
            },
        )()
        session.get = lambda *_args, **_kwargs: response

        record = poll(
            session,
            "https://example.invalid",
            1_000,
            "target0001",
        )

        self.assertEqual("target0001", record["id"])
        self.assertEqual("running", record["state"])

    def test_execute_includes_transport_status_timeline(self):
        profile = MODULE.Profile(
            base_url="https://example.invalid",
            username="user",
            database_id="1",
            schema="default",
        )
        client = MODULE.SupersetClient(
            profile=profile,
            password_loader=lambda: "unused",
        )
        client._ensure_session = lambda: None
        payload = {
            "data": [{"value": 1}],
            "columns": [{"name": "value"}],
            "query_id": 319773,
            "status": "success",
            "query": {
                "id": "target0001",
                "serverId": 319773,
                "state": "success",
            },
        }
        response = type(
            "Response",
            (),
            {
                "status_code": 200,
                "headers": {"content-type": "application/json"},
                "text": "",
                "url": "https://example.invalid/superset/sql_json/",
            },
        )()
        timeline = [
            {
                "observed_at_seconds": 1.2,
                "record": {
                    "id": "target0001",
                    "state": "running",
                    "progress": 0,
                },
            },
            {
                "observed_at_seconds": 5.3,
                "record": {
                    "id": "target0001",
                    "state": "success",
                    "progress": 100,
                },
            },
        ]
        client._post_query = lambda _sql: (
            response,
            payload,
            "target0001",
            timeline,
        )

        try:
            result = client.execute("SELECT 1", max_retries=0)
        except ValueError:
            result = {}

        self.assertEqual(timeline, result.get("status_timeline"))


class CompatibilityTests(unittest.TestCase):
    def test_client_accepts_old_database_and_schema_overrides(self):
        profile = MODULE.Profile(
            base_url="https://example.invalid", username="user", database_id="1", schema="default"
        )
        client = MODULE.SupersetClient(
            profile=profile, password_loader=lambda: "unused", database_id=2, schema="custom", timeout=9
        )
        self.assertEqual(client.profile.database_id, "2")
        self.assertEqual(client.profile.schema, "custom")
        self.assertEqual(client.profile.query_timeout_seconds, 9)


class SessionIdentityTests(unittest.TestCase):
    def setUp(self):
        self.profile = MODULE.Profile(
            base_url="https://example.invalid",
            username="current-user",
            database_id="123",
            schema="hive",
        )

    @staticmethod
    def session_payload(**overrides):
        payload = {
            "version": MODULE.SESSION_CACHE_VERSION,
            "base_url": "https://example.invalid",
            "username": "current-user",
            "authenticated_username": "current-user",
            "saved_at": time.time(),
            "csrf_token": "test-csrf",
            "cookies": [{
                "name": "session",
                "value": "test-cookie",
                "domain": "example.invalid",
                "path": "/",
                "secure": True,
                "expires": None,
            }],
        }
        payload.update(overrides)
        return payload

    def test_extracts_authenticated_username_from_sql_lab_page(self):
        html = '<a class="navbar-brand" href="/superset/profile/current-user/">Superset</a>'
        self.assertEqual(MODULE._extract_authenticated_username(html), "current-user")

    def test_rejects_legacy_cache_without_identity_binding(self):
        payload = self.session_payload()
        payload.pop("version")
        payload.pop("username")
        payload.pop("authenticated_username")
        payload.pop("base_url")
        with tempfile.TemporaryDirectory() as directory:
            session_path = Path(directory) / "session.dpapi"
            session_path.write_bytes(b"encrypted-placeholder")
            client = MODULE.SupersetClient(profile=self.profile, session_path=session_path)
            with patch.object(MODULE, "_load_secret", return_value=json.dumps(payload).encode()):
                self.assertFalse(client._load_cached_session())
            self.assertFalse(session_path.exists())

    def test_rejects_cache_bound_to_another_username(self):
        payload = self.session_payload(
            username="another-user",
            authenticated_username="another-user",
        )
        with tempfile.TemporaryDirectory() as directory:
            session_path = Path(directory) / "session.dpapi"
            session_path.write_bytes(b"encrypted-placeholder")
            client = MODULE.SupersetClient(profile=self.profile, session_path=session_path)
            with patch.object(MODULE, "_load_secret", return_value=json.dumps(payload).encode()):
                self.assertFalse(client._load_cached_session())
            self.assertFalse(session_path.exists())

    def test_accepts_cache_bound_to_configured_and_authenticated_username(self):
        payload = self.session_payload()
        with tempfile.TemporaryDirectory() as directory:
            session_path = Path(directory) / "session.dpapi"
            session_path.write_bytes(b"encrypted-placeholder")
            client = MODULE.SupersetClient(profile=self.profile, session_path=session_path)
            with patch.object(MODULE, "_load_secret", return_value=json.dumps(payload).encode()):
                self.assertTrue(client._load_cached_session())
            self.assertEqual(client._authenticated_username, "current-user")

    def test_changing_username_clears_old_credential_and_session(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile_path = root / "profile.json"
            credential_path = root / "credential.dpapi"
            session_path = root / "session.dpapi"
            MODULE.save_profile(self.profile, profile_path)
            credential_path.write_bytes(b"old-credential")
            session_path.write_bytes(b"old-session")
            args = Namespace(
                base_url=self.profile.base_url,
                username="new-user",
                database_id=self.profile.database_id,
                schema=self.profile.schema,
                sql_editor_id=None,
                ca_bundle=None,
                query_timeout=None,
                session_hours=None,
                max_result_rows=None,
            )
            with (
                patch.object(MODULE, "_profile_path", return_value=profile_path),
                patch.object(MODULE, "_credential_path", return_value=credential_path),
                patch.object(MODULE, "_session_path", return_value=session_path),
                redirect_stdout(io.StringIO()),
            ):
                MODULE.command_configure(args)
            self.assertFalse(credential_path.exists())
            self.assertFalse(session_path.exists())


if __name__ == "__main__":
    unittest.main()
