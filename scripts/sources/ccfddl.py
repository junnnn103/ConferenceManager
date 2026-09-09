"""ccfddl/ccf-deadlines 어댑터.

저장소 구조: conference/<카테고리>/<id>.yml
카테고리를 미리 알 수 없으므로 순서대로 시도한다.

주의: ccfddl은 start/end 같은 구조화된 개최일을 주지 않고
'April 13 - 17, 2026' 형태의 자유 텍스트만 준다.
"""

from datetime import datetime

import yaml

from scripts.dateparse import parse_date_range
from scripts.models import Deadline, Edition

RAW_BASE = "https://raw.githubusercontent.com/ccfddl/ccf-deadlines/main/conference"

# 저장소의 카테고리 디렉터리. 학회가 어디에 있는지 몰라 전부 시도한다.
CCFDDL_CATEGORIES = ("AI", "CG", "CT", "DB", "DS", "HI", "MX", "NW", "SC", "SE")

_TIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d")


def _parse_datetime(value) -> datetime | None:
    """'2025-09-11 23:59:59' 형태를 읽는다. 'TBD' 등은 None."""
    if not value:
        return None
    text = str(value).strip()
    for fmt in _TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def parse_ccfddl(raw: list) -> list[Edition]:
    """ccfddl YAML 문서를 Edition 목록으로 정규화한다."""
    if not raw:
        return []
    doc = raw[0]
    editions: list[Edition] = []

    for conf in doc.get("confs") or []:
        year = conf.get("year")
        if year is None:
            continue

        timezone = conf.get("timezone")
        deadlines: list[Deadline] = []
        for entry in conf.get("timeline") or []:
            label = entry.get("comment")
            abstract_at = _parse_datetime(entry.get("abstract_deadline"))
            if abstract_at:
                deadlines.append(Deadline(
                    type="abstract", label=label or "Abstract", date=abstract_at,
                    timezone=timezone, source="ccfddl",
                ))
            paper_at = _parse_datetime(entry.get("deadline"))
            if paper_at:
                deadlines.append(Deadline(
                    type="paper", label=label or "Paper", date=paper_at,
                    timezone=timezone, source="ccfddl",
                ))

        date_text = str(conf.get("date") or "").strip()
        span = parse_date_range(date_text)
        editions.append(Edition(
            year=int(year),
            date_text="" if date_text.upper() in {"TBD", "TBA"} else date_text,
            start=span[0] if span else None,
            end=span[1] if span else None,
            # place 콤마 정리는 Edition.__post_init__(scripts/models.py의
            # normalize_place)이 모든 소스에 공통으로 적용한다.
            place=conf.get("place"),
            link=conf.get("link"),
            deadlines=deadlines,
            source="ccfddl",
        ))
    return editions


def fetch_ccfddl(conf_id: str, session) -> list[Edition]:
    """카테고리를 순회하며 해당 id의 YAML을 찾는다. 없으면 빈 목록."""
    for category in CCFDDL_CATEGORIES:
        response = session.get(f"{RAW_BASE}/{category}/{conf_id}.yml", timeout=30)
        if response.status_code == 200:
            return parse_ccfddl(yaml.safe_load(response.text))
    return []
