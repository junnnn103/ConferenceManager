"""CFP 페이지에서 추출해 검증 게이트를 통과한 단계들.

manual과 달리 회차 전체가 아니라 '단계'만 제공한다.
poster / LBW / workshop 처럼 공개 소스가 다루지 않는 트랙이 대상이며,
병합에서 최하위라 상위 소스가 이미 가진 단계는 채우지 않는다.

data/scraped/raw/ 는 검증 전 원본이라 여기서 읽지 않는다.
"""

from datetime import datetime
from pathlib import Path

import yaml

from scripts.models import Deadline

_TIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d")


def _parse_datetime(value) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    text = str(value).strip()
    for fmt in _TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def load_scraped(directory: Path) -> dict[tuple[str, int], list[Deadline]]:
    """(abbr, year)를 키로 하는 Deadline 목록을 돌려준다."""
    if not directory.exists():
        return {}
    out: dict[tuple[str, int], list[Deadline]] = {}

    # raw/ 는 검증 전 원본이므로 glob이 아니라 최상위만 훑는다.
    for path in sorted(directory.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        abbr = data.get("abbr")
        if not abbr:
            continue
        for entry in data.get("editions") or []:
            year = entry.get("year")
            if year is None:
                continue
            deadlines = [
                Deadline(
                    type=str(d.get("type") or "other"),
                    label=str(d.get("label") or "Other"),
                    date=when,
                    timezone=d.get("timezone"),
                    source="cfp-scrape",
                    evidence=d.get("evidence"),
                )
                for d in (entry.get("deadlines") or [])
                if (when := _parse_datetime(d.get("date")))
            ]
            if deadlines:
                out[(str(abbr), int(year))] = deadlines
    return out
