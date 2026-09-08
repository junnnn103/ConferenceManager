from datetime import date, datetime
from pathlib import Path

from scripts.sources.manual import load_manual


def test_loads_editions_keyed_by_abbr(tmp_path):
    path = tmp_path / "manual.yaml"
    path.write_text(
        """
conferences:
  hri:
    editions:
      - year: 2026
        date_text: "March 9-12, 2026"
        start: 2026-03-09
        end: 2026-03-12
        place: "Christchurch New Zealand"
        link: "https://humanrobotinteraction.org/2026/"
        deadlines:
          - type: paper
            label: "Full Paper"
            date: "2025-10-01 23:59:59"
            timezone: AoE
""",
        encoding="utf-8",
    )
    result = load_manual(path)
    assert set(result) == {"hri"}
    ed = result["hri"][0]
    assert ed.year == 2026
    assert ed.start == date(2026, 3, 9)
    assert ed.place == "Christchurch New Zealand"
    assert ed.source == "manual"
    assert ed.deadlines[0].date == datetime(2025, 10, 1, 23, 59, 59)
    assert ed.deadlines[0].source == "manual"


def test_missing_file_returns_empty(tmp_path):
    assert load_manual(tmp_path / "absent.yaml") == {}


def test_empty_conferences_key_returns_empty(tmp_path):
    path = tmp_path / "manual.yaml"
    path.write_text("conferences: {}\n", encoding="utf-8")
    assert load_manual(path) == {}
