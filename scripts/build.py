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
