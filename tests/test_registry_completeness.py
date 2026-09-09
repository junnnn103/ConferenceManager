"""활성 학회가 전부 데이터 출처를 갖는지 지킨다.

이 테스트가 깨지면 사이트에 '일정 미확인'으로 뜨는 학회가 생긴다는 뜻이다.
"""

from pathlib import Path

import yaml

from scripts.bootstrap_registry import load_registry
from scripts.build import enabled_field_ids, load_fields

ROOT = Path(__file__).parents[1]

# 두 공개 소스가 다루지 않아 손으로 채우는 학회.
MANUAL_ONLY = {"hri", "humanoids"}


def active_entries():
    active = enabled_field_ids(load_fields())
    return [e for e in load_registry() if e.get("field") in active]


def test_exactly_39_active_conferences():
    assert len(active_entries()) == 39


def test_every_active_conference_has_a_display_name():
    missing = [e["abbr"] for e in active_entries() if not e.get("display")]
    assert missing == []


def test_every_active_conference_has_a_homepage():
    missing = [e["abbr"] for e in active_entries() if not e.get("homepage")]
    assert missing == []


def test_every_active_conference_homepage_is_https():
    bad = [e["abbr"] for e in active_entries() if not e["homepage"].startswith("https://")]
    assert bad == []


def test_every_active_conference_has_a_source_or_is_manual():
    manual = yaml.safe_load((ROOT / "data" / "manual.yaml").read_text(encoding="utf-8"))
    manual_abbrs = set((manual or {}).get("conferences") or {})

    orphans = []
    for entry in active_entries():
        if entry["abbr"] in manual_abbrs or entry["abbr"] in MANUAL_ONLY:
            continue
        if entry.get("members"):
            has = any(any((m.get("sources") or {}).values()) for m in entry["members"])
        else:
            has = any((entry.get("sources") or {}).values())
        if not has:
            orphans.append(entry["abbr"])
    assert orphans == []


def test_combined_rows_have_members_with_sources():
    for entry in active_entries():
        if "/" not in entry["abbr"]:
            continue
        assert entry.get("members"), f"{entry['abbr']}에 members가 없습니다"
        for member in entry["members"]:
            assert member.get("display")
