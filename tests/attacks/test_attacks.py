"""The security gate. A single failure here means the guardrail is broken."""

from __future__ import annotations

import pytest

from tests.attacks.corpus import MUST_ALLOW, MUST_BLOCK


@pytest.mark.parametrize("sql,why", MUST_BLOCK, ids=[w for _, w in MUST_BLOCK])
def test_must_block(guard, sql, why):
    verdict = guard.check(sql)
    assert verdict.allowed is False, f"SHOULD HAVE BLOCKED ({why}): {sql!r}"
    assert verdict.violated_rules, "a block must name the rule(s) it violated"


@pytest.mark.parametrize("sql", MUST_ALLOW)
def test_must_allow(guard, sql):
    verdict = guard.check(sql)
    assert verdict.allowed is True, f"FALSE BLOCK: {sql!r} -> {verdict.reason}"
    assert verdict.normalized_sql


def test_block_rate_is_total(guard):
    """Explicitly assert the headline metric: 100% block rate."""
    blocked = sum(1 for sql, _ in MUST_BLOCK if not guard.check(sql).allowed)
    assert blocked == len(MUST_BLOCK), f"block rate {blocked}/{len(MUST_BLOCK)}"
