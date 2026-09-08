from datetime import date, datetime
from pathlib import Path

import yaml

from scripts.sources.aideadlines import parse_aideadlines

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture():
    return yaml.safe_load((FIXTURES / "aideadlines_cvpr.yml").read_text(encoding="utf-8"))


def test_parses_every_edition_sorted_by_year():
    editions = parse_aideadlines(load_fixture())
    assert [e.year for e in editions] == [2025, 2026, 2027]


def test_prefers_structured_start_end_over_text():
    ed = next(e for e in parse_aideadlines(load_fixture()) if e.year == 2026)
    assert ed.start == date(2026, 6, 3)
    assert ed.end == date(2026, 6, 7)


def test_falls_back_to_parsing_date_text_when_start_missing():
    # 2025 항목에는 start/end가 없고 date 문자열만 있다
    ed = next(e for e in parse_aideadlines(load_fixture()) if e.year == 2025)
    assert ed.start == date(2025, 6, 10)
    assert ed.end == date(2025, 6, 17)


def test_place_joins_city_and_country():
    ed = next(e for e in parse_aideadlines(load_fixture()) if e.year == 2026)
    assert ed.place == "Denver USA"


def test_reads_multi_stage_deadlines():
    ed = next(e for e in parse_aideadlines(load_fixture()) if e.year == 2026)
    assert [d.type for d in ed.deadlines] == ["abstract", "paper", "notification"]
    assert ed.deadlines[1].label == "Paper Submission"
    assert ed.deadlines[1].date == datetime(2025, 11, 13, 23, 59, 59)
    assert all(d.source == "ai-deadlines" for d in ed.deadlines)


def test_falls_back_to_flat_deadline_when_no_deadlines_array():
    ed = next(e for e in parse_aideadlines(load_fixture()) if e.year == 2025)
    assert [d.type for d in ed.deadlines] == ["paper"]
    assert ed.deadlines[0].date == datetime(2024, 11, 14, 23, 59, 0)
    assert ed.deadlines[0].timezone == "UTC-8"


def test_edition_without_any_deadline_is_kept():
    ed = next(e for e in parse_aideadlines(load_fixture()) if e.year == 2027)
    assert ed.deadlines == []
    assert ed.start == date(2027, 6, 19)


def test_primary_deadline_picks_paper_stage():
    ed = next(e for e in parse_aideadlines(load_fixture()) if e.year == 2026)
    assert ed.primary_deadline() == datetime(2025, 11, 13, 23, 59, 59)
