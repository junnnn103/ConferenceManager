from datetime import date

import pytest

from scripts.dateparse import parse_date_range


@pytest.mark.parametrize(
    "text,expected",
    [
        # 같은 달 안에서 끝나는 경우 - 가장 흔한 형태
        ("June 3-7, 2026", (date(2026, 6, 3), date(2026, 6, 7))),
        ("April 13 - 17, 2026", (date(2026, 4, 13), date(2026, 4, 17))),
        ("December 14-17, 2026", (date(2026, 12, 14), date(2026, 12, 17))),
        # 달을 넘기는 경우
        ("February 25 - March 4, 2025", (date(2025, 2, 25), date(2025, 3, 4))),
        ("July 27 - August 1, 2025", (date(2025, 7, 27), date(2025, 8, 1))),
        # 축약 월 이름
        ("Sep 13-17, 2026", (date(2026, 9, 13), date(2026, 9, 17))),
        # 마침표가 붙는 경우 (fmcad)
        ("Oct. 6-10, 2025", (date(2025, 10, 6), date(2025, 10, 10))),
        # 전부 대문자 (sp, fast)
        ("MAY 18-21, 2026", (date(2026, 5, 18), date(2026, 5, 21))),
        ("FEBRUARY 24-26, 2026", (date(2026, 2, 24), date(2026, 2, 26))),
        # 쉼표 없음 (icpads)
        ("November 22-26 2026", (date(2026, 11, 22), date(2026, 11, 26))),
        # 일-월 순서 (ecscw, iwqos)
        ("29 June - 3 July, 2026", (date(2026, 6, 29), date(2026, 7, 3))),
        # 끝 날짜만 일-월 순서 (cgo)
        ("January 31 - 4 February, 2026", (date(2026, 1, 31), date(2026, 2, 4))),
        # 하루짜리
        ("May 4, 2026", (date(2026, 5, 4), date(2026, 5, 4))),
        # 엔 대시
        ("June 3–7, 2026", (date(2026, 6, 3), date(2026, 6, 7))),
        # 공백이 지저분한 경우
        ("  June   3-7,  2026 ", (date(2026, 6, 3), date(2026, 6, 7))),
    ],
)
def test_parses_known_formats(text, expected):
    assert parse_date_range(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "TBD",
        "TBA",
        "May 2027 (exact dates TBD)",
        "March-April, 2025",   # 일자가 없음
        "Dec, 2025",           # 월만
        "November, 2025",      # 월만
        "",
        None,
    ],
)
def test_returns_none_for_undated(text):
    assert parse_date_range(text) is None


def test_invalid_calendar_date_returns_none():
    # 2월 30일 - 정규식은 통과하지만 달력상 존재하지 않는다
    assert parse_date_range("February 30-31, 2026") is None
