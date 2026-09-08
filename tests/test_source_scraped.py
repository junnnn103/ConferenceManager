from datetime import datetime
from pathlib import Path

from scripts.sources.scraped import load_scraped

FIXTURES = Path(__file__).parent / "fixtures"


def test_loads_deadlines_keyed_by_abbr_and_year(tmp_path):
    (tmp_path / "chi.yaml").write_text(
        (FIXTURES / "scraped_chi.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    result = load_scraped(tmp_path)
    assert set(result) == {("chi", 2026)}

    deadlines = result[("chi", 2026)]
    assert [d.type for d in deadlines] == ["lbw", "workshop"]
    assert deadlines[0].date == datetime(2026, 2, 12, 23, 59, 59)
    assert all(d.source == "cfp-scrape" for d in deadlines)


def test_evidence_is_preserved(tmp_path):
    (tmp_path / "chi.yaml").write_text(
        (FIXTURES / "scraped_chi.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    lbw = load_scraped(tmp_path)[("chi", 2026)][0]
    assert lbw.evidence["url"] == "https://chi2026.acm.org/lbw/"
    assert "February 12, 2026" in lbw.evidence["raw_text"]


def test_missing_directory_returns_empty(tmp_path):
    assert load_scraped(tmp_path / "absent") == {}


def test_raw_subdirectory_is_ignored(tmp_path):
    (tmp_path / "raw").mkdir()
    (tmp_path / "raw" / "chi.yaml").write_text("abbr: chi\neditions: []\n", encoding="utf-8")
    assert load_scraped(tmp_path) == {}
