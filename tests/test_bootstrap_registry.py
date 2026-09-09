from pathlib import Path

import pytest
import yaml

from scripts.bootstrap_registry import (
    FIELD_ASSIGNMENT,
    build_registry,
    load_registry,
    normalize_abbr,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_field_assignment_covers_every_conference_exactly_once():
    assert len(FIELD_ASSIGNMENT) == 99


def test_field_assignment_only_uses_defined_fields():
    defined = {f["id"] for f in yaml.safe_load(
        (Path(__file__).parents[1] / "data" / "fields.yaml").read_text(encoding="utf-8")
    )["fields"]}
    assert set(FIELD_ASSIGNMENT.values()) <= defined


def test_exactly_39_conferences_are_in_enabled_fields():
    enabled = {f["id"] for f in yaml.safe_load(
        (Path(__file__).parents[1] / "data" / "fields.yaml").read_text(encoding="utf-8")
    )["fields"] if f["enabled"]}
    active = [a for a, f in FIELD_ASSIGNMENT.items() if f in enabled]
    assert len(active) == 39


@pytest.mark.parametrize(
    "raw,expected",
    [("CVPR", "cvpr"), ("NeurIPS", "neurips"), ("VLDB/PVLDB", "vldb"),
     ("NAACL/HLT", "naacl"), ("ECML PKDD/PKDD", "ecmlpkdd"), ("ACM MM", "acmmm")],
)
def test_normalize_abbr(raw, expected):
    assert normalize_abbr(raw) == expected


def test_build_registry_reads_grade_and_marks_ai_specialist():
    entries = build_registry(FIXTURES / "grades.xlsx", FIXTURES / "ai_specialist.xlsx")
    by_abbr = {e["abbr"]: e for e in entries}

    assert by_abbr["cvpr"]["grade"] == "최우수"
    assert by_abbr["cvpr"]["full_name"] == "Computer Vision and Pattern Recognition"
    assert by_abbr["cvpr"]["ai_specialist"] is True
    assert by_abbr["cvpr"]["field"] == "CV"

    # 결합 행: 양쪽 모두 AI Specialist 목록에 있어야 True
    assert by_abbr["iccv/eccv"]["ai_specialist"] is True

    # AI Specialist 목록에 없는 학회
    assert by_abbr["SID"]["ai_specialist"] is False
    assert by_abbr["SID"]["field"] == "Display/Optics"


def test_build_registry_applies_ai_specialist_aliases():
    """두 엑셀이 같은 학회를 다르게 적는 경우(nips vs NeurIPS, kdd vs SIGKDD)에도
    AI_SPECIALIST_ALIASES 덕분에 True로 매칭되어야 한다."""
    entries = build_registry(FIXTURES / "grades.xlsx", FIXTURES / "ai_specialist.xlsx")
    by_abbr = {e["abbr"]: e for e in entries}

    assert by_abbr["kdd"]["ai_specialist"] is True
    # 목록에 정말 없는 학회는 별칭을 추가해도 여전히 False여야 한다.
    assert by_abbr["SID"]["ai_specialist"] is False


def test_build_registry_seeds_empty_source_mapping():
    entries = build_registry(FIXTURES / "grades.xlsx", FIXTURES / "ai_specialist.xlsx")
    cvpr = next(e for e in entries if e["abbr"] == "cvpr")
    assert cvpr["sources"] == {"ai_deadlines": None, "ccfddl": None}
    assert cvpr["homepage"] is None
    # 표시명 기본값은 엑셀 약어. 사람이 나중에 다듬는다.
    assert cvpr["display"] == "cvpr"
    # 단일 학회는 members가 없다. 결합 행만 채운다.
    assert cvpr["members"] is None


def test_build_registry_seeds_members_for_combined_rows():
    entries = build_registry(FIXTURES / "grades.xlsx", FIXTURES / "ai_specialist.xlsx")
    combined = next(e for e in entries if e["abbr"] == "iccv/eccv")
    assert [m["display"] for m in combined["members"]] == ["iccv", "eccv"]
    assert combined["members"][0]["sources"] == {"ai_deadlines": None, "ccfddl": None}


def test_real_registry_flags_ai_specialist_aliases_correctly():
    """실제 커밋된 registry.yaml에서, 두 엑셀이 다르게 적는 학회들이
    ai_specialist=True로 정확히 반영되어 있는지 확인한다."""
    entries = {e["abbr"]: e for e in load_registry()}
    for abbr in ("nips", "kdd", "mm", "bigdataconf", "siggrapha"):
        assert entries[abbr]["ai_specialist"] is True, abbr


def test_load_registry_roundtrips(tmp_path):
    entries = build_registry(FIXTURES / "grades.xlsx", FIXTURES / "ai_specialist.xlsx")
    path = tmp_path / "registry.yaml"
    path.write_text(
        yaml.safe_dump({"conferences": entries}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    assert load_registry(path) == entries
