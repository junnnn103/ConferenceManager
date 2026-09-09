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


def test_place_commas_are_normalized_like_other_sources(tmp_path):
    # manual만 콤마 정리를 빼먹었던 회귀를 막는다 - ccfddl은 이미
    # _normalize_place를 거쳐 "Yokohama Japan"처럼 나오는데(test_source_
    # ccfddl.py의 test_place_commas_become_spaces), manual은 사람이 적은
    # 값을 그대로 통과시켜 HRI/IJCAI/RSS 2027 항목만 콤마가 남은 채
    # 다른 35개 행과 다르게 표시된 적이 있다. 이제 둘 다 Edition 생성
    # 시점(scripts/models.py의 normalize_place)에서 같은 규칙을 받는다.
    path = tmp_path / "manual.yaml"
    path.write_text(
        """
conferences:
  hri:
    editions:
      - year: 2027
        date_text: "March 8-12, 2027"
        place: "Santa Clara, California, USA"
        link: "https://humanrobotinteraction.org/"
        deadlines: []
""",
        encoding="utf-8",
    )
    ed = load_manual(path)["hri"][0]
    assert ed.place == "Santa Clara California USA"


def test_missing_file_returns_empty(tmp_path):
    assert load_manual(tmp_path / "absent.yaml") == {}


def test_empty_conferences_key_returns_empty(tmp_path):
    path = tmp_path / "manual.yaml"
    path.write_text("conferences: {}\n", encoding="utf-8")
    assert load_manual(path) == {}
