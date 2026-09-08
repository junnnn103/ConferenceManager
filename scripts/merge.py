"""소스 병합, 결합 행 해소, 회차 선택.

병합은 회차(연도) 단위로 소스를 통째 고른다. 필드 단위로 섞지 않는
이유는, 값이 어긋났을 때 어느 값이 어디서 왔는지 추적할 수 없게 되기
때문이다. cfp-scrape만 예외로 상위 소스가 갖지 않은 단계를 채운다.
"""

from dataclasses import replace
from datetime import date

from scripts.models import Deadline, Edition

# 앞에 올수록 우선한다.
SOURCE_PRIORITY = ("manual", "ai-deadlines", "ccfddl")


def merge_by_year(by_source: dict[str, list[Edition]]) -> dict[int, Edition]:
    """연도별로 가장 높은 우선순위 소스의 회차를 통째로 고른다."""
    merged: dict[int, Edition] = {}
    # 우선순위 역순으로 덮어써서 결국 최상위가 남게 한다.
    for source in reversed(SOURCE_PRIORITY):
        for edition in by_source.get(source) or []:
            merged[edition.year] = edition
    return merged


def apply_scraped(edition: Edition, extra: list[Deadline]) -> Edition:
    """CFP에서 추출한 단계를 채운다. 이미 있는 타입은 절대 건드리지 않는다."""
    if not extra:
        return edition
    existing = {d.type for d in edition.deadlines}
    additions = [d for d in extra if d.type not in existing]
    if not additions:
        return edition
    return replace(edition, deadlines=[*edition.deadlines, *additions])


def edition_status(edition: Edition, today: date) -> str:
    """upcoming / past / unknown."""
    end = edition.end or edition.start
    if end is None:
        return "unknown"
    return "upcoming" if end >= today else "past"


def select_editions(editions: list[Edition], today: date) -> list[Edition]:
    """직전 1개와 차기 1개만 남긴다.

    브라우저가 날짜 경계를 넘어가도 올바른 회차를 고를 수 있도록 둘을 넘긴다.
    날짜가 없는 회차는 다른 후보가 전혀 없을 때만 살린다.
    """
    if not editions:
        return []

    dated = [e for e in editions if (e.end or e.start) is not None]
    if not dated:
        # 전부 날짜 미상이면 가장 최근 연도 하나만 남겨 '일정 미확인'으로 보낸다.
        return [max(editions, key=lambda e: e.year)]

    upcoming = sorted(
        (e for e in dated if edition_status(e, today) == "upcoming"),
        key=lambda e: (e.start or e.end),
    )
    past = sorted(
        (e for e in dated if edition_status(e, today) == "past"),
        key=lambda e: (e.start or e.end),
    )

    picked = []
    if past:
        picked.append(past[-1])
    if upcoming:
        picked.append(upcoming[0])
    return picked


def pick_member(
    members: dict[str, list[Edition]], today: date
) -> tuple[str | None, list[Edition]]:
    """결합 행에서 대표 학회를 고른다.

    ICCV/ECCV, ASRU/SLT처럼 격년으로 번갈아 열리는 쌍이 대상이다.
    차기 회차가 더 이른 쪽을 대표로 삼고, 차기가 없으면 가장 최근에
    열린 쪽을 쓴다.
    """
    best_name: str | None = None
    best_key = None

    for name, editions in members.items():
        if not editions:
            continue
        upcoming = [e for e in editions if edition_status(e, today) == "upcoming"]
        if upcoming:
            # 차기가 있는 쪽이 무조건 우선. 그중 가장 이른 것.
            key = (0, min((e.start or e.end) for e in upcoming))
        else:
            dated = [e for e in editions if (e.end or e.start) is not None]
            if dated:
                # 차기가 없으면 가장 최근에 끝난 쪽. 최신일수록 앞서도록 부호를 뒤집는다.
                key = (1, -max((e.end or e.start) for e in dated).toordinal())
            else:
                key = (2, 0)
        if best_key is None or key < best_key:
            best_key, best_name = key, name

    if best_name is None:
        return None, []
    return best_name, members[best_name]
