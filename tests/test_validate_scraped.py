from datetime import date

import pytest

from scripts.validate_scraped import normalize_whitespace, validate_extraction

PAGE = """
CHI 2026 Call for Participation

Late-Breaking Work submission deadline: February 12, 2026
Workshop proposals are due October 15, 2025
"""

START = date(2026, 4, 13)
TODAY = date(2025, 9, 8)


def item(**kw):
    base = {
        "type": "lbw",
        "label": "Late-Breaking Work",
        "date": "2026-02-12 23:59:59",
        "confidence": "high",
        "raw_text": "Late-Breaking Work submission deadline: February 12, 2026",
        "url": "https://chi2026.acm.org/lbw/",
    }
    base.update(kw)
    return base


def test_accepts_item_whose_raw_text_appears_in_page():
    accepted, rejected = validate_extraction([item()], PAGE, START, TODAY)
    assert len(accepted) == 1
    assert rejected == []
    assert accepted[0]["evidence"]["raw_text"].startswith("Late-Breaking Work")
    assert accepted[0]["evidence"]["url"] == "https://chi2026.acm.org/lbw/"
    assert "confidence" not in accepted[0]


def test_rejects_fabricated_raw_text():
    # 모델이 문장을 지어낸 경우 - 가장 중요한 방어선
    bad = item(raw_text="Poster deadline: March 3, 2026", type="poster")
    accepted, rejected = validate_extraction([bad], PAGE, START, TODAY)
    assert accepted == []
    assert rejected[0]["reject_reason"] == "raw_text_not_in_page"


def test_raw_text_match_ignores_whitespace_differences():
    spaced = item(raw_text="Late-Breaking   Work submission deadline:\n February 12, 2026")
    accepted, _ = validate_extraction([spaced], PAGE, START, TODAY)
    assert len(accepted) == 1


def test_rejects_deadline_after_conference_start():
    late = item(date="2026-05-01 23:59:59")
    accepted, rejected = validate_extraction([late], PAGE, START, TODAY)
    assert accepted == []
    assert rejected[0]["reject_reason"] == "deadline_after_conference"


def test_rejects_deadline_more_than_18_months_before_conference():
    ancient = item(date="2024-01-01 23:59:59")
    accepted, rejected = validate_extraction([ancient], PAGE, START, TODAY)
    assert accepted == []
    assert rejected[0]["reject_reason"] == "deadline_too_early"


def test_rejects_low_confidence():
    unsure = item(confidence="low")
    accepted, rejected = validate_extraction([unsure], PAGE, START, TODAY)
    assert accepted == []
    assert rejected[0]["reject_reason"] == "low_confidence"


def test_rejects_unparseable_date():
    broken = item(date="sometime in spring")
    accepted, rejected = validate_extraction([broken], PAGE, START, TODAY)
    assert accepted == []
    assert rejected[0]["reject_reason"] == "unparseable_date"


def test_rejects_missing_raw_text():
    empty = item(raw_text="")
    accepted, rejected = validate_extraction([empty], PAGE, START, TODAY)
    assert accepted == []
    assert rejected[0]["reject_reason"] == "raw_text_not_in_page"


def test_rejects_unknown_track():
    weird = item(type="keynote")
    accepted, rejected = validate_extraction([weird], PAGE, START, TODAY)
    assert accepted == []
    assert rejected[0]["reject_reason"] == "unknown_track"


def test_date_range_check_is_skipped_when_conference_start_unknown():
    accepted, rejected = validate_extraction([item()], PAGE, None, TODAY)
    assert len(accepted) == 1


def test_processes_every_item_independently():
    good = item()
    bad = item(raw_text="invented text", type="poster")
    accepted, rejected = validate_extraction([good, bad], PAGE, START, TODAY)
    assert len(accepted) == 1
    assert len(rejected) == 1


def test_normalize_whitespace_collapses_runs():
    assert normalize_whitespace("a  b\n\tc ") == "a b c"
