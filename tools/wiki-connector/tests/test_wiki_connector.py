import importlib.util
import io
import json
import pathlib
import sys
import unittest
from contextlib import redirect_stdout
from unittest import mock


MODULE_PATH = pathlib.Path(__file__).resolve().parents[1] / "wiki_connector.py"
SPEC = importlib.util.spec_from_file_location("wiki_connector", MODULE_PATH)
wiki = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = wiki
SPEC.loader.exec_module(wiki)


class FakeSession:
    base = "https://wiki.example.invalid"

    def __init__(self):
        self.paths = []
        self.closed = False

    def fetch_json(self, path):
        self.paths.append(path)
        if path == "/rest/api/user/current":
            return {"username": "tester", "displayName": "Test User"}
        if path.startswith("/rest/api/search?"):
            return {
                "totalSize": 1,
                "results": [{
                    "content": {"id": "42", "title": "Welcome", "type": "page"},
                    "excerpt": "safe excerpt",
                }],
            }
        if path.startswith("/rest/api/content/42?"):
            return {
                "id": "42",
                "title": "Welcome",
                "version": {"number": 3, "when": "2026-01-01"},
                "body": {"view": {"value": "<h1>Hello</h1><p>World</p>"}},
            }
        raise AssertionError("unexpected fake path: %s" % path)

    def close(self):
        self.closed = True


class SearchAndReadTests(unittest.TestCase):
    def test_search_encodes_cql_and_read_returns_markdown(self):
        sess = FakeSession()
        result = wiki.do_search(sess, "risk/a?b", field="text", limit=1)
        self.assertEqual(result["results"][0]["id"], "42")
        search_path = sess.paths[-1]
        self.assertIn("%2F", search_path)
        self.assertIn("%3F", search_path)
        self.assertNotIn("risk/a?b", search_path)

        page = wiki.do_read(sess, 42, chars=100)
        self.assertEqual(page["title"], "Welcome")
        self.assertIn("# Hello", page["body"])
        self.assertIn("World", page["body"])


class SupportReportTests(unittest.TestCase):
    def test_report_excludes_config_secrets_and_paths(self):
        cfg = {
            "wiki_base": "https://secret-company.example/wiki",
            "channel": "token",
            "platform": "server",
            "token_env": "VERY_SECRET_TOKEN_NAME",
            "allowed_users": ["private.person@example.com"],
            "browser": {"profile_dir": r"C:\\Users\\private\\profile"},
        }
        with mock.patch.object(wiki, "detect_browser", return_value=None), \
                mock.patch.object(wiki, "_safe_local_outcomes", return_value={"total": 0, "outcomes": {}}), \
                mock.patch.object(wiki, "_safe_last_failure", return_value=None):
            report = wiki.build_support_report(cfg)
        text = json.dumps(report, ensure_ascii=False)
        for secret in (
                "secret-company", "VERY_SECRET_TOKEN_NAME", "private.person",
                r"C:\\Users\\private"):
            self.assertNotIn(secret, text)
        self.assertEqual(report["channel"], "token")
        self.assertEqual(report["confluenceType"], "server")

    def test_issue_url_percent_encodes_report(self):
        url = wiki.support_issue_url({"note": "a/b?c & 中文"})
        self.assertIn("issues/new?title=", url)
        self.assertNotIn("a/b?c", url)
        self.assertIn("%2F", url)


class UrlValidationTests(unittest.TestCase):
    def test_accepts_https_base_and_optional_internal_http(self):
        self.assertEqual(
            wiki.normalize_wiki_url("https://wiki.example.com/confluence/"),
            "https://wiki.example.com/confluence")
        self.assertEqual(
            wiki.normalize_wiki_url("http://wiki.internal", allow_http=True),
            "http://wiki.internal")

    def test_rejects_credentials_query_page_url_and_plain_http(self):
        invalid = (
            "https://user:pass@wiki.example.com",
            "https://wiki.example.com/?token=secret",
            "https://wiki.example.com/pages/viewpage.action",
            "https://wiki.example.com/display/SPACE/Page",
            "http://wiki.example.com",
            "https://wiki.example.com/bad path",
        )
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(wiki.WikiError):
                wiki.normalize_wiki_url(value)


class DoctorTests(unittest.TestCase):
    def test_doctor_with_fake_token_session(self):
        sess = FakeSession()
        cfg = {"channel": "token", "platform": "server", "allowed_users": ["tester"]}
        out = io.StringIO()
        with mock.patch.object(wiki, "make_session", return_value=sess), \
                mock.patch.object(wiki, "_module_available", return_value=False), \
                redirect_stdout(out):
            wiki.cmd_doctor(cfg, object())
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["status"], "PASS")
        self.assertTrue(payload["checks"]["search"])
        self.assertTrue(payload["checks"]["read"])
        self.assertTrue(payload["checks"]["readOnly"])
        self.assertTrue(sess.closed)

    def test_real_command_failure_points_to_sanitized_report_flow(self):
        err = io.StringIO()
        with mock.patch.object(sys, "argv", ["wiki_connector.py", "doctor"]), \
                mock.patch.object(wiki, "load_config",
                                  side_effect=wiki.WikiError("configuration failed", code=6)), \
                mock.patch.object(wiki, "write_support_report") as write_report, \
                mock.patch.object(wiki, "save_last_failure"), \
                mock.patch.object(wiki, "log_telemetry"), \
                self.assertRaises(SystemExit) as stopped, \
                mock.patch("sys.stderr", err):
            wiki.main()
        self.assertEqual(stopped.exception.code, 6)
        payload = json.loads(err.getvalue())
        self.assertEqual(payload["next"],
                         "python wiki_connector.py report --open-issue")
        write_report.assert_called_once()


class ReadOnlyTests(unittest.TestCase):
    def test_cli_exposes_no_mutation_command(self):
        parser = wiki.build_parser()
        subparsers = next(action for action in parser._actions
                          if getattr(action, "choices", None))
        commands = set(subparsers.choices)
        self.assertFalse(commands & {"create", "update", "write", "delete", "attach"})
        self.assertTrue(wiki.READ_ONLY)

    def test_batch_rejects_mutation_job(self):
        sess = FakeSession()
        with self.assertRaises(wiki.WikiError):
            wiki.run_job(sess, {"action": "update", "page_id": 42})
        self.assertEqual(sess.paths, [])

    def test_browser_cdp_rejects_non_local_websocket(self):
        sess = wiki.BrowserSession({
            "wiki_base": "https://wiki.example.com",
            "platform": "server",
            "browser": {"port": 9222},
        })
        self.assertEqual(
            sess._local_websocket_url("ws://127.0.0.1:9222/devtools/page/1"),
            "ws://127.0.0.1:9222/devtools/page/1")
        with self.assertRaises(wiki.WikiError):
            sess._local_websocket_url("ws://192.0.2.10:9222/devtools/page/1")

    def test_source_does_not_weaken_browser_or_persist_token(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("--remote-allow-origins=*", source)
        self.assertNotIn("setx ", source.lower())
        self.assertIn("--remote-debugging-address=127.0.0.1", source)


if __name__ == "__main__":
    unittest.main()
