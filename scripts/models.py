"""소스에 무관한 공용 데이터 모델.

모든 소스 어댑터는 외부 스키마를 이 형태로 정규화해 내놓는다.
날짜는 전부 절대 시각으로만 담는다 - D-day 같은 상대 표현은
브라우저가 계산하므로 여기서 만들지 않는다.
"""

from dataclasses import dataclass, field as dc_field
from datetime import date, datetime

# primary_deadline을 고를 때 "본 논문 마감"으로 인정하는 타입.
PAPER_TYPES = ("paper", "submission")


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
        """본 논문 마감. 없으면 가장 늦은 마감으로 대체한다."""
        if not self.deadlines:
            return None
        papers = [d for d in self.deadlines if d.type in PAPER_TYPES]
        if papers:
            return max(d.date for d in papers)
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
