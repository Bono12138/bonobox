#!/usr/bin/env python3
"""wiki_connector.py — Give your AI agent read-only access to your company wiki (Confluence).

Two access channels, one command set:

  Channel "token"   : official REST API with a Personal Access Token / basic credential
                      (recommended when your company issues API credentials).
  Channel "browser" : reuses a dedicated local browser profile that YOU log into.
                      The profile stays on this computer and may contain a live session.

Commands:
    init      Interactive (or flag-driven) setup + self-check
    status    Check connectivity and current wiki identity
    search    CQL keyword search        [--field text|title] [--limit 10]
    read      Read a page as markdown   --page-id N [--start 0] [--chars 12000]
    history   Version history           --page-id N | --diff A B | --at V
    batch     Run many jobs in one go   --jobs jobs.json [--out results.jsonl]
    feedback  Create a sanitized compatibility report and open a pre-filled Issue
    version   Print version

Exit codes: 0 ok · 2 auth/service problem · 3 identity not allowed ·
4 request failed · 6 missing/invalid configuration.
"""
import argparse
import difflib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from html.parser import HTMLParser

VERSION = "0.1.0-beta.1"
REPO_URL = "https://github.com/Bono12138/bonobox"
TOOL_URL = REPO_URL + "/tree/main/tools/wiki-connector"

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(TOOL_DIR, "config.json")
TELEMETRY_FILE = os.path.join(TOOL_DIR, "telemetry.jsonl")
SUPPORT_REPORT_FILE = os.path.join(TOOL_DIR, "support-report.json")
LAST_FAILURE_FILE = os.path.join(TOOL_DIR, ".last-failure.json")
DEFAULT_PORT = 9222
READ_ONLY = True

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ---------------------------------------------------------------- errors

class WikiError(Exception):
    def __init__(self, message, code=4):
        super().__init__(message)
        self.code = code


def die_config(hint):
    raise WikiError("Configuration missing or incomplete: %s\n"
                    "Run: python wiki_connector.py init" % hint, code=6)


# ---------------------------------------------------------------- telemetry

def log_telemetry(event):
    """Append one local JSON line (no credentials, no wiki content, no URLs).
    Telemetry never breaks the main flow and never leaves this machine unless
    the user explicitly runs `feedback` and confirms."""
    try:
        event = dict(event)
        event["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        event["v"] = VERSION
        with open(TELEMETRY_FILE, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------- config

def load_config(require=True):
    if not os.path.exists(CONFIG_FILE):
        if require:
            die_config("config.json not found.")
        return {}
    with open(CONFIG_FILE, encoding="utf-8") as fh:
        return json.load(fh)


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)
    try:
        os.chmod(CONFIG_FILE, 0o600)
    except OSError:
        pass  # Windows


def api_base(cfg):
    base = (cfg.get("wiki_base") or "").rstrip("/")
    if not base:
        die_config("wiki_base not set.")
    if cfg.get("platform") == "cloud" and not base.endswith("/wiki"):
        return base + "/wiki"
    return base


# ---------------------------------------------------------------- transports

class TokenSession:
    """Channel A: official REST API with a credential from an environment variable.

    The credential VALUE is never written to any file by this tool — config.json
    only stores the NAME of the environment variable that holds it.
    """

    def __init__(self, cfg):
        self.base = api_base(cfg)
        env_name = cfg.get("token_env") or "WIKI_TOKEN"
        self.env_name = env_name
        value = os.environ.get(env_name, "")
        if not value:
            die_config("environment variable %s is not set. Export your token first, "
                       "e.g.  set %s=your-token  (Windows) or export %s=your-token (macOS/Linux)"
                       % (env_name, env_name, env_name))
        token_type = cfg.get("token_type", "pat")
        if token_type == "basic":
            import base64
            self._auth = "Basic " + base64.b64encode(value.encode()).decode()
        else:
            self._auth = "Bearer " + value

    def fetch_json(self, path):
        req = urllib.request.Request(self.base + path)
        req.add_header("Authorization", self._auth)
        req.add_header("Accept", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise WikiError(
                    "Wiki returned %d: the credential in $%s is missing, expired, "
                    "or lacks permission. Renew it and retry." % (exc.code, self.env_name),
                    code=2)
            if exc.code == 404:
                raise WikiError("Wiki returned 404 for the requested read-only API endpoint.",
                                code=4)
            raise WikiError("Wiki returned %d for a read-only API request."
                            % exc.code, code=4)
        except urllib.error.URLError as exc:
            raise WikiError("Cannot reach the wiki. Check network/VPN and your "
                            "company TLS certificate trust.", code=2)


class BrowserSession:
    """Channel B: reuse the session of a local browser the user already logged into.

    The tool drives a dedicated browser instance (launched by `init` or `launch`)
    over its local automation interface and executes fetch() inside the wiki tab.
    The connector does not export or print cookies, passwords, or tokens. The dedicated
    local browser profile can contain a live session and must remain private."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.base = api_base(cfg)
        self.port = int(cfg.get("browser", {}).get("port") or DEFAULT_PORT)
        self.cdp = "http://127.0.0.1:%d" % self.port
        self.ws = None
        self._next_id = 1

    # -- low level -------------------------------------------------------
    def _http_json(self, url, timeout=5):
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read())

    def _list_tabs(self):
        return self._http_json(self.cdp + "/json/list")

    def _local_websocket_url(self, value):
        """Accept CDP websocket URLs only from this process's loopback port."""
        parsed = urllib.parse.urlsplit(value or "")
        if (parsed.scheme not in ("ws", "wss")
                or parsed.hostname not in ("127.0.0.1", "localhost", "::1")
                or parsed.port != self.port):
            raise WikiError(
                "The browser returned a non-local automation endpoint. Stopping.",
                code=2)
        return value

    def _find_wiki_tab(self, tabs):
        wiki_origin = (self.cfg.get("wiki_base") or "").rstrip("/")
        for tab in tabs:
            if tab.get("type") == "page" and tab.get("url", "").startswith(wiki_origin):
                return tab
        return None

    def connect(self):
        try:
            import websocket
        except ImportError:
            raise WikiError("Missing dependency: pip install websocket-client", code=6)
        try:
            tabs = self._list_tabs()
        except Exception:
            raise WikiError(
                "The local wiki browser is not running. Start it with:\n"
                "  python wiki_connector.py login\nthen complete the login in the window "
                "— it will wait for you and confirm.", code=2)
        tab = self._find_wiki_tab(tabs)
        if tab is None:
            version = self._http_json(self.cdp + "/json/version")
            ws = websocket.create_connection(
                self._local_websocket_url(version["webSocketDebuggerUrl"]),
                timeout=30, suppress_origin=True)
            ws.send(json.dumps({"id": 1, "method": "Target.createTarget",
                                "params": {"url": self.cfg.get("wiki_base")}}))
            while True:
                msg = json.loads(ws.recv())
                if msg.get("id") == 1:
                    break
            ws.close()
            deadline = time.time() + 60
            while time.time() < deadline:
                tabs = self._list_tabs()
                tab = self._find_wiki_tab(tabs)
                if tab is not None:
                    break
                time.sleep(1)
        if tab is None:
            raise WikiError(
                "No wiki page found yet — the browser is probably waiting for you to "
                "log in. Complete the login in the opened window, then retry.", code=2)
        self.ws = websocket.create_connection(
            self._local_websocket_url(tab["webSocketDebuggerUrl"]),
            timeout=60, suppress_origin=True)
        return self

    def close(self):
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass

    def _eval_js(self, expression):
        msg_id = self._next_id
        self._next_id += 1
        try:
            self.ws.send(json.dumps({
                "id": msg_id, "method": "Runtime.evaluate",
                "params": {"expression": expression, "awaitPromise": True,
                           "returnByValue": True}}))
            while True:
                msg = json.loads(self.ws.recv())
                if msg.get("id") != msg_id:
                    continue
                if "error" in msg:
                    raise WikiError("Local query service communication error", code=2)
                result = msg.get("result", {})
                if result.get("exceptionDetails"):
                    raise WikiError("In-page script error: %s"
                                    % result["exceptionDetails"].get("text"), code=4)
                return result.get("result", {}).get("value")
        except WikiError:
            raise
        except Exception:
            raise WikiError(
                "The local wiki browser stopped responding. Retry once; if it keeps "
                "happening, run: python wiki_connector.py login", code=4)

    # -- public ----------------------------------------------------------
    def fetch_json(self, path):
        url = self.base + path
        expr = """(async () => {
            const r = await fetch(%s, {credentials: 'same-origin',
                                      headers: {'Accept': 'application/json'}});
            const text = await r.text();
            let data = null;
            try { data = JSON.parse(text); } catch (e) { data = null; }
            return JSON.stringify({status: r.status, data: data,
                                   snippet: text.slice(0, 200)});
        })()""" % json.dumps(url)
        raw = None
        for attempt in range(4):
            try:
                raw = self._eval_js(expr)
                break
            except WikiError as exc:
                # page still loading: relative fetch can fail early; wait and retry
                if "Failed to parse URL" in str(exc) and attempt < 3:
                    time.sleep(2)
                    continue
                raise
        if raw is None:
            raise WikiError("In-page fetch returned nothing (the tab may be "
                            "redirecting to a login page).", code=2)
        out = json.loads(raw)
        status = out["status"]
        if status in (401, 403):
            raise WikiError(
                "Wiki returned %d: the browser session is not logged in (any more). "
                "Run: python wiki_connector.py login  — it opens the window, waits "
                "for you, and confirms when done." % status, code=2)
        if out["data"] is None:
            raise WikiError("Wiki returned %d with a non-JSON response. The session may "
                            "be on a login or proxy page." % status, code=4)
        if status >= 400:
            raise WikiError("Wiki returned %d for a read-only API request." % status,
                            code=4)
        return out["data"]


# ---------------------------------------------------------------- markdown

class MarkdownConverter(HTMLParser):
    """Minimal HTML -> markdown for Confluence view bodies (stdlib only)."""

    BLOCK_TAGS = {"p", "div", "section", "article", "header", "footer", "blockquote"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self._pre = 0
        self._list_stack = []
        self._skip = 0  # inside script/style
        self._cell = []
        self._row = []
        self._in_cell = False
        self._rows = []

    def _emit(self, text):
        self.parts.append(text)

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1
            return
        if self._skip:
            return
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._emit("\n\n" + "#" * (int(tag[1])) + " ")
        elif tag == "br":
            self._emit("\n")
        elif tag in self.BLOCK_TAGS:
            self._emit("\n\n")
        elif tag in ("ul", "ol"):
            self._list_stack.append(tag)
            self._emit("\n")
        elif tag == "li":
            self._emit("\n" + "  " * (len(self._list_stack) - 1) + "- ")
        elif tag == "pre":
            self._pre += 1
            self._emit("\n\n```\n")
        elif tag == "code" and not self._pre:
            self._emit("`")
        elif tag == "table":
            self._rows = []
            self._emit("\n\n")
        elif tag == "tr":
            self._row = []
        elif tag in ("td", "th"):
            self._cell = []
            self._in_cell = True
        elif tag == "strong" or tag == "b":
            self._emit("**")
        elif tag == "em" or tag == "i":
            self._emit("*")
        elif tag == "img":
            src = dict(attrs).get("src", "")
            alt = dict(attrs).get("alt", "image")
            if src:
                self._emit("![%s](%s)" % (alt, src))
        elif tag == "a":
            pass  # link text is kept; href dropped for brevity

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = max(0, self._skip - 1)
            return
        if self._skip:
            return
        if tag in ("ul", "ol"):
            if self._list_stack:
                self._list_stack.pop()
            self._emit("\n")
        elif tag == "pre":
            self._pre = max(0, self._pre - 1)
            self._emit("\n```\n")
        elif tag == "code" and not self._pre:
            self._emit("`")
        elif tag in ("td", "th"):
            self._in_cell = False
            self._row.append("".join(self._cell).replace("|", "\\|").strip())
        elif tag == "tr":
            if self._row:
                self._rows.append(self._row)
        elif tag == "table":
            for i, row in enumerate(self._rows):
                self._emit("| " + " | ".join(row) + " |\n")
                if i == 0:
                    self._emit("|" + " --- |" * len(row) + "\n")
            self._rows = []
        elif tag in ("strong", "b"):
            self._emit("**")
        elif tag in ("em", "i"):
            self._emit("*")

    def handle_data(self, data):
        if self._skip:
            return
        if self._in_cell:
            self._cell.append(data)
            return
        if self._pre:
            self._emit(data)
        else:
            self._emit(" ".join(data.split()) + " " if data.strip() else "")

    def text(self):
        out = "".join(self.parts)
        while "\n\n\n" in out:
            out = out.replace("\n\n\n", "\n\n")
        return out.strip()


def to_markdown(html_text):
    conv = MarkdownConverter()
    try:
        conv.feed(html_text)
        return conv.text()
    except Exception:
        return html_text  # never fail a read because of formatting


# ---------------------------------------------------------------- shared ops

def make_session(cfg):
    channel = cfg.get("channel")
    if channel == "token":
        return TokenSession(cfg)
    if channel == "browser":
        return BrowserSession(cfg).connect()
    die_config("channel must be 'token' or 'browser'.")


def current_user(sess):
    data = sess.fetch_json("/rest/api/user/current")
    username = data.get("username") or data.get("name") or ""
    display = data.get("displayName") or ""
    return username, display


def check_identity(sess, cfg):
    username, display = current_user(sess)
    if not username:
        raise WikiError("Could not determine the current wiki identity — "
                        "probably not logged in.", code=2)
    allowed = {u.lower() for u in cfg.get("allowed_users") or []}
    if allowed and username.lower() not in allowed:
        raise WikiError(
            "Current wiki identity %r is not in the allowed_users list from your "
            "config (%s). Stopping. If this is the wrong account, log out and back in "
            "with the right one; if it should be allowed, update config.json."
            % (username, sorted(allowed)), code=3)
    return username, display


SEARCH_ENDPOINTS = ["/rest/api/search", "/rest/api/content/search"]


def do_search(sess, query, field="text", limit=10):
    safe_q = query.replace("\\", "\\\\").replace('"', '\\"')
    cql = '%s~"%s"' % ("title" if field == "title" else "text", safe_q)
    last_404 = None
    for endpoint in SEARCH_ENDPOINTS:
        path = "%s?cql=%s&limit=%d" % (
            endpoint, urllib.parse.quote(cql, safe=""), limit)
        try:
            data = sess.fetch_json(path)
        except WikiError as exc:
            if "404" in str(exc) and endpoint == SEARCH_ENDPOINTS[0]:
                last_404 = exc
                continue
            raise
        results = []
        for item in data.get("results", []):
            content = item.get("content") if endpoint == "/rest/api/search" else item
            content = content or {}
            page_id = content.get("id")
            if not page_id:
                continue
            results.append({
                "id": page_id,
                "title": content.get("title", ""),
                "type": content.get("type", ""),
                "excerpt": (item.get("excerpt") or "")[:300],
                "lastModified": item.get("lastModified", "")
                or ((content.get("version") or {}).get("when") or ""),
            })
        return {"cql": cql, "totalSize": data.get("totalSize", len(results)),
                "results": results}
    raise last_404 or WikiError("No search endpoint available", code=4)


def do_read(sess, page_id, start=0, chars=12000, fmt="markdown"):
    data = sess.fetch_json(
        "/rest/api/content/%d?expand=body.view,body.storage,version,space" % page_id)
    body = ((data.get("body") or {}).get("view") or {}).get("value") \
        or ((data.get("body") or {}).get("storage") or {}).get("value") or ""
    if fmt == "markdown":
        body = to_markdown(body)
    total = len(body)
    start = max(0, start)
    end = min(total, start + chars)
    return {
        "id": str(page_id),
        "title": data.get("title", ""),
        "version": (data.get("version") or {}).get("number"),
        "lastModified": (data.get("version") or {}).get("when", ""),
        "url": "%s/pages/viewpage.action?pageId=%d" % (api_base_url(sess), page_id),
        "format": fmt,
        "bodyTotalChars": total,
        "start": start,
        "nextStart": end if end < total else None,
        "body": body[start:end],
    }


def api_base_url(sess):
    return sess.base


def _version_meta(sess, page_id, number):
    """Metadata of one version via the historical-status read (works on old
    Confluence where /version listing does not exist)."""
    data = sess.fetch_json(
        "/rest/api/content/%d?status=historical&version=%d&expand=version"
        % (page_id, number))
    v = data.get("version") or {}
    return {"version": v.get("number", number), "when": v.get("when", ""),
            "by": ((v.get("by") or {}).get("displayName")
                   or (v.get("by") or {}).get("username") or ""),
            "comment": v.get("message", "")}


def do_history_list(sess, page_id, max_versions=20):
    current = sess.fetch_json("/rest/api/content/%d?expand=version" % page_id)
    cur_no = (current.get("version") or {}).get("number")
    versions = []
    synthesized = False
    try:
        data = sess.fetch_json("/rest/api/content/%d/version?limit=200" % page_id)
        for v in data.get("results", []):
            versions.append({
                "version": v.get("number"),
                "when": v.get("when", ""),
                "by": ((v.get("by") or {}).get("displayName")
                       or (v.get("by") or {}).get("username") or ""),
                "comment": v.get("message", ""),
            })
    except WikiError as exc:
        if "404" not in str(exc):
            raise
        # Older Confluence: synthesize the list by probing historical versions
        # (current down to current-max_versions+1).
        synthesized = True
        for n in range(cur_no, max(0, cur_no - max_versions), -1):
            try:
                versions.append(_version_meta(sess, page_id, n))
            except WikiError:
                break  # hit a deleted/unavailable version; stop there
    versions.sort(key=lambda v: v.get("version") or 0, reverse=True)
    for v in versions:
        v["current"] = (v["version"] == cur_no)
    out = {"pageId": str(page_id), "currentVersion": cur_no, "versions": versions}
    if synthesized:
        out["note"] = ("This Confluence version has no version-list endpoint; "
                       "showing the latest %d versions." % len(versions))
    return out


def do_read_at(sess, page_id, version_no, chars=12000):
    data = sess.fetch_json(
        "/rest/api/content/%d?status=historical&version=%d&expand=body.view,version"
        % (page_id, version_no))
    body = ((data.get("body") or {}).get("view") or {}).get("value") or ""
    body = to_markdown(body)
    return {
        "id": str(page_id),
        "title": data.get("title", ""),
        "version": version_no,
        "format": "markdown",
        "bodyTotalChars": len(body),
        "body": body[:chars],
        "truncated": len(body) > chars,
    }


def do_diff(sess, page_id, va, vb):
    a = do_read_at(sess, page_id, va, chars=400000)["body"]
    b = do_read_at(sess, page_id, vb, chars=400000)["body"]
    diff = list(difflib.unified_diff(
        a.splitlines(), b.splitlines(),
        fromfile="v%d" % va, tofile="v%d" % vb, lineterm=""))
    added = [l[1:].strip() for l in diff if l.startswith("+") and not l.startswith("+++") and l[1:].strip()]
    removed = [l[1:].strip() for l in diff if l.startswith("-") and not l.startswith("---") and l[1:].strip()]
    return {"pageId": str(page_id), "from": va, "to": vb,
            "added": added, "removed": removed}


# ---------------------------------------------------------------- browser launch

BROWSER_CANDIDATES = {
    "win32": [
        os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                     "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                     "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                     "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                     "Microsoft", "Edge", "Application", "msedge.exe"),
    ],
    "darwin": [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ],
    "linux": ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
              "microsoft-edge"],
}


def detect_browser():
    for cand in BROWSER_CANDIDATES.get(sys.platform, BROWSER_CANDIDATES["linux"]):
        found = shutil.which(cand) or (cand if os.path.exists(cand) else None)
        if found:
            return found
    return None


def port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def pick_port(preferred=DEFAULT_PORT):
    if port_free(preferred):
        return preferred
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def launch_browser(cfg, wait_seconds=20):
    """Start the dedicated wiki browser (idempotent)."""
    browser = (cfg.get("browser") or {})
    exe = browser.get("path") or detect_browser()
    if not exe:
        raise WikiError("No Chrome/Edge/Chromium found. Set browser.path in "
                        "config.json to your browser executable.", code=6)
    port = int(browser.get("port") or DEFAULT_PORT)
    if not port_free(port):
        print(json.dumps({"service": "already_running", "port": port},
                         ensure_ascii=False))
        return
    profile = browser.get("profile_dir") or os.path.join(TOOL_DIR, ".browser-profile")
    url = cfg.get("wiki_base") or "about:blank"
    args = [exe, "--remote-debugging-address=127.0.0.1",
            "--remote-debugging-port=%d" % port,
            "--user-data-dir=%s" % profile, "--no-first-run", url]
    kwargs = {"close_fds": True}
    if sys.platform == "win32":
        kwargs["creationflags"] = (getattr(subprocess, "DETACHED_PROCESS", 0)
                                   | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(args, **kwargs)
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if not port_free(port):
            print(json.dumps({"service": "started", "port": port}, ensure_ascii=False))
            return
        time.sleep(1)
    raise WikiError("Browser did not start within %ds." % wait_seconds, code=2)


# ---------------------------------------------------------------- commands

def cmd_status(cfg, _args):
    sess = make_session(cfg)
    try:
        username, display = check_identity(sess, cfg)
        print(json.dumps({"service": "connected", "channel": cfg.get("channel"),
                          "identity": username, "displayName": display,
                          "identityAllowed": True}, ensure_ascii=False, indent=2))
    finally:
        if hasattr(sess, "close"):
            sess.close()


def cmd_search(cfg, args):
    sess = make_session(cfg)
    try:
        username, _ = check_identity(sess, cfg)
        out = {"identity": username}
        out.update(do_search(sess, args.query, args.field, args.limit))
        print(json.dumps(out, ensure_ascii=False, indent=2))
    finally:
        if hasattr(sess, "close"):
            sess.close()


def cmd_read(cfg, args):
    sess = make_session(cfg)
    try:
        username, _ = check_identity(sess, cfg)
        out = {"identity": username}
        out.update(do_read(sess, args.page_id, args.start, args.chars, args.format))
        print(json.dumps(out, ensure_ascii=False, indent=2))
    finally:
        if hasattr(sess, "close"):
            sess.close()


def cmd_history(cfg, args):
    sess = make_session(cfg)
    try:
        username, _ = check_identity(sess, cfg)
        out = {"identity": username}
        if args.diff:
            out.update(do_diff(sess, args.page_id, args.diff[0], args.diff[1]))
        elif args.at:
            out.update(do_read_at(sess, args.page_id, args.at, args.chars))
        else:
            out.update(do_history_list(sess, args.page_id))
        print(json.dumps(out, ensure_ascii=False, indent=2))
    finally:
        if hasattr(sess, "close"):
            sess.close()


def run_job(sess, job):
    action = job.get("action")
    if action == "search":
        return do_search(sess, job["query"], job.get("field", "text"),
                         int(job.get("limit", 10)))
    if action == "read":
        return do_read(sess, int(job["page_id"]), int(job.get("start", 0)),
                       int(job.get("chars", 12000)), job.get("format", "markdown"))
    if action == "history":
        return do_history_list(sess, int(job["page_id"]))
    raise WikiError("Unknown action %r (supported: search / read / history)"
                    % action, code=4)


def cmd_batch(cfg, args):
    with open(args.jobs, encoding="utf-8") as fh:
        jobs = json.load(fh)
    if not isinstance(jobs, list) or not jobs:
        raise WikiError("jobs file must be a non-empty JSON array", code=4)
    sess = make_session(cfg)
    lines, ok_count = [], 0
    try:
        username, _ = check_identity(sess, cfg)
        for idx, job in enumerate(jobs):
            try:
                result = run_job(sess, job)
                ok_count += 1
                lines.append(json.dumps({"index": idx, "ok": True, "result": result},
                                        ensure_ascii=False))
            except WikiError as exc:
                if exc.code in (2, 3):
                    raise  # session/identity problems abort the whole batch
                lines.append(json.dumps({"index": idx, "ok": False,
                                         "error": str(exc)}, ensure_ascii=False))
    finally:
        if hasattr(sess, "close"):
            sess.close()
    payload = "\n".join(lines) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(payload)
        print(json.dumps({"identity": username, "jobs": len(jobs), "ok": ok_count,
                          "failed": len(jobs) - ok_count, "out": args.out},
                         ensure_ascii=False))
    else:
        sys.stdout.write(payload)
    if ok_count == 0:
        sys.exit(4)


def cmd_launch(cfg, _args):
    launch_browser(cfg)


LOGIN_GUIDE = """
================= 需要你操作：登录公司 Wiki =================

一个浏览器窗口已经打开（或已经存在），里面是公司 Wiki。

请看一下那个窗口：

  情况 1：页面已经能看到 Wiki 内容（有你的头像/名字）
          -> 什么都不用做，本命令会自动检测到并继续。

  情况 2：页面停在登录页
          -> 用你平时登录公司系统的方式完成登录：
             点 SSO 登录按钮 / 输密码 / 手机审批 / 扫码，都可以。
             登录成功后本命令会自动检测到并继续。

  注意：
  * 这个窗口请保持开着（可以最小化，不要关闭）。
  * 整个过程最多等 10 分钟；超时没登录的话，重新运行本命令即可。

正在等待你完成登录（每 3 秒自动检查一次）...
"""

LOGIN_GUIDE_EN = """
================= ACTION NEEDED: log in to your company wiki =================

A browser window has opened (or is already open) showing your company wiki.

Please look at that window:

  Case 1: you already see wiki content (your avatar/name is shown)
          -> nothing to do; this command will detect it and continue.

  Case 2: the page is a login page
          -> log in the way you normally do at your company:
             SSO button / password / phone approval / QR code — all fine.
             This command will detect the login and continue automatically.

  Notes:
  * Keep this window open (minimizing is fine, do not close it).
  * We wait up to 10 minutes; if it times out, just run this command again.

Waiting for you to complete the login (checking every 3 seconds)...
"""


def cmd_login(cfg, _args):
    """First-class login UX: launch the browser, show crystal-clear guidance,
    wait until the user is actually logged in, and confirm the identity."""
    if cfg.get("channel") != "browser":
        # token channel has no interactive login; just verify the token
        sess = TokenSession(cfg)
        username, display = current_user(sess)
        print("Token channel is active. Identity: %s (%s)" % (display, username))
        return
    launch_browser(cfg)
    print(LOGIN_GUIDE_EN)
    print(LOGIN_GUIDE)
    deadline = time.time() + 600
    while time.time() < deadline:
        try:
            sess = BrowserSession(cfg).connect()
            username, display = current_user(sess)
            sess.close()
            print("\nLogin OK — you are %s (%s)." % (display, username))
            print("登录成功 —— 当前身份：%s (%s)。" % (display, username))
            print("You can now tell your agent to continue. / 现在可以告诉你的 Agent 继续了。")
            return
        except WikiError:
            time.sleep(3)
    raise WikiError(
        "Login was not completed within 10 minutes. / 10 分钟内未完成登录。\n"
        "Just run the same command again:  python wiki_connector.py login",
        code=2)


def cmd_version(_cfg, _args):
    print(json.dumps({"name": "wiki-connector", "version": VERSION,
                      "repo": REPO_URL}, ensure_ascii=False))


def _safe_local_outcomes():
    from collections import Counter
    try:
        with open(TELEMETRY_FILE, encoding="utf-8") as fh:
            rows = [json.loads(line) for line in fh if line.strip()]
    except Exception:
        rows = []
    counts = Counter(str(row.get("outcome", "unknown")) for row in rows)
    return {"total": len(rows), "outcomes": dict(sorted(counts.items()))}


def _safe_last_failure():
    try:
        with open(LAST_FAILURE_FILE, encoding="utf-8") as fh:
            value = json.load(fh)
        if isinstance(value, dict):
            return {key: value.get(key) for key in ("action", "category", "code", "ts")}
    except Exception:
        pass
    return None


def build_support_report(cfg=None):
    """Build a shareable report without wiki URL, identity, query, content or paths."""
    import platform as _pf
    cfg = cfg or {}
    channel = cfg.get("channel")
    if channel not in ("token", "browser"):
        channel = "not-configured"
    confluence_type = cfg.get("platform")
    if confluence_type not in ("server", "cloud"):
        confluence_type = "not-detected"
    return {
        "tool": "wiki-connector",
        "version": VERSION,
        "reportSchema": 1,
        "os": {"system": _pf.system(), "release": _pf.release(),
               "machine": _pf.machine()},
        "python": "%d.%d.%d" % sys.version_info[:3],
        "configPresent": os.path.exists(CONFIG_FILE),
        "channel": channel,
        "confluenceType": confluence_type,
        "browserDetected": bool(detect_browser()),
        "dependency": {"websocketClient": _module_available("websocket")},
        "localRuns": _safe_local_outcomes(),
        "lastFailure": _safe_last_failure(),
        "privacy": "No wiki URL, username, query, page ID, content, credential or local path.",
    }


def _module_available(name):
    try:
        __import__(name)
        return True
    except Exception:
        return False


def write_support_report(cfg=None):
    report = build_support_report(cfg)
    with open(SUPPORT_REPORT_FILE, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    return report


def save_last_failure(action, category, code):
    value = {"action": action, "category": category, "code": code,
             "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    try:
        with open(LAST_FAILURE_FILE, "w", encoding="utf-8") as fh:
            json.dump(value, fh, ensure_ascii=False, indent=2)
    except Exception:
        pass


def support_issue_url(report):
    title = "[wiki-connector] 兼容性反馈 v%s" % VERSION
    body = ("请先确认下面内容不含公司名称、网址、账号、查询词或文档内容，再提交。\n\n"
            "```json\n%s\n```\n\n"
            "发生了什么：\n\nAgent 已尝试过什么：\n\n是否安装成功：是 / 否\n"
            % json.dumps(report, ensure_ascii=False, indent=2))
    return "%s/issues/new?title=%s&body=%s" % (
        REPO_URL, urllib.parse.quote(title, safe=""),
        urllib.parse.quote(body, safe=""))


def cmd_report(cfg, args):
    report = write_support_report(cfg)
    url = support_issue_url(report)
    result = {"report": os.path.basename(SUPPORT_REPORT_FILE), "safeToShare": True,
              "reviewBeforeSubmit": True, "issueUrl": url}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.open_issue:
        webbrowser.open(url)


def cmd_doctor(cfg, _args):
    browser_channel = cfg.get("channel") == "browser"
    checks = {
        "python": True,
        "dependency": (not browser_channel) or _module_available("websocket"),
        "config": bool(cfg),
        "browser": (not browser_channel) or bool(detect_browser()),
        "readOnly": READ_ONLY,
        "connection": False,
        "identity": False,
        "search": False,
        "read": False,
    }
    sess = make_session(cfg)
    try:
        check_identity(sess, cfg)
        checks["connection"] = True
        checks["identity"] = True
        probe = do_search(sess, "a", limit=1)
        checks["search"] = True
        first = next((row for row in probe.get("results", []) if row.get("id")), None)
        if not first:
            path = "/rest/api/search?cql=%s&limit=1" % urllib.parse.quote(
                "type=page", safe="")
            data = sess.fetch_json(path)
            candidates = [(item.get("content") or item) for item in data.get("results", [])]
            first = next((row for row in candidates if row.get("id")), None)
        if first:
            checks["read"] = bool(do_read(sess, int(first["id"]), chars=100).get("title"))
    finally:
        if hasattr(sess, "close"):
            sess.close()
    if not all(checks.values()):
        raise WikiError("doctor did not complete every check: %s" % checks, code=4)
    print(json.dumps({"status": "PASS", "checks": checks,
                      "supportCommand": "python wiki_connector.py report --open-issue"},
                     ensure_ascii=False, indent=2))


def cmd_feedback(cfg, args):
    """Compatibility alias for the support-report flow."""
    args.open_issue = True
    cmd_report(cfg, args)


# ---------------------------------------------------------------- init

def _detect_platform(wiki_base):
    """Return ('server'|'cloud', api_base) by probing anonymous endpoints."""
    for platform, base in (("server", wiki_base.rstrip("/")),
                           ("cloud", wiki_base.rstrip("/") + "/wiki")):
        req = urllib.request.Request(base + "/rest/api/user/current")
        req.add_header("Accept", "application/json")
        try:
            urllib.request.urlopen(req, timeout=10)
            return platform, base  # 200 without auth (rare but fine)
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                return platform, base  # reachable, needs login
        except Exception:
            continue
    raise WikiError("Could not reach a Confluence REST API. Check the base URL, "
                    "VPN/network and TLS certificate trust, then retry.", code=6)


def normalize_wiki_url(value, allow_http=False):
    value = (value or "").strip().rstrip("/")
    if any(ord(ch) < 32 for ch in value) or any(ch.isspace() for ch in value):
        raise WikiError("Wiki URL must not contain spaces or control characters.", code=6)
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in ("https", "http") or not parsed.netloc:
        raise WikiError("Wiki URL must be a complete http(s) URL.", code=6)
    if parsed.username or parsed.password:
        raise WikiError("Do not put a username or password inside the Wiki URL.", code=6)
    if parsed.query or parsed.fragment:
        raise WikiError("Use the Wiki base URL without query parameters or fragments.", code=6)
    path_lower = parsed.path.lower()
    if ("/pages/" in path_lower or "/display/" in path_lower
            or "/spaces/" in path_lower):
        raise WikiError("Use the Wiki base URL, not a page or space URL.", code=6)
    if parsed.scheme == "http" and not allow_http:
        raise WikiError(
            "This Wiki uses plain HTTP. If your company intentionally runs an internal "
            "HTTP Wiki, review that risk and re-run init with --allow-http.", code=6)
    return value


def cmd_init(_cfg, args):
    wiki_url = args.wiki_url
    if not wiki_url and not args.non_interactive:
        wiki_url = input("Your company Confluence URL (e.g. https://wiki.example.com): ").strip()
    if not wiki_url:
        raise WikiError("init needs --wiki-url (or an interactive answer).", code=6)
    wiki_url = normalize_wiki_url(wiki_url, args.allow_http)

    print("[1/5] Detecting Confluence type ...")
    platform, _ = _detect_platform(wiki_url)
    print("      -> %s" % platform)

    channel = args.channel
    if not channel and not args.non_interactive:
        print("\nWhich access channel?")
        print("  token   = official API token/PAT (recommended if your company issues one)")
        print("  browser = use a dedicated local browser profile (the login session stays on this computer)")
        channel = (input("Channel [browser]: ").strip() or "browser")
    channel = channel or "browser"

    cfg = {"wiki_base": wiki_url, "platform": platform, "channel": channel,
           "allowed_users": []}

    if channel == "token":
        env_name = args.token_env or "WIKI_TOKEN"
        cfg["token_env"] = env_name
        cfg["token_type"] = args.token_type
        if not os.environ.get(env_name):
            print("\nSet your credential as an environment variable named %s" % env_name)
            print("  Windows PowerShell（只在当前窗口生效）:")
            print("    $env:%s = Read-Host \"Token\"" % env_name)
            print("  macOS/Linux:    export %s=\"your-token\"" % env_name)
            print("For Confluence Server/DC use a Personal Access Token (Profile -> "
                  "Personal Access Tokens). For Cloud use email:api-token and "
                  "--token-type basic.")
            if args.non_interactive:
                raise WikiError("$%s not set; set it and re-run init." % env_name, code=6)
            input("Press Enter after setting it (this terminal must see the variable) ...")
    else:
        port = args.port or pick_port()
        cfg["browser"] = {"port": port,
                          "profile_dir": os.path.join(TOOL_DIR, ".browser-profile")}
        if args.browser_path:
            cfg["browser"]["path"] = args.browser_path

    save_config(cfg)
    print("[2/5] config.json written (channel=%s)" % channel)

    if channel == "browser":
        print("[3/5] Starting the dedicated wiki browser ...")
        print("[4/5] Guided login — watch the browser window:")
        cmd_login(cfg, args)
    else:
        print("[3/5] Checking token ...")
        sess = TokenSession(cfg)
        username, display = current_user(sess)
        print("      Token works. Identity: %s (%s)" % (display, username))
        print("[4/5] (no browser needed for token channel)")

    print("[5/5] Self-check: search + read ...")
    cfg = load_config()
    sess = make_session(cfg)
    try:
        probe = do_search(sess, "a", limit=1)
        if not probe["results"]:
            # some wikis need a real word; fall back to CQL type filter
            path = "/rest/api/search?cql=%s&limit=1" % urllib.parse.quote(
                "type=page", safe="")
            data = sess.fetch_json(path)
            probe = {"results": [{"id": (i.get("content") or {}).get("id")}
                                 for i in data.get("results", [])]}
        first = next((r for r in probe["results"] if r.get("id")), None)
        if not first:
            raise WikiError("Self-check search returned no pages at all.", code=4)
        read_back = do_read(sess, int(first["id"]), chars=200)
        assert read_back["title"], "empty title on self-check read"
    finally:
        if hasattr(sess, "close"):
            sess.close()

    print("\nPASS — wiki-connector is ready. Try:")
    print("  python wiki_connector.py search --query \"onboarding\"")
    print("  python wiki_connector.py read --page-id %s" % first["id"])
    print("\nPoint your AI agent at INSTALL.md so it learns how to use these commands.")


# ---------------------------------------------------------------- main

def build_parser():
    parser = argparse.ArgumentParser(description="Read-only company wiki connector "
                                                 "for AI agents")
    parser.add_argument("--version", action="store_true", help="print version")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("init", help="first-time setup + self-check")
    p.add_argument("--wiki-url", default="")
    p.add_argument("--channel", choices=["token", "browser"], default="")
    p.add_argument("--token-env", default="")
    p.add_argument("--token-type", choices=["pat", "basic"], default="pat")
    p.add_argument("--browser-path", default="")
    p.add_argument("--port", type=int, default=0)
    p.add_argument("--allow-http", action="store_true")
    p.add_argument("--non-interactive", action="store_true")

    sub.add_parser("launch", help="start the dedicated wiki browser (browser channel)")

    sub.add_parser("login", help="guided login: opens the window, waits for you, "
                                 "and confirms your identity")

    p = sub.add_parser("status", help="check connectivity and identity")

    p = sub.add_parser("search", help="keyword search (CQL)")
    p.add_argument("--query", required=True)
    p.add_argument("--field", choices=["text", "title"], default="text")
    p.add_argument("--limit", type=int, default=10)

    p = sub.add_parser("read", help="read a page (markdown, segmented)")
    p.add_argument("--page-id", type=int, required=True)
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--chars", type=int, default=12000)
    p.add_argument("--format", choices=["markdown", "html"], default="markdown")

    p = sub.add_parser("history", help="page version history / diff / read old version")
    p.add_argument("--page-id", type=int, required=True)
    p.add_argument("--diff", nargs=2, type=int, metavar=("A", "B"))
    p.add_argument("--at", type=int, default=0, metavar="V")
    p.add_argument("--chars", type=int, default=12000)

    p = sub.add_parser("batch", help="run many search/read/history jobs in one session")
    p.add_argument("--jobs", required=True)
    p.add_argument("--out", default="")

    sub.add_parser("doctor", help="run connection, identity, search and read checks")
    p = sub.add_parser("report", help="create a sanitized support report")
    p.add_argument("--open-issue", action="store_true")
    sub.add_parser("feedback", help="create a sanitized report and open GitHub Issues")
    sub.add_parser("version", help="print version")
    return parser


def outcome_of(exc):
    msg = str(exc)
    if exc.code == 6:
        return "config"
    if exc.code == 3:
        return "identity"
    if exc.code == 2 and ("not running" in msg or "did not start" in msg):
        return "service_down"
    if exc.code == 2:
        return "auth"
    return "request_failed"


def main():
    args = build_parser().parse_args()
    if args.version and not args.cmd:
        cmd_version({}, args)
        return
    if not args.cmd:
        build_parser().print_help()
        sys.exit(6)
    handlers = {"init": cmd_init, "launch": cmd_launch, "login": cmd_login,
                "status": cmd_status,
                "search": cmd_search, "read": cmd_read, "history": cmd_history,
                "batch": cmd_batch, "doctor": cmd_doctor, "report": cmd_report,
                "feedback": cmd_feedback, "version": cmd_version}
    handler = handlers[args.cmd]
    started = time.time()
    try:
        if args.cmd in ("init", "version"):
            cfg = {}
        elif args.cmd in ("report", "feedback"):
            cfg = load_config(require=False)
        else:
            cfg = load_config()
        handler(cfg, args)
        log_telemetry({"action": args.cmd, "outcome": "ok",
                       "latencySec": round(time.time() - started, 1)})
    except WikiError as exc:
        category = outcome_of(exc)
        log_telemetry({"action": args.cmd, "outcome": category,
                       "latencySec": round(time.time() - started, 1)})
        save_last_failure(args.cmd, category, exc.code)
        try:
            write_support_report(locals().get("cfg") or {})
        except Exception:
            pass
        print(json.dumps({"error": str(exc), "code": exc.code,
                          "supportReport": os.path.basename(SUPPORT_REPORT_FILE),
                          "next": "python wiki_connector.py report --open-issue"},
                         ensure_ascii=False),
              file=sys.stderr)
        sys.exit(exc.code)
    except FileNotFoundError as exc:
        save_last_failure(args.cmd, "local_file", 4)
        write_support_report(locals().get("cfg") or {})
        print(json.dumps({"error": "A required local file was not found.", "code": 4,
                          "supportReport": os.path.basename(SUPPORT_REPORT_FILE),
                          "next": "python wiki_connector.py report --open-issue"},
                         ensure_ascii=False), file=sys.stderr)
        sys.exit(4)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as exc:  # never leak a traceback to the caller
        log_telemetry({"action": args.cmd, "outcome": "internal"})
        save_last_failure(args.cmd, "internal", 4)
        try:
            write_support_report(locals().get("cfg") or {})
        except Exception:
            pass
        print(json.dumps({"error": "An internal error occurred (%s)."
                                   % type(exc).__name__, "code": 4,
                          "supportReport": os.path.basename(SUPPORT_REPORT_FILE),
                          "next": "python wiki_connector.py report --open-issue"},
                         ensure_ascii=False), file=sys.stderr)
        sys.exit(4)


if __name__ == "__main__":
    main()
