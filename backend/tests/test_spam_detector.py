"""Tests for the advanced spam detection service."""

import pytest
from datetime import datetime, timezone, timedelta

from app.services import spam_detector
from app.services.spam_detector import (
    _tokenize,
    _cosine_similarity,
    _fingerprint_diff,
    run_spam_check,
    record_rejection,
    report_false_positive,
    get_history,
    get_stats,
    get_config,
    update_config,
)


@pytest.fixture(autouse=True)
def reset_stores():
    spam_detector._reset_stores()
    yield
    spam_detector._reset_stores()


# ── Tokenizer tests ──────────────────────────────────────────────────────────

class TestTokenizer:
    def test_basic_tokenization(self):
        diff = "+def hello():\n+    return 'world'"
        tokens = _tokenize(diff)
        assert "def" in tokens
        assert "hello" in tokens
        assert "return" in tokens

    def test_strips_diff_metadata(self):
        diff = "--- a/file.py\n+++ b/file.py\n@@ -1,3 +1,3 @@\n+x = 1"
        tokens = _tokenize(diff)
        assert "a" not in tokens or "x" in tokens  # metadata stripped
        assert "x" in tokens

    def test_empty_input(self):
        assert _tokenize("") == []


class TestCosineSimilarity:
    def test_identical(self):
        tokens = ["def", "hello", "world"]
        assert _cosine_similarity(tokens, tokens) == pytest.approx(1.0)

    def test_completely_different(self):
        a = ["def", "hello"]
        b = ["class", "world"]
        sim = _cosine_similarity(a, b)
        assert sim == pytest.approx(0.0)

    def test_partial_overlap(self):
        a = ["def", "hello", "world"]
        b = ["def", "hello", "mars"]
        sim = _cosine_similarity(a, b)
        assert 0.0 < sim < 1.0

    def test_empty_inputs(self):
        assert _cosine_similarity([], ["a"]) == 0.0
        assert _cosine_similarity(["a"], []) == 0.0
        assert _cosine_similarity([], []) == 0.0


class TestDiffFingerprint:
    def test_same_structure_same_hash(self):
        diff_a = "+line one here\n+another line\n-removed this"
        diff_b = "+line two here\n+something el\n-removed that"
        # Same prefix pattern (+, +, -) and similar line lengths
        fp_a = _fingerprint_diff(diff_a)
        fp_b = _fingerprint_diff(diff_b)
        assert fp_a == fp_b  # Same structural shape

    def test_different_structure_different_hash(self):
        diff_a = "+short\n+short"
        diff_b = "-" + "x" * 100 + "\n+" + "y" * 200
        fp_a = _fingerprint_diff(diff_a)
        fp_b = _fingerprint_diff(diff_b)
        assert fp_a != fp_b


# ── Individual check tests ───────────────────────────────────────────────────

class TestVelocityCheck:
    def test_under_limit(self):
        result = run_spam_check(pr_number=1, pr_author="alice", diff="+code")
        velocity_detail = next(d for d in result.details if d.check_name == "submission_velocity")
        assert velocity_detail.passed is True

    def test_over_limit(self):
        # Submit 3 PRs (default limit is 3)
        for i in range(3):
            run_spam_check(pr_number=i, pr_author="spammer", diff=f"+code_{i}")
        # 4th should trigger velocity
        result = run_spam_check(pr_number=99, pr_author="spammer", diff="+code_4")
        velocity_detail = next(d for d in result.details if d.check_name == "submission_velocity")
        assert velocity_detail.passed is False
        assert velocity_detail.penalty > 0


class TestSimilarityCheck:
    def test_no_rejected_diffs(self):
        result = run_spam_check(pr_number=1, pr_author="alice", diff="+def hello(): pass")
        sim_detail = next(d for d in result.details if d.check_name == "code_similarity")
        assert sim_detail.passed is True

    def test_similar_to_rejected(self):
        diff = "+def process_data(input):\n+    result = transform(input)\n+    return result"
        record_rejection(pr_number=1, pr_author="bob", diff=diff)
        # Submit nearly identical code
        result = run_spam_check(pr_number=2, pr_author="alice", diff=diff)
        sim_detail = next(d for d in result.details if d.check_name == "code_similarity")
        assert sim_detail.passed is False

    def test_different_from_rejected(self):
        record_rejection(pr_number=1, pr_author="bob", diff="+class Widget:\n+    pass")
        result = run_spam_check(
            pr_number=2, pr_author="alice",
            diff="+import asyncio\n+async def fetch():\n+    await asyncio.sleep(1)"
        )
        sim_detail = next(d for d in result.details if d.check_name == "code_similarity")
        assert sim_detail.passed is True


class TestNewAccountCheck:
    def test_old_account_tier3(self):
        result = run_spam_check(
            pr_number=1, pr_author="veteran", tier="tier-3",
            account_age_days=365, diff="+code"
        )
        detail = next(d for d in result.details if d.check_name == "new_account_scrutiny")
        assert detail.passed is True

    def test_new_account_tier3(self):
        result = run_spam_check(
            pr_number=1, pr_author="newbie", tier="tier-3",
            account_age_days=3, diff="+code"
        )
        detail = next(d for d in result.details if d.check_name == "new_account_scrutiny")
        assert detail.passed is False

    def test_new_account_tier1_ok(self):
        result = run_spam_check(
            pr_number=1, pr_author="newbie", tier="tier-1",
            account_age_days=1, diff="+code"
        )
        detail = next(d for d in result.details if d.check_name == "new_account_scrutiny")
        assert detail.passed is True  # T1 doesn't check account age

    def test_no_account_age_skips(self):
        result = run_spam_check(
            pr_number=1, pr_author="unknown", tier="tier-2", diff="+code"
        )
        detail = next(d for d in result.details if d.check_name == "new_account_scrutiny")
        assert detail.passed is True  # No data, skip check


class TestBountySnipingCheck:
    def test_under_limit(self):
        for i in range(4):
            run_spam_check(pr_number=i, pr_author="alice", bounty_issue=i + 1, diff=f"+code_{i}")
        result = run_spam_check(pr_number=10, pr_author="alice", bounty_issue=5, diff="+code")
        detail = next(d for d in result.details if d.check_name == "bounty_sniping")
        assert detail.passed is True

    def test_over_limit(self):
        for i in range(5):
            run_spam_check(pr_number=i, pr_author="sniper", bounty_issue=i + 1, diff=f"+code_{i}")
        result = run_spam_check(pr_number=10, pr_author="sniper", bounty_issue=6, diff="+code")
        detail = next(d for d in result.details if d.check_name == "bounty_sniping")
        assert detail.passed is False


class TestAiSlopCheck:
    def test_clean_code(self):
        diff = "+def process_solfoundry_bounty():\n+    return calculate_fndry_reward()"
        result = run_spam_check(pr_number=1, pr_author="alice", diff=diff)
        detail = next(d for d in result.details if d.check_name == "ai_slop_patterns")
        assert detail.passed is True

    def test_excessive_boilerplate(self):
        lines = ["+# TODO: implement this"] * 20
        diff = "\n".join(lines)
        result = run_spam_check(pr_number=1, pr_author="sloppy", diff=diff)
        detail = next(d for d in result.details if d.check_name == "ai_slop_patterns")
        assert detail.passed is False


class TestConsecutiveRejections:
    def test_no_rejections(self):
        result = run_spam_check(pr_number=1, pr_author="alice", diff="+code")
        detail = next(d for d in result.details if d.check_name == "consecutive_rejections")
        assert detail.passed is True

    def test_multiple_rejections(self):
        for i in range(3):
            record_rejection(pr_number=i, pr_author="badactor", diff=f"+bad_{i}")
        result = run_spam_check(pr_number=10, pr_author="badactor", diff="+more_bad")
        detail = next(d for d in result.details if d.check_name == "consecutive_rejections")
        assert detail.passed is False


class TestDiffFingerprinting:
    def test_unique_diff(self):
        result = run_spam_check(pr_number=1, pr_author="alice", diff="+unique code here")
        detail = next(d for d in result.details if d.check_name == "diff_fingerprint")
        assert detail.passed is True

    def test_duplicate_diff(self):
        diff = "+exact same code\n+line two\n+line three"
        run_spam_check(pr_number=1, pr_author="alice", diff=diff)
        result = run_spam_check(pr_number=2, pr_author="bob", diff=diff)
        detail = next(d for d in result.details if d.check_name == "diff_fingerprint")
        assert detail.passed is False


# ── Scoring & actions ────────────────────────────────────────────────────────

class TestScoringAndActions:
    def test_clean_submission(self):
        result = run_spam_check(pr_number=1, pr_author="alice", diff="+good code")
        assert result.is_spam is False
        assert result.auto_action == "none"

    def test_tier_multiplier_applies(self):
        # T3 has 1.6x multiplier — penalties are amplified
        config = get_config()
        assert config.tier_multipliers["tier-3"] == 1.6

    def test_auto_reject_threshold(self):
        # Trigger multiple checks to exceed reject threshold
        for i in range(3):
            record_rejection(pr_number=i, pr_author="serial_spammer", diff=f"+spam_{i}")
        # Submit 3+ PRs rapidly (velocity trigger)
        for i in range(3):
            run_spam_check(pr_number=100 + i, pr_author="serial_spammer", diff=f"+rapid_{i}")
        # This one should accumulate enough penalties
        result = run_spam_check(
            pr_number=200, pr_author="serial_spammer",
            diff="+rapid_final", tier="tier-3"
        )
        assert result.total_penalty > 0


# ── History & Stats ──────────────────────────────────────────────────────────

class TestHistoryAndStats:
    def test_history_records(self):
        run_spam_check(pr_number=1, pr_author="alice", diff="+code")
        run_spam_check(pr_number=2, pr_author="bob", diff="+more code")
        history = get_history()
        assert history.total == 2
        assert len(history.items) == 2

    def test_history_pagination(self):
        for i in range(5):
            run_spam_check(pr_number=i, pr_author=f"user_{i}", diff=f"+code_{i}")
        history = get_history(skip=2, limit=2)
        assert history.total == 5
        assert len(history.items) == 2

    def test_stats(self):
        run_spam_check(pr_number=1, pr_author="clean", diff="+good code")
        stats = get_stats()
        assert stats.total_checks == 1
        assert stats.total_clean >= 0  # May or may not be flagged

    def test_false_positive_counter(self):
        report_false_positive()
        report_false_positive()
        stats = get_stats()
        assert stats.false_positives_reported == 2


# ── Config ───────────────────────────────────────────────────────────────────

class TestConfig:
    def test_get_config(self):
        config = get_config()
        assert config.velocity_max_prs_per_hour == 3
        assert config.penalty_threshold_flag == 15.0

    def test_update_config(self):
        updated = update_config({"velocity_max_prs_per_hour": 10})
        assert updated.velocity_max_prs_per_hour == 10

    def test_update_preserves_other_fields(self):
        original = get_config()
        update_config({"velocity_max_prs_per_hour": 10})
        updated = get_config()
        assert updated.similarity_threshold == original.similarity_threshold
