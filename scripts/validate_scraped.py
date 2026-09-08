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
    page_text = page_path.read_text(encoding="utf-8") if page_path.exists() else ""

    editions = []
    all_rejected: list[dict] = []
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
        document, rejected = _validate_one(raw_json, today)
        total_rejected.extend(rejected)
        out_path = SCRAPED_DIR / f"{raw_json.stem}.yaml"
        if document is None:
            out_path.unlink(missing_ok=True)
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
