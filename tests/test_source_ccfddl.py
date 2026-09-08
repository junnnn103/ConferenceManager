from datetime import date, datetime
from pathlib import Path

import yaml

from scripts.sources.ccfddl import parse_ccfddl

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture():
    return yaml.safe_load((FIXTURES / "ccfddl_chi.yml").read_text(encoding="utf-8"))


def test_parses_every_edition():
    editions = parse_ccfddl(load_fixture())
    assert [e.year for e in editions] == [2025, 2026, 2027]


def test_parses_date_range_from_free_text():
    ed = next(e for e in parse_ccfddl(load_fixture()) if e.year == 2026)
    assert ed.start == date(2026, 4, 13)
    assert ed.end == date(2026, 4, 17)
    assert ed.date_text == "April 13 - 17, 2026"


def test_undated_edition_keeps_none_without_raising():
    ed = next(e for e in parse_ccfddl(load_fixture()) if e.year == 2027)
    assert ed.start is None
    assert ed.end is None


def test_place_commas_become_spaces():
    ed = next(e for e in parse_ccfddl(load_fixture()) if e.year == 2025)
    assert ed.place == "Yokohama Japan"


def test_extracts_abstract_and_paper_deadlines():
    ed = next(e for e in parse_ccfddl(load_fixture()) if e.year == 2026)
    by_type = {d.type: d for d in ed.deadlines}
    assert by_type["abstract"].date == datetime(2025, 9, 4, 23, 59, 59)
    assert by_type["paper"].date == datetime(2025, 9, 11, 23, 59, 59)
    assert by_type["paper"].timezone == "AoE"
    assert all(d.source == "ccfddl" for d in ed.deadlines)


def test_comment_becomes_deadline_label():
    ed = next(e for e in parse_ccfddl(load_fixture()) if e.year == 2026)
    paper = next(d for d in ed.deadlines if d.type == "paper")
    assert paper.label == "Papers track"


def test_unparseable_deadline_is_skipped_not_crashed():
    ed = next(e for e in parse_ccfddl(load_fixture()) if e.year == 2027)
    assert ed.deadlines == []


def test_edition_source_is_tagged():
    assert all(e.source == "ccfddl" for e in parse_ccfddl(load_fixture()))
