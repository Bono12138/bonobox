from __future__ import annotations

import argparse
import csv
import ctypes
import getpass
import hashlib
import json
import os
import platform
import random
import re
import string
import sys
import threading
import time
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Optional
from urllib.parse import unquote, urlparse

import requests
from ctypes import wintypes


APP_NAME = "bonobox-query-superset"
APP_VERSION = "1.0.0-beta.2"
DEFAULT_QUERY_TIMEOUT = 300
DEFAULT_SESSION_HOURS = 12
DEFAULT_TRANSIENT_RETRIES = 1
DEFAULT_MAX_RESULT_ROWS = 10_000
SESSION_CACHE_VERSION = 2
USER_AGENT = (
    f"bonobox-query-superset/{APP_VERSION} "
    "(Windows; read-only SQL Lab client)"
)
BLOCKED_KEYWORDS = {
    "ALTER", "ANALYZE", "ATTACH", "CALL", "COMMENT", "COPY", "CREATE",
    "DEALLOCATE", "DELETE", "DETACH", "DROP", "EXECUTE", "EXPORT", "GRANT",
    "IMPORT", "INSERT", "INTO", "LOCK", "MERGE", "OPTIMIZE", "PRAGMA",
    "PREPARE", "REFRESH", "RENAME", "REPLACE", "REVOKE", "SET", "TRUNCATE",
    "UNLOAD", "UNLOCK", "UPDATE", "USE", "VACUUM",
}
DANGEROUS_FUNCTIONS = {
    "DBLINK_EXEC", "LO_IMPORT", "NEXTVAL", "PG_ADVISORY_LOCK",
    "PG_ADVISORY_XACT_LOCK", "PG_CANCEL_BACKEND", "PG_TERMINATE_BACKEND",
    "SET_CONFIG", "SETVAL",
}


def _state_root() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    return (Path(base) if base else Path.home() / ".local" / "share") / APP_NAME


def _profile_path() -> Path:
    return _state_root() / "profile.json"


def _credential_path() -> Path:
    return _state_root() / "credential.dpapi"


def _session_path() -> Path:
    return _state_root() / "session.dpapi"


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _require_windows() -> None:
    if os.name != "nt":
        raise RuntimeError("This skill currently supports Windows only.")


def _blob_from_bytes(data: bytes) -> tuple[DATA_BLOB, ctypes.Array[Any]]:
    buffer = ctypes.create_string_buffer(data)
    blob = DATA_BLOB(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    return blob, buffer


def dpapi_protect(data: bytes) -> bytes:
    _require_windows()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    in_blob, _buffer = _blob_from_bytes(data)
    out_blob = DATA_BLOB()
    if not crypt32.CryptProtectData(
        ctypes.byref(in_blob), APP_NAME, None, None, None, 0, ctypes.byref(out_blob)
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        kernel32.LocalFree(out_blob.pbData)


def dpapi_unprotect(data: bytes) -> bytes:
    _require_windows()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    in_blob, _buffer = _blob_from_bytes(data)
    out_blob = DATA_BLOB()
    if not crypt32.CryptUnprotectData(
        ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        kernel32.LocalFree(out_blob.pbData)


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    try:
        tmp.write_bytes(data)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _save_secret(path: Path, data: bytes) -> None:
    _atomic_write(path, dpapi_protect(data))


def _load_secret(path: Path) -> bytes:
    return dpapi_unprotect(path.read_bytes())


@dataclass(frozen=True)
class Profile:
    base_url: str
    username: str
    database_id: str
    schema: str
    sql_editor_id: str = ""
    ca_bundle: str = ""
    query_timeout_seconds: int = DEFAULT_QUERY_TIMEOUT
    session_hours: int = DEFAULT_SESSION_HOURS
    max_result_rows: int = DEFAULT_MAX_RESULT_ROWS

    @property
    def tls_verify(self) -> bool | str:
        return self.ca_bundle or True


def _validate_profile(data: dict[str, Any]) -> Profile:
    required = ("base_url", "username", "database_id", "schema")
    missing = [key for key in required if not str(data.get(key, "")).strip()]
    if missing:
        raise RuntimeError("Missing profile fields: " + ", ".join(missing))
    base_url = str(data["base_url"]).strip().rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise RuntimeError("base_url must be a complete HTTPS URL.")
    ca_bundle = str(data.get("ca_bundle", "")).strip()
    if ca_bundle and not Path(ca_bundle).is_file():
        raise RuntimeError(f"Configured CA bundle does not exist: {ca_bundle}")
    timeout = int(data.get("query_timeout_seconds", DEFAULT_QUERY_TIMEOUT))
    session_hours = int(data.get("session_hours", DEFAULT_SESSION_HOURS))
    max_result_rows = int(data.get("max_result_rows", DEFAULT_MAX_RESULT_ROWS))
    if timeout < 1 or session_hours < 1 or max_result_rows < 1:
        raise RuntimeError("Timeout, session lifetime, and maximum result rows must be positive integers.")
    return Profile(
        base_url=base_url,
        username=str(data["username"]).strip(),
        database_id=str(data["database_id"]).strip(),
        schema=str(data["schema"]).strip(),
        sql_editor_id=str(data.get("sql_editor_id", "")).strip(),
        ca_bundle=ca_bundle,
        query_timeout_seconds=timeout,
        session_hours=session_hours,
        max_result_rows=max_result_rows,
    )


def load_profile(path: Optional[Path] = None) -> Profile:
    target = path or _profile_path()
    if not target.exists():
        raise RuntimeError(f"Profile not configured. Run configure first. Expected: {target}")
    return _validate_profile(json.loads(target.read_text(encoding="utf-8")))


def save_profile(profile: Profile, path: Optional[Path] = None) -> Path:
    target = path or _profile_path()
    payload = (json.dumps(asdict(profile), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    _atomic_write(target, payload)
    return target


def _extract_csrf_token(html: str) -> str:
    for pattern in (
        r'name=["\']csrf_token["\'][^>]*value=["\']([^"\']+)',
        r'id=["\']csrf_token["\'][^>]*value=["\']([^"\']+)',
    ):
        match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1)
    return ""


def _extract_authenticated_username(html: str) -> str:
    match = re.search(
        r'href=["\']/superset/profile/([^/"\'?]+)/?["\']',
        html,
        re.IGNORECASE,
    )
    return unquote(match.group(1)).strip() if match else ""


def _session_cache_matches_profile(saved: Any, profile: Profile) -> bool:
    if not isinstance(saved, dict):
        return False
    return (
        saved.get("version") == SESSION_CACHE_VERSION
        and str(saved.get("base_url", "")).rstrip("/") == profile.base_url
        and str(saved.get("username", "")).casefold() == profile.username.casefold()
        and str(saved.get("authenticated_username", "")).casefold()
        == profile.username.casefold()
    )


def _generate_client_id() -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=10))


def _sql_code(sql: str) -> str:
    """Replace strings/comments with spaces while preserving statement punctuation."""
    out: list[str] = []
    i = 0
    state = "code"
    quote = ""
    while i < len(sql):
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < len(sql) else ""
        if state == "code":
            if ch in ("'", '"', "`"):
                state, quote = "quote", ch
                out.append(" ")
            elif ch == "-" and nxt == "-":
                state = "line_comment"
                out.extend((" ", " "))
                i += 1
            elif ch == "/" and nxt == "*":
                state = "block_comment"
                out.extend((" ", " "))
                i += 1
            else:
                out.append(ch)
        elif state == "quote":
            out.append(" ")
            if ch == quote:
                if nxt == quote:
                    out.append(" ")
                    i += 1
                else:
                    state = "code"
            elif ch == "\\" and nxt:
                out.append(" ")
                i += 1
        elif state == "line_comment":
            out.append("\n" if ch in "\r\n" else " ")
            if ch in "\r\n":
                state = "code"
        else:
            out.append(" ")
            if ch == "*" and nxt == "/":
                out.append(" ")
                i += 1
                state = "code"
        i += 1
    if state in {"quote", "block_comment"}:
        raise ValueError("SQL contains an unterminated string or block comment.")
    return "".join(out)


def validate_readonly_sql(sql: str) -> str:
    sql = sql.lstrip("\ufeff").strip()
    if not sql:
        raise ValueError("SQL is empty.")
    code = _sql_code(sql)
    semicolons = [m.start() for m in re.finditer(";", code)]
    if semicolons:
        if len(semicolons) != 1 or code[semicolons[0] + 1 :].strip():
            raise ValueError("Submit exactly one SQL statement; multi-statement SQL is blocked.")
        sql = sql[: semicolons[0]].rstrip()
        code = code[: semicolons[0]]
    words = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", code.upper())
    if not words:
        raise ValueError("No SQL keyword was found.")
    if words[0] in {"SHOW", "DESCRIBE", "DESC"}:
        raise ValueError("SHOW/DESCRIBE are blocked by this Superset connection; query information_schema instead.")
    if words[0] not in {"SELECT", "WITH", "EXPLAIN"}:
        raise ValueError("Only SELECT, WITH ... SELECT, or EXPLAIN SELECT is allowed.")
    blocked = sorted(set(words) & BLOCKED_KEYWORDS)
    if blocked:
        raise ValueError("Write or administration keyword blocked: " + ", ".join(blocked))
    called_functions = {
        match.group(1).upper()
        for match in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", code)
    }
    dangerous = sorted(called_functions & DANGEROUS_FUNCTIONS)
    if dangerous:
        raise ValueError("State-changing or administrative function blocked: " + ", ".join(dangerous))
    if words[0] == "WITH" and "SELECT" not in words:
        raise ValueError("WITH must lead to a read-only SELECT.")
    if words[0] == "EXPLAIN" and not ({"SELECT", "WITH"} & set(words[1:])):
        raise ValueError("EXPLAIN must describe a SELECT query.")
    return sql


@dataclass
class ErrorInfo:
    category: str
    message: str
    query_id: Any = None
    status_code: Optional[int] = None
    retryable: bool = False
    details: Any = None


class SupersetError(RuntimeError):
    def __init__(self, info: ErrorInfo):
        super().__init__(info.message)
        self.info = info


class SupersetSQLError(SupersetError):
    pass


class SupersetServerError(SupersetError):
    pass


def _error_message(payload: Any, fallback: str) -> str:
    if isinstance(payload, dict):
        error = payload.get("error") or payload.get("message")
        if isinstance(error, str):
            return error.strip()
        if error is not None:
            return json.dumps(error, ensure_ascii=False)
    return fallback.strip()


def classify_error(status_code: int, payload: Any, fallback: str = "") -> ErrorInfo:
    message = _error_message(payload, fallback or f"HTTP {status_code}")
    lower = message.lower()
    query_id = payload.get("query_id") if isinstance(payload, dict) else None
    details = payload if isinstance(payload, dict) else fallback[:1000]
    if status_code in {401, 403} or "redirected to login" in lower or "login required" in lower:
        return ErrorInfo("auth", message, query_id, status_code, False, details)
    if "only select statements are allowed" in lower or "not allowed against this database" in lower:
        return ErrorInfo("policy", message, query_id, status_code, False, details)
    if any(x in lower for x in ("access denied", "permission denied", "not authorized", "unauthorized")):
        return ErrorInfo("permission", message, query_id, status_code, False, details)
    if any(x in lower for x in ("does not exist", "cannot be resolved", "not found", "unknown column", "unknown table")):
        return ErrorInfo("object", message, query_id, status_code, False, details)
    if any(x in lower for x in ("exceeded", "out of memory", "memory limit", "insufficient resources")):
        return ErrorInfo("resource", message, query_id, status_code, False, details)
    if any(x in lower for x in ("syntax", "mismatched input", "line ")):
        return ErrorInfo("sql", message, query_id, status_code, False, details)
    if "timed out" in lower or "timeout" in lower:
        return ErrorInfo("timeout", message, query_id, status_code, False, details)
    retryable = status_code in {429, 502, 503, 504}
    return ErrorInfo("server", message, query_id, status_code, retryable, details)


def _is_login_response(response: requests.Response, payload: Any) -> bool:
    if "login" in response.url.lower():
        return True
    content_type = response.headers.get("content-type", "").lower()
    return not isinstance(payload, (dict, list)) and "html" in content_type and "login" in response.text[:2000].lower()


def _response_payload(response: requests.Response) -> Any:
    try:
        return response.json()
    except (requests.exceptions.JSONDecodeError, json.JSONDecodeError, ValueError):
        return None


def find_sqllab_query(payload: Any, client_id: str) -> Optional[dict[str, Any]]:
    """Return a bounded SQL Lab status record for one known client id."""
    if isinstance(payload, dict):
        candidates = list(payload.values())
    elif isinstance(payload, list):
        candidates = payload
    else:
        return None
    allowed = (
        "id",
        "serverId",
        "state",
        "progress",
        "startDttm",
        "endDttm",
        "rows",
        "resultsKey",
        "errorMessage",
        "limit_reached",
    )
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        candidate_id = str(
            candidate.get("id") or candidate.get("client_id") or ""
        )
        if candidate_id == client_id:
            return {
                key: candidate.get(key)
                for key in allowed
                if key in candidate
            }
    return None


def _lifecycle_seconds(query: Any) -> Optional[float]:
    if not isinstance(query, dict):
        return None
    try:
        start = float(query["startDttm"])
        end = float(query["endDttm"])
    except (KeyError, TypeError, ValueError):
        return None
    if end < start:
        return None
    return round((end - start) / 1000.0, 3)


def poll_sqllab_status_once(
    session: requests.Session,
    base_url: str,
    since_ms: int,
    client_id: str,
) -> Optional[dict[str, Any]]:
    response = session.get(
        base_url + f"/superset/queries/{since_ms}",
        timeout=(5, 10),
    )
    if response.status_code != 200:
        return None
    try:
        payload = response.json()
    except (requests.exceptions.JSONDecodeError, json.JSONDecodeError, ValueError):
        return None
    return find_sqllab_query(payload, client_id)


class SupersetClient:
    def __init__(
        self,
        profile: Optional[Profile] = None,
        password_loader: Optional[Callable[[], str]] = None,
        *,
        session_path: Optional[Path] = None,
        database_id: Optional[str | int] = None,
        schema: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        selected_profile = profile or load_profile()
        overrides: dict[str, Any] = {}
        if database_id is not None:
            overrides["database_id"] = str(database_id)
        if schema is not None:
            overrides["schema"] = schema
        if timeout is not None:
            overrides["query_timeout_seconds"] = int(timeout)
        self.profile = replace(selected_profile, **overrides) if overrides else selected_profile
        self._password_loader = password_loader or self._default_password_loader
        self._session_path = session_path or _session_path()
        self._session: Optional[requests.Session] = None
        self._csrf_token = ""
        self._authenticated_username = ""
        self._session_source = "none"
        self.last_result: dict[str, Any] = {}
        self._last_transport_context: dict[str, Any] = {}

    @staticmethod
    def _default_password_loader() -> str:
        if not _credential_path().exists():
            raise SupersetError(ErrorInfo("auth", "Credential not configured. Run auth first."))
        return _load_secret(_credential_path()).decode("utf-8")

    def _new_session(self) -> requests.Session:
        session = requests.Session()
        session.verify = self.profile.tls_verify
        session.headers.update({"User-Agent": USER_AGENT})
        return session

    def _load_cached_session(self) -> bool:
        if not self._session_path.exists():
            return False
        try:
            saved = json.loads(_load_secret(self._session_path).decode("utf-8"))
            if not _session_cache_matches_profile(saved, self.profile):
                self._session_path.unlink(missing_ok=True)
                return False
            age = time.time() - float(saved["saved_at"])
            if age < 0 or age > self.profile.session_hours * 3600:
                self._session_path.unlink(missing_ok=True)
                return False
            session = self._new_session()
            for cookie in saved.get("cookies", []):
                session.cookies.set(
                    cookie["name"], cookie["value"], domain=cookie.get("domain") or None,
                    path=cookie.get("path") or "/", secure=bool(cookie.get("secure")),
                    expires=cookie.get("expires"),
                )
            self._session = session
            self._csrf_token = str(saved["csrf_token"])
            self._authenticated_username = str(saved["authenticated_username"])
            self._session_source = "cache"
            return bool(self._csrf_token and len(session.cookies))
        except Exception:
            self._session_path.unlink(missing_ok=True)
            self._session = None
            self._csrf_token = ""
            self._authenticated_username = ""
            return False

    def _save_cached_session(self) -> None:
        if not self._session or not self._csrf_token or not self._authenticated_username:
            return
        cookies = []
        for cookie in self._session.cookies:
            cookies.append({
                "name": cookie.name, "value": cookie.value, "domain": cookie.domain,
                "path": cookie.path, "secure": bool(cookie.secure), "expires": cookie.expires,
            })
        data = {
            "version": SESSION_CACHE_VERSION,
            "base_url": self.profile.base_url,
            "username": self.profile.username,
            "authenticated_username": self._authenticated_username,
            "saved_at": time.time(),
            "csrf_token": self._csrf_token,
            "cookies": cookies,
        }
        _save_secret(self._session_path, json.dumps(data).encode("utf-8"))

    def _login(self) -> None:
        password = self._password_loader()
        if not password:
            raise SupersetError(ErrorInfo("auth", "Empty Superset password."))
        session = self._new_session()
        try:
            login_page = session.get(self.profile.base_url + "/login/", timeout=(15, 30))
            login_page.raise_for_status()
            csrf = _extract_csrf_token(login_page.text)
            if not csrf:
                raise SupersetServerError(ErrorInfo("server", "Could not find the login CSRF token."))
            response = session.post(
                self.profile.base_url + "/login/",
                data={"username": self.profile.username, "password": password, "csrf_token": csrf},
                headers={"Referer": self.profile.base_url + "/login/", "Origin": self.profile.base_url},
                timeout=(15, 30), allow_redirects=False,
            )
            has_session = "session" in session.cookies
            if not ((response.status_code == 302 or response.status_code >= 500) and has_session):
                raise SupersetError(ErrorInfo("auth", f"Login failed: HTTP {response.status_code}."))
            sql_lab = session.get(self.profile.base_url + "/superset/sqllab", timeout=(15, 30))
            if "login" in sql_lab.url.lower():
                raise SupersetError(ErrorInfo("auth", "Superset did not accept the saved credential."))
            csrf = _extract_csrf_token(sql_lab.text)
            if not csrf:
                raise SupersetServerError(ErrorInfo("server", "Could not find the SQL Lab CSRF token."))
            authenticated_username = _extract_authenticated_username(sql_lab.text)
            if not authenticated_username:
                raise SupersetServerError(
                    ErrorInfo("server", "Could not verify which Superset user owns the new session.")
                )
            if authenticated_username.casefold() != self.profile.username.casefold():
                raise SupersetError(
                    ErrorInfo(
                        "auth",
                        "Superset session identity does not match the configured username.",
                        details={
                            "configured_username": self.profile.username,
                            "authenticated_username": authenticated_username,
                        },
                    )
                )
        except requests.exceptions.SSLError as exc:
            raise SupersetServerError(ErrorInfo("network", "TLS certificate verification failed. Configure your organization's CA bundle if required.", details=str(exc))) from exc
        except (requests.Timeout, requests.ConnectionError) as exc:
            raise SupersetServerError(ErrorInfo("network", "Could not connect to Superset. Check the required network, VPN, or access client.", retryable=True, details=str(exc))) from exc
        self._session = session
        self._csrf_token = csrf
        self._authenticated_username = authenticated_username
        self._session_source = "login"
        self._save_cached_session()

    def _ensure_session(self) -> None:
        if self._session and self._csrf_token:
            return
        if not self._load_cached_session():
            self._login()

    def _observe_query_status(
        self,
        client_id: str,
        since_ms: int,
        stop_event: threading.Event,
        timeline: list[dict[str, Any]],
        started: float,
    ) -> None:
        assert self._session is not None
        observer = self._new_session()
        observer.cookies.update(self._session.cookies)
        last_signature: tuple[Any, ...] | None = None
        try:
            while not stop_event.is_set() and len(timeline) < 500:
                observed_at = round(time.perf_counter() - started, 3)
                try:
                    record = poll_sqllab_status_once(
                        observer,
                        self.profile.base_url,
                        since_ms,
                        client_id,
                    )
                    if record:
                        signature = (
                            record.get("state"),
                            record.get("progress"),
                            record.get("rows"),
                            record.get("errorMessage"),
                            record.get("endDttm"),
                        )
                        if signature != last_signature:
                            timeline.append(
                                {
                                    "observed_at_seconds": observed_at,
                                    "record": record,
                                }
                            )
                            last_signature = signature
                        if str(record.get("state") or "").casefold() in {
                            "success",
                            "failed",
                            "stopped",
                        }:
                            break
                except requests.RequestException as exc:
                    timeline.append(
                        {
                            "observed_at_seconds": observed_at,
                            "observer_error": (
                                f"{type(exc).__name__}: {str(exc)[:300]}"
                            ),
                        }
                    )
                stop_event.wait(2.0)
        finally:
            observer.close()

    def _post_query(
        self,
        sql: str,
        *,
        timeout_seconds: Optional[int] = None,
    ) -> tuple[requests.Response, Any, str, list[dict[str, Any]]]:
        assert self._session is not None
        client_id = _generate_client_id()
        since_ms = int(time.time() * 1000) - 5000
        started = time.perf_counter()
        timeline: list[dict[str, Any]] = []
        stop_event = threading.Event()
        observer = threading.Thread(
            target=self._observe_query_status,
            args=(client_id, since_ms, stop_event, timeline, started),
            daemon=True,
            name=f"sqllab-status-{client_id}",
        )
        self._last_transport_context = {
            "client_id": client_id,
            "status_timeline": timeline,
        }
        observer.start()
        read_timeout = max(
            1,
            int(timeout_seconds or self.profile.query_timeout_seconds),
        )
        try:
            response = self._session.post(
                self.profile.base_url + "/superset/sql_json/",
                data={
                    "client_id": client_id,
                    "database_id": self.profile.database_id,
                    "json": "true",
                    "runAsync": "false",
                    "schema": self.profile.schema,
                    "sql": sql,
                    "sql_editor_id": self.profile.sql_editor_id,
                    "tab": "Query",
                    "tmp_table_name": "",
                    "select_as_cta": "false",
                    "templateParams": "{}",
                    "queryLimit": str(self.profile.max_result_rows),
                },
                headers={
                    "X-CSRFToken": self._csrf_token,
                    "Referer": self.profile.base_url + "/superset/sqllab/",
                },
                timeout=(15, read_timeout),
            )
        finally:
            stop_event.set()
            observer.join(timeout=1.0)
        return response, _response_payload(response), client_id, list(timeline)

    def execute(
        self,
        sql: str,
        *,
        max_retries: int = DEFAULT_TRANSIENT_RETRIES,
        timeout_seconds: Optional[int] = None,
    ) -> dict[str, Any]:
        sql = validate_readonly_sql(sql)
        max_retries = min(DEFAULT_TRANSIENT_RETRIES, max(0, int(max_retries)))
        relogged = False
        transient_attempt = 0
        started = time.perf_counter()
        while True:
            self._ensure_session()
            try:
                transport = (
                    self._post_query(
                        sql,
                        timeout_seconds=timeout_seconds,
                    )
                    if timeout_seconds is not None
                    else self._post_query(sql)
                )
                if len(transport) == 2:
                    response, payload = transport
                    transport_client_id = ""
                    status_timeline: list[dict[str, Any]] = []
                else:
                    (
                        response,
                        payload,
                        transport_client_id,
                        status_timeline,
                    ) = transport
            except requests.Timeout as exc:
                info = ErrorInfo(
                    "timeout",
                    "Query exceeded "
                    f"{int(timeout_seconds or self.profile.query_timeout_seconds)} "
                    "seconds.",
                    details={
                        "transport_error": str(exc),
                        **self._last_transport_context,
                    },
                )
                raise SupersetServerError(info) from exc
            except requests.ConnectionError as exc:
                info = ErrorInfo("network", "Connection to Superset failed.", retryable=True, details=str(exc))
                if transient_attempt < max_retries:
                    transient_attempt += 1
                    time.sleep(transient_attempt)
                    continue
                raise SupersetServerError(info) from exc
            if _is_login_response(response, payload) or response.status_code in {401, 403}:
                if relogged:
                    raise SupersetError(ErrorInfo("auth", "Superset session is invalid after a fresh login.", status_code=response.status_code))
                self._session_path.unlink(missing_ok=True)
                self._session = None
                self._csrf_token = ""
                self._authenticated_username = ""
                self._login()
                relogged = True
                continue
            if response.status_code != 200:
                info = classify_error(response.status_code, payload, response.text[:1000])
                if info.retryable and transient_attempt < max_retries:
                    transient_attempt += 1
                    time.sleep(transient_attempt)
                    continue
                error_type = SupersetSQLError if info.category in {"policy", "sql", "object", "permission", "resource"} else SupersetServerError
                raise error_type(info)
            if not isinstance(payload, (dict, list)):
                raise SupersetServerError(ErrorInfo(
                    "server", "Superset returned a non-JSON response.", status_code=response.status_code,
                    details={"content_type": response.headers.get("content-type", ""), "body_start": response.text[:300]},
                ))
            if isinstance(payload, dict) and payload.get("error"):
                info = classify_error(response.status_code, payload)
                raise SupersetSQLError(info)
            rows = payload.get("data", []) if isinstance(payload, dict) else payload
            if not isinstance(rows, list):
                raise SupersetServerError(ErrorInfo("server", "Superset JSON did not contain a row list.", details=payload))
            if len(rows) > self.profile.max_result_rows:
                raise SupersetSQLError(
                    ErrorInfo(
                        "resource",
                        "Superset returned more rows than the configured local result limit; nothing was saved.",
                        query_id=payload.get("query_id") if isinstance(payload, dict) else None,
                        details={
                            "row_count": len(rows),
                            "max_result_rows": self.profile.max_result_rows,
                            "note": "The synchronous endpoint may receive the server response before this local check runs.",
                        },
                    )
                )
            columns = payload.get("columns", []) if isinstance(payload, dict) else []
            column_names = []
            for column in columns if isinstance(columns, list) else []:
                column_names.append(str(column.get("name"))) if isinstance(column, dict) else column_names.append(str(column))
            if not column_names and rows and isinstance(rows[0], dict):
                column_names = list(rows[0].keys())
            query = (
                payload.get("query")
                if isinstance(payload, dict)
                and isinstance(payload.get("query"), dict)
                else {}
            )
            result = {
                "rows": rows, "columns": column_names,
                "query_id": payload.get("query_id") if isinstance(payload, dict) else None,
                "status": payload.get("status") if isinstance(payload, dict) else "success",
                "client_id": query.get("id") or transport_client_id,
                "server_query_id": (
                    query.get("serverId")
                    if query.get("serverId") is not None
                    else payload.get("query_id")
                    if isinstance(payload, dict)
                    else None
                ),
                "query_state": query.get("state"),
                "query_progress": query.get("progress"),
                "query_start_dttm": query.get("startDttm"),
                "query_end_dttm": query.get("endDttm"),
                "superset_lifecycle_seconds": _lifecycle_seconds(query),
                "query_rows": query.get("rows"),
                "results_key": query.get("resultsKey"),
                "query_error_message": query.get("errorMessage"),
                "limit_reached": bool(query.get("limit_reached")) or len(rows) >= self.profile.max_result_rows,
                "max_result_rows": self.profile.max_result_rows,
                "status_timeline": status_timeline,
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "session_source": self._session_source,
                "authenticated_username": self._authenticated_username,
                "database_connection_id": self.profile.database_id,
            }
            self.last_result = result
            return result

    def query(
        self,
        sql: str,
        max_retries: Optional[int] = None,
        timeout: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        original_profile = self.profile
        if timeout is not None:
            self.profile = replace(self.profile, query_timeout_seconds=int(timeout))
        retries = (
            DEFAULT_TRANSIENT_RETRIES
            if max_retries is None
            else min(DEFAULT_TRANSIENT_RETRIES, max(0, int(max_retries) - 1))
        )
        try:
            return self.execute(sql, max_retries=retries)["rows"]
        finally:
            self.profile = original_profile

    def close(self) -> None:
        if self._session:
            self._session.close()
        self._session = None
        self._csrf_token = ""
        self._authenticated_username = ""


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return str(value)


def _csv_safe(value: Any) -> Any:
    safe = _json_safe(value)
    if isinstance(safe, str) and safe.lstrip("\t\r\n").startswith(("=", "+", "-", "@")):
        return "'" + safe
    return safe


def _result_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_csv(path: Path, rows: list[Any], columns: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    column_list = list(columns)
    if not column_list and rows and isinstance(rows[0], dict):
        column_list = list(rows[0].keys())
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        if rows and not isinstance(rows[0], dict):
            writer = csv.writer(handle)
            writer.writerow(["value"])
            writer.writerows([[_csv_safe(row)] for row in rows])
            return
        writer = csv.writer(handle)
        writer.writerow([_csv_safe(column) for column in column_list])
        for row in rows:
            writer.writerow([_csv_safe(row.get(key)) for key in column_list])


def save_run(sql: str, result: dict[str, Any], output: Optional[Path] = None) -> dict[str, str]:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    sql_hash = hashlib.sha256(sql.encode("utf-8")).hexdigest()
    run_id = f"{stamp}-{sql_hash[:8]}"
    run_dir = _state_root() / "runs" / run_id
    result_path = output.resolve() if output else run_dir / "result.csv"
    run_dir.mkdir(parents=True, exist_ok=True)
    query_path = run_dir / "query.sql"
    manifest_path = run_dir / "manifest.json"
    query_path.write_text(sql.rstrip() + "\n", encoding="utf-8")
    _write_csv(result_path, result["rows"], result["columns"])
    profile = load_profile()
    manifest = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "base_url": profile.base_url,
        "database_id": profile.database_id,
        "schema": profile.schema,
        "query_id": result.get("query_id"),
        "client_id": result.get("client_id"),
        "server_query_id": result.get("server_query_id"),
        "status": result.get("status"),
        "query_state": result.get("query_state"),
        "query_progress": result.get("query_progress"),
        "query_start_dttm": result.get("query_start_dttm"),
        "query_end_dttm": result.get("query_end_dttm"),
        "superset_lifecycle_seconds": result.get("superset_lifecycle_seconds"),
        "status_timeline": result.get("status_timeline") or [],
        "query_rows": result.get("query_rows"),
        "results_key": result.get("results_key"),
        "query_error_message": result.get("query_error_message"),
        "limit_reached": result.get("limit_reached"),
        "max_result_rows": result.get("max_result_rows", profile.max_result_rows),
        "elapsed_seconds": result.get("elapsed_seconds"),
        "session_source": result.get("session_source"),
        "row_count": len(result["rows"]),
        "columns": result["columns"],
        "sql_sha256": sql_hash,
        "result_sha256": _result_hash(result_path),
        "query_path": str(query_path),
        "result_path": str(result_path),
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"run_dir": str(run_dir), "result_path": str(result_path), "manifest_path": str(manifest_path)}


def _prompt(label: str, current: str = "", *, required: bool = True) -> str:
    suffix = f" [{current}]" if current else ""
    value = input(f"{label}{suffix}: ").strip()
    value = value or current
    if required and not value:
        raise SystemExit(f"{label} is required.")
    return value


def command_configure(args: argparse.Namespace) -> int:
    current: dict[str, Any] = {}
    if _profile_path().exists():
        current = asdict(load_profile())
    interactive = not all((args.base_url, args.username, args.database_id, args.schema))
    data = {
        "base_url": args.base_url or (None if interactive else current.get("base_url")),
        "username": args.username or (None if interactive else current.get("username")),
        "database_id": args.database_id or (None if interactive else current.get("database_id")),
        "schema": args.schema or (None if interactive else current.get("schema")),
        "sql_editor_id": args.sql_editor_id if args.sql_editor_id is not None else current.get("sql_editor_id", ""),
        "ca_bundle": args.ca_bundle if args.ca_bundle is not None else current.get("ca_bundle", ""),
        "query_timeout_seconds": args.query_timeout or current.get("query_timeout_seconds", DEFAULT_QUERY_TIMEOUT),
        "session_hours": args.session_hours or current.get("session_hours", DEFAULT_SESSION_HOURS),
        "max_result_rows": args.max_result_rows or current.get("max_result_rows", DEFAULT_MAX_RESULT_ROWS),
    }
    if interactive:
        data["base_url"] = args.base_url or _prompt("Superset HTTPS URL", str(current.get("base_url", "")))
        data["username"] = args.username or _prompt("Username", str(current.get("username", "")))
        data["database_id"] = args.database_id or _prompt("SQL Lab database ID", str(current.get("database_id", "")))
        data["schema"] = args.schema or _prompt("Default schema", str(current.get("schema", "")))
        if args.sql_editor_id is None:
            data["sql_editor_id"] = _prompt("SQL editor ID (optional)", str(current.get("sql_editor_id", "")), required=False)
        if args.ca_bundle is None:
            data["ca_bundle"] = _prompt("Company CA bundle path (optional)", str(current.get("ca_bundle", "")), required=False)
    profile = _validate_profile(data)
    identity_changed = bool(current) and (
        str(current.get("base_url", "")).rstrip("/") != profile.base_url
        or str(current.get("username", "")).casefold() != profile.username.casefold()
    )
    target = save_profile(profile)
    _session_path().unlink(missing_ok=True)
    if identity_changed:
        _credential_path().unlink(missing_ok=True)
    print(json.dumps({
        "ok": True,
        "profile_path": str(target),
        "tls_verification": True,
        "credential_reset": identity_changed,
    }, ensure_ascii=False))
    return 0


def command_auth(_args: argparse.Namespace) -> int:
    load_profile()
    password = getpass.getpass("Superset password: ")
    confirm = getpass.getpass("Confirm Superset password: ")
    if not password or password != confirm:
        raise SystemExit("Passwords were empty or did not match. Nothing was saved.")
    _save_secret(_credential_path(), password.encode("utf-8"))
    _session_path().unlink(missing_ok=True)
    print(json.dumps({"ok": True, "credential_path": str(_credential_path()), "secret_printed": False}, ensure_ascii=False))
    return 0


def command_status(_args: argparse.Namespace) -> int:
    profile_exists = _profile_path().exists()
    cached_session_present = _session_path().exists()
    payload: dict[str, Any] = {
        "windows": os.name == "nt", "python": sys.version.split()[0],
        "requests": requests.__version__, "state_root": str(_state_root()),
        "profile_configured": profile_exists, "credential_configured": _credential_path().exists(),
        "cached_session_present": cached_session_present, "tls_verification": True,
    }
    if profile_exists:
        profile = load_profile()
        cached_session_matches_profile = False
        if cached_session_present:
            try:
                saved = json.loads(_load_secret(_session_path()).decode("utf-8"))
                cached_session_matches_profile = _session_cache_matches_profile(saved, profile)
            except Exception:
                cached_session_matches_profile = False
        payload["profile"] = {
            "base_url": profile.base_url, "username": profile.username,
            "database_connection_id": profile.database_id, "schema": profile.schema,
            "ca_bundle_configured": bool(profile.ca_bundle),
            "max_result_rows": profile.max_result_rows,
        }
        payload["cached_session_matches_profile"] = cached_session_matches_profile
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if profile_exists and payload["credential_configured"] and payload["windows"] else 2


def command_run(args: argparse.Namespace) -> int:
    if bool(args.sql) == bool(args.sql_file):
        raise SystemExit("Provide exactly one of --sql or --sql-file.")
    sql = args.sql if args.sql else args.sql_file.read_text(encoding="utf-8-sig")
    sql = validate_readonly_sql(sql)
    client = SupersetClient()
    result = client.execute(sql, max_retries=args.transient_retries)
    paths = {} if args.no_save else save_run(sql, result, args.output)
    preview_count = max(0, args.preview_rows)
    payload = {
        "ok": True, "query_id": result.get("query_id"), "status": result.get("status"),
        "elapsed_seconds": result["elapsed_seconds"], "session_source": result["session_source"],
        "authenticated_username": result["authenticated_username"],
        "database_connection_id": result["database_connection_id"],
        "row_count": len(result["rows"]), "columns": result["columns"],
        "max_result_rows": result["max_result_rows"],
        "limit_reached": result["limit_reached"],
        "preview": _json_safe(result["rows"][:preview_count]), **paths,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def command_doctor(args: argparse.Namespace) -> int:
    started = time.perf_counter()
    client = SupersetClient()
    result = client.execute("SELECT 1 AS connection_test", max_retries=args.transient_retries)
    print(json.dumps({
        "ok": True, "tls_verification": True, "query_id": result.get("query_id"),
        "session_source": result["session_source"],
        "configured_username": client.profile.username,
        "authenticated_username": result["authenticated_username"],
        "database_connection_id": result["database_connection_id"],
        "query_seconds": result["elapsed_seconds"], "total_seconds": round(time.perf_counter() - started, 3),
    }, ensure_ascii=False, indent=2))
    return 0


def build_compatibility_report(args: argparse.Namespace) -> dict[str, Any]:
    """Build a bounded report that is safe to paste into a public Issue."""
    platform_version = str(args.platform_version or "unknown").strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+() -]{0,49}", platform_version):
        raise ValueError(
            "Platform version may contain only a short public version label; "
            "do not include a URL, company name, path, or server detail."
        )
    return {
        "report_schema": 1,
        "tool": "bonobox-superset-query",
        "tool_version": APP_VERSION,
        "result": args.result,
        "platform": args.platform,
        "platform_version": platform_version,
        "login_type": args.login_type,
        "transport": args.transport,
        "operating_system": f"{platform.system()} {platform.release()}".strip(),
        "python": platform.python_version(),
        "agent": args.agent,
        "database_type": args.database_type,
        "doctor_select_1": args.doctor_result,
        "failure_stage": args.failure_stage,
        "error_category": args.error_category,
        "user_review_required": True,
        "redaction_notice": (
            "Do not add company names, internal URLs, usernames, credentials, "
            "cookies, tokens, SQL, results, object names, query IDs, local paths, "
            "customer data, or internal screenshots."
        ),
    }


def compatibility_report_markdown(report: dict[str, Any]) -> str:
    rows = [
        ("Tool version", report["tool_version"]),
        ("Result", report["result"]),
        ("Platform", report["platform"]),
        ("Platform version", report["platform_version"]),
        ("Login type", report["login_type"]),
        ("Query transport", report["transport"]),
        ("Operating system", report["operating_system"]),
        ("Python", report["python"]),
        ("Agent", report["agent"]),
        ("Database type", report["database_type"]),
        ("Doctor SELECT 1", report["doctor_select_1"]),
        ("Failure stage", report["failure_stage"]),
        ("Error category", report["error_category"]),
    ]
    lines = [
        "## Data platform compatibility report",
        "",
        "| Field | Value |",
        "|---|---|",
        *[f"| {label} | `{value}` |" for label, value in rows],
        "",
        "### Public-data check",
        "",
        "- [ ] I reviewed this report before posting it.",
        "- [ ] I did not add company names, internal URLs, usernames, credentials, cookies, tokens, SQL, results, object names, query IDs, local paths, customer data, or internal screenshots.",
        "",
        "> This report describes compatibility only. It does not prove that an enterprise platform or database is safe for unrestricted Agent access.",
    ]
    return "\n".join(lines) + "\n"


def command_compatibility_report(args: argparse.Namespace) -> int:
    report = build_compatibility_report(args)
    content = (
        compatibility_report_markdown(report)
        if args.format == "markdown"
        else json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(args.output, content.encode("utf-8"))
    print(content, end="")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Windows Superset read-only query helper for Agent skills.")
    sub = parser.add_subparsers(dest="command", required=True)
    configure = sub.add_parser("configure", help="Create or update the local non-secret profile.")
    configure.add_argument("--base-url")
    configure.add_argument("--username")
    configure.add_argument("--database-id")
    configure.add_argument("--schema")
    configure.add_argument("--sql-editor-id")
    configure.add_argument("--ca-bundle")
    configure.add_argument("--query-timeout", type=int)
    configure.add_argument("--session-hours", type=int)
    configure.add_argument("--max-result-rows", type=int)
    configure.set_defaults(handler=command_configure)
    auth = sub.add_parser("auth", help="Save the password with Windows DPAPI.")
    auth.set_defaults(handler=command_auth)
    status = sub.add_parser("status", help="Show setup state without making a network request.")
    status.set_defaults(handler=command_status)
    doctor = sub.add_parser("doctor", help="Run a live SELECT 1 connectivity check.")
    doctor.add_argument("--transient-retries", type=int, default=DEFAULT_TRANSIENT_RETRIES)
    doctor.set_defaults(handler=command_doctor)
    report = sub.add_parser(
        "compatibility-report",
        help="Generate a bounded, redacted report for a public compatibility Issue.",
    )
    report.add_argument(
        "--result", required=True,
        choices=("success", "partial", "failed", "unsupported"),
    )
    report.add_argument(
        "--platform", required=True,
        choices=(
            "superset-legacy", "superset-modern-api", "power-bi", "metabase",
            "dbx", "databricks", "other-enterprise-platform",
        ),
    )
    report.add_argument("--platform-version", default="unknown")
    report.add_argument(
        "--login-type", default="unknown",
        choices=("password-form", "sso", "oauth", "mfa", "custom", "token", "unknown"),
    )
    report.add_argument(
        "--transport", default="unknown",
        choices=("legacy-sync", "modern-api", "browser", "native-api", "unknown"),
    )
    report.add_argument(
        "--agent", default="unknown",
        choices=("codex", "cursor", "claude-code", "other", "unknown"),
    )
    report.add_argument(
        "--database-type", default="unknown",
        choices=(
            "hive", "trino", "presto", "postgresql", "mysql", "snowflake",
            "bigquery", "databricks", "other", "unknown",
        ),
    )
    report.add_argument(
        "--doctor-result", default="not-attempted",
        choices=("passed", "failed", "not-attempted"),
    )
    report.add_argument(
        "--failure-stage", default="none",
        choices=("none", "environment", "install", "configure", "auth", "doctor", "query"),
    )
    report.add_argument(
        "--error-category", default="none",
        choices=(
            "none", "unsupported", "auth", "policy", "permission", "sql", "object",
            "resource", "timeout", "network", "server", "local",
        ),
    )
    report.add_argument("--format", choices=("markdown", "json"), default="markdown")
    report.add_argument("--output", type=Path)
    report.set_defaults(handler=command_compatibility_report)
    run = sub.add_parser("run", help="Execute one read-only SQL statement.")
    run.add_argument("--sql")
    run.add_argument("--sql-file", type=Path)
    run.add_argument("--output", type=Path)
    run.add_argument("--preview-rows", type=int, default=20)
    run.add_argument("--transient-retries", type=int, default=DEFAULT_TRANSIENT_RETRIES)
    run.add_argument("--no-save", action="store_true")
    run.set_defaults(handler=command_run)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except SupersetError as exc:
        print(json.dumps({"ok": False, **_json_safe(asdict(exc.info))}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    except (RuntimeError, ValueError, OSError) as exc:
        print(json.dumps({"ok": False, "category": "local", "message": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
