from datetime import date, datetime

from scripts.build import build, enabled_field_ids
from scripts.models import Deadline, Edition

FIELDS = [
    {"id": "CV", "label": "CV", "color": "#3b82f6", "enabled": True},
    {"id": "Network", "label": "Network", "color": "#64748b", "enabled": False},
]

REGISTRY = [
    {
        "abbr": "cvpr", "display": "CVPR",
        "full_name": "Computer Vision and Pattern Recognition",
        "grade": "최우수", "ai_specialist": True, "field": "CV",
        "homepage": "https://cvpr.thecvf.com/", "members": None,
        "sources": {"ai_deadlines": "cvpr", "ccfddl": "cvpr"},
    },
    {
        "abbr": "infocom", "display": "INFOCOM", "full_name": "IEEE INFOCOM",
        "grade": "최우수", "ai_specialist": True, "field": "Network",
        "homepage": None, "members": None,
        "sources": {"ai_deadlines": None, "ccfddl": "infocom"},
    },
    {
        "abbr": "hri", "display": "HRI", "full_name": "Human Robot Interaction",
        "grade": "우수", "ai_specialist": True, "field": "CV",
        "homepage": None, "members": None,
        "sources": {"ai_deadlines": None, "ccfddl": None},
    },
]

TODAY = date(2026, 1, 15)


def cvpr_edition():
    return Edition(
        year=2026, date_text="June 3-7, 2026",
        start=date(2026, 6, 3), end=date(2026, 6, 7),
        place="Denver USA", link="https://cvpr.thecvf.com/2026",
        deadlines=[Deadline("paper", "Paper", datetime(2025, 11, 13, 23, 59, 59),
                            "AoE", "ai-deadlines")],
        source="ai-deadlines",
    )


def make_fetchers(hf=None, ccf=None):
    return {
        "ai-deadlines": lambda cid: (hf or {}).get(cid, []),
        "ccfddl": lambda cid: (ccf or {}).get(cid, []),
    }


def test_enabled_field_ids():
    assert enabled_field_ids(FIELDS) == {"CV"}


def test_disabled_field_conferences_are_excluded():
    out = build(REGISTRY, FIELDS, make_fetchers(hf={"cvpr": [cvpr_edition()]}),
                manual={}, scraped={}, today=TODAY)
    assert [c["abbr"] for c in out["conferences"]] == ["cvpr"]
    assert "infocom" not in str(out)


def test_conference_carries_registry_metadata():
    out = build(REGISTRY, FIELDS, make_fetchers(hf={"cvpr": [cvpr_edition()]}),
                manual={}, scraped={}, today=TODAY)
    conf = out["conferences"][0]
    assert conf["abbr"] == "CVPR"
    assert conf["abbr_group"] == "cvpr"
    assert conf["grade"] == "최우수"
    assert conf["ai_specialist"] is True
    assert conf["homepage"] == "https://cvpr.thecvf.com/"
    assert conf["editions"][0]["primary_deadline"] == "2025-11-13T23:59:59"


def test_conference_without_any_edition_goes_to_unresolved():
    out = build(REGISTRY, FIELDS, make_fetchers(), manual={}, scraped={}, today=TODAY)
    assert out["conferences"] == []
    assert [u["abbr"] for u in out["unresolved"]] == ["CVPR", "HRI"]


def test_manual_supplies_conference_with_no_source_mapping():
    manual = {"hri": [Edition(2026, "March 9-12, 2026", date(2026, 3, 9), date(2026, 3, 12),
                              "Christchurch New Zealand", None,
                              [Deadline("paper", "Full Paper", datetime(2025, 10, 1),
                                        "AoE", "manual")], "manual")]}
    out = build(REGISTRY, FIELDS, make_fetchers(), manual=manual, scraped={}, today=TODAY)
    assert [c["abbr"] for c in out["conferences"]] == ["HRI"]
    assert out["conferences"][0]["editions"][0]["place"] == "Christchurch New Zealand"


def test_scraped_deadlines_are_attached_to_matching_edition():
    scraped = {("cvpr", 2026): [Deadline("poster", "Posters", datetime(2026, 4, 21),
                                         None, "cfp-scrape",
                                         {"raw_text": "x", "url": "y"})]}
    out = build(REGISTRY, FIELDS, make_fetchers(hf={"cvpr": [cvpr_edition()]}),
                manual={}, scraped=scraped, today=TODAY)
    types = [d["type"] for d in out["conferences"][0]["editions"][0]["deadlines"]]
    assert types == ["paper", "poster"]


def test_fields_section_lists_only_enabled_fields():
    out = build(REGISTRY, FIELDS, make_fetchers(hf={"cvpr": [cvpr_edition()]}),
                manual={}, scraped={}, today=TODAY)
    assert out["fields"] == [{"id": "CV", "label": "CV", "color": "#3b82f6"}]


def test_failing_fetcher_does_not_abort_the_build():
    def explode(_):
        raise RuntimeError("network down")

    fetchers = {"ai-deadlines": explode,
                "ccfddl": lambda cid: {"cvpr": [cvpr_edition()]}.get(cid, [])}
    out = build(REGISTRY, FIELDS, fetchers, manual={}, scraped={}, today=TODAY)
    assert [c["abbr"] for c in out["conferences"]] == ["CVPR"]


def test_output_has_generated_at_timestamp():
    out = build(REGISTRY, FIELDS, make_fetchers(hf={"cvpr": [cvpr_edition()]}),
                manual={}, scraped={}, today=TODAY)
    assert "generated_at" in out


def test_combined_row_picks_member_and_uses_its_display_name():
    registry = [{
        "abbr": "iccv/eccv", "display": "ICCV/ECCV", "full_name": "ICCV / ECCV",
        "grade": "최우수", "ai_specialist": True, "field": "CV",
        "homepage": None,
        "members": [
            {"display": "ICCV", "sources": {"ai_deadlines": "iccv", "ccfddl": "iccv"}},
            {"display": "ECCV", "sources": {"ai_deadlines": "eccv", "ccfddl": "eccv"}},
        ],
        "sources": {"ai_deadlines": None, "ccfddl": None},
    }]
    hf = {
        "iccv": [Edition(2027, "", date(2027, 10, 1), date(2027, 10, 6), "", None, [], "ai-deadlines")],
        "eccv": [Edition(2026, "", date(2026, 9, 8), date(2026, 9, 13), "", None, [], "ai-deadlines")],
    }
    out = build(registry, FIELDS, make_fetchers(hf=hf), manual={}, scraped={}, today=TODAY)
    conf = out["conferences"][0]
    assert conf["abbr"] == "ECCV"        # 2026-01-15 기준 차기는 ECCV 2026
    assert conf["abbr_group"] == "iccv/eccv"
