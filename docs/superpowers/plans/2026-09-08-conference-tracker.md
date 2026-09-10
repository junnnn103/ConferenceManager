# 학회 일정 트래커 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** AI/HCI 인접 학회 39개의 개최일·제출마감을 매일 자동 갱신되는 정적 웹페이지로 추적한다.

**Architecture:** Python 빌드 스크립트가 `data/`의 커밋된 YAML과 두 개의 공개 데이터 소스(ccfddl, huggingface/ai-deadlines)를 병합해 `docs/data/conferences.json`을 만들고, 정적 HTML/JS가 이를 클라이언트에서 렌더링한다. D-day와 정렬은 브라우저의 현재 날짜로 계산하므로 빌드가 밀려도 어긋나지 않는다. CFP 페이지 추출은 빌드와 분리된 선택적 단계다.

**Tech Stack:** Python 3.11+, `openpyxl`(부트스트랩 전용), `PyYAML`, `requests`, `pytest`. 프론트엔드는 의존성 없는 vanilla HTML/CSS/JS. GitHub Actions + GitHub Pages.

**Spec:** `docs/superpowers/specs/2026-09-08-conference-tracker-design.md`

## Global Constraints

- **Python 3.11 이상.** `match` 문과 `datetime.date.fromisoformat`의 확장 포맷 지원에 의존한다.
- **테스트는 네트워크를 타지 않는다.** 모든 소스 응답은 `tests/fixtures/`의 고정 파일로 대체한다. 네트워크를 쓰는 테스트는 이 프로젝트에서 실패로 간주한다.
- **소스 우선순위는 `manual` > `ai-deadlines` > `ccfddl` > `cfp-scrape`.** 회차(연도) 단위로 소스를 통째 선택하며 필드 단위로 섞지 않는다. `cfp-scrape`는 상위 소스에 없는 단계만 채운다.
- **D-day와 정렬 순서는 클라이언트에서 계산한다.** `conferences.json`에는 절대 시각(ISO 8601)만 담고, 상대 표현(`D-42`)은 절대 넣지 않는다.
- **활성 학회는 39개, `registry.yaml`에는 99개 전부를 담는다.** 비활성은 `fields.yaml`의 `enabled: false`로 걸러진다.
- **다음 경로는 `.gitignore` 대상이며 빌드가 의존해서는 안 된다:** `학술연수 학회 리스트/`, `학술연수 파견자 처우기준/`, `학술연수 파견중 학회 참가 기준/`, `레퍼런스1.png`, `레퍼런스2.png`.
- **커밋 메시지는 한국어로 쓴다.** 기존 커밋(`3d8dd91`, `b937f59` 등)의 형식을 따른다.

---

## File Structure

| 파일 | 책임 |
|---|---|
| `scripts/models.py` | 공유 데이터 클래스 `Deadline` / `Edition` / `Conference`. 모든 소스가 이 형태로 정규화된다 |
| `scripts/dateparse.py` | ccfddl의 자유 텍스트 날짜(`April 13 - 17, 2026`) → `(date, date)`. 순수 함수 |
| `scripts/bootstrap_registry.py` | 엑셀 2개 → `data/registry.yaml`. 빌드가 아닌 수동 실행 |
| `scripts/sources/ccfddl.py` | ccfddl YAML → `Edition` 목록 |
| `scripts/sources/aideadlines.py` | huggingface/ai-deadlines YAML → `Edition` 목록 |
| `scripts/sources/manual.py` | `data/manual.yaml` → `Edition` 목록 |
| `scripts/sources/scraped.py` | `data/scraped/*.yaml` → `Deadline` 목록 (회차 전체가 아니라 단계만) |
| `scripts/merge.py` | 소스 우선순위 적용, 결합 행 해소, 회차 선택 |
| `scripts/validate_scraped.py` | CFP 추출 결과 검증 게이트. 네트워크·모델 미사용 |
| `scripts/build.py` | 엔트리포인트. `data/` → `docs/data/conferences.json` |
| `docs/index.html` | 표 골격, 필터 UI |
| `docs/app.js` | JSON 로드, 렌더링, 정렬, 필터, 토글 |
| `docs/style.css` | 다크 테마, 반응형 |
| `.claude/commands/scrape-cfp.md` | CFP 추출 프롬프트. 예약 실행과 수동 실행이 공유 |

소스 어댑터를 `scripts/sources/` 아래로 나눈 이유는 각 파일이 **하나의 외부 스키마만** 알게 하기 위해서다. 스키마가 바뀌면 한 파일만 고치면 되고, 각각을 픽스처로 독립 테스트할 수 있다.

---

## Task 1: 프로젝트 스캐폴딩과 데이터 모델

**Files:**
- Create: `pyproject.toml`
- Create: `scripts/__init__.py`
- Create: `scripts/models.py`
- Create: `scripts/sources/__init__.py`
- Create: `tests/__init__.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces: `Deadline(type: str, label: str, date: datetime, timezone: str | None, source: str, evidence: dict | None)`, `Edition(year: int, date_text: str, start: date | None, end: date | None, place: str, link: str | None, deadlines: list[Deadline], source: str)`, `Conference(abbr: str, abbr_group: str, full_name: str, grade: str, ai_specialist: bool, field: str, homepage: str | None, editions: list[Edition])`. 이후 모든 태스크가 이 타입을 쓴다.

- [ ] **Step 1: `pyproject.toml` 작성**

```toml
[project]
name = "conference-manager"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "PyYAML>=6.0",
    "requests>=2.31",
]

[project.optional-dependencies]
bootstrap = ["openpyxl>=3.1"]
dev = ["pytest>=8.0"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

`openpyxl`이 선택 의존성인 이유: 부트스트랩에만 쓰이고 CI 빌드에는 필요 없다.

- [ ] **Step 2: 실패하는 테스트 작성**

`tests/test_models.py`:

```python
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


def test_edition_primary_deadline_prefers_paper_over_unrelated_submission():
    # ECCV처럼 "submission" 타입이 튜토리얼/워크숍/AI Art 같은 논문과 무관한
    # 트랙에도 쓰이는 경우, "paper" 타입이 있으면 그것만 후보여야 한다.
    # submission 타입 중 가장 늦은 것(AI Art, 6월)이 이겨서는 안 된다.
    ed = Edition(
        year=2026, date_text="", start=None, end=None, place="", link=None,
        source="ccfddl",
        deadlines=[
            Deadline("submission", "Tutorial Proposal Submission", datetime(2026, 2, 15), None, "ccfddl"),
            Deadline("paper", "Paper Submission", datetime(2026, 3, 5), None, "ccfddl"),
            Deadline("submission", "AI Art Submission", datetime(2026, 6, 14), None, "ccfddl"),
        ],
    )
    assert ed.primary_deadline() == datetime(2026, 3, 5)


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
```

- [ ] **Step 3: 테스트가 실패하는지 확인**

Run: `python -m pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.models'`

- [ ] **Step 4: 최소 구현 작성**

`scripts/__init__.py`, `scripts/sources/__init__.py`, `tests/__init__.py`는 빈 파일로 만든다.

`scripts/models.py`:

```python
"""소스에 무관한 공용 데이터 모델.

모든 소스 어댑터는 외부 스키마를 이 형태로 정규화해 내놓는다.
날짜는 전부 절대 시각으로만 담는다 - D-day 같은 상대 표현은
브라우저가 계산하므로 여기서 만들지 않는다.
"""

from dataclasses import dataclass, field as dc_field
from datetime import date, datetime

# primary_deadline을 고를 때 "본 논문 마감"으로 인정하는 타입.
# 우선순위가 있는 단계별 폴백이다 - 평평한 집합이 아니다. "submission"은
# ECCV의 튜토리얼/워크숍/AI Art 제출처럼 논문과 무관한 트랙에도 쓰이므로,
# "paper" 타입이 하나라도 있으면 그것만 후보로 삼고 "submission"은 "paper"가
# 전혀 없는 학회(ICASSP, INTERSPEECH 등)에서만 대신 쓴다.
PAPER_TYPES = ("paper",)
SUBMISSION_FALLBACK_TYPES = ("submission",)


@dataclass
class Deadline:
    type: str
    label: str
    date: datetime
    timezone: str | None
    source: str
    evidence: dict | None = None

    def to_dict(self) -> dict:
        out = {
            "type": self.type,
            "label": self.label,
            "date": self.date.isoformat(),
            "source": self.source,
        }
        if self.timezone:
            out["timezone"] = self.timezone
        if self.evidence:
            out["evidence"] = self.evidence
        return out


@dataclass
class Edition:
    year: int
    date_text: str
    start: date | None
    end: date | None
    place: str
    link: str | None
    deadlines: list[Deadline]
    source: str

    def primary_deadline(self) -> datetime | None:
        """본 논문 마감. paper 타입을 최우선으로, 없으면 submission 타입을,
        그마저 없으면 가장 늦은 마감으로 대체한다."""
        if not self.deadlines:
            return None
        papers = [d for d in self.deadlines if d.type in PAPER_TYPES]
        if papers:
            return max(d.date for d in papers)
        submissions = [d for d in self.deadlines if d.type in SUBMISSION_FALLBACK_TYPES]
        if submissions:
            return max(d.date for d in submissions)
        return max(d.date for d in self.deadlines)

    def to_dict(self) -> dict:
        primary = self.primary_deadline()
        return {
            "year": self.year,
            "date_text": self.date_text,
            "start": self.start.isoformat() if self.start else None,
            "end": self.end.isoformat() if self.end else None,
            "place": self.place,
            "link": self.link,
            "deadlines": [d.to_dict() for d in self.deadlines],
            "primary_deadline": primary.isoformat() if primary else None,
            "source": self.source,
        }


@dataclass
class Conference:
    abbr: str
    abbr_group: str
    full_name: str
    grade: str
    ai_specialist: bool
    field: str
    homepage: str | None
    editions: list[Edition] = dc_field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "abbr": self.abbr,
            "abbr_group": self.abbr_group,
            "full_name": self.full_name,
            "grade": self.grade,
            "ai_specialist": self.ai_specialist,
            "field": self.field,
            "homepage": self.homepage,
            "editions": [e.to_dict() for e in self.editions],
        }
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `python -m pytest tests/test_models.py -v`
Expected: PASS — 8 passed

- [ ] **Step 6: 커밋**

```bash
git add pyproject.toml scripts/ tests/
git commit -m "$(cat <<'MSG'
프로젝트 스캐폴딩과 공용 데이터 모델 추가

Deadline / Edition / Conference. 모든 소스 어댑터가 이 형태로
정규화해 내놓는다. 날짜는 절대 시각만 담고 D-day는 담지 않는다.
MSG
)"
```

---

## Task 2: 날짜 파서

ccfddl은 개최일을 구조화된 필드 없이 자유 텍스트로만 준다(`date: April 13 - 17, 2026`). 정렬과 회차 선택이 전부 이 값에 의존하므로 별도 모듈로 분리해 집중적으로 테스트한다. 실제 ccfddl 데이터 675건에 대해 아래 구현이 98.5%를 파싱하며, 나머지는 `TBD`나 월만 있는 값이라 파싱 대상이 아니다.

**Files:**
- Create: `scripts/dateparse.py`
- Test: `tests/test_dateparse.py`

**Interfaces:**
- Consumes: 없음
- Produces: `parse_date_range(text: str) -> tuple[date, date] | None`. Task 4(ccfddl 어댑터)가 사용한다.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_dateparse.py`:

```python
from datetime import date

import pytest

from scripts.dateparse import parse_date_range


@pytest.mark.parametrize(
    "text,expected",
    [
        # 같은 달 안에서 끝나는 경우 - 가장 흔한 형태
        ("June 3-7, 2026", (date(2026, 6, 3), date(2026, 6, 7))),
        ("April 13 - 17, 2026", (date(2026, 4, 13), date(2026, 4, 17))),
        ("December 14-17, 2026", (date(2026, 12, 14), date(2026, 12, 17))),
        # 달을 넘기는 경우
        ("February 25 - March 4, 2025", (date(2025, 2, 25), date(2025, 3, 4))),
        ("July 27 - August 1, 2025", (date(2025, 7, 27), date(2025, 8, 1))),
        # 축약 월 이름
        ("Sep 13-17, 2026", (date(2026, 9, 13), date(2026, 9, 17))),
        # 마침표가 붙는 경우 (fmcad)
        ("Oct. 6-10, 2025", (date(2025, 10, 6), date(2025, 10, 10))),
        # 전부 대문자 (sp, fast)
        ("MAY 18-21, 2026", (date(2026, 5, 18), date(2026, 5, 21))),
        ("FEBRUARY 24-26, 2026", (date(2026, 2, 24), date(2026, 2, 26))),
        # 쉼표 없음 (icpads)
        ("November 22-26 2026", (date(2026, 11, 22), date(2026, 11, 26))),
        # 일-월 순서 (ecscw, iwqos)
        ("29 June - 3 July, 2026", (date(2026, 6, 29), date(2026, 7, 3))),
        # 끝 날짜만 일-월 순서 (cgo)
        ("January 31 - 4 February, 2026", (date(2026, 1, 31), date(2026, 2, 4))),
        # 하루짜리
        ("May 4, 2026", (date(2026, 5, 4), date(2026, 5, 4))),
        # 엔 대시
        ("June 3–7, 2026", (date(2026, 6, 3), date(2026, 6, 7))),
        # 공백이 지저분한 경우
        ("  June   3-7,  2026 ", (date(2026, 6, 3), date(2026, 6, 7))),
    ],
)
def test_parses_known_formats(text, expected):
    assert parse_date_range(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "TBD",
        "TBA",
        "May 2027 (exact dates TBD)",
        "March-April, 2025",   # 일자가 없음
        "Dec, 2025",           # 월만
        "November, 2025",      # 월만
        "",
        None,
    ],
)
def test_returns_none_for_undated(text):
    assert parse_date_range(text) is None


def test_invalid_calendar_date_returns_none():
    # 2월 30일 - 정규식은 통과하지만 달력상 존재하지 않는다
    assert parse_date_range("February 30-31, 2026") is None
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python -m pytest tests/test_dateparse.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.dateparse'`

- [ ] **Step 3: 최소 구현 작성**

`scripts/dateparse.py`:

```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_dateparse.py -v`
Expected: PASS — 24 passed

- [ ] **Step 5: 커밋**

```bash
git add scripts/dateparse.py tests/test_dateparse.py
git commit -m "$(cat <<'MSG'
ccfddl 자유 텍스트 개최일 파서 추가

ccfddl은 start/end 구조화 필드 없이 "April 13 - 17, 2026" 문자열만
준다. 실제 데이터 675건 중 98.5%를 파싱하며, 나머지는 TBD나
월만 있는 값이라 None을 돌려 미상으로 처리한다.
MSG
)"
```

---

## Task 3: registry 부트스트랩과 분야 정의

엑셀은 **1회 입력**이다. 이 태스크가 엑셀을 `data/registry.yaml`로 변환하고 나면, 이후 빌드는 엑셀을 보지 않는다. 덕분에 엑셀 원본을 `.gitignore`에 두고도 CI가 돈다.

`FIELD_ASSIGNMENT`는 엑셀에서 유도할 수 없는 큐레이션 값이라 스크립트에 상수로 박는다. 99개 전부에 대해 검증된 매핑이다.

**Files:**
- Create: `scripts/bootstrap_registry.py`
- Create: `data/fields.yaml`
- Test: `tests/test_bootstrap_registry.py`
- Test: `tests/fixtures/make_xlsx_fixtures.py`

**Interfaces:**
- Consumes: 없음
- Produces: `data/registry.yaml` (99개 항목), `data/fields.yaml`. Task 8(build)이 읽는다. `load_registry(path) -> list[dict]`도 함께 노출하며, 각 dict는 `abbr`, `display`, `full_name`, `grade`, `ai_specialist`, `field`, `homepage`, `members`, `sources` 키를 갖는다. `members`는 결합 행에서만 목록이고 그 외에는 `None`이다.

- [ ] **Step 1: `data/fields.yaml` 작성**

`enabled: true`인 10개 분야가 활성 39개 학회를 만든다. 나머지는 데이터는 남기되 사이트에서 뺀다 — 나중에 `enabled`만 켜면 되살아난다.

```yaml
# 분야 정의. enabled: false인 분야의 학회는 빌드 결과에서 제외된다.
# 되살리려면 enabled만 true로 바꾸면 된다 (엑셀 불필요).
fields:
  - id: ML
    label: ML
    color: "#a855f7"
    enabled: true
  - id: CV
    label: CV
    color: "#3b82f6"
    enabled: true
  - id: NLP
    label: NLP
    color: "#22c55e"
    enabled: true
  - id: Speech
    label: Speech
    color: "#14b8a6"
    enabled: true
  - id: Robotics
    label: Robotics
    color: "#f97316"
    enabled: true
  - id: DM/IR
    label: DM/IR
    color: "#eab308"
    enabled: true
  - id: HCI
    label: HCI
    color: "#ec4899"
    enabled: true
  - id: Graphics
    label: Graphics
    color: "#8b5cf6"
    enabled: true
  - id: Multimedia
    label: Multimedia
    color: "#06b6d4"
    enabled: true
  - id: AR/VR
    label: AR/VR
    color: "#f43f5e"
    enabled: true
  - id: DB
    label: DB
    color: "#64748b"
    enabled: false
  - id: Security
    label: Security
    color: "#64748b"
    enabled: false
  - id: SE/PL
    label: SE/PL
    color: "#64748b"
    enabled: false
  - id: OS/HPC
    label: OS/HPC
    color: "#64748b"
    enabled: false
  - id: Architecture
    label: Architecture
    color: "#64748b"
    enabled: false
  - id: Network
    label: Network
    color: "#64748b"
    enabled: false
  - id: Medical
    label: Medical
    color: "#64748b"
    enabled: false
  - id: InfoTheory
    label: Info Theory
    color: "#64748b"
    enabled: false
  - id: Circuits
    label: 회로/반도체
    color: "#64748b"
    enabled: false
  - id: RF/Power
    label: RF/전력
    color: "#64748b"
    enabled: false
  - id: Display/Optics
    label: 디스플레이/광학
    color: "#64748b"
    enabled: false
  - id: Materials
    label: 소재/화학/물리
    color: "#64748b"
    enabled: false
  - id: Thermal
    label: 열/에너지
    color: "#64748b"
    enabled: false
  - id: Food
    label: 식품
    color: "#64748b"
    enabled: false
```

- [ ] **Step 2: 합성 엑셀 픽스처 생성기 작성**

원본 엑셀은 `.gitignore` 대상이라 CI에서 못 쓴다. 같은 시트 구조를 가진 축약본을 만들어 커밋한다.

`tests/fixtures/make_xlsx_fixtures.py`:

```python
"""테스트용 합성 엑셀을 만든다. 원본 사내 엑셀은 커밋되지 않으므로
같은 시트 구조를 가진 축약본이 필요하다.

실행: python tests/fixtures/make_xlsx_fixtures.py
"""

from pathlib import Path

import openpyxl

HERE = Path(__file__).parent


def make_grade_xlsx(path: Path) -> None:
    """26년 우수 학회 List.xlsx 와 같은 구조.
    B열=No, C열=등급, D열=약어, E열=Full Name, 데이터는 5행부터.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    # openpyxl은 기본 시트를 "Sheet"로 만든다. 실제 엑셀 두 개 모두 "Sheet1"이고
    # bootstrap_registry.py가 그 이름을 찾으므로 픽스처도 맞춰야 한다.
    ws.title = "Sheet1"
    ws["B2"] = "26년 최우수/우수 학회 List"
    ws["B4"], ws["C4"], ws["D4"], ws["E4"] = "No", "등급", "약어", "Full Name"
    rows = [
        (1, "최우수", "cvpr", "Computer Vision and Pattern Recognition"),
        (2, "최우수", "nips", "Neural Information Processing Systems"),
        (3, "최우수", "iccv/eccv", "International Conference on Computer Vision / European Conference on Computer Vision"),
        (4, "우수", "wacv", "IEEE Winter Conference on Applications of Computer Vision"),
        (5, "우수", "SID", "SID DISPLAYWEEK"),
    ]
    for i, row in enumerate(rows, start=5):
        for j, value in enumerate(row):
            ws.cell(row=i, column=2 + j, value=value)
    wb.save(path)


def make_ai_specialist_xlsx(path: Path) -> None:
    """260406_AI_Specialist_인정학회리스트.xlsx 와 같은 구조.
    B열=대분류(첫 행에만), C열=No, D열=약어, E열=학회명, 데이터는 5행부터.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws["B2"] = "AI Specialist 인정 학회 List"
    ws["B4"], ws["C4"], ws["D4"], ws["E4"] = "대분류", "No", "약어", "학회명(영문)"
    rows = [
        ("AI/Data", 1, "CVPR", "Computer Vision and Pattern Recognition"),
        (None, 2, "NeurIPS", "Neural Information Processing Systems"),
        (None, 3, "ICCV", "International Conference on Computer Vision"),
        (None, 4, "ECCV", "European Conference on Computer Vision"),
        (None, 5, "WACV", "IEEE Winter Conference on Applications of Computer Vision"),
    ]
    for i, row in enumerate(rows, start=5):
        for j, value in enumerate(row):
            if value is not None:
                ws.cell(row=i, column=2 + j, value=value)
    wb.save(path)


if __name__ == "__main__":
    make_grade_xlsx(HERE / "grades.xlsx")
    make_ai_specialist_xlsx(HERE / "ai_specialist.xlsx")
    print("wrote", HERE / "grades.xlsx", "and", HERE / "ai_specialist.xlsx")
```

Run: `python tests/fixtures/make_xlsx_fixtures.py`

- [ ] **Step 3: 실패하는 테스트 작성**

`tests/test_bootstrap_registry.py`:

```python
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


def test_load_registry_roundtrips(tmp_path):
    entries = build_registry(FIXTURES / "grades.xlsx", FIXTURES / "ai_specialist.xlsx")
    path = tmp_path / "registry.yaml"
    path.write_text(
        yaml.safe_dump({"conferences": entries}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    assert load_registry(path) == entries
```

- [ ] **Step 4: 테스트가 실패하는지 확인**

Run: `python -m pytest tests/test_bootstrap_registry.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.bootstrap_registry'`

- [ ] **Step 5: 구현 작성**

`scripts/bootstrap_registry.py`. `FIELD_ASSIGNMENT`는 아래 99개를 그대로 쓴다 — 엑셀에서 유도할 수 없는 큐레이션 값이다.

```python
"""엑셀 2개를 data/registry.yaml로 변환한다.

이 스크립트는 빌드가 아니다. 엑셀이 갱신될 때 사람이 직접 실행한다.
변환이 끝나면 빌드는 registry.yaml만 읽으므로, 엑셀 원본을
.gitignore에 두어도 CI가 정상 동작한다.

사용법:
    python scripts/bootstrap_registry.py            # 새로 생성
    python scripts/bootstrap_registry.py --diff     # 기존과 비교만
"""

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
REGISTRY_PATH = ROOT / "data" / "registry.yaml"
EXCEL_DIR = ROOT / "학술연수 학회 리스트"
GRADE_XLSX = EXCEL_DIR / "26년 우수 학회 List.xlsx"
AI_XLSX = EXCEL_DIR / "260406_AI_Specialist_인정학회리스트.xlsx"

# 엑셀에서 유도할 수 없는 큐레이션 매핑. 99개 전부를 덮는다.
FIELD_ASSIGNMENT = {
    "cvpr": "CV", "nips": "ML", "iclr": "ML", "iccv/eccv": "CV", "icml": "ML",
    "aaai": "ML", "acl": "NLP", "emnlp": "NLP", "ijcai": "ML", "naacl": "NLP",
    "chi": "HCI", "icassp": "Speech", "kdd": "DM/IR", "icra": "Robotics",
    "sp": "Security", "www": "DM/IR", "interspeech": "Speech", "wacv": "CV",
    "uss": "Security", "siggraph": "Graphics", "sigir": "DM/IR", "mm": "Multimedia",
    "miccai": "Medical", "ccs": "Security", "cikm": "DM/IR", "corl": "Robotics",
    "iros": "Robotics", "icse": "SE/PL", "infocom": "Network", "wsdm": "DM/IR",
    "icc": "Network", "vldb": "DB", "ndss": "Security", "sigmod": "DB",
    "asplos": "Architecture", "icde": "DB", "isscc": "Circuits", "rss": "Robotics",
    "icip": "CV", "sigcomm": "Network", "globecom": "Network", "eurocrypt": "Security",
    "isca": "Architecture", "nsdi": "Network", "fse": "SE/PL", "crypto": "Security",
    "micro": "Architecture", "mlsys": "ML", "isit": "InfoTheory", "ase": "SE/PL",
    "hri": "Robotics", "osdi": "OS/HPC", "bigdataconf": "DM/IR", "UbiComp": "HCI",
    "recsys": "DM/IR", "iui": "HCI", "dac": "Architecture", "pldi": "SE/PL",
    "uist": "HCI", "hpca": "Architecture", "sc": "OS/HPC", "icdcs": "OS/HPC",
    "embc": "Medical", "eurosys": "OS/HPC", "ICME": "Multimedia", "vtc": "Network",
    "issta": "SE/PL", "asru/slt": "Speech", "vr": "AR/VR", "vlsi": "Circuits",
    "fpga": "Architecture", "sigmetrics": "OS/HPC", "sosp": "OS/HPC",
    "sensys": "Network", "mobisys": "Network", "cav": "SE/PL", "APEC": "RF/Power",
    "conext": "Network", "bibm": "Medical", "ismar": "AR/VR", "EuCAP": "RF/Power",
    "mmsys": "Network", "ccnc": "Network", "IMS": "RF/Power", "humanoids": "Robotics",
    "mobicom": "Network", "RFIC": "Circuits", "siggrapha": "Graphics",
    "SID": "Display/Optics", "iTherm": "Thermal", "SPIEarvrmr": "Display/Optics",
    "SPIEopto": "Display/Optics", "ACS": "Materials", "APS": "Materials",
    "EFFT": "Food", "ict": "Thermal", "IIR": "Thermal", "MRS": "Materials",
    "IFT": "Food",
}


def normalize_abbr(raw: str) -> str:
    """약어를 비교 가능한 형태로 정규화한다.

    'VLDB/PVLDB' 같은 별칭 표기는 앞쪽만 취하고, 공백과 기호를 지운다.
    두 엑셀이 같은 학회를 다르게 적는 경우(NeurIPS vs nips)를 흡수하기 위함이다.
    """
    first = str(raw).split("/")[0]
    return re.sub(r"[^a-z0-9]", "", first.lower())


def _read_grade_rows(path: Path) -> list[tuple[str, str, str]]:
    import openpyxl

    ws = openpyxl.load_workbook(path, data_only=True)["Sheet1"]
    out = []
    for row in ws.iter_rows(min_row=5, values_only=True):
        abbr, full_name = row[3], row[4]
        if not abbr:
            continue
        out.append((str(abbr).strip(), str(row[2]).strip(), str(full_name or "").strip()))
    return out


def _read_ai_specialist_abbrs(path: Path) -> set[str]:
    import openpyxl

    ws = openpyxl.load_workbook(path, data_only=True)["Sheet1"]
    found = set()
    for row in ws.iter_rows(min_row=5, values_only=True):
        if not row[3]:
            continue
        for part in str(row[3]).split("/"):
            found.add(normalize_abbr(part))
    return found


def build_registry(grade_xlsx: Path, ai_xlsx: Path) -> list[dict]:
    ai_abbrs = _read_ai_specialist_abbrs(ai_xlsx)
    entries = []
    for abbr, grade, full_name in _read_grade_rows(grade_xlsx):
        # 결합 행('iccv/eccv')은 구성원이 전부 목록에 있을 때만 True로 본다.
        parts = [normalize_abbr(p) for p in abbr.split("/")]
        raw_parts = [p.strip() for p in abbr.split("/")]
        entries.append({
            "abbr": abbr,
            # 표시명. 기본값은 엑셀 약어이고, 사람이 'CVPR'처럼 다듬는다.
            "display": abbr,
            "full_name": full_name,
            "grade": grade,
            "ai_specialist": all(p in ai_abbrs for p in parts),
            "field": FIELD_ASSIGNMENT.get(abbr),
            "homepage": None,
            # 결합 행(격년 교대 학회 쌍)만 members를 갖는다.
            # 병합 단계가 구성원을 각각 조회한 뒤 차기 회차가 이른 쪽을 대표로 삼는다.
            "members": (
                [{"display": p, "sources": {"ai_deadlines": None, "ccfddl": None}}
                 for p in raw_parts]
                if len(raw_parts) > 1 else None
            ),
            "sources": {"ai_deadlines": None, "ccfddl": None},
        })
    return entries


def load_registry(path: Path = REGISTRY_PATH) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data["conferences"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--diff", action="store_true",
                        help="파일을 쓰지 않고 기존 registry와의 차이만 출력")
    args = parser.parse_args()

    if not GRADE_XLSX.exists():
        print(f"엑셀을 찾을 수 없습니다: {GRADE_XLSX}", file=sys.stderr)
        print("이 스크립트는 엑셀이 로컬에 있을 때만 실행합니다.", file=sys.stderr)
        return 1

    entries = build_registry(GRADE_XLSX, AI_XLSX)
    unmapped = [e["abbr"] for e in entries if not e["field"]]
    if unmapped:
        print(f"분야 매핑이 없는 약어: {unmapped}", file=sys.stderr)
        print("FIELD_ASSIGNMENT에 추가한 뒤 다시 실행하세요.", file=sys.stderr)
        return 1

    if args.diff:
        if not REGISTRY_PATH.exists():
            print("기존 registry.yaml이 없습니다. --diff 없이 실행하세요.")
            return 0
        old = {e["abbr"]: e for e in load_registry()}
        new = {e["abbr"]: e for e in entries}
        for abbr in sorted(new.keys() - old.keys()):
            print(f"  추가: {abbr} ({new[abbr]['grade']})")
        for abbr in sorted(old.keys() - new.keys()):
            print(f"  삭제: {abbr}")
        for abbr in sorted(old.keys() & new.keys()):
            if old[abbr]["grade"] != new[abbr]["grade"]:
                print(f"  등급 변경: {abbr} {old[abbr]['grade']} -> {new[abbr]['grade']}")
            if old[abbr]["ai_specialist"] != new[abbr]["ai_specialist"]:
                print(f"  AI Specialist 변경: {abbr} -> {new[abbr]['ai_specialist']}")
        print("\nhomepage와 sources는 손으로 붙인 값이라 자동 반영하지 않습니다.")
        return 0

    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(
        yaml.safe_dump({"conferences": entries}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    print(f"{len(entries)}개 학회를 {REGISTRY_PATH}에 기록했습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `python -m pytest tests/test_bootstrap_registry.py -v`
Expected: PASS — 13 passed (parametrize 6건 포함)

- [ ] **Step 7: 실제 registry 생성**

Run: `python scripts/bootstrap_registry.py`
Expected: `99개 학회를 .../data/registry.yaml에 기록했습니다.`

확인: `python -c "import yaml,pathlib; d=yaml.safe_load(pathlib.Path('data/registry.yaml').read_text()); print(len(d['conferences']))"` → `99`

- [ ] **Step 8: 커밋**

```bash
git add scripts/bootstrap_registry.py data/fields.yaml data/registry.yaml \
        tests/test_bootstrap_registry.py tests/fixtures/
git commit -m "$(cat <<'MSG'
엑셀 → registry.yaml 부트스트랩과 분야 정의 추가

엑셀은 1회 입력이다. 이후 빌드는 registry.yaml만 읽으므로
사내 엑셀 원본을 gitignore에 두고도 CI가 돈다.

- 99개 학회 전부에 분야를 매핑, 활성 10개 분야가 39개 학회를 만든다
- 결합 행(iccv/eccv)은 구성원이 모두 인정 목록에 있을 때만 AI Specialist
- --diff 모드로 내년 엑셀과의 차이만 확인 가능. 자동 덮어쓰기는 안 한다
- 테스트용 합성 엑셀 픽스처 생성기 포함 (원본은 커밋 대상이 아님)
MSG
)"
```

---

## Task 4: ccfddl 소스 어댑터

ccfddl은 CS 전반 354개 학회를 다루며 우리 39개 중 대부분을 덮는다. 파일 경로가 `conference/<카테고리>/<id>.yml` 형태라 id만 알면 바로 가져올 수 있다. 개최일은 자유 텍스트뿐이라 Task 2의 파서를 쓴다.

**Files:**
- Create: `scripts/sources/ccfddl.py`
- Test: `tests/test_source_ccfddl.py`
- Test: `tests/fixtures/ccfddl_chi.yml`

**Interfaces:**
- Consumes: `scripts.models.Deadline`, `scripts.models.Edition`, `scripts.dateparse.parse_date_range`
- Produces: `parse_ccfddl(raw: list) -> list[Edition]`, `fetch_ccfddl(conf_id: str, session) -> list[Edition]`, `CCFDDL_CATEGORIES: tuple[str, ...]`

- [ ] **Step 1: 픽스처 작성**

`tests/fixtures/ccfddl_chi.yml` — 실제 ccfddl `conference/HI/chi.yml`의 축약본:

```yaml
- title: CHI
  description: ACM Conference on Human Factors in Computing Systems
  sub: HI
  rank:
    ccf: A
    core: A*
    thcpl: A
  dblp: chi
  confs:
    - year: 2025
      id: chi25
      link: https://chi2025.acm.org/
      timeline:
        - abstract_deadline: '2024-09-05 23:59:59'
          deadline: '2024-09-12 23:59:59'
      timezone: AoE
      date: April 26 - May 1, 2025
      place: Yokohama, Japan
    - year: 2026
      id: chi26
      link: https://chi2026.acm.org/
      timeline:
        - abstract_deadline: '2025-09-04 23:59:59'
          deadline: '2025-09-11 23:59:59'
          comment: Papers track
      timezone: AoE
      date: April 13 - 17, 2026
      place: Centre de Convencions Internacional de Barcelona, Barcelona, Spain
    - year: 2027
      id: chi27
      link: https://chi2027.acm.org/
      timeline:
        - deadline: TBD
      timezone: AoE
      date: TBD
      place: TBD
```

- [ ] **Step 2: 실패하는 테스트 작성**

`tests/test_source_ccfddl.py`:

```python
from datetime import date, datetime
from pathlib import Path

import yaml

from scripts.sources.ccfddl import parse_ccfddl

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture():
    return yaml.safe_load((FIXTURES / "ccfddl_chi.yml").read_text(encoding="utf-8"))


def test_parses_every_edition():
    editions = parse_ccfddl(load_fixture())
    assert [e.year for e in editions] == [2025, 2026, 2027]


def test_parses_date_range_from_free_text():
    ed = next(e for e in parse_ccfddl(load_fixture()) if e.year == 2026)
    assert ed.start == date(2026, 4, 13)
    assert ed.end == date(2026, 4, 17)
    assert ed.date_text == "April 13 - 17, 2026"


def test_undated_edition_keeps_none_without_raising():
    ed = next(e for e in parse_ccfddl(load_fixture()) if e.year == 2027)
    assert ed.start is None
    assert ed.end is None


def test_place_commas_become_spaces():
    ed = next(e for e in parse_ccfddl(load_fixture()) if e.year == 2025)
    assert ed.place == "Yokohama Japan"


def test_extracts_abstract_and_paper_deadlines():
    ed = next(e for e in parse_ccfddl(load_fixture()) if e.year == 2026)
    by_type = {d.type: d for d in ed.deadlines}
    assert by_type["abstract"].date == datetime(2025, 9, 4, 23, 59, 59)
    assert by_type["paper"].date == datetime(2025, 9, 11, 23, 59, 59)
    assert by_type["paper"].timezone == "AoE"
    assert all(d.source == "ccfddl" for d in ed.deadlines)


def test_comment_becomes_deadline_label():
    ed = next(e for e in parse_ccfddl(load_fixture()) if e.year == 2026)
    paper = next(d for d in ed.deadlines if d.type == "paper")
    assert paper.label == "Papers track"


def test_unparseable_deadline_is_skipped_not_crashed():
    ed = next(e for e in parse_ccfddl(load_fixture()) if e.year == 2027)
    assert ed.deadlines == []


def test_edition_source_is_tagged():
    assert all(e.source == "ccfddl" for e in parse_ccfddl(load_fixture()))
```

- [ ] **Step 3: 테스트가 실패하는지 확인**

Run: `python -m pytest tests/test_source_ccfddl.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.sources.ccfddl'`

- [ ] **Step 4: 구현 작성**

`scripts/sources/ccfddl.py`:

```python
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


def _normalize_place(value) -> str:
    """'Bari, Italy' -> 'Bari Italy'. 레퍼런스 표기와 맞춘다."""
    if not value or str(value).strip().upper() in {"TBD", "TBA"}:
        return ""
    return " ".join(str(value).replace(",", " ").split())


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
            place=_normalize_place(conf.get("place")),
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
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `python -m pytest tests/test_source_ccfddl.py -v`
Expected: PASS — 8 passed

- [ ] **Step 6: 커밋**

```bash
git add scripts/sources/ccfddl.py tests/test_source_ccfddl.py tests/fixtures/ccfddl_chi.yml
git commit -m "$(cat <<'MSG'
ccfddl 소스 어댑터 추가

카테고리 디렉터리를 순회해 <id>.yml을 찾고 Edition으로 정규화한다.
개최일은 자유 텍스트뿐이라 dateparse를 쓰고, 읽히지 않으면
None으로 두어 미상 처리한다. place의 쉼표는 공백으로 바꾼다.
MSG
)"
```

---

## Task 5: ai-deadlines 소스 어댑터

huggingface/ai-deadlines는 ccfddl보다 훨씬 상세하다 — `start`/`end` ISO 필드, 다단계 `deadlines` 배열, `city`/`country`/`venue`를 준다. 활성 39개 중 24개가 여기서 2026년 다단계 일정을 얻는다. 그래서 병합 우선순위가 ccfddl보다 높다.

**Files:**
- Create: `scripts/sources/aideadlines.py`
- Test: `tests/test_source_aideadlines.py`
- Test: `tests/fixtures/aideadlines_cvpr.yml`

**Interfaces:**
- Consumes: `scripts.models.Deadline`, `scripts.models.Edition`
- Produces: `parse_aideadlines(raw: list) -> list[Edition]`, `fetch_aideadlines(conf_id: str, session) -> list[Edition]`

- [ ] **Step 1: 픽스처 작성**

`tests/fixtures/aideadlines_cvpr.yml` — 실제 `src/data/conferences/cvpr.yml`의 축약본:

```yaml
- title: CVPR
  year: 2026
  id: cvpr26
  full_name: IEEE/CVF Conference on Computer Vision and Pattern Recognition
  link: https://cvpr.thecvf.com/Conferences/2026/CallForPapers
  deadline: '2025-11-13 23:59:59'
  date: June 3-7, 2026
  start: 2026-06-03
  end: 2026-06-07
  tags:
    - computer-vision
    - machine-learning
  deadlines:
    - type: abstract
      label: Abstract Submission
      date: '2025-11-07 23:59:59'
      timezone: AoE
    - type: paper
      label: Paper Submission
      date: '2025-11-13 23:59:59'
      timezone: AoE
    - type: notification
      label: Final Decisions
      date: '2026-02-20 23:59:59'
      timezone: AoE
  city: Denver
  country: USA
  abstract_deadline: '2025-11-07 23:59:59'
  rankings: 'CCF: A, CORE: A*, THCPL: A'
  venue: Colorado Convention Center, Denver, USA
- title: CVPR
  year: 2027
  id: cvpr27
  link: https://cvpr.thecvf.com/
  date: June 19-26, 2027
  start: 2027-06-19
  end: 2027-06-26
  city: Seattle
  country: USA
  note: Submission deadlines to be announced.
- title: CVPR
  year: 2025
  id: cvpr25
  link: https://cvpr.thecvf.com/Conferences/2025/CallForPapers
  deadline: '2024-11-14 23:59:00'
  timezone: UTC-8
  date: June 10-17, 2025
  city: Nashville
  country: Tennessee
```

- [ ] **Step 2: 실패하는 테스트 작성**

`tests/test_source_aideadlines.py`:

```python
from datetime import date, datetime
from pathlib import Path

import yaml

from scripts.sources.aideadlines import parse_aideadlines

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture():
    return yaml.safe_load((FIXTURES / "aideadlines_cvpr.yml").read_text(encoding="utf-8"))


def test_parses_every_edition_sorted_by_year():
    editions = parse_aideadlines(load_fixture())
    assert [e.year for e in editions] == [2025, 2026, 2027]


def test_prefers_structured_start_end_over_text():
    ed = next(e for e in parse_aideadlines(load_fixture()) if e.year == 2026)
    assert ed.start == date(2026, 6, 3)
    assert ed.end == date(2026, 6, 7)


def test_falls_back_to_parsing_date_text_when_start_missing():
    # 2025 항목에는 start/end가 없고 date 문자열만 있다
    ed = next(e for e in parse_aideadlines(load_fixture()) if e.year == 2025)
    assert ed.start == date(2025, 6, 10)
    assert ed.end == date(2025, 6, 17)


def test_structured_start_end_wins_when_text_disagrees():
    # 픽스처의 2026 항목은 start/end와 date 문자열이 같은 값으로 파싱되므로,
    # 구현이 구조화 필드를 무시해도 통과한다. 둘이 어긋나는 입력이라야 선호를 증명한다.
    raw = [{
        "title": "CVPR",
        "year": 2026,
        "start": "2026-06-03",
        "end": "2026-06-07",
        "date": "December 1-2, 2026",
    }]
    ed = parse_aideadlines(raw)[0]
    assert ed.start == date(2026, 6, 3)
    assert ed.end == date(2026, 6, 7)


def test_place_joins_city_and_country():
    ed = next(e for e in parse_aideadlines(load_fixture()) if e.year == 2026)
    assert ed.place == "Denver USA"


def test_reads_multi_stage_deadlines():
    ed = next(e for e in parse_aideadlines(load_fixture()) if e.year == 2026)
    assert [d.type for d in ed.deadlines] == ["abstract", "paper", "notification"]
    assert ed.deadlines[1].label == "Paper Submission"
    assert ed.deadlines[1].date == datetime(2025, 11, 13, 23, 59, 59)
    assert all(d.source == "ai-deadlines" for d in ed.deadlines)


def test_falls_back_to_flat_deadline_when_no_deadlines_array():
    ed = next(e for e in parse_aideadlines(load_fixture()) if e.year == 2025)
    assert [d.type for d in ed.deadlines] == ["paper"]
    assert ed.deadlines[0].date == datetime(2024, 11, 14, 23, 59, 0)
    assert ed.deadlines[0].timezone == "UTC-8"


def test_edition_without_any_deadline_is_kept():
    ed = next(e for e in parse_aideadlines(load_fixture()) if e.year == 2027)
    assert ed.deadlines == []
    assert ed.start == date(2027, 6, 19)


def test_primary_deadline_picks_paper_stage():
    ed = next(e for e in parse_aideadlines(load_fixture()) if e.year == 2026)
    assert ed.primary_deadline() == datetime(2025, 11, 13, 23, 59, 59)
```

- [ ] **Step 3: 테스트가 실패하는지 확인**

Run: `python -m pytest tests/test_source_aideadlines.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.sources.aideadlines'`

- [ ] **Step 4: 구현 작성**

`scripts/sources/aideadlines.py`:

```python
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
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `python -m pytest tests/test_source_aideadlines.py -v`
Expected: PASS — 9 passed

- [ ] **Step 6: 커밋**

```bash
git add scripts/sources/aideadlines.py tests/test_source_aideadlines.py \
        tests/fixtures/aideadlines_cvpr.yml
git commit -m "$(cat <<'MSG'
huggingface/ai-deadlines 소스 어댑터 추가

다단계 deadlines 배열과 start/end ISO 필드를 그대로 살린다.
활성 39개 중 24개가 여기서 2026년 다단계 일정을 얻으므로
병합 우선순위를 ccfddl보다 높게 둔다.

다단계 배열이 없는 오래된 항목은 평면 deadline 필드로,
start/end가 없으면 date 자유 텍스트 파싱으로 각각 대체한다.
MSG
)"
```

---

## Task 6: manual과 scraped 로더

두 로더는 성격이 다르다. `manual`은 **회차 전체**를 제공하는 최우선 소스이고(ccfddl·ai-deadlines가 아예 모르는 HRI·Humanoids용), `scraped`는 **단계만** 제공하는 최하위 보충재다(poster/LBW/workshop). 그래서 반환 타입이 다르다.

**Files:**
- Create: `scripts/sources/manual.py`
- Create: `scripts/sources/scraped.py`
- Create: `data/manual.yaml`
- Test: `tests/test_source_manual.py`
- Test: `tests/test_source_scraped.py`
- Test: `tests/fixtures/scraped_chi.yaml`

**Interfaces:**
- Consumes: `scripts.models.Deadline`, `scripts.models.Edition`
- Produces: `load_manual(path) -> dict[str, list[Edition]]` (키는 registry의 `abbr`), `load_scraped(directory) -> dict[tuple[str, int], list[Deadline]]` (키는 `(abbr, year)`)

- [ ] **Step 1: `data/manual.yaml` 작성**

두 소스 모두 모르는 학회의 일정을 손으로 적는다. 시작 시점에는 HRI만 실제 값으로 채우고, 나머지는 확인되는 대로 추가한다.

```yaml
# 두 공개 소스가 다루지 않는 학회의 일정. 최우선 소스다.
# year를 반드시 명시하며, 그 연차에만 적용된다.
conferences:
  hri:
    editions:
      - year: 2026
        date_text: "March 9-12, 2026"
        start: 2026-03-09
        end: 2026-03-12
        place: "Christchurch New Zealand"
        link: "https://humanrobotinteraction.org/2026/"
        deadlines:
          - type: paper
            label: "Full Paper"
            date: "2025-10-01 23:59:59"
            timezone: AoE
```

`humanoids`와 홀수해 `asru`는 개최 정보가 공개되는 대로 같은 형식으로 추가한다. 값을 모르는 상태로 빈 항목을 만들지 않는다 — 빈 항목은 "일정 미확인"으로 표시되는 것보다 나쁘다.

- [ ] **Step 2: scraped 픽스처 작성**

`tests/fixtures/scraped_chi.yaml` — `validate_scraped.py`가 만들어낼 형태:

```yaml
abbr: chi
editions:
  - year: 2026
    deadlines:
      - type: lbw
        label: "Late-Breaking Work"
        date: "2026-02-12 23:59:59"
        evidence:
          raw_text: "Late-Breaking Work submission deadline: February 12, 2026"
          url: "https://chi2026.acm.org/lbw/"
      - type: workshop
        label: "Workshop Proposals"
        date: "2025-10-15 23:59:59"
        evidence:
          raw_text: "Workshop proposals are due October 15, 2025"
          url: "https://chi2026.acm.org/workshops/"
```

- [ ] **Step 3: 실패하는 테스트 작성**

`tests/test_source_manual.py`:

```python
from datetime import date, datetime
from pathlib import Path

from scripts.sources.manual import load_manual


def test_loads_editions_keyed_by_abbr(tmp_path):
    path = tmp_path / "manual.yaml"
    path.write_text(
        """
conferences:
  hri:
    editions:
      - year: 2026
        date_text: "March 9-12, 2026"
        start: 2026-03-09
        end: 2026-03-12
        place: "Christchurch New Zealand"
        link: "https://humanrobotinteraction.org/2026/"
        deadlines:
          - type: paper
            label: "Full Paper"
            date: "2025-10-01 23:59:59"
            timezone: AoE
""",
        encoding="utf-8",
    )
    result = load_manual(path)
    assert set(result) == {"hri"}
    ed = result["hri"][0]
    assert ed.year == 2026
    assert ed.start == date(2026, 3, 9)
    assert ed.place == "Christchurch New Zealand"
    assert ed.source == "manual"
    assert ed.deadlines[0].date == datetime(2025, 10, 1, 23, 59, 59)
    assert ed.deadlines[0].source == "manual"


def test_missing_file_returns_empty(tmp_path):
    assert load_manual(tmp_path / "absent.yaml") == {}


def test_empty_conferences_key_returns_empty(tmp_path):
    path = tmp_path / "manual.yaml"
    path.write_text("conferences: {}\n", encoding="utf-8")
    assert load_manual(path) == {}
```

`tests/test_source_scraped.py`:

```python
from datetime import datetime
from pathlib import Path

from scripts.sources.scraped import load_scraped

FIXTURES = Path(__file__).parent / "fixtures"


def test_loads_deadlines_keyed_by_abbr_and_year(tmp_path):
    (tmp_path / "chi.yaml").write_text(
        (FIXTURES / "scraped_chi.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    result = load_scraped(tmp_path)
    assert set(result) == {("chi", 2026)}

    deadlines = result[("chi", 2026)]
    assert [d.type for d in deadlines] == ["lbw", "workshop"]
    assert deadlines[0].date == datetime(2026, 2, 12, 23, 59, 59)
    assert all(d.source == "cfp-scrape" for d in deadlines)


def test_evidence_is_preserved(tmp_path):
    (tmp_path / "chi.yaml").write_text(
        (FIXTURES / "scraped_chi.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    lbw = load_scraped(tmp_path)[("chi", 2026)][0]
    assert lbw.evidence["url"] == "https://chi2026.acm.org/lbw/"
    assert "February 12, 2026" in lbw.evidence["raw_text"]


def test_missing_directory_returns_empty(tmp_path):
    assert load_scraped(tmp_path / "absent") == {}


def test_raw_subdirectory_is_ignored(tmp_path):
    # raw/ 는 검증 게이트를 통과하지 않은 추출 결과다. 재귀 글롭으로 바뀌면
    # 검증 안 된 날짜가 사이트로 새어 나간다. 픽스처에 실제 마감을 넣어야
    # 그 회귀가 결과에 드러난다 — 빈 editions로는 어느 쪽이든 빈 dict라 구분되지 않는다.
    (tmp_path / "raw").mkdir()
    (tmp_path / "raw" / "chi.yaml").write_text(
        """
abbr: chi
editions:
  - year: 2026
    deadlines:
      - type: lbw
        label: "검증 안 된 추출값"
        date: "2026-02-12 23:59:59"
""",
        encoding="utf-8",
    )
    assert load_scraped(tmp_path) == {}
```

- [ ] **Step 4: 테스트가 실패하는지 확인**

Run: `python -m pytest tests/test_source_manual.py tests/test_source_scraped.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.sources.manual'`

- [ ] **Step 5: 구현 작성**

`scripts/sources/manual.py`:

```python
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
                place=str(entry.get("place") or ""),
                link=entry.get("link"),
                deadlines=deadlines,
                source="manual",
            ))
        if editions:
            out[abbr] = sorted(editions, key=lambda e: e.year)
    return out
```

`scripts/sources/scraped.py`:

```python
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
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `python -m pytest tests/test_source_manual.py tests/test_source_scraped.py -v`
Expected: PASS — 8 passed

- [ ] **Step 7: 커밋**

```bash
git add scripts/sources/manual.py scripts/sources/scraped.py data/manual.yaml \
        tests/test_source_manual.py tests/test_source_scraped.py \
        tests/fixtures/scraped_chi.yaml
git commit -m "$(cat <<'MSG'
manual과 scraped 로더 추가

성격이 달라 반환 타입도 다르다. manual은 회차 전체를 주는 최우선
소스(HRI 등 공개 소스가 모르는 학회용)이고, scraped는 단계만 주는
최하위 보충재(poster/LBW/workshop)다.

scraped는 data/scraped/ 최상위만 읽는다. raw/ 는 검증 전 원본이라
빌드가 건드리지 않는다.
MSG
)"
```

---

## Task 7: CFP 검증 게이트

이 프로젝트에서 **가장 중요한 코드**다. CFP 페이지 추출은 LLM이 하므로 그럴듯한 날짜를 지어낼 수 있고, 그것이 사실처럼 표시되면 마감을 놓친다. 게이트는 네트워크도 모델도 쓰지 않는 순수 함수라, 추출 주체가 바뀌어도 그대로 유효하다.

가장 강력한 방어선은 **원문 대조**다: 추출 결과가 들고 온 `raw_text`가 실제로 가져온 페이지 본문 안에 있어야 한다. 지어낸 문장은 여기서 걸린다.

**Files:**
- Create: `scripts/validate_scraped.py`
- Test: `tests/test_validate_scraped.py`

**Interfaces:**
- Consumes: 없음 (순수 함수)
- Produces: `validate_extraction(items: list[dict], page_text: str, conference_start: date | None, today: date) -> tuple[list[dict], list[dict]]` — `(채택, 탈락)`을 돌려주며 탈락 항목에는 `reject_reason`이 붙는다. `normalize_whitespace(text: str) -> str`.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_validate_scraped.py`:

```python
from datetime import date
import json
import sys

import pytest

from scripts import validate_scraped
from scripts.validate_scraped import normalize_whitespace, validate_extraction

PAGE = """
CHI 2026 Call for Participation

Late-Breaking Work submission deadline: February 12, 2026
Workshop proposals are due October 15, 2025
"""

START = date(2026, 4, 13)
TODAY = date(2025, 9, 8)


def item(**kw):
    base = {
        "type": "lbw",
        "label": "Late-Breaking Work",
        "date": "2026-02-12 23:59:59",
        "confidence": "high",
        "raw_text": "Late-Breaking Work submission deadline: February 12, 2026",
        "url": "https://chi2026.acm.org/lbw/",
    }
    base.update(kw)
    return base


def test_accepts_item_whose_raw_text_appears_in_page():
    accepted, rejected = validate_extraction([item()], PAGE, START, TODAY)
    assert len(accepted) == 1
    assert rejected == []
    assert accepted[0]["evidence"]["raw_text"].startswith("Late-Breaking Work")
    assert accepted[0]["evidence"]["url"] == "https://chi2026.acm.org/lbw/"
    assert "confidence" not in accepted[0]


def test_rejects_fabricated_raw_text():
    # 모델이 문장을 지어낸 경우 - 가장 중요한 방어선
    bad = item(raw_text="Poster deadline: March 3, 2026", type="poster")
    accepted, rejected = validate_extraction([bad], PAGE, START, TODAY)
    assert accepted == []
    assert rejected[0]["reject_reason"] == "raw_text_not_in_page"


def test_raw_text_match_ignores_whitespace_differences():
    spaced = item(raw_text="Late-Breaking   Work submission deadline:\n February 12, 2026")
    accepted, _ = validate_extraction([spaced], PAGE, START, TODAY)
    assert len(accepted) == 1


def test_rejects_deadline_after_conference_start():
    late = item(date="2026-05-01 23:59:59")
    accepted, rejected = validate_extraction([late], PAGE, START, TODAY)
    assert accepted == []
    assert rejected[0]["reject_reason"] == "deadline_after_conference"


def test_rejects_deadline_more_than_18_months_before_conference():
    ancient = item(date="2024-01-01 23:59:59")
    accepted, rejected = validate_extraction([ancient], PAGE, START, TODAY)
    assert accepted == []
    assert rejected[0]["reject_reason"] == "deadline_too_early"


def test_rejects_low_confidence():
    unsure = item(confidence="low")
    accepted, rejected = validate_extraction([unsure], PAGE, START, TODAY)
    assert accepted == []
    assert rejected[0]["reject_reason"] == "low_confidence"


def test_rejects_unparseable_date():
    broken = item(date="sometime in spring")
    accepted, rejected = validate_extraction([broken], PAGE, START, TODAY)
    assert accepted == []
    assert rejected[0]["reject_reason"] == "unparseable_date"


def test_rejects_missing_raw_text():
    empty = item(raw_text="")
    accepted, rejected = validate_extraction([empty], PAGE, START, TODAY)
    assert accepted == []
    assert rejected[0]["reject_reason"] == "raw_text_not_in_page"


def test_rejects_unknown_track():
    weird = item(type="keynote")
    accepted, rejected = validate_extraction([weird], PAGE, START, TODAY)
    assert accepted == []
    assert rejected[0]["reject_reason"] == "unknown_track"


def test_date_range_check_is_skipped_when_conference_start_unknown():
    accepted, rejected = validate_extraction([item()], PAGE, None, TODAY)
    assert len(accepted) == 1


def test_processes_every_item_independently():
    good = item()
    bad = item(raw_text="invented text", type="poster")
    accepted, rejected = validate_extraction([good, bad], PAGE, START, TODAY)
    assert len(accepted) == 1
    assert len(rejected) == 1


def test_normalize_whitespace_collapses_runs():
    assert normalize_whitespace("a  b\n\tc ") == "a b c"


def test_rejects_real_sentence_that_does_not_mention_the_claimed_date():
    # 페이지에 실재하는 문장이라도 주장된 날짜를 언급하지 않으면 대조가 아니다.
    # 이것이 없으면 아무 문장이나 날조된 날짜를 뒷받침한다.
    unrelated = item(raw_text="Workshop proposals are due October 15, 2025",
                     date="2026-03-03 23:59:59")
    accepted, rejected = validate_extraction([unrelated], PAGE, START, TODAY)
    assert accepted == []
    assert rejected[0]["reject_reason"] == "date_not_in_raw_text"


def test_accepts_iso_date_written_in_raw_text():
    page = "Poster deadline is 2026-02-12 for all submissions."
    iso = item(type="poster", raw_text="Poster deadline is 2026-02-12 for all submissions.",
               date="2026-02-12 23:59:59")
    accepted, _ = validate_extraction([iso], page, START, TODAY)
    assert len(accepted) == 1


def test_accepts_day_before_month_in_raw_text():
    page = "Posters are due 12 February and cannot be extended."
    dayfirst = item(type="poster", raw_text="Posters are due 12 February and cannot be extended.",
                    date="2026-02-12 23:59:59")
    accepted, _ = validate_extraction([dayfirst], page, START, TODAY)
    assert len(accepted) == 1


def test_year_or_id_digits_adjacent_to_a_month_do_not_corroborate():
    # "2012 February"의 12는 연도 꼬리이지 일자가 아니다. 단어 경계가 없으면
    # 페이지에 실재하는 아무 문장이나 2월 12일을 뒷받침하게 된다.
    page = "The conference series started in 2012 February in Boston."
    spurious = item(
        type="poster",
        raw_text="The conference series started in 2012 February in Boston.",
        date="2026-02-12 23:59:59",
    )
    accepted, rejected = validate_extraction([spurious], page, START, TODAY)
    assert accepted == []
    assert rejected[0]["reject_reason"] == "date_not_in_raw_text"


def test_existing_yaml_is_kept_when_no_items_pass(tmp_path, monkeypatch):
    """기존 YAML이 있고 이번 실행에서 검증할 항목이 없으면 파일을 유지한다.

    transient failure가 기존 데이터를 지우지 않도록 한다.
    """
    scraped_dir = tmp_path / "scraped"
    scraped_dir.mkdir()
    raw_dir = scraped_dir / "raw"
    raw_dir.mkdir()

    # 기존 YAML 파일 생성
    existing_yaml = scraped_dir / "chi.yaml"
    existing_yaml.write_text("abbr: chi\neditions:\n  - year: 2025\n", encoding="utf-8")

    # 현재 실행에서 검증할 수 없는 JSON (모든 항목이 탈락할 raw_text)
    raw_json = raw_dir / "chi.json"
    raw_json.write_text(
        json.dumps({
            "abbr": "chi",
            "editions": [{
                "year": 2026,
                "conference_start": "2026-04-13",
                "items": [{
                    "type": "lbw",
                    "label": "LBW",
                    "date": "2026-02-12 23:59:59",
                    "confidence": "high",
                    "raw_text": "fabricated text",
                    "url": "http://example.com",
                }],
            }],
        }),
        encoding="utf-8",
    )

    # page.txt 파일이 없어서 page_text_missing이 될 것
    monkeypatch.setattr(validate_scraped, "SCRAPED_DIR", scraped_dir)
    monkeypatch.setattr(sys, "argv", ["validate_scraped.py"])

    exit_code = validate_scraped.main()

    # 기존 YAML이 여전히 존재해야 함
    assert existing_yaml.exists()
    assert existing_yaml.read_text(encoding="utf-8").startswith("abbr: chi")


def test_one_malformed_json_does_not_stop_next_file(tmp_path, monkeypatch):
    """한 파일이 손상되어도 다음 파일은 처리된다."""
    scraped_dir = tmp_path / "scraped"
    scraped_dir.mkdir()
    raw_dir = scraped_dir / "raw"
    raw_dir.mkdir()

    # 첫 번째 파일: conference_start가 잘못된 형식
    bad_json = raw_dir / "aaa_bad.json"
    bad_json.write_text(
        json.dumps({
            "abbr": "bad",
            "editions": [{
                "year": 2026,
                "conference_start": "not-a-date",  # 잘못된 형식
                "items": [],
            }],
        }),
        encoding="utf-8",
    )

    # 두 번째 파일: 정상적인 파일
    good_json = raw_dir / "zzz_good.json"
    page_text = "Poster deadline is 2026-02-12."
    good_json.write_text(
        json.dumps({
            "abbr": "good",
            "editions": [{
                "year": 2026,
                "conference_start": "2026-04-13",
                "items": [{
                    "type": "poster",
                    "label": "Poster",
                    "date": "2026-02-12 23:59:59",
                    "confidence": "high",
                    "raw_text": "Poster deadline is 2026-02-12",
                    "url": "http://example.com",
                }],
            }],
        }),
        encoding="utf-8",
    )
    (raw_dir / "zzz_good.txt").write_text(page_text, encoding="utf-8")

    monkeypatch.setattr(validate_scraped, "SCRAPED_DIR", scraped_dir)
    monkeypatch.setattr(sys, "argv", ["validate_scraped.py"])

    exit_code = validate_scraped.main()

    # 좋은 파일의 YAML이 생성되어야 함
    good_yaml = scraped_dir / "zzz_good.yaml"
    assert good_yaml.exists()
    content = good_yaml.read_text(encoding="utf-8")
    assert "abbr: good" in content
    assert "2026-02-12" in content
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python -m pytest tests/test_validate_scraped.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.validate_scraped'`

- [ ] **Step 3: 구현 작성**

`scripts/validate_scraped.py`:

```python
"""CFP 추출 결과의 검증 게이트.

추출은 모델이 하지만 채택 여부는 이 코드가 정한다.
네트워크도 모델도 쓰지 않는 순수 함수라, 추출 주체가 바뀌어도
안전장치는 그대로 유효하다.

핵심은 원문 대조다. 추출 결과가 들고 온 raw_text가 실제 페이지
본문 안에 없으면 그 항목은 지어낸 것으로 보고 버린다.
"""

import argparse
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
SCRAPED_DIR = ROOT / "data" / "scraped"

# 인정하는 트랙. 이 밖의 값은 모델이 지어낸 분류로 보고 버린다.
KNOWN_TRACKS = frozenset({
    "poster", "lbw", "workshop", "demo", "tutorial", "doctoral_consortium", "other",
})

# 개최일로부터 이보다 더 앞선 마감은 잘못 읽은 것으로 본다.
MAX_LEAD = timedelta(days=548)  # 약 18개월

_TIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d")

_MONTH_NUMBERS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

_DATE_IN_TEXT = re.compile(
    r"(?P<month>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(?P<day>\d{1,2})(?:st|nd|rd|th)?\b"
    r"|\b(?P<day2>\d{1,2})(?:st|nd|rd|th)?\s+(?P<month2>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?"
    r"|\b(?P<iso>\d{4}-\d{2}-\d{2})\b",
    re.I,
)


def normalize_whitespace(text: str) -> str:
    """연속 공백·개행·탭을 공백 하나로 접는다.

    CFP 페이지는 HTML에서 줄바꿈이 임의로 들어가므로,
    원문 대조를 공백에 관대하게 만들어야 정상 항목이 억울하게 걸리지 않는다.
    """
    return re.sub(r"\s+", " ", str(text)).strip()


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


def mentions_date(text: str, when: datetime) -> bool:
    """raw_text가 주장된 날짜를 실제로 언급하는지 확인한다.

    부분 문자열 검사만으로는 페이지에 실재하는 아무 문장이나 날조된 날짜를
    뒷받침할 수 있다. 문장 안에 그 날짜가 적혀 있어야 대조가 성립한다.
    연도는 요구하지 않는다 - CFP는 "February 12"만 쓰고 연도는 제목에 두는 일이 흔하다.
    """
    for m in _DATE_IN_TEXT.finditer(text or ""):
        if m.group("iso"):
            try:
                if date.fromisoformat(m.group("iso")) == when.date():
                    return True
            except ValueError:
                pass
            continue
        month = (m.group("month") or m.group("month2") or "").lower()[:3]
        day = m.group("day") or m.group("day2")
        if _MONTH_NUMBERS.get(month) == when.month and int(day) == when.day:
            return True
    return False


def validate_extraction(
    items: list[dict],
    page_text: str,
    conference_start: date | None,
    today: date,
) -> tuple[list[dict], list[dict]]:
    """게이트를 통과한 항목과 탈락 항목을 나눠 돌려준다.

    탈락 항목에는 reject_reason이 붙어 리포트에 쓰인다.
    한 항목이 실패해도 나머지는 계속 검사한다.
    """
    haystack = normalize_whitespace(page_text)
    accepted: list[dict] = []
    rejected: list[dict] = []

    def reject(item: dict, reason: str) -> None:
        rejected.append({**item, "reject_reason": reason})

    for item in items:
        if str(item.get("confidence", "")).lower() == "low":
            reject(item, "low_confidence")
            continue

        track = str(item.get("type") or "")
        if track not in KNOWN_TRACKS:
            reject(item, "unknown_track")
            continue

        raw_text = normalize_whitespace(item.get("raw_text") or "")
        if not raw_text or raw_text not in haystack:
            reject(item, "raw_text_not_in_page")
            continue

        when = _parse_datetime(item.get("date"))
        if when is None:
            reject(item, "unparseable_date")
            continue

        if conference_start is not None:
            if when.date() > conference_start:
                reject(item, "deadline_after_conference")
                continue
            if conference_start - when.date() > MAX_LEAD:
                reject(item, "deadline_too_early")
                continue

        if not mentions_date(raw_text, when):
            reject(item, "date_not_in_raw_text")
            continue

        accepted.append({
            "type": track,
            "label": str(item.get("label") or track.replace("_", " ").title()),
            "date": when.strftime("%Y-%m-%d %H:%M:%S"),
            "evidence": {
                "raw_text": normalize_whitespace(item.get("raw_text")),
                "url": item.get("url") or "",
            },
        })

    return accepted, rejected


def _validate_one(raw_json: Path, today: date) -> tuple[dict | None, list[dict]]:
    """data/scraped/raw/<abbr>.json 하나를 검증해 출력 문서를 만든다."""
    import json

    payload = json.loads(raw_json.read_text(encoding="utf-8"))
    abbr = payload["abbr"]
    page_path = raw_json.with_suffix(".txt")

    editions = []
    all_rejected: list[dict] = []

    # 페이지 텍스트 파일이 없으면 모든 항목을 page_text_missing 사유로 탈락시킨다.
    if not page_path.exists():
        for entry in payload.get("editions") or []:
            for item in entry.get("items") or []:
                all_rejected.append({
                    **item,
                    "reject_reason": "page_text_missing",
                    "abbr": abbr,
                    "year": entry.get("year")
                })
        return None, all_rejected

    page_text = page_path.read_text(encoding="utf-8")

    for entry in payload.get("editions") or []:
        start = entry.get("conference_start")
        start_date = date.fromisoformat(start) if start else None
        accepted, rejected = validate_extraction(
            entry.get("items") or [], page_text, start_date, today
        )
        for item in rejected:
            all_rejected.append({**item, "abbr": abbr, "year": entry.get("year")})
        if accepted:
            editions.append({"year": int(entry["year"]), "deadlines": accepted})

    if not editions:
        return None, all_rejected
    return {"abbr": abbr, "editions": editions}, all_rejected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true",
                        help="탈락 항목이 하나라도 있으면 종료 코드 1")
    args = parser.parse_args()

    raw_dir = SCRAPED_DIR / "raw"
    if not raw_dir.exists():
        print("data/scraped/raw 가 없습니다. 검증할 것이 없습니다.")
        return 0

    today = date.today()
    total_accepted = 0
    total_rejected: list[dict] = []

    for raw_json in sorted(raw_dir.glob("*.json")):
        try:
            document, rejected = _validate_one(raw_json, today)
        except Exception as e:
            print(f"경고: {raw_json.stem} 처리 중 오류, 건너뜀: {e}", file=sys.stderr)
            continue

        total_rejected.extend(rejected)
        out_path = SCRAPED_DIR / f"{raw_json.stem}.yaml"
        if document is None:
            if out_path.exists():
                print(f"경고: {out_path}가 유지됨 (이번 실행에서 검증할 항목이 없음)",
                      file=sys.stderr)
            continue
        out_path.write_text(
            yaml.safe_dump(document, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        total_accepted += sum(len(e["deadlines"]) for e in document["editions"])

    print(f"채택 {total_accepted}건, 탈락 {len(total_rejected)}건")
    for item in total_rejected:
        print(f"  탈락 [{item['reject_reason']}] {item.get('abbr')} "
              f"{item.get('year')} {item.get('type')} {item.get('date')}",
              file=sys.stderr)

    if args.strict and total_rejected:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_validate_scraped.py -v`
Expected: PASS — 18 passed

- [ ] **Step 5: 커밋**

```bash
git add scripts/validate_scraped.py tests/test_validate_scraped.py
git commit -m "$(cat <<'MSG'
CFP 추출 검증 게이트 추가

추출은 모델이 하지만 채택은 이 코드가 정한다. 네트워크도 모델도
쓰지 않는 순수 함수라 추출 주체가 바뀌어도 안전장치는 유효하다.

네 개의 게이트:
- raw_text가 실제 페이지 본문의 부분 문자열인가 (환각 방어의 핵심,
  공백 정규화 후 비교해 정상 항목이 억울하게 걸리지 않게 한다)
- 마감이 개최일 이전이고 18개월 이내인가
- confidence: low 제외
- 알 수 없는 트랙 분류 제외

한 항목이 실패해도 나머지는 계속 검사하고, 탈락 사유를 남긴다.
MSG
)"
```

---

## Task 8: 병합과 회차 선택

세 가지를 한다. **소스 병합**(회차 단위로 소스를 통째 선택), **결합 행 해소**(ICCV/ECCV 같은 격년 교대 쌍에서 대표 고르기), **회차 선택**(직전 1개 + 차기 1개만 남기기).

필드 단위로 섞지 않는 이유는 값이 어긋났을 때 어느 값이 어디서 왔는지 추적할 수 없게 되기 때문이다. `cfp-scrape`만 예외로, 상위 소스가 **갖지 않은 단계만** 채운다.

**Files:**
- Create: `scripts/merge.py`
- Test: `tests/test_merge.py`

**Interfaces:**
- Consumes: `scripts.models.Deadline`, `scripts.models.Edition`
- Produces: `SOURCE_PRIORITY`, `merge_by_year(by_source: dict[str, list[Edition]]) -> dict[int, Edition]`, `apply_scraped(edition: Edition, extra: list[Deadline]) -> Edition`, `select_editions(editions: list[Edition], today: date) -> list[Edition]`, `edition_status(edition: Edition, today: date) -> str`, `pick_member(members: dict[str, list[Edition]], today: date) -> tuple[str | None, list[Edition]]`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_merge.py`:

```python
from datetime import date, datetime

from scripts.merge import (
    SOURCE_PRIORITY,
    apply_scraped,
    edition_status,
    merge_by_year,
    pick_member,
    select_editions,
)
from scripts.models import Deadline, Edition


def ed(year, source, start=None, end=None, deadlines=None, place="X"):
    return Edition(
        year=year, date_text="", start=start, end=end, place=place,
        link=None, deadlines=deadlines or [], source=source,
    )


def dl(kind, when, source="ccfddl"):
    return Deadline(kind, kind.title(), when, None, source)


def test_source_priority_order():
    assert SOURCE_PRIORITY == ("manual", "ai-deadlines", "ccfddl")


def test_higher_priority_source_wins_whole_edition():
    merged = merge_by_year({
        "ccfddl": [ed(2026, "ccfddl", place="From ccfddl")],
        "ai-deadlines": [ed(2026, "ai-deadlines", place="From HF")],
    })
    assert merged[2026].place == "From HF"
    assert merged[2026].source == "ai-deadlines"


def test_manual_beats_everything():
    merged = merge_by_year({
        "ccfddl": [ed(2026, "ccfddl", place="C")],
        "ai-deadlines": [ed(2026, "ai-deadlines", place="H")],
        "manual": [ed(2026, "manual", place="M")],
    })
    assert merged[2026].place == "M"


def test_lower_priority_fills_years_the_higher_one_lacks():
    merged = merge_by_year({
        "ccfddl": [ed(2025, "ccfddl"), ed(2026, "ccfddl")],
        "ai-deadlines": [ed(2026, "ai-deadlines")],
    })
    assert merged[2025].source == "ccfddl"
    assert merged[2026].source == "ai-deadlines"


def test_fields_are_never_mixed_across_sources():
    # HF 회차가 이겼다면 place도 deadlines도 전부 HF 것이어야 한다
    merged = merge_by_year({
        "ccfddl": [ed(2026, "ccfddl", place="C", deadlines=[dl("paper", datetime(2025, 1, 1))])],
        "ai-deadlines": [ed(2026, "ai-deadlines", place="H")],
    })
    assert merged[2026].place == "H"
    assert merged[2026].deadlines == []


def test_apply_scraped_adds_missing_track():
    base = ed(2026, "ai-deadlines", deadlines=[dl("paper", datetime(2025, 9, 11), "ai-deadlines")])
    extra = [Deadline("lbw", "LBW", datetime(2026, 2, 12), None, "cfp-scrape",
                      {"raw_text": "x", "url": "y"})]
    result = apply_scraped(base, extra)
    assert [d.type for d in result.deadlines] == ["paper", "lbw"]


def test_apply_scraped_never_overwrites_existing_track():
    base = ed(2026, "ai-deadlines", deadlines=[dl("paper", datetime(2025, 9, 11), "ai-deadlines")])
    extra = [Deadline("paper", "Paper", datetime(2025, 1, 1), None, "cfp-scrape")]
    result = apply_scraped(base, extra)
    assert len(result.deadlines) == 1
    assert result.deadlines[0].source == "ai-deadlines"


def test_apply_scraped_with_no_extra_returns_equivalent_edition():
    base = ed(2026, "ccfddl", deadlines=[dl("paper", datetime(2025, 9, 11))])
    assert apply_scraped(base, []).deadlines == base.deadlines


def test_apply_scraped_does_not_mutate_the_input_edition():
    # 같은 Edition 객체가 빌드 중 여러 곳에서 도달 가능하므로, 원본을 건드리면
    # 엉뚱한 곳에 cfp-scrape 단계가 섞인다. replace로 새 객체를 만들어야 한다.
    base = ed(2026, "ai-deadlines",
              deadlines=[dl("paper", datetime(2025, 9, 11), "ai-deadlines")])
    before = list(base.deadlines)
    extra = [Deadline("lbw", "LBW", datetime(2026, 2, 12), None, "cfp-scrape")]

    result = apply_scraped(base, extra)

    assert base.deadlines == before
    assert result is not base
    assert result.deadlines is not base.deadlines
    assert [d.type for d in result.deadlines] == ["paper", "lbw"]


def test_edition_status_upcoming_when_end_is_today_or_later():
    assert edition_status(ed(2026, "x", end=date(2026, 4, 17)), date(2026, 4, 17)) == "upcoming"
    assert edition_status(ed(2026, "x", end=date(2026, 4, 17)), date(2026, 1, 1)) == "upcoming"


def test_edition_status_past_when_ended():
    assert edition_status(ed(2026, "x", end=date(2026, 4, 17)), date(2026, 4, 18)) == "past"


def test_edition_status_unknown_without_dates():
    assert edition_status(ed(2026, "x"), date(2026, 1, 1)) == "unknown"


def test_select_editions_keeps_one_past_and_one_upcoming():
    editions = [
        ed(2024, "x", start=date(2024, 6, 1), end=date(2024, 6, 5)),
        ed(2025, "x", start=date(2025, 6, 1), end=date(2025, 6, 5)),
        ed(2026, "x", start=date(2026, 6, 1), end=date(2026, 6, 5)),
        ed(2027, "x", start=date(2027, 6, 1), end=date(2027, 6, 5)),
    ]
    picked = select_editions(editions, date(2025, 9, 8))
    assert [e.year for e in picked] == [2025, 2026]


def test_select_editions_returns_only_past_when_nothing_upcoming():
    editions = [ed(2024, "x", start=date(2024, 6, 1), end=date(2024, 6, 5))]
    assert [e.year for e in select_editions(editions, date(2026, 1, 1))] == [2024]


def test_select_editions_keeps_undated_editions_as_fallback():
    editions = [ed(2026, "x")]
    assert [e.year for e in select_editions(editions, date(2026, 1, 1))] == [2026]


def test_select_editions_on_empty_input():
    assert select_editions([], date(2026, 1, 1)) == []


def test_pick_member_chooses_earliest_upcoming():
    # ICCV는 홀수해, ECCV는 짝수해. 2026년 9월 기준 차기는 ICCV 2027.
    members = {
        "iccv": [ed(2025, "ccfddl", start=date(2025, 10, 19), end=date(2025, 10, 25)),
                 ed(2027, "ccfddl", start=date(2027, 10, 1), end=date(2027, 10, 6))],
        "eccv": [ed(2026, "ccfddl", start=date(2026, 9, 8), end=date(2026, 9, 13))],
    }
    name, editions = pick_member(members, date(2026, 9, 20))
    assert name == "iccv"
    assert [e.year for e in editions] == [2025, 2027]


def test_pick_member_prefers_the_one_actually_upcoming():
    members = {
        "iccv": [ed(2025, "ccfddl", start=date(2025, 10, 19), end=date(2025, 10, 25))],
        "eccv": [ed(2026, "ccfddl", start=date(2026, 9, 8), end=date(2026, 9, 13))],
    }
    name, _ = pick_member(members, date(2026, 1, 1))
    assert name == "eccv"


def test_pick_member_with_no_upcoming_prefers_the_most_recently_held():
    # 둘 다 차기 회차가 없을 때는 가장 최근에 열린 쪽이 대표가 되어야 한다.
    # pick_member의 -toordinal 부호가 이 비교를 뒤집는 장치다.
    members = {
        "iccv": [ed(2023, "ccfddl", start=date(2023, 10, 1), end=date(2023, 10, 6))],
        "eccv": [ed(2024, "ccfddl", start=date(2024, 9, 29), end=date(2024, 10, 4))],
    }
    name, editions = pick_member(members, date(2026, 9, 20))
    assert name == "eccv"
    assert [e.year for e in editions] == [2024]


def test_pick_member_with_no_data_returns_none():
    assert pick_member({"iccv": [], "eccv": []}, date(2026, 1, 1)) == (None, [])
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python -m pytest tests/test_merge.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.merge'`

- [ ] **Step 3: 구현 작성**

`scripts/merge.py`:

```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_merge.py -v`
Expected: PASS — 20 passed

- [ ] **Step 5: 커밋**

```bash
git add scripts/merge.py tests/test_merge.py
git commit -m "$(cat <<'MSG'
소스 병합, 결합 행 해소, 회차 선택 추가

병합은 회차 단위로 소스를 통째 고른다. 필드 단위로 섞으면 값이
어긋났을 때 출처 추적이 불가능해지기 때문이다. cfp-scrape만 예외로
상위 소스가 갖지 않은 단계를 채운다.

결합 행(ICCV/ECCV, ASRU/SLT)은 격년 교대 쌍이라 양쪽을 조회한 뒤
차기 회차가 이른 쪽을 대표로 삼는다.

회차는 직전 1개 + 차기 1개만 남긴다. 브라우저가 날짜 경계를 넘어도
올바른 회차를 고를 수 있게 하기 위함이다.
MSG
)"
```

---

## Task 9: 빌드 엔트리포인트

`data/`와 두 소스를 모아 `docs/data/conferences.json`을 만든다. 네트워크 호출은 **주입 가능한 fetcher 함수**로 감싸, 테스트가 네트워크 없이 전체 파이프라인을 돌릴 수 있게 한다.

**Files:**
- Create: `scripts/build.py`
- Test: `tests/test_build.py`

**Interfaces:**
- Consumes: Task 1·3·6·8의 전부
- Produces: `build(registry, fields, fetchers, manual, scraped, today) -> dict`, `load_fields(path) -> list[dict]`, `enabled_field_ids(fields) -> set[str]`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_build.py`:

```python
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
    assert [c["abbr"] for c in out["conferences"]] == ["CVPR"]
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


def test_only_the_adjacent_editions_survive():
    # build는 회차를 직전 1개 + 차기 1개로 줄인다. 전부 내보내면 JSON이 부풀고
    # 브라우저가 고르지 말아야 할 오래된 회차까지 후보로 받는다.
    many = [
        Edition(year, "", date(year, 6, 1), date(year, 6, 5), "X", None, [], "ai-deadlines")
        for year in (2023, 2024, 2025, 2026, 2027)
    ]
    out = build(REGISTRY, FIELDS, make_fetchers(hf={"cvpr": many}),
                manual={}, scraped={}, today=TODAY)
    years = [e["year"] for e in out["conferences"][0]["editions"]]
    assert years == [2025, 2026]


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
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python -m pytest tests/test_build.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.build'`

- [ ] **Step 3: 구현 작성**

`scripts/build.py`:

```python
"""빌드 엔트리포인트: data/ + 공개 소스 -> docs/data/conferences.json

네트워크 호출은 주입 가능한 fetcher로 감쌌다. 테스트가 네트워크 없이
전체 파이프라인을 돌릴 수 있어야 하기 때문이다.

한 소스가 죽어도 빌드는 계속한다. 사이트가 어제 데이터로라도 떠 있는 편이
아예 안 뜨는 것보다 낫다.
"""

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

from scripts.bootstrap_registry import load_registry
from scripts.merge import apply_scraped, merge_by_year, pick_member, select_editions
from scripts.models import Conference, Edition
from scripts.sources.aideadlines import fetch_aideadlines
from scripts.sources.ccfddl import fetch_ccfddl
from scripts.sources.manual import load_manual
from scripts.sources.scraped import load_scraped

ROOT = Path(__file__).parents[1]
FIELDS_PATH = ROOT / "data" / "fields.yaml"
MANUAL_PATH = ROOT / "data" / "manual.yaml"
SCRAPED_DIR = ROOT / "data" / "scraped"
OUTPUT_PATH = ROOT / "docs" / "data" / "conferences.json"

KST = timezone.utc  # 표시는 클라이언트가 하므로 생성 시각만 UTC로 남긴다


def load_fields(path: Path = FIELDS_PATH) -> list[dict]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))["fields"]


def enabled_field_ids(fields: list[dict]) -> set[str]:
    return {f["id"] for f in fields if f.get("enabled")}


def _gather(source_ids: dict, fetchers: dict, abbr: str) -> dict[str, list[Edition]]:
    """소스별 회차 목록을 모은다. 실패한 소스는 건너뛴다."""
    by_source: dict[str, list[Edition]] = {}
    for key, source_name in (("ai_deadlines", "ai-deadlines"), ("ccfddl", "ccfddl")):
        conf_id = (source_ids or {}).get(key)
        if not conf_id:
            continue
        try:
            by_source[source_name] = fetchers[source_name](conf_id) or []
        except Exception as exc:  # 한 소스의 실패가 빌드 전체를 막지 않게 한다
            print(f"경고: {abbr}의 {source_name} 조회 실패: {exc}", file=sys.stderr)
    return by_source


def build(
    registry: list[dict],
    fields: list[dict],
    fetchers: dict,
    manual: dict[str, list[Edition]],
    scraped: dict[tuple[str, int], list],
    today: date,
) -> dict:
    active_fields = enabled_field_ids(fields)
    conferences: list[dict] = []
    unresolved: list[dict] = []

    for entry in registry:
        if entry.get("field") not in active_fields:
            continue

        abbr_group = entry["abbr"]
        display = entry.get("display") or abbr_group
        manual_editions = manual.get(abbr_group, [])

        if entry.get("members"):
            # 결합 행: 구성원을 각각 조회한 뒤 차기 회차가 이른 쪽을 대표로 삼는다.
            per_member: dict[str, list[Edition]] = {}
            for member in entry["members"]:
                by_source = _gather(member.get("sources"), fetchers, abbr_group)
                if manual_editions:
                    by_source["manual"] = manual_editions
                per_member[member["display"]] = list(merge_by_year(by_source).values())
            chosen, editions = pick_member(per_member, today)
            if chosen:
                display = chosen
        else:
            by_source = _gather(entry.get("sources"), fetchers, abbr_group)
            if manual_editions:
                by_source["manual"] = manual_editions
            editions = list(merge_by_year(by_source).values())

        selected = select_editions(editions, today)
        selected = [
            apply_scraped(e, scraped.get((abbr_group, e.year), [])) for e in selected
        ]

        if not selected:
            unresolved.append({"abbr": display, "reason": "소스에 회차 정보가 없음"})
            continue

        conferences.append(Conference(
            abbr=display,
            abbr_group=abbr_group,
            full_name=entry.get("full_name") or "",
            grade=entry.get("grade") or "",
            ai_specialist=bool(entry.get("ai_specialist")),
            field=entry["field"],
            homepage=entry.get("homepage"),
            editions=selected,
        ).to_dict())

    return {
        "generated_at": datetime.now(KST).isoformat(),
        "fields": [
            {"id": f["id"], "label": f["label"], "color": f["color"]}
            for f in fields if f.get("enabled")
        ],
        "conferences": conferences,
        "unresolved": unresolved,
    }


def main() -> int:
    import requests

    session = requests.Session()
    session.headers["User-Agent"] = "conference-manager (github actions)"

    fetchers = {
        "ai-deadlines": lambda cid: fetch_aideadlines(cid, session),
        "ccfddl": lambda cid: fetch_ccfddl(cid, session),
    }

    result = build(
        registry=load_registry(),
        fields=load_fields(),
        fetchers=fetchers,
        manual=load_manual(MANUAL_PATH),
        scraped=load_scraped(SCRAPED_DIR),
        today=date.today(),
    )

    if not result["conferences"]:
        # 두 소스가 모두 죽은 경우. 기존 JSON을 덮어쓰지 않는다.
        print("학회를 하나도 만들지 못했습니다. 기존 파일을 유지합니다.", file=sys.stderr)
        return 1

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"학회 {len(result['conferences'])}개, 미확인 {len(result['unresolved'])}개")
    for item in result["unresolved"]:
        print(f"  미확인: {item['abbr']} - {item['reason']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/test_build.py -v`
Expected: PASS — 11 passed

- [ ] **Step 5: 전체 테스트 실행**

Run: `python -m pytest -v`
Expected: PASS — 모든 테스트 통과

- [ ] **Step 6: 실제 빌드 1회 실행**

`data/registry.yaml`의 `sources`는 아직 전부 `null`이므로 대부분 미확인으로 나온다. 이 시점의 목적은 파이프라인이 끝까지 도는지 확인하는 것이다.

Run: `python -m scripts.build`
Expected: `학회 1개, 미확인 38개` 와 종료 코드 0.

`sources`가 전부 비어 있는데도 학회가 하나 나오는 이유는 Task 6에서 넣은
`data/manual.yaml`의 HRI 항목 때문이다. manual은 소스 매핑과 무관하게 회차를 직접
공급하므로, 활성 39개 중 HRI만 해소되고 나머지 38개가 `unresolved`로 간다.
Task 10이 소스 매핑을 채우면 이 38개가 해소된다.

이 단계에서 `main()`의 0건 검사를 약화시키지 말 것 — 지금은 발동하지 않을 뿐,
두 소스가 모두 죽었을 때 기존 JSON을 지키는 장치로 여전히 필요하다.

- [ ] **Step 7: 커밋**

```bash
git add scripts/build.py tests/test_build.py
git commit -m "$(cat <<'MSG'
빌드 엔트리포인트 추가

data/ 와 두 공개 소스를 모아 docs/data/conferences.json을 만든다.
네트워크 호출을 주입 가능한 fetcher로 감싸 테스트가 네트워크 없이
전체 파이프라인을 돌린다.

한 소스가 죽어도 빌드는 계속한다. 두 소스가 모두 죽어 학회가
하나도 안 나오면 기존 JSON을 덮어쓰지 않고 종료 코드 1을 낸다.
MSG
)"
```

---

## Task 10: 소스 id 매핑 채우기

`registry.yaml`의 `sources`가 비어 있으면 빌드가 아무것도 만들지 못한다. 이 태스크가 활성 39개의 매핑을 채워 사이트를 처음으로 살아나게 한다.

앞선 조사에서 확인된 사실: 활성 39개 중 **36개가 ccfddl로, 24개가 ai-deadlines로** 해소되고, **HRI·Humanoids·홀수해 ASRU 3개만** 수동이 필요하다.

**Files:**
- Modify: `data/registry.yaml` (활성 39개의 `display`, `homepage`, `sources`)
- Create: `tests/test_registry_completeness.py`

**Interfaces:**
- Consumes: `scripts.bootstrap_registry.load_registry`, `scripts.build.enabled_field_ids`
- Produces: 없음 (데이터만)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_registry_completeness.py`:

```python
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
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `python -m pytest tests/test_registry_completeness.py -v`
Expected: FAIL — `test_every_active_conference_has_a_homepage`와 `test_every_active_conference_has_a_source_or_is_manual`이 39개 대부분을 orphan으로 보고한다.

- [ ] **Step 3: 소스 id 후보를 조사하는 도우미 실행**

두 저장소의 파일 목록을 받아 registry의 약어와 대조해, 매핑 후보를 출력한다.

```bash
python - <<'PY'
import json, urllib.request, os, yaml, pathlib, re

def tree(repo, prefix, strip):
    url = f"https://api.github.com/repos/{repo}/git/trees/HEAD?recursive=1"
    data = json.load(urllib.request.urlopen(url))
    out = set()
    for node in data["tree"]:
        p = node["path"]
        if p.startswith(prefix) and p.endswith(".yml"):
            out.add(os.path.basename(p)[: -len(strip)])
    return out

hf = tree("huggingface/ai-deadlines", "src/data/conferences/", ".yml")
ccf = tree("ccfddl/ccf-deadlines", "conference/", ".yml")

reg = yaml.safe_load(pathlib.Path("data/registry.yaml").read_text(encoding="utf-8"))
fields = yaml.safe_load(pathlib.Path("data/fields.yaml").read_text(encoding="utf-8"))
active = {f["id"] for f in fields["fields"] if f["enabled"]}

def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())

for e in reg["conferences"]:
    if e["field"] not in active:
        continue
    for part in e["abbr"].split("/"):
        key = norm(part)
        hf_hit = key if key in hf else next((c for c in hf if norm(c) == key), None)
        ccf_hit = key if key in ccf else next((c for c in ccf if norm(c) == key), None)
        print(f"{e['abbr']:14s} {part:12s} hf={hf_hit or '-':16s} ccf={ccf_hit or '-'}")
PY
```

출력에서 `-`로 남는 항목은 이름이 달라 자동 대조가 안 된 것이다. 이미 확인된 별칭은 다음과 같다:

| registry 약어 | ai_deadlines | ccfddl |
|---|---|---|
| `nips` | `neurips` | `nips` |
| `kdd` | `kdd` | `sigkdd` |
| `siggraph` | `siggraph` | `sig` |
| `siggrapha` | (없음) | `siga` |
| `mm` | `acm_mm` | `mm` |
| `bigdataconf` | (없음) | `bigdata` |
| `UbiComp` | (없음) | `ubicomp` |
| `ICME` | (없음) | `icme` |
| `asru/slt` | (없음) | `slt` (ASRU는 수동) |

- [ ] **Step 4: `data/registry.yaml` 채우기**

활성 39개 각각에 `display`(사람이 읽을 약어), `homepage`(연차와 무관한 공식 주소), `sources`를 채운다. 예시:

```yaml
  - abbr: cvpr
    display: CVPR
    full_name: Computer Vision and Pattern Recognition
    grade: 최우수
    ai_specialist: true
    field: CV
    homepage: https://cvpr.thecvf.com/
    members: null
    sources:
      ai_deadlines: cvpr
      ccfddl: cvpr
  - abbr: iccv/eccv
    display: ICCV/ECCV
    full_name: International Conference on Computer Vision / European Conference on Computer Vision
    grade: 최우수
    ai_specialist: true
    field: CV
    homepage: https://www.thecvf.com/
    members:
      - display: ICCV
        sources:
          ai_deadlines: iccv
          ccfddl: iccv
      - display: ECCV
        sources:
          ai_deadlines: eccv
          ccfddl: eccv
    sources:
      ai_deadlines: null
      ccfddl: null
  - abbr: hri
    display: HRI
    full_name: ACM/IEEE International Conference on Human Robot Interaction
    grade: 우수
    ai_specialist: true
    field: Robotics
    homepage: https://humanrobotinteraction.org/
    members: null
    sources:
      ai_deadlines: null
      ccfddl: null
```

비활성 60개는 손대지 않는다 — 나중에 되살릴 때 채우면 된다.

- [ ] **Step 5: 테스트 통과 확인**

Run: `python -m pytest tests/test_registry_completeness.py -v`
Expected: PASS — 5 passed

- [ ] **Step 6: 실제 빌드로 확인**

Run: `python -m scripts.build`
Expected: `학회 3x개, 미확인 x개` — 미확인은 Humanoids와 홀수해 ASRU 정도여야 한다. 그보다 많으면 소스 id 매핑이 잘못된 것이므로 stderr의 미확인 목록을 보고 고친다.

확인: `python -c "import json;d=json.load(open('docs/data/conferences.json'));print(len(d['conferences']),[u['abbr'] for u in d['unresolved']])"`

- [ ] **Step 7: 커밋**

```bash
git add data/registry.yaml docs/data/conferences.json tests/test_registry_completeness.py
git commit -m "$(cat <<'MSG'
활성 39개 학회의 소스 id와 홈페이지 매핑

registry의 sources가 비어 있으면 빌드가 아무것도 만들지 못한다.
이 커밋으로 사이트가 처음으로 데이터를 갖는다.

별칭이 필요한 곳: nips->neurips(HF), kdd->sigkdd(ccfddl),
siggraph->sig, siggrapha->siga, mm->acm_mm(HF), bigdataconf->bigdata.

활성 학회 전부가 출처를 갖는지 테스트로 지킨다. 이 테스트가 깨지면
사이트에 '일정 미확인'으로 뜨는 학회가 생긴다는 뜻이다.
MSG
)"
```

---

## Task 11: 프론트엔드 순수 로직

D-day 계산과 회차 선택은 **브라우저의 현재 날짜**로 해야 한다. 하루 한 번만 빌드해도 표시가 어긋나지 않게 하기 위함이다. 이 로직은 DOM과 무관하므로 별도 모듈로 떼어 `node --test`로 검증한다. 외부 의존성은 없다.

**Files:**
- Create: `docs/lib.js`
- Test: `tests/js/lib.test.mjs`

**Interfaces:**
- Consumes: `docs/data/conferences.json`의 스키마 (Task 9가 정한 형태)
- Produces: `pickEdition(editions, now)`, `dayDelta(isoDate, now)`, `formatDeadline(edition, now)`, `formatDateRange(edition)`, `compareBy(key, direction, now)`, `matchesFilters(conf, filters, now)`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/js/lib.test.mjs`:

```javascript
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  compareBy,
  dayDelta,
  formatDeadline,
  matchesFilters,
  nextDeadline,
  pickEdition,
} from "../../docs/lib.js";

// 로컬 달력 날짜 생성자를 쓴다 - "2026-09-08T00:00:00Z" 같은 UTC 인스턴트
// 문자열은 서부 미국 등에서 로컬로 환산하면 전날(9/7)이 되어, startOfDay가
// now를 로컬 날짜로 읽도록 고친 뒤에는 테스트 자체가 시간대에 따라
// 달라진다. new Date(2026, 8, 8)은 어느 시간대에서 실행해도 "9월 8일"을
// 뜻한다.
const NOW = new Date(2026, 8, 8);

const edition = (year, start, end, primary) => ({
  year,
  date_text: `${start} ~ ${end}`,
  start,
  end,
  place: "Somewhere",
  link: null,
  deadlines: primary ? [{ type: "paper", label: "Paper", date: primary, source: "ccfddl" }] : [],
  primary_deadline: primary ?? null,
  source: "ccfddl",
});

const conf = (over = {}) => ({
  abbr: "EMNLP",
  abbr_group: "emnlp",
  full_name: "Empirical Methods in NLP",
  grade: "최우수",
  ai_specialist: true,
  field: "NLP",
  homepage: "https://example.org/",
  editions: [edition(2026, "2026-10-24", "2026-10-29", "2026-05-25T23:59:59")],
  ...over,
});

test("dayDelta counts whole days to a future date", () => {
  assert.equal(dayDelta("2026-09-18T23:59:59", NOW), 10);
});

test("dayDelta is negative for a passed date", () => {
  assert.equal(dayDelta("2026-05-25T23:59:59", NOW), -106);
});

test("dayDelta returns null for missing input", () => {
  assert.equal(dayDelta(null, NOW), null);
});

test("pickEdition prefers the next upcoming one", () => {
  const editions = [
    edition(2025, "2025-11-05", "2025-11-09", "2025-05-19T23:59:59"),
    edition(2026, "2026-10-24", "2026-10-29", "2026-05-25T23:59:59"),
  ];
  assert.equal(pickEdition(editions, NOW).year, 2026);
});

test("pickEdition falls back to the most recent past one", () => {
  const editions = [edition(2025, "2025-11-05", "2025-11-09", null)];
  assert.equal(pickEdition(editions, NOW).year, 2025);
});

test("pickEdition returns null for an empty list", () => {
  assert.equal(pickEdition([], NOW), null);
});

test("formatDeadline marks a future deadline as upcoming", () => {
  const result = formatDeadline(edition(2027, "2027-01-01", "2027-01-05", "2026-12-01T23:59:59"), NOW);
  assert.equal(result.state, "upcoming");
  assert.equal(result.dday, "D-84");
});

test("formatDeadline marks a passed deadline with a plus sign", () => {
  const result = formatDeadline(edition(2026, "2026-10-24", "2026-10-29", "2026-05-25T23:59:59"), NOW);
  assert.equal(result.state, "past");
  assert.equal(result.dday, "D+106");
});

test("formatDeadline reports unknown when there is no deadline", () => {
  const result = formatDeadline(edition(2026, "2026-10-24", "2026-10-29", null), NOW);
  assert.equal(result.state, "unknown");
  assert.equal(result.text, "미정");
});

test("formatDeadline's text is the deadline's calendar date regardless of the viewer's timezone", () => {
  // "2026-05-25T23:59:59" has no offset. Parsed as local time in, say,
  // America/Los_Angeles, that instant falls on May 26 in UTC — so naively
  // formatting `new Date(iso)` with timeZone: "UTC" would print "May 26"
  // there while printing "May 25" in UTC/Asia-Seoul. The deadline is a
  // published calendar date, not an instant, so the text must not depend on
  // where the browser happens to be.
  const result = formatDeadline(edition(2026, "2026-10-24", "2026-10-29", "2026-05-25T23:59:59"), NOW);
  assert.equal(result.text, "May 25, 2026");
});

test("compareBy date sorts nearest first and pushes past editions down", () => {
  const upcoming = conf({ abbr: "A", editions: [edition(2026, "2026-10-24", "2026-10-29", null)] });
  const past = conf({ abbr: "B", editions: [edition(2026, "2026-01-05", "2026-01-09", null)] });
  const sorted = [past, upcoming].sort(compareBy("date", "asc", NOW));
  assert.deepEqual(sorted.map((c) => c.abbr), ["A", "B"]);
});

test("compareBy grade ranks 최우수 above 우수", () => {
  const top = conf({ abbr: "A", grade: "최우수" });
  const good = conf({ abbr: "B", grade: "우수" });
  const sorted = [good, top].sort(compareBy("grade", "asc", NOW));
  assert.deepEqual(sorted.map((c) => c.abbr), ["A", "B"]);
});

test("matchesFilters passes everything when no filter is set", () => {
  const filters = { fields: new Set(), grades: new Set(), aiOnly: false, hidePast: false, query: "" };
  assert.equal(matchesFilters(conf(), filters, NOW), true);
});

test("matchesFilters restricts by field", () => {
  const filters = { fields: new Set(["CV"]), grades: new Set(), aiOnly: false, hidePast: false, query: "" };
  assert.equal(matchesFilters(conf(), filters, NOW), false);
});

test("matchesFilters searches abbreviation and full name case-insensitively", () => {
  const base = { fields: new Set(), grades: new Set(), aiOnly: false, hidePast: false };
  assert.equal(matchesFilters(conf(), { ...base, query: "emnlp" }, NOW), true);
  assert.equal(matchesFilters(conf(), { ...base, query: "empirical" }, NOW), true);
  assert.equal(matchesFilters(conf(), { ...base, query: "siggraph" }, NOW), false);
});

test("matchesFilters hidePast drops conferences whose deadline has passed", () => {
  const filters = { fields: new Set(), grades: new Set(), aiOnly: false, hidePast: true, query: "" };
  assert.equal(matchesFilters(conf(), filters, NOW), false);
});

test("matchesFilters aiOnly keeps only AI Specialist conferences", () => {
  const filters = { fields: new Set(), grades: new Set(), aiOnly: true, hidePast: false, query: "" };
  assert.equal(matchesFilters(conf({ ai_specialist: false }), filters, NOW), false);
});

// --- nextDeadline: rolling-deadline (다회차) 학회의 대표 마감 선택 ---
//
// UbiComp처럼 연 4회 라운드가 있는 학회는 build가 계산한 primary_deadline이
// "가장 늦은 라운드"라 학회가 끝난 뒤 날짜가 뜬다. 브라우저는 아직 지나지
// 않은 것 중 가장 이른 라운드를 대표로 보여줘야 한다.

const rollingEdition = (rounds, primary) => ({
  year: 2026,
  date_text: "2026-10-11 ~ 2026-10-15",
  start: "2026-10-11",
  end: "2026-10-15",
  place: "Somewhere",
  link: null,
  deadlines: rounds,
  primary_deadline: primary,
  source: "ccfddl",
});

const UBICOMP_ROUNDS = [
  { type: "paper", label: "first round", date: "2026-02-01T23:59:59", source: "ccfddl" },
  { type: "paper", label: "second round", date: "2026-05-01T23:59:59", source: "ccfddl" },
  { type: "paper", label: "third round", date: "2026-08-01T23:59:59", source: "ccfddl" },
  { type: "paper", label: "fourth round", date: "2026-11-01T23:59:59", source: "ccfddl" },
];

test("nextDeadline picks the earliest future round, not the latest", () => {
  // Between the second and third rounds: first/second have passed, third and
  // fourth have not. The earliest future one (third) must win, not the last
  // (fourth) — a naive "just take the last entry" implementation would also
  // return the fourth round here by coincidence unless two rounds are still
  // ahead, which is why this NOW is chosen deliberately.
  const midYear = new Date(2026, 5, 1);
  const result = nextDeadline(rollingEdition(UBICOMP_ROUNDS, "2026-11-01T23:59:59"), midYear);
  assert.equal(result.label, "third round");
  assert.equal(result.date, "2026-08-01T23:59:59");
});

test("nextDeadline falls back to the last round when every round has passed", () => {
  const laterNow = new Date(2026, 11, 1);
  const result = nextDeadline(rollingEdition(UBICOMP_ROUNDS, "2026-11-01T23:59:59"), laterNow);
  assert.equal(result.label, "fourth round");
  assert.equal(result.date, "2026-11-01T23:59:59");
});

test("nextDeadline with an empty deadlines array falls back to primary_deadline", () => {
  const ed = { ...rollingEdition([], null), primary_deadline: "2026-12-01T23:59:59" };
  const result = nextDeadline(ed, NOW);
  assert.equal(result.date, "2026-12-01T23:59:59");
});

test("nextDeadline returns null when there is neither deadlines nor primary_deadline", () => {
  assert.equal(nextDeadline(rollingEdition([], null), NOW), null);
});

test("formatDeadline label matches the chosen rolling-deadline round", () => {
  const result = formatDeadline(rollingEdition(UBICOMP_ROUNDS, "2026-11-01T23:59:59"), NOW);
  assert.equal(result.state, "upcoming");
  assert.equal(result.label, "fourth round");
});

test("compareBy deadline sorts by the next unresolved round, not primary_deadline", () => {
  // At NOW itself only the last UbiComp round is still future, so its next
  // round and its primary_deadline (the latest round) are the same date —
  // a fixture built around NOW couldn't tell a correct implementation from
  // one that reads primary_deadline directly (this is exactly how the first
  // version of this test failed to discriminate). Use midYear instead: two
  // rounds (third, fourth) are still ahead, so "next round" (Aug 1) and
  // "primary_deadline" (Nov 1, the latest round) genuinely disagree.
  //
  // UBICOMP's next round is Aug 1 (before SOON's Sep 20 deadline) — correct
  // sorting by next round puts UBICOMP first. Sorting by primary_deadline
  // instead would compare Nov 1 against Sep 20 and put SOON first — the
  // opposite order — so this fixture fails under the old behavior.
  const midYear = new Date(2026, 5, 1);
  const rolling = conf({
    abbr: "UBICOMP",
    editions: [rollingEdition(UBICOMP_ROUNDS, "2026-11-01T23:59:59")],
  });
  const soon = conf({
    abbr: "SOON",
    editions: [edition(2026, "2026-12-01", "2026-12-05", "2026-09-20T23:59:59")],
  });
  const sorted = [soon, rolling].sort(compareBy("deadline", "asc", midYear));
  assert.deepEqual(sorted.map((c) => c.abbr), ["UBICOMP", "SOON"]);
});

// --- nextDeadline must ignore non-paper deadline types ---
//
// 실제 데이터에는 WACV/SIGGRAPH/ECCV처럼 논문 마감 외에도 등록(registration),
// 리뷰공개(review_release), 통보(notification), camera-ready 같은 타입이
// 같은 deadlines 배열에 섞여 있다. 날짜순으로 "아직 지나지 않은 것"만 고르면
// 이런 행정 일정이 논문 마감보다 먼저 뽑혀 나올 수 있다. build가 primary_deadline을
// 계산할 때 쓰는 것과 같은 타입 집합(paper, submission)만 후보로 삼아야 한다.

const wacvLikeEdition = () => ({
  year: 2026,
  date_text: "2026-01-01 ~ 2026-01-05",
  start: "2026-01-01",
  end: "2026-01-05",
  place: "Somewhere",
  link: null,
  deadlines: [
    { type: "registration", label: "Round 1 Registration", date: "2025-07-11T23:59:59", source: "ccfddl" },
    { type: "submission", label: "Round 1 Submission", date: "2025-07-18T23:59:59", source: "ccfddl" },
    { type: "review_release", label: "Round 1 Reviews Released", date: "2025-09-05T23:59:59", source: "ccfddl" },
    { type: "submission", label: "Round 2 Submission", date: "2025-09-19T23:59:59", source: "ccfddl" },
    { type: "notification", label: "Round 2 Decisions", date: "2026-10-09T23:59:59", source: "ccfddl" },
    { type: "camera_ready", label: "Camera Ready", date: "2026-11-02T23:59:59", source: "ccfddl" },
  ],
  primary_deadline: "2025-09-19T23:59:59",
  source: "ccfddl",
});

test("nextDeadline ignores non-paper types like notification and camera_ready", () => {
  // NOW = 2026-09-08: both submission rounds have passed. The next chronological
  // entry in the raw array is "Round 2 Decisions" (notification), which must NOT
  // be picked — it isn't a paper deadline. Correct behavior falls back to the
  // last paper/submission-type entry, Round 2 Submission.
  const result = nextDeadline(wacvLikeEdition(), NOW);
  assert.equal(result.type, "submission");
  assert.equal(result.label, "Round 2 Submission");
});

// --- nextDeadline must prefer "paper" over an unrelated "submission" ---
//
// ECCV's real deadlines array uses "submission" for tracks that have nothing
// to do with the main paper deadline: Tutorial Proposal Submission, Workshop
// Proposal Submission, and — dated well after the actual paper deadline — AI
// Art Submission. A flat PAPER_TYPES set of {paper, submission} lets that
// later, unrelated AI Art date outrank the real "Paper Submission" (type
// "paper"). When any "paper"-typed deadline exists, "submission"-typed ones
// must not be considered at all.

const eccvLikeEdition = () => ({
  year: 2026,
  date_text: "2026-06-01 ~ 2026-06-05",
  start: "2026-06-01",
  end: "2026-06-05",
  place: "Somewhere",
  link: null,
  deadlines: [
    { type: "submission", label: "Tutorial Proposal Submission", date: "2026-02-15T23:59:59", source: "ccfddl" },
    { type: "submission", label: "Workshop Proposal Submission", date: "2026-02-27T23:59:59", source: "ccfddl" },
    { type: "paper", label: "Paper Submission", date: "2026-03-05T22:00:00", source: "ccfddl" },
    { type: "submission", label: "AI Art Submission", date: "2026-06-14T23:59:59", source: "ccfddl" },
  ],
  primary_deadline: "2026-03-05T22:00:00",
  source: "ccfddl",
});

test("nextDeadline prefers paper over a later, unrelated submission-typed entry", () => {
  // NOW = 2026-09-08: everything above has passed, including the Jun 14 AI
  // Art Submission. A flat type set would fall back to the latest entry
  // overall (AI Art Submission); tiering by paper-first must fall back to
  // the latest *paper*-typed entry instead (there's only one: Paper Submission).
  const result = nextDeadline(eccvLikeEdition(), NOW);
  assert.equal(result.type, "paper");
  assert.equal(result.label, "Paper Submission");
});

test("formatDeadline shows ECCV's Paper Submission, not the later AI Art Submission", () => {
  const result = formatDeadline(eccvLikeEdition(), NOW);
  assert.equal(result.label, "Paper Submission");
});
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `node --test tests/js/`
Expected: FAIL — `Cannot find module .../docs/lib.js`

- [ ] **Step 3: 구현 작성**

`docs/lib.js`:

```javascript
// DOM에 의존하지 않는 순수 로직. node --test로 검증한다.
//
// D-day와 회차 선택을 브라우저의 현재 날짜로 계산하는 것이 핵심이다.
// 빌드가 며칠 밀려도 표시가 어긋나지 않아야 하기 때문이다.

const MS_PER_DAY = 86400000;
const GRADE_RANK = { 최우수: 0, 우수: 1 };

// primary_deadline을 고를 때 "본 논문 마감"으로 인정하는 타입.
// 우선순위가 있는 단계별 폴백이다 - 평평한 집합이 아니다. "submission"은
// ECCV의 튜토리얼/워크숍/AI Art 제출처럼 논문과 무관한 트랙에도 쓰이므로,
// "paper" 타입이 하나라도 있으면 그것만 후보로 삼고 "submission"은 "paper"가
// 전혀 없는 학회(ICASSP, INTERSPEECH 등)에서만 대신 쓴다.
// scripts/models.py의 PAPER_TYPES/SUBMISSION_FALLBACK_TYPES와 반드시 같아야
// 한다 — 여기서 다르게 고르면 build가 계산한 primary_deadline과 브라우저가
// 고르는 다음 회차가 서로 다른 기준으로 어긋나게 된다.
const PAPER_TYPES = ["paper"];
const SUBMISSION_FALLBACK_TYPES = ["submission"];

function paperCandidates(deadlines) {
  const papers = deadlines.filter((d) => PAPER_TYPES.includes(d.type));
  if (papers.length > 0) return papers;
  return deadlines.filter((d) => SUBMISSION_FALLBACK_TYPES.includes(d.type));
}

/**
 * 날짜를 하루 단위 UTC 타임스탬프로 정규화한다.
 *
 * 두 입력의 의미가 다르므로 처리도 달라야 한다. 마감 문자열
 * ("2026-11-01T23:59:59"처럼 오프셋이 없는 것)은 발표된 달력 날짜이므로
 * 앞 10자(연-월-일)만 읽어 UTC로 고정한다 - JS의 기본 파싱에 맡기면
 * 오프셋 없는 시각을 뷰어의 로컬 시간대로 해석해서, 예를 들어 서부 미국
 * 뷰어는 같은 마감을 하루 늦은 날짜로 보게 된다. 반대로 now는 뷰어 자신의
 * '오늘'이므로 로컬 달력 날짜(getFullYear/getMonth/getDate)를 그대로 쓴다.
 */
function startOfDay(value) {
  if (typeof value === "string") {
    const [y, m, d] = value.slice(0, 10).split("-").map(Number);
    return Date.UTC(y, m - 1, d);
  }
  return Date.UTC(value.getFullYear(), value.getMonth(), value.getDate());
}

/** 오늘부터 대상 날짜까지의 일수. 과거면 음수, 입력이 없으면 null. */
export function dayDelta(isoDate, now) {
  if (!isoDate) return null;
  return Math.round((startOfDay(isoDate) - startOfDay(now)) / MS_PER_DAY);
}

/** 종료일이 오늘 이후인 회차 중 가장 이른 것. 없으면 가장 최근에 지난 회차. */
export function pickEdition(editions, now) {
  if (!editions || editions.length === 0) return null;
  const dated = editions.filter((e) => e.end || e.start);
  if (dated.length === 0) return editions[editions.length - 1];

  const today = startOfDay(now);
  const upcoming = dated
    .filter((e) => startOfDay(e.end || e.start) >= today)
    .sort((a, b) => startOfDay(a.start || a.end) - startOfDay(b.start || b.end));
  if (upcoming.length > 0) return upcoming[0];

  return dated
    .slice()
    .sort((a, b) => startOfDay(a.end || a.start) - startOfDay(b.end || b.start))
    .pop();
}

/**
 * 화면에 대표로 보여줄 마감. 아직 지나지 않은 것 중 가장 이른 것을 고른다.
 *
 * 롤링 마감을 쓰는 학회(UbiComp은 연 4회)에서 build가 계산해 둔
 * primary_deadline은 "가장 늦은 라운드"라, 학회가 끝난 뒤 날짜가 대표로 뜬다.
 * 연구자에게 쓸모 있는 값은 다음에 닥칠 마감이므로 브라우저에서 고른다.
 *
 * 후보는 논문 마감 타입(paper, 없으면 submission)으로 한정한다 — 실제
 * 데이터에는 같은 deadlines 배열에 등록/리뷰공개/통보/camera-ready 같은
 * 행정 일정도 섞여 있어서(WACV, SIGGRAPH, ECCV), 타입을 가리지 않고
 * 날짜순으로만 고르면 "다음 마감"이 논문 제출과 무관한 통보일이나
 * camera-ready로 뽑힐 수 있다. paperCandidates가 paper/submission 사이의
 * 우선순위까지 가려낸다 — ECCV의 AI Art Submission처럼 무관한 트랙에도
 * "submission" 타입이 쓰이기 때문이다.
 */
export function nextDeadline(edition, now) {
  const all = paperCandidates(edition?.deadlines ?? []);
  if (all.length === 0) {
    return edition?.primary_deadline
      ? { type: "paper", label: "Paper", date: edition.primary_deadline }
      : null;
  }
  const today = startOfDay(now);
  const sorted = all.slice().sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));
  return sorted.find((d) => startOfDay(d.date) >= today) ?? sorted[sorted.length - 1];
}

/** 제출마감 셀에 표시할 값. */
export function formatDeadline(edition, now) {
  const chosen = nextDeadline(edition, now);
  if (!chosen) return { state: "unknown", text: "미정", dday: "", label: "" };

  const delta = dayDelta(chosen.date, now);
  // startOfDay(chosen.date)는 마감의 달력 날짜를 UTC 자정으로 고정해 두므로,
  // 이걸 다시 UTC로 표시하면 뷰어의 시간대와 무관하게 항상 같은 날짜가 나온다.
  // new Date(chosen.date)를 곧바로 넘기면 오프셋 없는 시각이 로컬로 파싱되어
  // 자정 근처 마감(예: 23:59:59)이 시간대에 따라 하루 밀려 보일 수 있다.
  const text = new Date(startOfDay(chosen.date)).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
  if (delta >= 0) return { state: "upcoming", text, dday: `D-${delta}`, label: chosen.label };
  return { state: "past", text, dday: `D+${Math.abs(delta)}`, label: chosen.label };
}

/** 개최일 표시. 소스가 준 원문이 있으면 그대로 쓴다. */
export function formatDateRange(edition) {
  if (!edition) return "미정";
  if (edition.date_text) return edition.date_text;
  if (!edition.start) return "미정";
  return edition.end && edition.end !== edition.start
    ? `${edition.start} ~ ${edition.end}`
    : edition.start;
}

function sortKey(conf, key, now) {
  const edition = pickEdition(conf.editions, now);
  switch (key) {
    case "abbr":
      return conf.abbr.toLowerCase();
    case "field":
      return conf.field.toLowerCase();
    case "grade":
      return GRADE_RANK[conf.grade] ?? 99;
    case "place":
      return (edition?.place || "").toLowerCase();
    case "deadline": {
      const chosen = nextDeadline(edition, now);
      return chosen ? startOfDay(chosen.date) : Number.POSITIVE_INFINITY;
    }
    case "date":
    default: {
      const when = edition?.start || edition?.end;
      return when ? startOfDay(when) : Number.POSITIVE_INFINITY;
    }
  }
}

/**
 * 정렬 비교자. 이미 지난 회차는 정렬 키와 무관하게 항상 아래로 민다 —
 * 가까운 미래가 맨 위에 오는 것이 이 표의 목적이기 때문이다.
 */
export function compareBy(key, direction, now) {
  const sign = direction === "desc" ? -1 : 1;
  const today = startOfDay(now);

  const isPast = (conf) => {
    const edition = pickEdition(conf.editions, now);
    const end = edition?.end || edition?.start;
    return end ? startOfDay(end) < today : false;
  };

  return (a, b) => {
    const pastA = isPast(a);
    const pastB = isPast(b);
    if (pastA !== pastB) return pastA ? 1 : -1;

    const ka = sortKey(a, key, now);
    const kb = sortKey(b, key, now);
    if (ka < kb) return -1 * sign;
    if (ka > kb) return 1 * sign;
    return a.abbr.localeCompare(b.abbr);
  };
}

/** 필터 통과 여부. filters.fields와 filters.grades는 Set이며 빈 Set은 '전체'를 뜻한다. */
export function matchesFilters(conf, filters, now) {
  if (filters.fields.size > 0 && !filters.fields.has(conf.field)) return false;
  if (filters.grades.size > 0 && !filters.grades.has(conf.grade)) return false;
  if (filters.aiOnly && !conf.ai_specialist) return false;

  if (filters.hidePast) {
    const edition = pickEdition(conf.editions, now);
    const delta = dayDelta(edition?.primary_deadline, now);
    if (delta === null || delta < 0) return false;
  }

  const query = (filters.query || "").trim().toLowerCase();
  if (query) {
    const haystack = `${conf.abbr} ${conf.full_name}`.toLowerCase();
    if (!haystack.includes(query)) return false;
  }
  return true;
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `node --test tests/js/`
Expected: PASS — 26 passed

- [ ] **Step 5: 커밋**

```bash
git add docs/lib.js tests/js/lib.test.mjs
git commit -m "$(cat <<'MSG'
프론트엔드 순수 로직과 node:test 검증 추가

D-day와 회차 선택을 브라우저의 현재 날짜로 계산한다. 빌드가 며칠
밀려도 표시와 정렬이 어긋나지 않게 하기 위함이다.

정렬은 이미 지난 회차를 정렬 키와 무관하게 항상 아래로 민다.
가까운 미래가 맨 위에 오는 것이 이 표의 목적이다.

DOM과 무관한 모듈로 떼어 외부 의존성 없이 node --test로 검증한다.
MSG
)"
```

---

## Task 12: 표 렌더링, 정렬, 필터

`docs/lib.js`의 순수 로직을 DOM에 붙인다. 렌더링·정렬·필터는 같은 렌더 루프를 공유하므로 한 태스크로 묶는다.

**Files:**
- Create: `docs/index.html`
- Create: `docs/app.js`

**Interfaces:**
- Consumes: `docs/lib.js`의 전체 export, `docs/data/conferences.json`
- Produces: `#conference-table tbody`에 학회당 `<tr data-abbr>` 한 행. Task 13이 이 행 아래에 펼침 행을 삽입한다.

- [ ] **Step 1: `docs/index.html` 작성**

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>학회 일정</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header class="page-header">
    <h1>학회 일정</h1>
    <p class="subtitle">
      26년 우수 학회 List 중 AI/HCI 인접 학회
      <span class="generated" id="generated-at"></span>
    </p>
  </header>

  <section class="controls" aria-label="필터">
    <input type="search" id="search" placeholder="학회명 검색" autocomplete="off">

    <div class="filter-group" id="field-filters" role="group" aria-label="분야"></div>

    <div class="filter-group" role="group" aria-label="등급">
      <button type="button" class="chip" data-grade="최우수">최우수</button>
      <button type="button" class="chip" data-grade="우수">우수</button>
    </div>

    <div class="filter-group">
      <button type="button" class="chip" id="ai-only">AI Specialist만</button>
      <button type="button" class="chip" id="hide-past">마감 지난 것 숨기기</button>
      <button type="button" class="chip" id="reset">필터 초기화</button>
    </div>
  </section>

  <p class="count" id="count" aria-live="polite"></p>

  <table id="conference-table">
    <thead>
      <tr>
        <th data-sort="abbr"><button type="button">학회 <span class="arrow"></span></button></th>
        <th data-sort="field"><button type="button">분야 <span class="arrow"></span></button></th>
        <th data-sort="grade"><button type="button">등급 <span class="arrow"></span></button></th>
        <th data-sort="date"><button type="button">개최일 <span class="arrow"></span></button></th>
        <th data-sort="place"><button type="button">장소 <span class="arrow"></span></button></th>
        <th data-sort="deadline"><button type="button">제출마감 <span class="arrow"></span></button></th>
        <th class="links-col">링크</th>
      </tr>
    </thead>
    <tbody></tbody>
  </table>

  <section class="unresolved" id="unresolved" hidden>
    <h2>일정 미확인 <span id="unresolved-count"></span></h2>
    <p class="hint">두 공개 소스와 수기 자료 어디에도 회차 정보가 없는 학회입니다.</p>
    <ul id="unresolved-list"></ul>
  </section>

  <script type="module" src="app.js"></script>
</body>
</html>
```

- [ ] **Step 2: `docs/app.js` 작성**

```javascript
import {
  compareBy,
  formatDateRange,
  formatDeadline,
  matchesFilters,
  pickEdition,
} from "./lib.js";

const STORAGE_KEY = "conference-manager-filters";

const state = {
  data: { conferences: [], fields: [], unresolved: [] },
  sortKey: "date",
  sortDir: "asc",
  filters: {
    fields: new Set(),
    grades: new Set(),
    aiOnly: false,
    hidePast: false,
    query: "",
  },
};

const el = {
  tbody: document.querySelector("#conference-table tbody"),
  fieldFilters: document.querySelector("#field-filters"),
  search: document.querySelector("#search"),
  count: document.querySelector("#count"),
  generatedAt: document.querySelector("#generated-at"),
  unresolved: document.querySelector("#unresolved"),
  unresolvedList: document.querySelector("#unresolved-list"),
  unresolvedCount: document.querySelector("#unresolved-count"),
};

// ---------- 필터 상태의 저장과 복원 ----------
// URL을 우선한다. 링크로 공유된 필터가 내 localStorage에 덮이면 안 되기 때문이다.

function readStateFromUrl() {
  const params = new URLSearchParams(location.search);
  if (!params.toString()) return false;
  state.filters.fields = new Set(params.getAll("field"));
  state.filters.grades = new Set(params.getAll("grade"));
  state.filters.aiOnly = params.get("ai") === "1";
  state.filters.hidePast = params.get("upcoming") === "1";
  state.filters.query = params.get("q") || "";
  state.sortKey = params.get("sort") || "date";
  state.sortDir = params.get("dir") === "desc" ? "desc" : "asc";
  return true;
}

function readStateFromStorage() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    if (!saved) return;
    state.filters.fields = new Set(saved.fields || []);
    state.filters.grades = new Set(saved.grades || []);
    state.filters.aiOnly = Boolean(saved.aiOnly);
    state.filters.hidePast = Boolean(saved.hidePast);
    state.filters.query = saved.query || "";
    state.sortKey = saved.sortKey || "date";
    state.sortDir = saved.sortDir || "asc";
  } catch {
    // 저장된 값이 깨졌으면 기본값으로 시작한다.
  }
}

function persistState() {
  const params = new URLSearchParams();
  state.filters.fields.forEach((f) => params.append("field", f));
  state.filters.grades.forEach((g) => params.append("grade", g));
  if (state.filters.aiOnly) params.set("ai", "1");
  if (state.filters.hidePast) params.set("upcoming", "1");
  if (state.filters.query) params.set("q", state.filters.query);
  if (state.sortKey !== "date") params.set("sort", state.sortKey);
  if (state.sortDir !== "asc") params.set("dir", state.sortDir);

  const qs = params.toString();
  history.replaceState(null, "", qs ? `?${qs}` : location.pathname);

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      fields: [...state.filters.fields],
      grades: [...state.filters.grades],
      aiOnly: state.filters.aiOnly,
      hidePast: state.filters.hidePast,
      query: state.filters.query,
      sortKey: state.sortKey,
      sortDir: state.sortDir,
    }));
  } catch {
    // 사파리 프라이빗 모드 등에서 실패할 수 있다. 기능에는 영향이 없다.
  }
}

// ---------- 렌더링 ----------

function fieldColor(id) {
  return state.data.fields.find((f) => f.id === id)?.color || "#64748b";
}

function fieldLabel(id) {
  return state.data.fields.find((f) => f.id === id)?.label || id;
}

function linkCell(conf, edition) {
  const cell = document.createElement("td");
  cell.className = "links-col";

  const home = document.createElement("a");
  home.textContent = "홈";
  home.className = "link-btn";
  home.title = "학회 공식 홈페이지";
  if (conf.homepage) {
    home.href = conf.homepage;
    home.target = "_blank";
    home.rel = "noopener";
  } else {
    home.classList.add("disabled");
  }
  cell.append(home);

  const cfp = document.createElement("a");
  cfp.textContent = "CFP";
  cfp.className = "link-btn";
  cfp.title = "이 회차의 논문 모집 공고";
  if (edition?.link) {
    cfp.href = edition.link;
    cfp.target = "_blank";
    cfp.rel = "noopener";
  } else {
    cfp.classList.add("disabled");
  }
  cell.append(cfp);
  return cell;
}

function renderRow(conf, now) {
  const edition = pickEdition(conf.editions, now);
  const row = document.createElement("tr");
  row.dataset.abbr = conf.abbr;

  const nameCell = document.createElement("td");
  nameCell.className = "name-col";
  const name = document.createElement(conf.homepage ? "a" : "span");
  name.className = "abbr";
  name.textContent = conf.abbr;
  if (conf.homepage) {
    name.href = conf.homepage;
    name.target = "_blank";
    name.rel = "noopener";
  }
  nameCell.append(name);
  if (conf.ai_specialist) {
    const badge = document.createElement("span");
    badge.className = "badge ai";
    badge.textContent = "AI Specialist";
    nameCell.append(badge);
  }
  const full = document.createElement("div");
  full.className = "full-name";
  full.textContent = conf.full_name;
  nameCell.append(full);
  row.append(nameCell);

  const fieldCell = document.createElement("td");
  const fieldBadge = document.createElement("span");
  fieldBadge.className = "badge field";
  fieldBadge.textContent = fieldLabel(conf.field);
  fieldBadge.style.setProperty("--badge-color", fieldColor(conf.field));
  fieldCell.append(fieldBadge);
  row.append(fieldCell);

  const gradeCell = document.createElement("td");
  const gradeBadge = document.createElement("span");
  gradeBadge.className = `badge grade ${conf.grade === "최우수" ? "top" : "good"}`;
  gradeBadge.textContent = conf.grade;
  gradeCell.append(gradeBadge);
  row.append(gradeCell);

  const dateCell = document.createElement("td");
  dateCell.textContent = formatDateRange(edition);
  row.append(dateCell);

  const placeCell = document.createElement("td");
  placeCell.textContent = edition?.place || "미정";
  row.append(placeCell);

  const deadlineCell = document.createElement("td");
  deadlineCell.className = "deadline-col";
  const info = formatDeadline(edition, now);
  const when = document.createElement("div");
  when.className = `deadline-date ${info.state}`;
  when.textContent = info.text;
  deadlineCell.append(when);
  if (info.dday) {
    const dday = document.createElement("div");
    dday.className = `dday ${info.state}`;
    dday.textContent = info.dday;
    deadlineCell.append(dday);
  }
  row.append(deadlineCell);

  row.append(linkCell(conf, edition));
  return row;
}

function render() {
  const now = new Date();
  const visible = state.data.conferences
    .filter((c) => matchesFilters(c, state.filters, now))
    .sort(compareBy(state.sortKey, state.sortDir, now));

  el.tbody.replaceChildren(...visible.map((c) => renderRow(c, now)));
  el.count.textContent = `${visible.length} / ${state.data.conferences.length}개 표시`;

  document.querySelectorAll("#conference-table th[data-sort]").forEach((th) => {
    const active = th.dataset.sort === state.sortKey;
    th.querySelector(".arrow").textContent = active
      ? (state.sortDir === "asc" ? "▲" : "▼")
      : "⇅";
    th.classList.toggle("active", active);
  });

  document.querySelectorAll("[data-field]").forEach((chip) => {
    chip.classList.toggle("on", state.filters.fields.has(chip.dataset.field));
  });
  document.querySelectorAll("[data-grade]").forEach((chip) => {
    chip.classList.toggle("on", state.filters.grades.has(chip.dataset.grade));
  });
  document.querySelector("#ai-only").classList.toggle("on", state.filters.aiOnly);
  document.querySelector("#hide-past").classList.toggle("on", state.filters.hidePast);

  persistState();
}

function renderStatic() {
  el.generatedAt.textContent = state.data.generated_at
    ? `· ${state.data.generated_at.slice(0, 10)} 갱신`
    : "";

  el.fieldFilters.replaceChildren(...state.data.fields.map((f) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip";
    chip.dataset.field = f.id;
    chip.textContent = f.label;
    chip.style.setProperty("--badge-color", f.color);
    return chip;
  }));

  const unresolved = state.data.unresolved || [];
  if (unresolved.length > 0) {
    el.unresolved.hidden = false;
    el.unresolvedCount.textContent = `${unresolved.length}개`;
    el.unresolvedList.replaceChildren(...unresolved.map((u) => {
      const li = document.createElement("li");
      li.textContent = `${u.abbr} — ${u.reason}`;
      return li;
    }));
  }
}

// ---------- 이벤트 ----------

function toggleInSet(set, value) {
  if (set.has(value)) set.delete(value);
  else set.add(value);
}

function wireEvents() {
  document.querySelectorAll("#conference-table th[data-sort]").forEach((th) => {
    th.querySelector("button").addEventListener("click", () => {
      const key = th.dataset.sort;
      if (state.sortKey === key) {
        state.sortDir = state.sortDir === "asc" ? "desc" : "asc";
      } else {
        state.sortKey = key;
        state.sortDir = "asc";
      }
      render();
    });
  });

  el.fieldFilters.addEventListener("click", (event) => {
    const chip = event.target.closest("[data-field]");
    if (!chip) return;
    toggleInSet(state.filters.fields, chip.dataset.field);
    render();
  });

  document.querySelectorAll("[data-grade]").forEach((chip) => {
    chip.addEventListener("click", () => {
      toggleInSet(state.filters.grades, chip.dataset.grade);
      render();
    });
  });

  document.querySelector("#ai-only").addEventListener("click", () => {
    state.filters.aiOnly = !state.filters.aiOnly;
    render();
  });

  document.querySelector("#hide-past").addEventListener("click", () => {
    state.filters.hidePast = !state.filters.hidePast;
    render();
  });

  document.querySelector("#reset").addEventListener("click", () => {
    state.filters = {
      fields: new Set(), grades: new Set(),
      aiOnly: false, hidePast: false, query: "",
    };
    el.search.value = "";
    render();
  });

  el.search.addEventListener("input", (event) => {
    state.filters.query = event.target.value;
    render();
  });
}

async function main() {
  const response = await fetch("data/conferences.json", { cache: "no-cache" });
  state.data = await response.json();

  if (!readStateFromUrl()) readStateFromStorage();
  el.search.value = state.filters.query;

  renderStatic();
  wireEvents();
  render();
}

main();
```

- [ ] **Step 3: 로컬에서 확인**

```bash
python -m http.server 8000 --directory docs
```

브라우저에서 `http://localhost:8000` 을 열고 다음을 눈으로 확인한다:

1. 표가 그려지고 행 수가 `count`와 맞는다
2. 기본 정렬이 개최일 오름차순이고, **개최일이 지난 학회가 목록 아래쪽에** 있다
3. `학회` 헤더를 누르면 약어순으로 바뀌고 화살표가 `▲`로 바뀐다. 한 번 더 누르면 `▼`
4. 분야 칩을 누르면 그 분야만 남고, 다시 누르면 해제된다
5. `AI Specialist만`, `마감 지난 것 숨기기`가 동작한다
6. 검색창에 `emnlp`와 `empirical`을 각각 넣었을 때 모두 EMNLP가 나온다
7. 필터를 건 상태에서 주소창에 `?field=...` 가 붙고, 그 URL을 새 탭에 붙여넣으면 같은 필터가 재현된다
8. 새로고침하면 필터가 유지된다 (localStorage)
9. `홈` 링크가 학회 홈페이지로, `CFP` 링크가 해당 회차 공고로 열린다. 링크가 없으면 흐리게 비활성

- [ ] **Step 4: 커밋**

```bash
git add docs/index.html docs/app.js
git commit -m "$(cat <<'MSG'
표 렌더링, 정렬, 필터, 검색 추가

lib.js의 순수 로직을 DOM에 붙였다. 렌더링과 정렬, 필터가 같은 렌더
루프를 공유한다.

필터 상태는 URL 쿼리스트링과 localStorage 양쪽에 남기되 복원은 URL을
우선한다. 링크로 공유된 필터가 내 localStorage에 덮이면 안 되기 때문이다.

링크 칸은 홈(연차 무관 공식 주소)과 CFP(해당 회차 공고) 둘로 나눴다.
MSG
)"
```

---

## Task 13: 제출마감 펼치기 토글

기본 상태는 주 마감 하나만 보여주고, 토글을 누르면 그 아래로 전 단계 타임라인이 펼쳐진다. 활성 39개 중 24개가 소스만으로 5~15단계를 갖고 있어 즉시 값어치가 있다.

CFP에서 추출한 단계는 점선 + `자동 추출` 배지로 구분하고, 원문 문장과 출처 링크를 툴팁으로 붙인다. 자동 추출을 한 번의 클릭으로 검증할 수 있어야 하기 때문이다.

**Files:**
- Modify: `docs/lib.js` (`extraDeadlines` 추가)
- Modify: `docs/app.js` (토글 버튼과 펼침 행)
- Modify: `docs/index.html` (전체 펼치기 버튼)
- Modify: `tests/js/lib.test.mjs` (`extraDeadlines` 테스트 추가)

**Interfaces:**
- Consumes: Task 11·12의 전부
- Produces: `extraDeadlines(edition) -> Deadline[]`

- [ ] **Step 1: 실패하는 테스트 추가**

`tests/js/lib.test.mjs` 끝에 덧붙인다:

```javascript
import { extraDeadlines } from "../../docs/lib.js";

const multiStage = {
  year: 2026,
  date_text: "June 3-7, 2026",
  start: "2026-06-03",
  end: "2026-06-07",
  place: "Denver USA",
  link: null,
  primary_deadline: "2025-11-13T23:59:59",
  source: "ai-deadlines",
  deadlines: [
    { type: "abstract", label: "Abstract", date: "2025-11-07T23:59:59", source: "ai-deadlines" },
    { type: "paper", label: "Paper", date: "2025-11-13T23:59:59", source: "ai-deadlines" },
    { type: "notification", label: "Decisions", date: "2026-02-20T23:59:59", source: "ai-deadlines" },
    {
      type: "poster", label: "Posters", date: "2026-04-21T22:00:00", source: "cfp-scrape",
      evidence: { raw_text: "Posters deadline: April 21, 2026", url: "https://x/" },
    },
  ],
};

test("extraDeadlines drops the primary deadline", () => {
  const types = extraDeadlines(multiStage).map((d) => d.type);
  assert.deepEqual(types, ["abstract", "notification", "poster"]);
});

test("extraDeadlines sorts chronologically", () => {
  const dates = extraDeadlines(multiStage).map((d) => d.date);
  assert.deepEqual(dates, [...dates].sort());
});

test("extraDeadlines is empty when only the primary deadline exists", () => {
  const single = { ...multiStage, deadlines: [multiStage.deadlines[1]] };
  assert.deepEqual(extraDeadlines(single), []);
});

test("extraDeadlines handles an edition with no deadlines", () => {
  assert.deepEqual(extraDeadlines({ deadlines: [], primary_deadline: null }), []);
  assert.deepEqual(extraDeadlines(null), []);
});
```

- [ ] **Step 2: 테스트가 실패하는지 확인**

Run: `node --test tests/js/`
Expected: FAIL — `extraDeadlines is not a function` 또는 import 오류

- [ ] **Step 3: `docs/lib.js`에 추가**

```javascript
/**
 * 주 마감을 뺀 나머지 단계를 시간순으로 돌려준다.
 * 토글을 펼쳤을 때 보여줄 목록이다.
 */
export function extraDeadlines(edition) {
  if (!edition || !edition.deadlines) return [];
  const primary = edition.primary_deadline;
  let primarySkipped = false;
  return edition.deadlines
    .filter((d) => {
      // 주 마감과 시각이 같은 항목 하나만 제외한다.
      // 같은 시각의 단계가 둘이면 나머지는 보여줘야 한다.
      if (!primarySkipped && d.date === primary) {
        primarySkipped = true;
        return false;
      }
      return true;
    })
    .slice()
    .sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `node --test tests/js/`
Expected: PASS — 20 passed

- [ ] **Step 5: `docs/index.html`에 전체 펼치기 버튼 추가**

`<p class="count" id="count" aria-live="polite"></p>` 바로 앞에 넣는다:

```html
    <div class="filter-group">
      <button type="button" class="chip" id="expand-all">전체 펼치기</button>
    </div>
```

- [ ] **Step 6: `docs/app.js` 수정**

`import` 문에 `extraDeadlines`를 추가하고, `state`에 펼침 상태를 담는다:

```javascript
import {
  compareBy,
  extraDeadlines,
  formatDateRange,
  formatDeadline,
  matchesFilters,
  pickEdition,
} from "./lib.js";
```

`state` 객체에 한 줄 추가한다 (펼침은 일회성이라 저장하지 않는다):

```javascript
  expanded: new Set(),
```

`renderRow`의 `deadlineCell` 블록 끝, `row.append(deadlineCell);` 바로 앞에 토글 버튼을 넣는다:

```javascript
  const extras = extraDeadlines(edition);
  if (extras.length > 0) {
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "stage-toggle";
    toggle.dataset.toggle = conf.abbr;
    const open = state.expanded.has(conf.abbr);
    toggle.setAttribute("aria-expanded", String(open));
    toggle.textContent = `${open ? "▾" : "▸"} +${extras.length}`;
    toggle.title = "부가 일정 보기";
    deadlineCell.append(toggle);
  }
```

펼침 행을 만드는 함수를 `renderRow` 아래에 추가한다:

```javascript
function renderStageRow(conf, edition, now) {
  const row = document.createElement("tr");
  row.className = "stage-row";

  const cell = document.createElement("td");
  cell.colSpan = 7;

  const list = document.createElement("ol");
  list.className = "stage-list";

  for (const stage of extraDeadlines(edition)) {
    const item = document.createElement("li");
    const scraped = stage.source === "cfp-scrape";
    item.className = scraped ? "stage scraped" : "stage";

    const label = document.createElement("span");
    label.className = "stage-label";
    label.textContent = stage.label;
    item.append(label);

    const when = document.createElement("span");
    when.className = "stage-date";
    when.textContent = new Date(stage.date).toLocaleDateString("en-US", {
      year: "numeric", month: "short", day: "numeric", timeZone: "UTC",
    });
    item.append(when);

    const info = formatDeadline({ primary_deadline: stage.date }, now);
    const dday = document.createElement("span");
    dday.className = `stage-dday ${info.state}`;
    dday.textContent = info.dday;
    item.append(dday);

    if (scraped) {
      // 자동 추출은 사람이 한 번의 클릭으로 검증할 수 있어야 한다.
      const badge = document.createElement(stage.evidence?.url ? "a" : "span");
      badge.className = "badge scraped-badge";
      badge.textContent = "자동 추출";
      badge.title = stage.evidence?.raw_text
        ? `CFP 원문: "${stage.evidence.raw_text}"`
        : "CFP 페이지에서 자동 추출한 일정";
      if (stage.evidence?.url) {
        badge.href = stage.evidence.url;
        badge.target = "_blank";
        badge.rel = "noopener";
      }
      item.append(badge);
    }
    list.append(item);
  }

  cell.append(list);
  row.append(cell);
  return row;
}
```

`render()`의 표 갱신 부분을 펼침 행까지 그리도록 바꾼다. 기존 `el.tbody.replaceChildren(...)` 한 줄을 아래로 교체한다:

```javascript
  const rows = [];
  for (const conf of visible) {
    rows.push(renderRow(conf, now));
    if (state.expanded.has(conf.abbr)) {
      const edition = pickEdition(conf.editions, now);
      if (extraDeadlines(edition).length > 0) {
        rows.push(renderStageRow(conf, edition, now));
      }
    }
  }
  el.tbody.replaceChildren(...rows);
```

`wireEvents()`에 토글 처리와 전체 펼치기를 추가한다:

```javascript
  el.tbody.addEventListener("click", (event) => {
    const toggle = event.target.closest("[data-toggle]");
    if (!toggle) return;
    const abbr = toggle.dataset.toggle;
    if (state.expanded.has(abbr)) state.expanded.delete(abbr);
    else state.expanded.add(abbr);
    render();
  });

  document.querySelector("#expand-all").addEventListener("click", (event) => {
    const now = new Date();
    const anyOpen = state.expanded.size > 0;
    state.expanded.clear();
    if (!anyOpen) {
      for (const conf of state.data.conferences) {
        if (extraDeadlines(pickEdition(conf.editions, now)).length > 0) {
          state.expanded.add(conf.abbr);
        }
      }
    }
    event.target.textContent = anyOpen ? "전체 펼치기" : "전체 접기";
    render();
  });
```

- [ ] **Step 7: 로컬에서 확인**

```bash
python -m http.server 8000 --directory docs
```

1. 제출마감 칸 오른쪽에 `▸ +6` 같은 버튼이 보인다. 부가 일정이 없는 학회에는 버튼이 없다
2. 누르면 아래로 타임라인이 펼쳐지고 버튼이 `▾`로 바뀐다
3. 각 단계에 개별 D-day가 붙는다
4. `전체 펼치기`를 누르면 전부 펼쳐지고 버튼 글자가 `전체 접기`로 바뀐다
5. 필터를 바꿔도 펼친 학회의 펼침 상태가 유지된다

CFP 추출 데이터는 Task 16 전까지 없으므로 `자동 추출` 배지는 그때 확인한다.

- [ ] **Step 8: 커밋**

```bash
git add docs/lib.js docs/app.js docs/index.html tests/js/lib.test.mjs
git commit -m "$(cat <<'MSG'
제출마감 펼치기 토글 추가

기본은 주 마감 하나만 보여주고 토글로 전 단계 타임라인을 펼친다.
활성 39개 중 24개가 소스만으로 5~15단계를 갖고 있다.

CFP 자동 추출 단계는 점선 + 배지로 구분하고, 원문 문장을 툴팁에,
출처 링크를 배지에 붙였다. 자동 추출을 한 번의 클릭으로 검증할 수
있어야 하기 때문이다.

펼침 상태는 일회성이라 URL이나 localStorage에 저장하지 않는다.
MSG
)"
```

---

## Task 14: 스타일

레퍼런스와 같은 다크 톤. 뷰어의 테마를 따르되 배경과 글자색을 명시적으로 칠한다. 모바일에서는 표 대신 카드로 전환한다.

**Files:**
- Create: `docs/style.css`

**Interfaces:**
- Consumes: Task 12·13이 만든 클래스 이름 전부
- Produces: 없음

- [ ] **Step 1: `docs/style.css` 작성**

```css
/* 색은 전부 :root에 토큰으로 정의하고, 다크에서 값만 바꾼다.
   미디어 쿼리 안에만 정의된 색을 만들지 않는다. */
:root {
  color-scheme: light dark;
  --bg: #ffffff;
  --surface: #f8fafc;
  --surface-alt: #f1f5f9;
  --border: #e2e8f0;
  --text: #0f172a;
  --text-dim: #64748b;
  --accent: #2563eb;
  --danger: #dc2626;
  --gold: #b45309;
  --silver: #64748b;
  --radius: 6px;
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0b0f19;
    --surface: #121826;
    --surface-alt: #1a2233;
    --border: #263041;
    --text: #e2e8f0;
    --text-dim: #7c8aa0;
    --accent: #60a5fa;
    --danger: #f87171;
    --gold: #fbbf24;
    --silver: #94a3b8;
  }
}

* { box-sizing: border-box; }

body {
  margin: 0;
  padding: 24px 16px 64px;
  background: var(--bg);
  color: var(--text);
  font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI",
        "Apple SD Gothic Neo", "Noto Sans KR", sans-serif;
}

.page-header { max-width: 1280px; margin: 0 auto 16px; }
.page-header h1 { margin: 0 0 4px; font-size: 22px; }
.subtitle { margin: 0; color: var(--text-dim); font-size: 13px; }
.generated { margin-left: 4px; }

.controls {
  max-width: 1280px;
  margin: 0 auto 12px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  align-items: center;
}

.filter-group { display: flex; flex-wrap: wrap; gap: 6px; }

#search {
  padding: 7px 12px;
  min-width: 200px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  font: inherit;
}
#search:focus { outline: 2px solid var(--accent); outline-offset: -1px; }

.chip {
  padding: 5px 11px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 999px;
  color: var(--text-dim);
  font: inherit;
  font-size: 13px;
  cursor: pointer;
}
.chip:hover { border-color: var(--accent); color: var(--text); }
.chip.on {
  background: var(--badge-color, var(--accent));
  border-color: transparent;
  color: #fff;
}

.count {
  max-width: 1280px;
  margin: 0 auto 8px;
  color: var(--text-dim);
  font-size: 12px;
}

table {
  max-width: 1280px;
  margin: 0 auto;
  width: 100%;
  border-collapse: collapse;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}

th, td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
}

thead th {
  background: var(--surface-alt);
  font-weight: 600;
  font-size: 12px;
  color: var(--text-dim);
  white-space: nowrap;
}
thead th button {
  all: unset;
  cursor: pointer;
  display: inline-flex;
  gap: 4px;
  align-items: center;
}
thead th.active { color: var(--text); }
.arrow { font-size: 10px; opacity: 0.7; }

tbody tr:hover { background: var(--surface-alt); }
tbody tr:last-child td { border-bottom: none; }

.abbr { font-weight: 600; color: var(--text); text-decoration: none; }
a.abbr:hover { color: var(--accent); text-decoration: underline; }
.full-name { margin-top: 2px; color: var(--text-dim); font-size: 12px; }

.badge {
  display: inline-block;
  padding: 1px 7px;
  border-radius: 999px;
  font-size: 11px;
  line-height: 1.6;
  white-space: nowrap;
}
.badge.field {
  background: color-mix(in srgb, var(--badge-color) 20%, transparent);
  color: var(--badge-color);
  border: 1px solid color-mix(in srgb, var(--badge-color) 40%, transparent);
}
.badge.ai {
  margin-left: 6px;
  background: color-mix(in srgb, var(--accent) 18%, transparent);
  color: var(--accent);
}
.badge.grade.top { background: color-mix(in srgb, var(--gold) 18%, transparent); color: var(--gold); }
.badge.grade.good { background: color-mix(in srgb, var(--silver) 18%, transparent); color: var(--silver); }

.deadline-col { white-space: nowrap; }
.deadline-date.past { text-decoration: line-through; color: var(--text-dim); }
.dday { margin-top: 2px; font-size: 11px; }
.dday.upcoming { color: var(--accent); font-weight: 600; }
.dday.past { color: var(--text-dim); }
.deadline-date.unknown { color: var(--text-dim); }

.stage-toggle {
  margin-top: 4px;
  padding: 1px 7px;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 999px;
  color: var(--text-dim);
  font: inherit;
  font-size: 11px;
  cursor: pointer;
}
.stage-toggle:hover { border-color: var(--accent); color: var(--accent); }

.stage-row td { background: var(--surface-alt); padding-top: 4px; }
.stage-list { margin: 0; padding: 0 0 0 4px; list-style: none; }
.stage {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  padding: 5px 8px;
  border-left: 2px solid var(--border);
  font-size: 12px;
}
/* 자동 추출은 실선이 아닌 점선으로 구분한다. */
.stage.scraped { border-left-style: dashed; border-left-color: var(--accent); }
.stage-label { min-width: 180px; color: var(--text); }
.stage-date { color: var(--text-dim); }
.stage-dday.upcoming { color: var(--accent); }
.stage-dday.past { color: var(--text-dim); text-decoration: line-through; }
.scraped-badge {
  background: color-mix(in srgb, var(--accent) 15%, transparent);
  color: var(--accent);
  text-decoration: none;
  cursor: help;
}

.links-col { white-space: nowrap; }
.link-btn {
  display: inline-block;
  margin-right: 4px;
  padding: 2px 8px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text-dim);
  font-size: 11px;
  text-decoration: none;
}
.link-btn:hover { border-color: var(--accent); color: var(--accent); }
.link-btn.disabled { opacity: 0.35; pointer-events: none; }

.unresolved {
  max-width: 1280px;
  margin: 24px auto 0;
  padding: 12px 16px;
  background: var(--surface);
  border: 1px dashed var(--border);
  border-radius: var(--radius);
}
.unresolved h2 { margin: 0 0 4px; font-size: 14px; }
.unresolved .hint { margin: 0 0 8px; color: var(--text-dim); font-size: 12px; }
.unresolved ul { margin: 0; padding-left: 18px; color: var(--text-dim); font-size: 13px; }

/* 좁은 화면에서는 표를 카드로 바꾼다. 가로 스크롤은 만들지 않는다. */
@media (max-width: 760px) {
  thead { display: none; }
  table, tbody, tr, td { display: block; width: 100%; }
  tr {
    margin-bottom: 8px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
  }
  td { border-bottom: none; padding: 6px 12px; }
  td:first-child { padding-top: 12px; }
  td:last-child { padding-bottom: 12px; }
  .stage-row td { padding: 8px 12px; }
  .stage-label { min-width: auto; }
}
```

- [ ] **Step 2: 확인**

```bash
python -m http.server 8000 --directory docs
```

1. 다크 모드에서 배경·글자·배지가 모두 읽힌다. OS 테마를 라이트로 바꿔도 마찬가지다
2. 지난 마감에 취소선이 그어지고 회색으로 흐려진다
3. 등급 배지가 최우수는 금색, 우수는 은색이다
4. 브라우저 창을 760px 이하로 줄이면 카드 레이아웃으로 바뀌고 **가로 스크롤이 생기지 않는다**
5. 펼침 행에서 자동 추출 항목의 왼쪽 선이 점선이다 (Task 16 이후 확인 가능)

- [ ] **Step 3: 커밋**

```bash
git add docs/style.css
git commit -m "$(cat <<'MSG'
스타일 추가: 다크 테마, 배지, 반응형 카드 레이아웃

색은 전부 :root 토큰으로 정의하고 다크에서 값만 바꾼다.
미디어 쿼리 안에만 정의된 색을 만들지 않아 한쪽 테마에서
투명해지는 일이 없게 했다.

760px 이하에서는 표를 카드로 전환한다. 가로 스크롤은 만들지 않는다.
MSG
)"
```

---

## Task 15: GitHub Actions와 Pages 배포

매일 06:00 KST에 두 공개 소스를 다시 읽어 `conferences.json`을 갱신한다. **시크릿이 전혀 필요 없다** — 공개 raw 파일만 읽기 때문이다.

**Files:**
- Create: `.github/workflows/build.yml`
- Create: `README.md`

**Interfaces:**
- Consumes: Task 7·9의 CLI (`python -m scripts.validate_scraped`, `python -m scripts.build`)
- Produces: 없음

- [ ] **Step 1: `.github/workflows/build.yml` 작성**

```yaml
name: build

on:
  schedule:
    # 21:00 UTC = 06:00 KST
    - cron: "0 21 * * *"
  workflow_dispatch:
  push:
    branches: [master, main]

permissions:
  contents: write

concurrency:
  group: build
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - uses: actions/setup-node@v4
        with:
          node-version: "20"

      - name: 의존성 설치
        run: pip install -e ".[dev,bootstrap]"

      - name: Python 테스트
        run: python -m pytest -q

      - name: JS 테스트
        run: node --test tests/js/

      # 커밋된 CFP 데이터가 여전히 게이트를 통과하는지 다시 확인한다.
      # 네트워크를 타지 않으므로 비용이 없고, 손으로 편집된 값이
      # 게이트를 우회하는 것을 막는다.
      - name: CFP 데이터 재검증
        run: python -m scripts.validate_scraped

      - name: 빌드
        run: python -m scripts.build

      - name: 변경분 커밋
        run: |
          if git diff --quiet -- docs/data/conferences.json data/scraped; then
            echo "변경 없음"
            exit 0
          fi
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add docs/data/conferences.json data/scraped
          git commit -m "학회 일정 자동 갱신 ($(date -u +%Y-%m-%d))"
          git push
```

`concurrency`를 둔 이유: 예약 실행과 push 트리거가 겹치면 두 잡이 같은 파일을 밀어 push 충돌이 난다. `cancel-in-progress: false`라 앞 잡이 끝날 때까지 기다린다.

- [ ] **Step 2: `README.md` 작성**

```markdown
# 학회 일정 트래커

26년 우수 학회 List 중 AI/HCI 인접 39개 학회의 개최일과 논문 제출마감을 추적합니다.

## 데이터 출처

- [huggingface/ai-deadlines](https://github.com/huggingface/ai-deadlines) — 다단계 마감, 개최지
- [ccfddl/ccf-deadlines](https://github.com/ccfddl/ccf-deadlines) — CS 전반
- `data/manual.yaml` — 위 두 소스가 다루지 않는 학회 (HRI, Humanoids, 홀수해 ASRU)
- `data/scraped/` — 학회 CFP 페이지에서 추출한 poster/LBW/workshop 일정

병합 우선순위는 `manual` > `ai-deadlines` > `ccfddl` > `cfp-scrape`이며,
회차 단위로 소스를 통째 고릅니다. `cfp-scrape`는 상위 소스에 없는 단계만 채웁니다.

## 로컬에서 돌리기

```bash
pip install -e ".[dev]"
python -m scripts.build
python -m http.server 8000 --directory docs
```

## 엑셀 갱신

엑셀은 빌드 입력이 아닙니다. 학회 목록의 원본은 `data/registry.yaml`이고,
엑셀은 이를 처음 만들 때만 씁니다.

```bash
pip install -e ".[bootstrap]"
python scripts/bootstrap_registry.py --diff   # 차이만 확인
```

`homepage`와 소스 id 매핑은 손으로 붙인 값이라 자동으로 덮어쓰지 않습니다.

## 분야 되살리기

`data/fields.yaml`에서 해당 분야의 `enabled`를 `true`로 바꾸고 다시 빌드하면 됩니다.
`data/registry.yaml`에는 99개 전부가 들어 있어 엑셀이 없어도 됩니다.

## 테스트

```bash
python -m pytest       # 파이썬
node --test tests/js/  # 프론트엔드 순수 로직
```

테스트는 네트워크를 타지 않습니다.
```

- [ ] **Step 3: 로컬에서 워크플로 단계를 그대로 실행해 확인**

```bash
pip install -e ".[dev,bootstrap]"
python -m pytest -q
node --test tests/js/
python -m scripts.validate_scraped
python -m scripts.build
```

Expected: 전부 통과하고 마지막에 `학회 3x개, 미확인 x개`

- [ ] **Step 4: 커밋하고 푸시**

```bash
git add .github/workflows/build.yml README.md
git commit -m "$(cat <<'MSG'
GitHub Actions 일일 빌드와 README 추가

공개 raw 파일만 읽으므로 시크릿이 필요 없다.

concurrency 그룹을 둬 예약 실행과 push 트리거가 겹칠 때
같은 파일을 밀어 push 충돌이 나는 것을 막는다.

빌드 전에 validate_scraped를 다시 돌린다. 네트워크를 타지 않으므로
비용이 없고, 손으로 편집된 CFP 값이 게이트를 우회하는 것을 막는다.
MSG
)"
git push -u origin master
```

- [ ] **Step 5: GitHub Pages 켜기**

저장소 **Settings → Pages** 에서:
- Source: `Deploy from a branch`
- Branch: `master`, 폴더: `/docs`
- Save

1~2분 뒤 `https://<사용자명>.github.io/ConferenceTracker/` 에서 확인한다.

- [ ] **Step 6: Actions 수동 실행으로 검증**

저장소 **Actions → build → Run workflow** 를 눌러 한 번 돌린다.
녹색으로 끝나고, `conferences.json`이 바뀌었다면 자동 커밋이 하나 올라와야 한다.

---

## Task 16: CFP 추출 커맨드와 시험 실행

poster/LBW/workshop 마감은 두 공개 소스에 사실상 없다(전체 데이터에서 각각 10건·11건, 우리 39개 중 ECCV·SIGGRAPH 둘뿐). CFP 페이지에서 직접 추출한다.

**39개 일괄로 가지 않는다.** CFP 페이지에 이런 일정이 실제로 적혀 있는지는 학회마다 다르고 돌려보기 전에는 알 수 없다. 5개로 먼저 시험하고 통과율을 본 뒤 확대를 결정한다.

**Files:**
- Create: `.claude/commands/scrape-cfp.md`
- Create: `data/scraped/.gitkeep`
- Modify: `data/scraped/raw/*` (시험 실행 산출물)

**Interfaces:**
- Consumes: `scripts/validate_scraped.py`의 입력 형식 (`data/scraped/raw/<abbr>.json` + `<abbr>.txt`)
- Produces: `data/scraped/<abbr>.yaml`

- [ ] **Step 1: `.claude/commands/scrape-cfp.md` 작성**

```markdown
---
description: 학회 CFP 페이지에서 poster/LBW/workshop 마감을 추출해 data/scraped/에 기록한다
---

학회 CFP 페이지를 읽어 부가 트랙 마감일을 추출한다.

## 대상

인자로 학회 약어가 주어지면 그것만 처리한다. 없으면 아래 5개를 처리한다:
`chi`, `uist`, `siggraph`, `mm`, `ismar`

대상 학회의 링크는 `data/registry.yaml`의 `homepage`와
`docs/data/conferences.json`의 해당 회차 `link`에서 찾는다.

## 절차

학회마다 다음을 수행한다.

1. `data/scraped/.cache.json`에서 그 학회의 `etag` / `last_modified`를 읽는다.
   있으면 조건부 요청을 보내고, 304가 오면 **건너뛴다**.
2. CFP 페이지를 가져온다. `robots.txt`가 금지하면 건너뛰고 그 사실을 기록한다.
   요청 간격은 최소 1초를 둔다.
3. 페이지 본문 텍스트를 `data/scraped/raw/<abbr>.txt`에 **그대로** 저장한다.
   검증 단계가 원문 대조에 쓰므로 임의로 줄이거나 다듬지 않는다.
4. 본문에서 부가 트랙 마감을 찾아 `data/scraped/raw/<abbr>.json`에 기록한다.
5. `data/scraped/.cache.json`을 갱신한다.

전부 끝나면 `python -m scripts.validate_scraped`를 실행하고 결과를 보고한다.

## 출력 형식

`data/scraped/raw/<abbr>.json`:

```json
{
  "abbr": "chi",
  "editions": [
    {
      "year": 2026,
      "conference_start": "2026-04-13",
      "items": [
        {
          "type": "lbw",
          "label": "Late-Breaking Work",
          "date": "2026-02-12 23:59:59",
          "confidence": "high",
          "raw_text": "Late-Breaking Work submission deadline: February 12, 2026",
          "url": "https://chi2026.acm.org/lbw/"
        }
      ]
    }
  ]
}
```

`conference_start`는 `docs/data/conferences.json`의 해당 회차 `start`를 그대로 쓴다.

## 규칙

- `type`은 다음 중 하나만 쓴다:
  `poster`, `lbw`, `workshop`, `demo`, `tutorial`, `doctoral_consortium`, `other`
- **`raw_text`는 그 날짜가 적혀 있던 문장을 페이지에서 글자 그대로 옮긴다.**
  요약하거나 바꿔 쓰지 않는다. 검증 단계가 이 문자열이 실제 페이지 본문에
  있는지 대조하며, 없으면 그 항목을 버린다.
- 본 논문(full paper) 마감은 추출하지 않는다. 이미 공개 소스가 갖고 있고,
  덮어쓰지 않는 것이 원칙이다.
- 날짜를 확신할 수 없으면 `confidence`를 `low`로 둔다. 검증에서 자동으로 걸러진다.
  **추측해서 채우지 않는다.** 빈손으로 돌아오는 것이 틀린 날짜보다 낫다.
- 페이지에 부가 트랙 일정이 없으면 `items`를 빈 배열로 둔다. 그것이 정상적인 결과다.
```

- [ ] **Step 2: 디렉터리 준비**

```bash
mkdir -p data/scraped/raw
touch data/scraped/.gitkeep
```

- [ ] **Step 3: 5개 학회로 시험 실행**

Claude Code에서 실행한다:

```
/scrape-cfp
```

- [ ] **Step 4: 결과 판단**

`python -m scripts.validate_scraped`의 출력에서 채택/탈락 건수를 본다.

| 상황 | 판단 |
|---|---|
| 채택이 여럿이고 탈락이 적다 | 확대한다. Step 5로 |
| 탈락 사유가 대부분 `raw_text_not_in_page` | 추출 프롬프트 문제다. `raw_text`를 그대로 옮기라는 규칙을 강화하고 다시 시험한다 |
| 채택이 0이고 `items`가 애초에 비어 있다 | 그 학회 CFP에 부가 일정이 없는 것이다. **자동화를 포기하고** `data/manual.yaml`로 돌린다 |

채택된 항목은 `data/scraped/<abbr>.yaml`을 직접 열어 날짜가 실제 CFP와 맞는지 **눈으로 한 번 확인한다.** 이 검토가 이 단계의 핵심이다.

- [ ] **Step 5: 확대 여부 결정**

시험이 쓸 만하면 `.claude/commands/scrape-cfp.md`의 기본 대상 목록을 활성 39개로 넓힌다. 학회별로 CFP 구조가 달라 통과율이 들쭉날쭉하므로, 한 번에 넓히기보다 분야별로 나눠 확인하는 편이 낫다.

- [ ] **Step 6: 빌드에 반영하고 확인**

```bash
python -m scripts.build
python -m http.server 8000 --directory docs
```

펼침 토글을 열어 `자동 추출` 배지가 점선 항목에 붙는지, 배지에 마우스를 올렸을 때 CFP 원문 문장이 뜨는지, 클릭하면 출처 페이지가 열리는지 확인한다.

- [ ] **Step 7: 커밋**

```bash
git add .claude/commands/scrape-cfp.md data/scraped docs/data/conferences.json
git commit -m "$(cat <<'MSG'
CFP 추출 커맨드와 5개 학회 시험 실행

poster/LBW/workshop 마감은 두 공개 소스에 사실상 없어 CFP 페이지에서
직접 추출한다. 추출 절차와 스키마를 슬래시 커맨드에 고정해
예약 실행과 수동 실행이 같은 규칙을 따르게 했다.

39개 일괄이 아니라 5개로 먼저 시험한다. CFP에 부가 일정이 실제로
적혀 있는지는 학회마다 달라 돌려보기 전에는 알 수 없다.
통과율이 낮은 학회는 억지로 자동화하지 않고 manual.yaml로 돌린다.
MSG
)"
```

- [ ] **Step 8: 주 1회 예약 실행 등록**

Claude Code에서:

```
/schedule
```

- 주기: 매주 일요일 오전
- 내용: `/scrape-cfp` 실행 후 변경분을 커밋하고 푸시
- 푸시가 `build.yml`을 깨우므로 사이트는 자동으로 따라온다

예약이 실패하거나 돌지 않아도 빌드는 커밋된 `data/scraped/`를 그대로 써서 정상 동작한다. 이 단계는 전적으로 선택적이다.
