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


# 2026-09-09에 huggingface/ai-deadlines와 ccfddl/ccf-deadlines의 파일 목록을 직접
# 받아 확인한 매핑이다. 이 표가 없으면 "값이 있긴 한데 틀린" source id를 아무
# 테스트도 잡지 못한다 - ai_specialist 플래그 7개가 몇 주 동안 틀린 채로 살아남은
# 것과 같은 실패 양상이다. 여기서 실패하면 registry.yaml이 잘못 수정됐거나 업스트림이
# 파일명을 바꾼 것이다 - 둘 다 사람이 봐야 한다.
VERIFIED_SOURCE_IDS = {
    "nips": {"ccfddl": "nips", "ai_deadlines": "neurips"},
    "kdd": {"ccfddl": "sigkdd", "ai_deadlines": "kdd"},
    "siggraph": {"ccfddl": "sig", "ai_deadlines": "siggraph"},
    "siggrapha": {"ccfddl": "siga", "ai_deadlines": None},
    "mm": {"ccfddl": "mm", "ai_deadlines": "acm_mm"},
    "bigdataconf": {"ccfddl": "bigdata", "ai_deadlines": None},
    "UbiComp": {"ccfddl": "ubicomp", "ai_deadlines": None},
    "ICME": {"ccfddl": "icme", "ai_deadlines": None},
    "cvpr": {"ccfddl": "cvpr", "ai_deadlines": "cvpr"},
    "chi": {"ccfddl": "chi", "ai_deadlines": "chi"},
}

# 결합 행(iccv/eccv, asru/slt)의 구성원 매핑. 구성원 이름으로 적혀 있어야
# 위 표와 별도로 확인한다.
VERIFIED_MEMBER_SOURCE_IDS = {
    ("iccv/eccv", "ICCV"): {"ccfddl": "iccv", "ai_deadlines": "iccv"},
    ("iccv/eccv", "ECCV"): {"ccfddl": "eccv", "ai_deadlines": "eccv"},
    ("asru/slt", "ASRU"): {"ccfddl": None, "ai_deadlines": None},
    ("asru/slt", "SLT"): {"ccfddl": "slt", "ai_deadlines": None},
}


def test_verified_source_ids_match_upstream():
    by_abbr = {e["abbr"]: e for e in active_entries()}
    mismatches = []
    for abbr, expected in VERIFIED_SOURCE_IDS.items():
        entry = by_abbr.get(abbr)
        assert entry is not None, f"{abbr}가 registry에 없습니다"
        actual = entry.get("sources") or {}
        for source, expected_id in expected.items():
            if actual.get(source) != expected_id:
                mismatches.append(
                    f"{abbr}.{source}: expected={expected_id!r} actual={actual.get(source)!r}"
                )
    assert mismatches == []


def test_verified_member_source_ids_match_upstream():
    by_abbr = {e["abbr"]: e for e in active_entries()}
    mismatches = []
    for (abbr, member_display), expected in VERIFIED_MEMBER_SOURCE_IDS.items():
        entry = by_abbr.get(abbr)
        assert entry is not None, f"{abbr}가 registry에 없습니다"
        members = {m["display"]: m for m in (entry.get("members") or [])}
        member = members.get(member_display)
        assert member is not None, f"{abbr}에 {member_display} 구성원이 없습니다"
        actual = member.get("sources") or {}
        for source, expected_id in expected.items():
            if actual.get(source) != expected_id:
                mismatches.append(
                    f"{abbr}/{member_display}.{source}: "
                    f"expected={expected_id!r} actual={actual.get(source)!r}"
                )
    assert mismatches == []
