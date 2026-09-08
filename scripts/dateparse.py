"""ccfddl의 자유 텍스트 개최일을 파싱한다.

ccfddl은 `start`/`end` 같은 구조화된 필드를 주지 않고
`date: April 13 - 17, 2026` 형태의 문자열만 준다.
실제 데이터 675건 기준 아래 패턴들이 98.5%를 덮는다.
나머지는 'TBD'나 월만 있는 값이라 파싱 대상이 아니며 None을 돌려준다.
"""

import re
from datetime import date

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

_M = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?"
_D = r"(\d{1,2})"
_Y = r"(\d{4})"
_DASH = r"\s*[-–]\s*"

# "February 25 - March 4, 2025"
_CROSS = re.compile(rf"^{_M}\s+{_D}{_DASH}{_M}\s+{_D}\s*,?\s*{_Y}$", re.I)
# "January 31 - 4 February, 2026"
_CROSS_DAY_LAST = re.compile(rf"^{_M}\s+{_D}{_DASH}{_D}\s+{_M}\s*,?\s*{_Y}$", re.I)
# "29 June - 3 July, 2026"
_DAY_FIRST = re.compile(rf"^{_D}\s+{_M}{_DASH}{_D}\s+{_M}\s*,?\s*{_Y}$", re.I)
# "June 3-7, 2026"
_SAME = re.compile(rf"^{_M}\s+{_D}{_DASH}{_D}\s*,?\s*{_Y}$", re.I)
# "May 4, 2026"
_SINGLE = re.compile(rf"^{_M}\s+{_D}\s*,?\s*{_Y}$", re.I)


def _month(name: str) -> int:
    return _MONTHS[name.lower()[:3]]


def _build(year: str, m1: str, d1: str, m2: str, d2: str) -> tuple[date, date] | None:
    """달력상 존재하지 않는 날짜는 None으로 돌려 호출자가 미상 처리하게 한다."""
    try:
        return (
            date(int(year), _month(m1), int(d1)),
            date(int(year), _month(m2), int(d2)),
        )
    except ValueError:
        return None


def parse_date_range(text: str | None) -> tuple[date, date] | None:
    """개최 시작일과 종료일을 돌려준다. 읽을 수 없으면 None."""
    if not text:
        return None
    s = " ".join(str(text).split())

    if m := _CROSS.match(s):
        m1, d1, m2, d2, y = m.groups()
        return _build(y, m1, d1, m2, d2)
    if m := _CROSS_DAY_LAST.match(s):
        m1, d1, d2, m2, y = m.groups()
        return _build(y, m1, d1, m2, d2)
    if m := _DAY_FIRST.match(s):
        d1, m1, d2, m2, y = m.groups()
        return _build(y, m1, d1, m2, d2)
    if m := _SAME.match(s):
        m1, d1, d2, y = m.groups()
        return _build(y, m1, d1, m1, d2)
    if m := _SINGLE.match(s):
        m1, d1, y = m.groups()
        return _build(y, m1, d1, m1, d1)
    return None
