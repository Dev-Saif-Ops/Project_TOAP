"""CLI tests."""

import tempfile
from pathlib import Path

from toap.cli import cmd_pretty, cmd_validate
from argparse import Namespace


SAMPLE = '§T[domain]\nƒ(DB_SRC)>q:"hello"|l:5'


def test_pretty_valid(capsys):
    code = cmd_pretty(Namespace(text=SAMPLE, file=None))
    out = capsys.readouterr().out
    assert code == 0
    assert "[TOAP DECODED]" in out
    assert "DB_SRC" in out


def test_pretty_invalid(capsys):
    code = cmd_pretty(Namespace(text="not toap", file=None))
    out = capsys.readouterr().out
    assert code == 1
    assert "PARSE FAILED" in out


def test_validate_multiline_block(capsys):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(SAMPLE)
        f.write("\n\n")
        f.write('ƒ(WEB_SRC)>q:"test"|l:1')
        path = f.name

    code = cmd_validate(Namespace(file=path))
    out = capsys.readouterr().out
    Path(path).unlink()
    assert code == 0
    assert "2/2 valid" in out
