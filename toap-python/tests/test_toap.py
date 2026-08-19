"""Tests for toap-python package."""

import pytest
from toap import TOAPParser, TOAPProxy, ToolRegistry


@pytest.fixture
def parser():
    return TOAPParser()


class TestParser:
    def test_full_react_pattern(self, parser):
        raw = '§T[sec_vuln_huawei_2026]\nƒ(DB_SRC)>q:"Huawei Cloud vulnerabilities"|l:5'
        r = parser.parse(raw)
        assert r.valid
        assert r.namespace == "DB_SRC"
        assert r.args == {"q": "Huawei Cloud vulnerabilities", "l": 5}

    def test_arg_aliases(self, parser):
        raw = 'ƒ(DB_SRC)>query:"test"|limit:5'
        r = parser.parse(raw)
        assert r.valid
        assert r.args == {"q": "test", "l": 5}

    def test_pretty_print(self, parser):
        raw = 'ƒ(DB_SRC)>q:"hello"|l:1'
        out = parser.pretty_print(raw)
        assert "[TOAP DECODED]" in out
        assert "DB_SRC" in out


class TestProxy:
    def test_intercept_and_execute(self):
        registry = ToolRegistry()
        registry.register("DB_SRC", lambda q, l=10: {"query": q, "limit": l})

        proxy = TOAPProxy(registry)
        raw = 'ƒ(DB_SRC)>q:"test"|l:5'
        result = proxy.intercept(raw)

        assert result.parsed.valid
        assert result.executed
        assert result.return_value == {"query": "test", "limit": 5}

    def test_rejects_invalid(self):
        proxy = TOAPProxy()
        result = proxy.intercept("not valid toap")
        assert not result.parsed.valid
        assert result.error


class TestPrompts:
    def test_build_system_prompt(self):
        from toap.prompts import build_system_prompt

        prompt = build_system_prompt("Query database", shots=2)
        assert "TOAP" in prompt
        assert "Query database" in prompt
        assert "§T" in prompt
