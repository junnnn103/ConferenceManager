"""손으로 적은 일정. 병합에서 최우선이다.

두 공개 소스가 아예 모르는 학회(HRI, Humanoids, 홀수해 ASRU)를 위한 것이며,
사람이 명시적으로 써넣은 값이므로 다른 소스를 이긴다.
"""

from datetime import date, datetime
from pathlib import Path

import yaml

from scripts.models import Deadline, Edition

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


def _as_date(value) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if not value:
        return None
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError:
        return None


def load_manual(path: Path) -> dict[str, list[Edition]]:
    """registry의 abbr을 키로 하는 Edition 목록을 돌려준다."""
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out: dict[str, list[Edition]] = {}

    for abbr, body in (data.get("conferences") or {}).items():
        editions = []
        for entry in body.get("editions") or []:
            deadlines = [
                Deadline(
                    type=str(d.get("type") or "paper"),
                    label=str(d.get("label") or "Paper"),
                    date=when,
                    timezone=d.get("timezone"),
                    source="manual",
                )
                for d in (entry.get("deadlines") or [])
                if (when := _parse_datetime(d.get("date")))
            ]
            editions.append(Edition(
                year=int(entry["year"]),
                date_text=str(entry.get("date_text") or ""),
                start=_as_date(entry.get("start")),
                end=_as_date(entry.get("end")),
                # place 콤마 정리는 Edition.__post_init__(scripts/models.py의
                # normalize_place)이 모든 소스에 공통으로 적용한다.
                place=entry.get("place"),
                link=entry.get("link"),
                deadlines=deadlines,
                source="manual",
            ))
        if editions:
            out[abbr] = sorted(editions, key=lambda e: e.year)
    return out
