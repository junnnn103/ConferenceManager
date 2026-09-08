from datetime import date, datetime

from scripts.models import Conference, Deadline, Edition


def test_deadline_holds_absolute_time_only():
    d = Deadline(
        type="paper",
        label="Paper",
        date=datetime(2025, 11, 13, 23, 59, 59),
        timezone="AoE",
        source="ai-deadlines",
    )
    assert d.evidence is None
    assert d.to_dict() == {
        "type": "paper",
        "label": "Paper",
        "date": "2025-11-13T23:59:59",
        "timezone": "AoE",
        "source": "ai-deadlines",
    }


def test_deadline_with_evidence_serializes_it():
    d = Deadline(
        type="poster",
        label="Posters",
        date=datetime(2026, 4, 21, 22, 0, 0),
        timezone=None,
        source="cfp-scrape",
        evidence={"raw_text": "Posters deadline: April 21, 2026", "url": "https://x/"},
    )
    assert d.to_dict()["evidence"]["url"] == "https://x/"
    assert "timezone" not in d.to_dict()


def test_edition_primary_deadline_prefers_paper():
    ed = Edition(
        year=2026,
        date_text="June 3-7, 2026",
        start=date(2026, 6, 3),
        end=date(2026, 6, 7),
        place="Denver USA",
        link=None,
        source="ai-deadlines",
        deadlines=[
            Deadline("abstract", "Abstract", datetime(2025, 11, 7), None, "ai-deadlines"),
            Deadline("paper", "Paper", datetime(2025, 11, 13), None, "ai-deadlines"),
            Deadline("notification", "Notify", datetime(2026, 2, 20), None, "ai-deadlines"),
        ],
    )
    assert ed.primary_deadline() == datetime(2025, 11, 13)


def test_edition_primary_deadline_falls_back_to_latest_when_no_paper():
    # paper 계열 단계가 하나도 없을 때만 최댓값 대체가 동작해야 한다
    ed = Edition(
        year=2026, date_text="", start=None, end=None, place="", link=None,
        source="ccfddl",
        deadlines=[
            Deadline("abstract", "Abstract", datetime(2025, 9, 4), None, "ccfddl"),
            Deadline("notification", "Notify", datetime(2026, 1, 20), None, "ccfddl"),
        ],
    )
    assert ed.primary_deadline() == datetime(2026, 1, 20)


def test_edition_primary_deadline_treats_submission_as_paper():
    ed = Edition(
        year=2026, date_text="", start=None, end=None, place="", link=None,
        source="ccfddl",
        deadlines=[
            Deadline("submission", "Submission", datetime(2025, 9, 11), None, "ccfddl"),
            Deadline("notification", "Notify", datetime(2026, 1, 20), None, "ccfddl"),
        ],
    )
    assert ed.primary_deadline() == datetime(2025, 9, 11)


def test_edition_primary_deadline_is_none_when_no_deadlines():
    ed = Edition(2026, "", None, None, "", None, [], "ccfddl")
    assert ed.primary_deadline() is None


def test_conference_serializes_nested_editions():
    conf = Conference(
        abbr="CVPR", abbr_group="cvpr",
        full_name="Computer Vision and Pattern Recognition",
        grade="최우수", ai_specialist=True, field="CV",
        homepage="https://cvpr.thecvf.com/",
        editions=[Edition(2026, "June 3-7, 2026", date(2026, 6, 3), date(2026, 6, 7),
                          "Denver USA", None, [], "ai-deadlines")],
    )
    out = conf.to_dict()
    assert out["abbr"] == "CVPR"
    assert out["editions"][0]["start"] == "2026-06-03"
    assert out["editions"][0]["primary_deadline"] is None
