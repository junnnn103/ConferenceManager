from datetime import date, datetime

from scripts.merge import (
    SOURCE_PRIORITY,
    apply_scraped,
    edition_status,
    merge_by_year,
    pick_member,
    select_editions,
)
from scripts.models import Deadline, Edition


def ed(year, source, start=None, end=None, deadlines=None, place="X"):
    return Edition(
        year=year, date_text="", start=start, end=end, place=place,
        link=None, deadlines=deadlines or [], source=source,
    )


def dl(kind, when, source="ccfddl"):
    return Deadline(kind, kind.title(), when, None, source)


def test_source_priority_order():
    assert SOURCE_PRIORITY == ("manual", "ai-deadlines", "ccfddl")


def test_higher_priority_source_wins_whole_edition():
    merged = merge_by_year({
        "ccfddl": [ed(2026, "ccfddl", place="From ccfddl")],
        "ai-deadlines": [ed(2026, "ai-deadlines", place="From HF")],
    })
    assert merged[2026].place == "From HF"
    assert merged[2026].source == "ai-deadlines"


def test_manual_beats_everything():
    merged = merge_by_year({
        "ccfddl": [ed(2026, "ccfddl", place="C")],
        "ai-deadlines": [ed(2026, "ai-deadlines", place="H")],
        "manual": [ed(2026, "manual", place="M")],
    })
    assert merged[2026].place == "M"


def test_lower_priority_fills_years_the_higher_one_lacks():
    merged = merge_by_year({
        "ccfddl": [ed(2025, "ccfddl"), ed(2026, "ccfddl")],
        "ai-deadlines": [ed(2026, "ai-deadlines")],
    })
    assert merged[2025].source == "ccfddl"
    assert merged[2026].source == "ai-deadlines"


def test_fields_are_never_mixed_across_sources():
    # HF 회차가 이겼다면 place도 deadlines도 전부 HF 것이어야 한다
    merged = merge_by_year({
        "ccfddl": [ed(2026, "ccfddl", place="C", deadlines=[dl("paper", datetime(2025, 1, 1))])],
        "ai-deadlines": [ed(2026, "ai-deadlines", place="H")],
    })
    assert merged[2026].place == "H"
    assert merged[2026].deadlines == []


def test_apply_scraped_adds_missing_track():
    base = ed(2026, "ai-deadlines", deadlines=[dl("paper", datetime(2025, 9, 11), "ai-deadlines")])
    extra = [Deadline("lbw", "LBW", datetime(2026, 2, 12), None, "cfp-scrape",
                      {"raw_text": "x", "url": "y"})]
    result = apply_scraped(base, extra)
    assert [d.type for d in result.deadlines] == ["paper", "lbw"]


def test_apply_scraped_never_overwrites_existing_track():
    base = ed(2026, "ai-deadlines", deadlines=[dl("paper", datetime(2025, 9, 11), "ai-deadlines")])
    extra = [Deadline("paper", "Paper", datetime(2025, 1, 1), None, "cfp-scrape")]
    result = apply_scraped(base, extra)
    assert len(result.deadlines) == 1
    assert result.deadlines[0].source == "ai-deadlines"


def test_apply_scraped_with_no_extra_returns_equivalent_edition():
    base = ed(2026, "ccfddl", deadlines=[dl("paper", datetime(2025, 9, 11))])
    assert apply_scraped(base, []).deadlines == base.deadlines


def test_edition_status_upcoming_when_end_is_today_or_later():
    assert edition_status(ed(2026, "x", end=date(2026, 4, 17)), date(2026, 4, 17)) == "upcoming"
    assert edition_status(ed(2026, "x", end=date(2026, 4, 17)), date(2026, 1, 1)) == "upcoming"


def test_edition_status_past_when_ended():
    assert edition_status(ed(2026, "x", end=date(2026, 4, 17)), date(2026, 4, 18)) == "past"


def test_edition_status_unknown_without_dates():
    assert edition_status(ed(2026, "x"), date(2026, 1, 1)) == "unknown"


def test_select_editions_keeps_one_past_and_one_upcoming():
    editions = [
        ed(2024, "x", start=date(2024, 6, 1), end=date(2024, 6, 5)),
        ed(2025, "x", start=date(2025, 6, 1), end=date(2025, 6, 5)),
        ed(2026, "x", start=date(2026, 6, 1), end=date(2026, 6, 5)),
        ed(2027, "x", start=date(2027, 6, 1), end=date(2027, 6, 5)),
    ]
    picked = select_editions(editions, date(2025, 9, 8))
    assert [e.year for e in picked] == [2025, 2026]


def test_select_editions_returns_only_past_when_nothing_upcoming():
    editions = [ed(2024, "x", start=date(2024, 6, 1), end=date(2024, 6, 5))]
    assert [e.year for e in select_editions(editions, date(2026, 1, 1))] == [2024]


def test_select_editions_keeps_undated_editions_as_fallback():
    editions = [ed(2026, "x")]
    assert [e.year for e in select_editions(editions, date(2026, 1, 1))] == [2026]


def test_select_editions_on_empty_input():
    assert select_editions([], date(2026, 1, 1)) == []


def test_pick_member_chooses_earliest_upcoming():
    # ICCV는 홀수해, ECCV는 짝수해. 2026년 9월 기준 차기는 ICCV 2027.
    members = {
        "iccv": [ed(2025, "ccfddl", start=date(2025, 10, 19), end=date(2025, 10, 25)),
                 ed(2027, "ccfddl", start=date(2027, 10, 1), end=date(2027, 10, 6))],
        "eccv": [ed(2026, "ccfddl", start=date(2026, 9, 8), end=date(2026, 9, 13))],
    }
    name, editions = pick_member(members, date(2026, 9, 20))
    assert name == "iccv"
    assert [e.year for e in editions] == [2025, 2027]


def test_pick_member_prefers_the_one_actually_upcoming():
    members = {
        "iccv": [ed(2025, "ccfddl", start=date(2025, 10, 19), end=date(2025, 10, 25))],
        "eccv": [ed(2026, "ccfddl", start=date(2026, 9, 8), end=date(2026, 9, 13))],
    }
    name, _ = pick_member(members, date(2026, 1, 1))
    assert name == "eccv"


def test_pick_member_with_no_upcoming_prefers_the_most_recently_held():
    # 둘 다 차기 회차가 없을 때는 가장 최근에 열린 쪽이 대표가 되어야 한다.
    # pick_member의 -toordinal 부호가 이 비교를 뒤집는 장치다.
    members = {
        "iccv": [ed(2023, "ccfddl", start=date(2023, 10, 1), end=date(2023, 10, 6))],
        "eccv": [ed(2024, "ccfddl", start=date(2024, 9, 29), end=date(2024, 10, 4))],
    }
    name, editions = pick_member(members, date(2026, 9, 20))
    assert name == "eccv"
    assert [e.year for e in editions] == [2024]


def test_pick_member_with_no_data_returns_none():
    assert pick_member({"iccv": [], "eccv": []}, date(2026, 1, 1)) == (None, [])
