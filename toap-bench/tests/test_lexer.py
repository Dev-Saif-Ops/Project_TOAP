"""Unit tests for TOAP v0.1 parser — 100% coverage on spec examples + edge cases."""

import pytest

from toap import TOAPParser


@pytest.fixture
def parser():
    return TOAPParser()


# ── Valid parses ──────────────────────────────────────────────

class TestValidParses:
    def test_full_react_pattern(self, parser):
        raw = '§T[sec_vuln_huawei_2026]\nƒ(DB_SRC)>q:"Huawei Cloud vulnerabilities"|l:5'
        r = parser.parse(raw)
        assert r.valid
        assert r.thought == "sec_vuln_huawei_2026"
        assert r.namespace == "DB_SRC"
        assert r.args == {"q": "Huawei Cloud vulnerabilities", "l": 5}

    def test_action_only_no_thought(self, parser):
        raw = 'ƒ(WEB_SRC)>q:"CVE-2026-1234 critical exploits"|l:10'
        r = parser.parse(raw)
        assert r.valid
        assert r.thought is None
        assert r.namespace == "WEB_SRC"
        assert r.args == {"q": "CVE-2026-1234 critical exploits", "l": 10}

    def test_api_call_multiple_args(self, parser):
        raw = '§T[infra_health_check]\nƒ(API_SRC)>endpoint:"/v1/status"|method:GET|timeout:30'
        r = parser.parse(raw)
        assert r.valid
        assert r.namespace == "API_SRC"
        assert r.args["endpoint"] == "/v1/status"
        assert r.args["method"] == "GET"
        assert r.args["timeout"] == 30

    def test_file_operation(self, parser):
        raw = '§T[report_generation]\nƒ(FS_SRC)>path:"/tmp/report.pdf"|mode:write'
        r = parser.parse(raw)
        assert r.valid
        assert r.namespace == "FS_SRC"
        assert r.args["path"] == "/tmp/report.pdf"
        assert r.args["mode"] == "write"

    def test_bare_identifier_value(self, parser):
        raw = "ƒ(API_SRC)>method:GET|format:json"
        r = parser.parse(raw)
        assert r.valid
        assert r.args["method"] == "GET"
        assert r.args["format"] == "json"

    def test_single_arg(self, parser):
        raw = 'ƒ(DB_SRC)>q:"simple query"'
        r = parser.parse(raw)
        assert r.valid
        assert r.args == {"q": "simple query"}

    def test_whitespace_trimmed(self, parser):
        raw = '  §T[domain]  \n  ƒ(NS)>k:"val"|n:1  '
        r = parser.parse(raw)
        assert r.valid
        assert r.thought == "domain"
        assert r.namespace == "NS"
        assert r.args == {"key": "val", "n": 1}


# ── Invalid parses ────────────────────────────────────────────

class TestInvalidParses:
    def test_empty_output(self, parser):
        r = parser.parse("")
        assert not r.valid
        assert any("Empty" in e.message for e in r.errors)

    def test_json_not_toap(self, parser):
        r = parser.parse('{"action": "query", "params": {}}')
        assert not r.valid

    def test_missing_action_line(self, parser):
        r = parser.parse("§T[domain_only]")
        assert not r.valid
        assert any("action" in e.message.lower() for e in r.errors)

    def test_empty_domain(self, parser):
        r = parser.parse("§T[]\nƒ(NS)>k:val")
        assert not r.valid

    def test_empty_namespace(self, parser):
        r = parser.parse('ƒ()>q:"test"')
        assert not r.valid

    def test_unquoted_string_with_spaces(self, parser):
        r = parser.parse("ƒ(DB_SRC)>q:unquoted string here")
        assert not r.valid

    def test_natural_language(self, parser):
        r = parser.parse("I will query the database for vulnerabilities.")
        assert not r.valid

    def test_multiple_action_lines(self, parser):
        raw = 'ƒ(A)>x:1\nƒ(B)>y:2'
        r = parser.parse(raw)
        assert not r.valid
        assert any("Multiple action" in e.message for e in r.errors)

    def test_duplicate_arg_keys(self, parser):
        raw = "ƒ(NS)>k:1|k:2"
        r = parser.parse(raw)
        assert not r.valid
        assert any("Duplicate" in e.message for e in r.errors)

    def test_invalid_arg_format(self, parser):
        raw = 'ƒ(NS)>badarg'
        r = parser.parse(raw)
        assert not r.valid


# ── Pretty printer ────────────────────────────────────────────

class TestPrettyPrint:
    def test_valid_pretty(self, parser):
        raw = '§T[domain]\nƒ(DB_SRC)>q:"test"|l:5'
        output = parser.pretty_print(raw)
        assert "[TOAP DECODED]" in output
        assert "domain" in output
        assert "DB_SRC" in output

    def test_invalid_pretty(self, parser):
        output = parser.pretty_print("not valid toap")
        assert "[TOAP PARSE FAILED]" in output


class TestArgAliases:
    def test_url_maps_to_endpoint(self, parser):
        raw = 'ƒ(API_SRC)>url:"/v1/status"|method:GET|timeout:30'
        r = parser.parse(raw)
        assert r.valid
        assert r.args["endpoint"] == "/v1/status"

    def test_query_limit_aliases(self, parser):
        raw = 'ƒ(DB_SRC)>query:"test query"|limit:5'
        r = parser.parse(raw)
        assert r.valid
        assert r.args == {"q": "test query", "l": 5}

    def test_action_maps_to_mode_lowercase(self, parser):
        raw = 'ƒ(FS_SRC)>path:"/etc/config"|action:READ'
        r = parser.parse(raw)
        assert r.valid
        assert r.args["mode"] == "read"

    def test_k_maps_to_key(self, parser):
        raw = 'ƒ(CACHE_SRC)>k:"session_123"'
        r = parser.parse(raw)
        assert r.valid
        assert r.args["key"] == "session_123"

    def test_time_maps_to_window(self, parser):
        raw = 'ƒ(LOG_SRC)>level:ERROR|time:"1h"|l:50'
        r = parser.parse(raw)
        assert r.valid
        assert r.args["window"] == "1h"

    def test_fs_op_read_maps_to_mode(self, parser):
        raw = 'ƒ(FS_SRC)>path:"/etc/config"|op:read'
        r = parser.parse(raw)
        assert r.valid
        assert r.args["mode"] == "read"

    def test_window_normalizes_last_hour(self, parser):
        raw = 'ƒ(LOG_SRC)>level:ERROR|time:"last 1 hour"|l:50'
        r = parser.parse(raw)
        assert r.valid
        assert r.args["window"] == "1h"
