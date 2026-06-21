"""Config defaults and YAML loading."""

from __future__ import annotations

from txt2sql.config import Config


def test_strict_defaults():
    c = Config()
    assert c.read_only is True
    assert c.allowed_statement_types == ["SELECT"]


def test_load_none_returns_defaults():
    assert Config.load(None).read_only is True


def test_load_yaml(tmp_path):
    p = tmp_path / "cfg.yaml"
    p.write_text(
        "read_only: false\nallowed_statement_types: [select, insert]\nrow_limit: 5\n",
        encoding="utf-8",
    )
    c = Config.load(p)
    assert c.read_only is False
    assert c.allowed_statement_types == ["SELECT", "INSERT"]  # upper-cased
    assert c.row_limit == 5
