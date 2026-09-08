"""huggingface/ai-deadlines 어댑터.

저장소 구조: src/data/conferences/<id>.yml
파일 하나가 연차 목록을 담고, 각 연차가 최상위 항목이다.

ccfddl과 달리 start/end ISO 필드와 다단계 deadlines 배열을 준다.
그래서 병합 우선순위가 ccfddl보다 높다.
"""

from datetime import date, datetime

import yaml

from scripts.dateparse import parse_date_range
from scripts.models import Deadline, Edition

RAW_BASE = (
    "https://raw.githubusercontent.com/huggingface/ai-deadlines/main/src/data/conferences"
)

_TIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d")


def _parse_datetime(value) -> datetime | None:
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
    """YAML이 date로 읽어줄 수도, 문자열로 남길 수도 있다."""
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


def _place(entry: dict) -> str:
    parts = [str(entry.get(k)).strip() for k in ("city", "country") if entry.get(k)]
    return " ".join(parts)


def _deadlines(entry: dict) -> list[Deadline]:
    """다단계 배열을 우선 쓰고, 없으면 평면 deadline 필드로 대체한다."""
    staged = entry.get("deadlines")
    if staged:
        out = []
        for item in staged:
            when = _parse_datetime(item.get("date"))
            if not when:
                continue
            kind = str(item.get("type") or "paper")
            out.append(Deadline(
                type=kind,
                label=str(item.get("label") or kind.replace("_", " ").title()),
                date=when,
                timezone=item.get("timezone") or entry.get("timezone"),
                source="ai-deadlines",
            ))
        return out

    out = []
    abstract_at = _parse_datetime(entry.get("abstract_deadline"))
    if abstract_at:
        out.append(Deadline("abstract", "Abstract", abstract_at,
                            entry.get("timezone"), "ai-deadlines"))
    paper_at = _parse_datetime(entry.get("deadline"))
    if paper_at:
        out.append(Deadline("paper", "Paper", paper_at,
                            entry.get("timezone"), "ai-deadlines"))
    return out


def parse_aideadlines(raw: list) -> list[Edition]:
    editions: list[Edition] = []
    for entry in raw or []:
        year = entry.get("year")
        if year is None:
            continue

        start = _as_date(entry.get("start"))
        end = _as_date(entry.get("end"))
        date_text = str(entry.get("date") or "").strip()
        if start is None or end is None:
            # 오래된 항목은 start/end가 없다. 자유 텍스트에서 되살린다.
            span = parse_date_range(date_text)
            if span:
                start, end = span

        editions.append(Edition(
            year=int(year),
            date_text=date_text,
            start=start,
            end=end,
            place=_place(entry),
            link=entry.get("link"),
            deadlines=_deadlines(entry),
            source="ai-deadlines",
        ))
    editions.sort(key=lambda e: e.year)
    return editions


def fetch_aideadlines(conf_id: str, session) -> list[Edition]:
    response = session.get(f"{RAW_BASE}/{conf_id}.yml", timeout=30)
    if response.status_code != 200:
        return []
    return parse_aideadlines(yaml.safe_load(response.text))
