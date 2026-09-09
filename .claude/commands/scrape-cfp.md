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
