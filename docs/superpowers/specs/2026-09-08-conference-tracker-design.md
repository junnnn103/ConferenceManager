# 학회 일정 트래커 설계

작성일: 2026-09-08

## 1. 목적

학술연수 대상 학회의 **개최일과 논문 제출마감을 한 페이지에서 추적**한다.
회사의 두 기준 문서(우수 학회 등급, AI Specialist 인정 여부)를 함께 표기해,
"이 학회에 내면 인정받나"와 "언제까지 내야 하나"를 한 번에 확인한다.

## 2. 범위

### 대상
`26년 우수 학회 List.xlsx`의 99개 학회 중 **AI/HCI 인접 39개**.

| 분야 | 수 | 학회 |
|---|---|---|
| ML | 6 | NeurIPS, ICLR, ICML, AAAI, IJCAI, MLSys |
| CV | 4 | CVPR, ICCV/ECCV, WACV, ICIP |
| NLP | 3 | ACL, EMNLP, NAACL |
| Speech | 3 | ICASSP, INTERSPEECH, ASRU/SLT |
| Robotics | 6 | ICRA, IROS, CoRL, RSS, HRI, Humanoids |
| DM/IR | 7 | KDD, SIGIR, CIKM, WSDM, RecSys, BigData, WWW |
| HCI | 4 | CHI, UIST, IUI, UbiComp |
| Graphics | 2 | SIGGRAPH, SIGGRAPH Asia |
| Multimedia | 2 | ACM MM, ICME |
| AR/VR | 2 | IEEE VR, ISMAR |

등급 분포: 최우수 21 / 우수 18.
`ICCV/ECCV`와 `ASRU/SLT`는 엑셀에서 한 행으로 묶여 있으므로 1개 항목으로 다룬다.

### 제외
- **저널** 전체 (`26년 우수 저널 List.xlsx` 미사용)
- **분야**: DB, Security, SE/PL, OS/HPC, Architecture, Network, Info Theory,
  Medical/Bio, 회로/반도체, RF/전력, 디스플레이/광학, 소재/화학/물리, 열/에너지, 식품
- **컬럼**: 레퍼런스에 있던 `Proc.` / `Poster` / `Expert`.
  판정 기준 원본 자료가 없어 채울 수 없다. 자료 확보 후 재논의한다.

제외 분야의 학회 데이터는 **빌드 결과에서 아예 빠진다**. 되살리려면
`data/fields.yaml`에서 해당 분야의 `enabled`를 켜고 다시 빌드한다.

## 3. 데이터 소스

| 소스 | 형태 | 커버리지(39개 기준) | 비고 |
|---|---|---|---|
| `huggingface/ai-deadlines` | `src/data/conferences/<id>.yml` | 높음 | 2027년치까지, 다단계 마감·venue·tags 제공 |
| `ccfddl/ccf-deadlines` | `conference/<cat>/<id>.yml` | 높음 | CS 전반 354개 |
| `data/manual.yaml` | 수기 | HRI, Humanoids, ASRU(홀수해) | 두 소스 모두 미커버 |
| CFP 페이지 파싱 | 학회 홈페이지 → LLM 추출 | poster/LBW/workshop 등 부가 트랙 | §9 참조 |

**`paperswithcode/ai-deadlines`(aideadlin.es)는 사용하지 않는다.** 데이터가 2024년에
멈춰 있고 2026년 항목이 0건이다. `huggingface/ai-deadlines`가 살아있는 후계 저장소다.

### 병합 규칙

한 학회의 **한 회차(연도)**에 대해 **소스를 통째로 하나 고른다**. 필드 단위로 섞지 않는다 —
소스 간 값이 어긋났을 때 어느 값이 어디서 왔는지 추적이 불가능해지기 때문이다.

우선순위: `manual` > `ai-deadlines` > `ccfddl` > `cfp-scrape`

**CFP 파싱 결과는 절대 상위 소스를 덮어쓰지 않는다.** 상위 소스에 없는 단계(주로
poster/LBW/workshop)만 채운다. 상위 소스와 같은 단계에 대해 값이 다르면 덮어쓰지 않고
빌드 경고로 남긴다 — 이 불일치는 버리지 말고 봐야 할 신호다 (CFP가 갱신됐는데 소스가
아직 못 따라온 경우일 수 있다).

`manual`이 최우선인 이유는 사람이 명시적으로 써넣은 값이기 때문이다. 다만 manual 항목은
반드시 `year`를 지정하며, 그 연도에만 적용된다. 상위 소스가 같은 연도를 이미 제공하는데
manual 항목이 존재하면 빌드가 경고를 낸다 (오래된 수동 데이터가 신선한 소스를 조용히
덮어쓰는 것을 막기 위함).

선택된 소스명은 각 항목에 `source` 필드로 남기고 UI에서 툴팁으로 노출한다.

## 4. 회차 선택

기준 시각은 **빌드 시각이 아니라 브라우저의 현재 날짜**다. 하루 한 번만 빌드해도
D-day가 어긋나지 않아야 하므로, JSON에는 절대 시각만 담고 D-day는 클라이언트에서 계산한다.

빌드 시점의 회차 선택 로직:

1. 종료일이 오늘 이후인 회차 중 **개최일이 가장 이른 것** → `status: upcoming`
2. 없으면 **가장 최근에 지난 회차** → `status: past`, UI에서 흐리게 + `(전년: …)` 표기
3. 회차 데이터 자체가 없으면 → `status: unknown`, 하단 "일정 미확인" 섹션으로

빌드는 후보 회차를 최대 2개(직전 1 + 차기 1) `editions` 배열에 담아, 날짜가 경계를
넘어가도 클라이언트가 올바른 회차를 고를 수 있게 한다. 클라이언트는 배열에서 위 규칙을
다시 적용해 표시할 회차 하나를 고른다.

### 결합 행 (`ICCV/ECCV`, `ASRU/SLT`)

엑셀에서 한 행으로 묶인 이 둘은 **격년으로 번갈아 열리는 학회 쌍**이다
(ICCV 홀수해 / ECCV 짝수해, ASRU 홀수해 / SLT 짝수해). 하나의 항목으로 취급하되,
양쪽 id를 모두 조회한 뒤 **차기 회차가 더 이른 쪽**을 그 시점의 대표로 삼는다.
표시되는 약어는 실제로 선택된 학회명(`ECCV`, `SLT` 등)을 쓰고,
`abbr_group` 필드에 원래 결합 표기(`ICCV/ECCV`)를 남겨 엑셀과 대조 가능하게 한다.

이 규칙 덕분에 2026년 기준 `ASRU/SLT` 행은 ccfddl의 `slt`로 해결되며,
manual이 필요한 것은 홀수해의 ASRU뿐이다.

## 5. 출력 데이터 모델

`docs/data/conferences.json`:

```json
{
  "generated_at": "2026-09-08T21:00:00+09:00",
  "fields": [{"id": "CV", "label": "CV", "color": "#3b82f6"}],
  "conferences": [
    {
      "abbr": "CVPR",
      "abbr_group": "cvpr",
      "full_name": "Computer Vision and Pattern Recognition",
      "grade": "최우수",
      "ai_specialist": true,
      "field": "CV",
      "homepage": "https://cvpr.thecvf.com/",
      "editions": [
        {
          "year": 2026,
          "date_text": "June 3-7, 2026",
          "start": "2026-06-03",
          "end": "2026-06-07",
          "place": "Denver USA",
          "link": "https://cvpr.thecvf.com/Conferences/2026/CallForPapers",
          "deadlines": [
            {"type": "abstract", "label": "Abstract", "date": "2025-11-07T23:59:59",
             "timezone": "AoE", "source": "ai-deadlines"},
            {"type": "paper", "label": "Paper", "date": "2025-11-13T23:59:59",
             "timezone": "AoE", "source": "ai-deadlines"},
            {"type": "poster", "label": "Posters", "date": "2026-04-21T22:00:00",
             "source": "cfp-scrape",
             "evidence": {
               "raw_text": "Posters submission deadline: April 21, 2026",
               "url": "https://s2026.siggraph.org/posters/"
             }}
          ],
          "primary_deadline": "2025-11-13T23:59:59",
          "source": "ai-deadlines"
        }
      ]
    }
  ],
  "unresolved": [{"abbr": "HRI", "reason": "no source data for 2026+"}]
}
```

`primary_deadline`은 `type: paper`를 우선하고, 없으면 가장 늦은 마감을 쓴다.
레퍼런스처럼 `(ARR)` 같은 부가 설명이 필요하면 `deadlines[].label`에 담는다.

`deadlines[].source`는 `manual` / `ai-deadlines` / `ccfddl` / `cfp-scrape` 중 하나다.
`cfp-scrape`인 항목만 `evidence`(원문 문장 + 출처 URL)를 갖고, UI가 이를 툴팁으로 노출한다.

`place` 정규화: ai-deadlines는 `city` / `country` / `venue`를 따로 주고 ccfddl은
`place` 한 줄을 준다. `"{city} {country}"` 형태로 통일하고, 둘 중 하나가 비면 있는 쪽만
쓴다. ccfddl의 `place`는 쉼표를 공백으로 바꿔 그대로 쓴다 (`Bari, Italy` → `Bari Italy`).
레퍼런스와 같은 표기다.

## 6. UI

### 컬럼

| 학회 ⇅ | 분야 ⇅ | 등급 ⇅ | 개최일 ▲ | 장소 ⇅ | 제출마감 ⇅ | 링크 |

- **학회** — 약어(굵게) + full name(작게). 약어 클릭 시 공식 홈페이지로 이동.
  AI Specialist 해당 시 배지
- **분야** — 색상 배지 (레퍼런스1 스타일)
- **등급** — 최우수(금) / 우수(은) 배지. 정렬 시 최우수 > 우수
- **개최일** — `Oct 24-29, 2026`. **기본 정렬 키**
- **장소** — `Budapest Hungary`
- **제출마감** — 날짜 + 아래 D-day.
  - 미래: `D-42`, 강조색
  - 과거: 취소선 + `D+106`, 회색
  - 미상: `미정` + `(전년: Oct 4 2025)` 회색 소자
- **링크** — 아이콘 두 개. `홈` = 학회 공식 홈페이지(`registry.yaml`의 `homepage`,
  연차와 무관하게 안정적), `CFP` = 해당 회차의 논문 모집 공고(소스가 준 `link`).
  둘 다 새 탭으로 연다. CFP 링크가 없는 회차는 아이콘을 흐리게 비활성 처리

### 제출마감 펼치기 토글

기본 상태에서 제출마감 셀은 **주 마감(full paper) 하나**와 그 D-day만 보여준다.
셀 오른쪽에 `▸ +6` 형태의 토글 버튼을 둔다 — 숫자는 숨겨진 부가 일정의 개수다.
부가 일정이 없는 학회는 버튼을 렌더링하지 않는다.

토글을 누르면 그 행 아래로 타임라인이 펼쳐지고, 각 단계마다 라벨·날짜·개별 D-day를 찍는다.
단계는 두 종류로 시각적으로 구분한다:

| 종류 | 예시 | 표시 |
|---|---|---|
| **소스 제공** | Abstract, Supplementary, Review Release, Rebuttal, Notification, Camera-ready | 실선 마커 |
| **CFP 자동 추출** | Poster, LBW, Workshop, Demo, Tutorial | 점선 마커 + `자동 추출` 배지 |

`자동 추출` 배지에 마우스를 올리면 **그 날짜를 뽑아낸 CFP 원문 문장**과 해당 페이지 링크가
뜬다. 사람이 한 번의 클릭으로 검증할 수 있어야 하기 때문이다 (§7 참조).

39개 중 24개는 소스만으로도 5~15단계를 갖고 있어 토글이 즉시 값어치를 한다.
헤더에 `전체 펼치기 / 접기` 버튼을 둔다. 펼침 상태는 저장하지 않는다 (일회성).

### 기본 정렬

**오늘 날짜 기준으로 개최일이 가까운 순(오름차순)이 기본값**이다.
이미 지난 회차(`status: past`)는 정렬 키와 무관하게 목록 **하단으로 밀어** 배치한다 —
가까운 미래가 항상 맨 위에 오게 하기 위함이다. 그 아래에 "일정 미확인" 섹션이 온다.

정렬은 클라이언트에서 브라우저의 현재 날짜로 매번 다시 계산하므로,
빌드가 며칠 밀려도 순서가 어긋나지 않는다.

### 필터 · 정렬

- 분야 멀티선택 토글
- 등급 토글 (최우수 / 우수)
- `AI Specialist만` 토글
- `마감 지난 것 숨기기` 토글
- 텍스트 검색 (약어 + full name)
- 모든 컬럼 헤더 클릭으로 정렬 토글
- 필터 상태를 URL 쿼리스트링에 반영해 공유 가능하게 하고, localStorage에도 저장

### 스타일

다크 테마 기본, 레퍼런스와 동일 톤. 모바일에서는 표 대신 카드 레이아웃으로 전환한다.
`prefers-color-scheme` 대응.

일정을 못 구한 학회는 숨기지 않고 하단 "일정 미확인 N개" 섹션에 모아 보여준다.

## 7. CFP 페이지 자동 파싱

poster/LBW/workshop 마감은 ccfddl과 ai-deadlines 어디에도 사실상 없다
(전체 데이터에서 각각 10건·11건, 우리 39개 중 ECCV·SIGGRAPH 둘뿐).
따라서 학회 CFP 페이지를 직접 읽어 추출한다.

**이 방식의 고유 위험은 LLM이 그럴듯한 날짜를 지어내고, 그것이 사실처럼 표시되는 것이다.**
아래 설계는 전부 그 위험을 막기 위한 것이다.

### 추출과 검증의 분리 (설계의 핵심)

추출은 모델이 하고, **채택 여부는 코드가 정한다.** 두 단계를 파일로 갈라놓는다:

```
[추출]  CFP 페이지 → data/scraped/raw/<abbr>.json
          Claude Code가 수행. 모델이 바뀌든 사람이 손으로 채우든 상관없다

[검증]  scripts/validate_scraped.py
          항상 코드가 실행. 게이트를 통과한 항목만 남긴다
        → data/scraped/<abbr>.yaml
```

이 분리 덕분에 **추출 주체를 바꿔도 안전장치가 약해지지 않는다.**
나중에 API 호출이나 다른 모델로 갈아타고 싶으면 추출 단계만 교체하면 된다.

### 추출 단계

**Claude Code가 주 1회 예약 실행으로 수행한다.** 별도 API 키나 종량 과금이 없고,
기존 Claude Code 플랜 안에서 동작한다.

1. 각 학회의 CFP 링크(회차 `link`, 없으면 `homepage`)를 가져온다
2. `robots.txt`를 확인하고, 초당 1요청으로 제한한다
3. `ETag` / `Last-Modified`를 `data/scraped/.cache.json`에 기록해
   **변하지 않은 페이지는 건너뛴다** — 첫 실행 이후에는 대부분 스킵된다
4. 페이지 본문 텍스트를 `data/scraped/raw/<abbr>.txt`에 그대로 저장한다.
   검증 단계가 원문 대조에 쓰므로 반드시 남겨야 한다
5. 추출 결과를 `data/scraped/raw/<abbr>.json`에 기록한다

각 추출 항목이 반드시 포함해야 하는 필드:

| 필드 | 설명 |
|---|---|
| `track` | `poster` / `lbw` / `workshop` / `demo` / `tutorial` / `doctoral_consortium` / `other` |
| `date` | ISO 8601 |
| `raw_text` | **그 날짜가 적혀 있던 원문 문장을 글자 그대로** |
| `confidence` | `high` / `medium` / `low` |

추출 절차와 스키마는 `.claude/commands/scrape-cfp.md`에 프롬프트로 고정해,
예약 실행과 수동 실행이 같은 규칙을 따르게 한다.

### 검증 게이트 (환각 방지의 핵심)

`scripts/validate_scraped.py`가 아래를 **전부** 검사한다.
하나라도 실패하면 그 항목은 버리고, 사유를 리포트에 남긴다.

1. **원문 대조** — `raw_text`가 `raw/<abbr>.txt`의 **부분 문자열이어야 한다**
   (공백 정규화 후 비교). 모델이 문장을 지어내면 여기서 걸린다.
   가장 강력하고 가장 싼 방어선이다
2. **날짜 범위** — 마감은 개최 시작일보다 앞서야 하고, 개최일 기준 18개월 이내여야 한다
3. **`confidence: low` 제외** — 채택하지 않고 로그에만 남긴다
4. **날짜가 원문 안에 있는가** — `raw_text`가 페이지의 부분 문자열인 것만으로는 부족하다.
   그 문장이 **주장된 날짜를 실제로 언급**해야 한다. 이것이 없으면 페이지에 실재하는
   아무 문장이나(`"Contact the organizers for more information."`) 날조된 날짜를 뒷받침한다.
   월+일 또는 ISO 형태를 요구하고 연도는 요구하지 않는다 — CFP는 `"February 12"`만 쓰고
   연도를 제목에 두는 일이 흔하기 때문이다. 숫자 앞뒤에 단어 경계가 필요하다:
   없으면 `"2012 February"`의 연도 꼬리가 2월 12일을 뒷받침한다
5. **상위 소스 미침범** — 이미 authoritative 소스가 가진 단계는 덮어쓰지 않는다 (§3)

이 스크립트는 **네트워크도 모델도 쓰지 않는다.** 순수 함수라 테스트하기 쉽고,
CI에서 매 빌드마다 다시 돌려 커밋된 데이터가 여전히 게이트를 통과하는지 확인한다.

### 사람의 검토

`data/scraped/`를 통째로 커밋하기 때문에 **모든 변경이 git diff로 드러난다.**
날짜가 바뀌거나 새로 생기면 커밋에서 눈에 띄고, 이상하면 되돌릴 수 있다.
자동 추출을 쓰되 감사 가능성을 잃지 않기 위한 장치다.

UI에서도 자동 추출 항목은 실선이 아닌 점선 + `자동 추출` 배지로 구분되며,
원문 문장과 출처 링크가 툴팁으로 붙는다 (§6).

### 단계적 도입

CFP 페이지에 poster/LBW 일정이 실제로 적혀 있는지는 학회마다 다르고,
돌려보기 전에는 알 수 없다. 따라서 한 번에 39개로 가지 않는다.

1. **1차** — CHI, UIST, SIGGRAPH, ACM MM, ISMAR 5개로 시험 실행.
   게이트 통과율과 실제로 잡힌 트랙을 확인한다
2. **판단** — 통과율이 낮거나 원하는 트랙이 안 잡히면, 그 학회는 `manual.yaml`로 돌린다.
   자동화가 안 되는 것을 억지로 자동화하지 않는다
3. **확대** — 시험 결과가 쓸 만하면 나머지로 넓힌다

### 실패 시 동작

- 예약 실행이 안 돌거나 실패해도 빌드는 **커밋된 `data/scraped/`를 그대로 쓴다**
- 개별 페이지 fetch/추출 실패 → 그 학회만 이전 결과 유지, 나머지 진행
- **채택이 0건이어도 기존 `<abbr>.yaml`을 삭제하지 않는다.** 일시적 실패(페이지 본문
  파일 누락 등)로 전부 탈락하는 일이 있으므로, 삭제는 사람이 하는 행위여야 한다
- **파일 하나의 파싱 실패가 배치를 멈추지 않는다.** 상한 하나가 다른 모든 학회의 발행을
  막지 않도록 파일 단위로 예외를 격리한다
- 즉 이 단계는 **전적으로 선택적**이며, 죽어도 사이트는 멀쩡하다

## 8. 저장소 구조

```
ConferenceTracker/
├─ 학술연수 학회 리스트/          # 원본 엑셀 — gitignore, 로컬에만 존재
├─ data/                         # 커밋됨. 여기가 빌드의 입력 전부
│  ├─ registry.yaml             # 학회 99개: 약어·full name·등급·AI Specialist·분야
│  │                            #   ·homepage·소스 id 매핑
│  ├─ fields.yaml               # 분야 정의(라벨·색상) + enabled 플래그
│  ├─ manual.yaml               # 수기 일정 (HRI, Humanoids, 홀수해 ASRU)
│  └─ scraped/                  # 커밋됨. git diff로 변경을 사람이 검토
│     ├─ raw/<abbr>.txt         #   가져온 페이지 본문 (원문 대조용)
│     ├─ raw/<abbr>.json        #   추출 결과 (검증 전)
│     ├─ .cache.json            #   ETag / Last-Modified
│     └─ <abbr>.yaml            #   게이트 통과분 (빌드가 읽는 것)
├─ .claude/commands/
│  └─ scrape-cfp.md             # 추출 절차·스키마 프롬프트. 예약/수동 공용
├─ scripts/
│  ├─ bootstrap_registry.py     # 엑셀 2개 → registry.yaml (수동 실행, 빌드 아님)
│  ├─ validate_scraped.py       # raw/ → scraped/*.yaml. 네트워크·모델 안 씀
│  ├─ build.py                  # 엔트리포인트
│  ├─ merge.py                  # 소스 병합 + 회차 선택
│  └─ sources/
│     ├─ aideadlines.py
│     ├─ ccfddl.py
│     ├─ manual.py
│     └─ scraped.py
├─ tests/
│  ├─ fixtures/                 # 고정 YAML 픽스처 (네트워크 없음)
│  └─ test_*.py
├─ docs/                        # GitHub Pages 루트
│  ├─ index.html
│  ├─ app.js
│  ├─ style.css
│  └─ data/conferences.json     # 빌드 산출물, 커밋됨
└─ .github/workflows/build.yml
```

### 엑셀은 빌드 입력이 아니다

엑셀은 **1회 부트스트랩 입력**이다. `scripts/bootstrap_registry.py`가 두 엑셀을 읽어
`data/registry.yaml`을 생성하고, 그 뒤로 빌드는 `data/`만 본다. 따라서 엑셀 원본을
`.gitignore`에 넣어도 CI 빌드가 정상 동작한다.

`registry.yaml`에는 **99개 전부**를 담는다 (비활성 분야 포함). 나중에 제외했던 분야를
되살릴 때 엑셀 없이 `fields.yaml`의 `enabled`만 켜면 되게 하기 위함이다.

내년 엑셀이 나오면 같은 스크립트를 `--diff` 모드로 돌려 신규/삭제/등급변경 학회를
출력하고, 사람이 확인한 뒤 `registry.yaml`에 반영한다. 자동 덮어쓰기는 하지 않는다 —
`homepage`와 소스 id 매핑은 손으로 붙인 값이라 날아가면 안 되기 때문이다.

## 9. 빌드 파이프라인

`scripts/build.py`:

1. `data/registry.yaml` 로드 → 99개 레지스트리
2. `fields.yaml`의 `enabled` 적용 → 비활성 분야 제거 → 39개
3. registry의 소스 id로 각 소스 조회, 회차 목록 수집
   (`data/scraped/`는 네트워크 없이 로컬 파일로 읽는다 — 스크레이핑은 별도 단계)
4. 병합(§3) + 회차 선택(§4)
5. `docs/data/conferences.json` 기록
6. 미해결 항목을 stderr와 GitHub Actions job summary에 리포트

빌드 전에 `validate_scraped.py`를 다시 돌려, 커밋된 CFP 데이터가 여전히 게이트를
통과하는지 확인한다. 네트워크를 타지 않으므로 비용이 없고, 손으로 편집된 값이
게이트를 우회하는 것을 막는다.

### 실패 처리

- 한 소스 fetch 실패 → 해당 소스만 건너뛰고 나머지로 빌드, 경고
- 두 소스 모두 실패 → 기존 `conferences.json`을 그대로 두고 `exit 1`.
  사이트는 어제 데이터로 계속 뜨고, Actions만 빨간불이 된다
- 개별 학회 파싱 실패 → 그 학회만 `unresolved`로 보내고 빌드는 계속

## 10. 테스트

pytest. **네트워크를 타지 않는다** — 소스 응답은 `tests/fixtures/`의 고정 YAML로 대체한다.

- `registry.yaml` 무결성: 99개 항목, 약어 중복 없음, 등급이 `{최우수, 우수}`에 속함
- 분야 매핑: 모든 학회가 `fields.yaml`에 정의된 분야를 정확히 하나 가짐
- 소스 매핑 완전성: 활성 39개 전부가 소스 id 또는 manual 항목을 가짐
- 부트스트랩: 엑셀 픽스처 → 기대하는 `registry.yaml`. 픽스처는 원본이 아니라
  같은 시트 구조를 가진 **합성 xlsx 몇 행**을 `tests/fixtures/`에 커밋한다
  (원본 엑셀은 gitignore 대상이므로 CI에서 쓸 수 없다)
- 기본 정렬: 기준 날짜를 주입해 upcoming이 past보다 위, upcoming 내부는 개최일 오름차순
- 소스 파서: 픽스처 → 정규화된 회차 목록
- 병합 우선순위: manual > ai-deadlines > ccfddl, 그리고 중복 시 경고 발생
- 회차 선택: 기준 날짜를 주입해 upcoming / past / unknown 세 분기를 각각 검증
- 출력 JSON이 §5 스키마를 만족
- **CFP 검증 게이트** — 이 프로젝트에서 가장 중요한 테스트다:
  - `raw_text`가 페이지 텍스트에 없으면 항목이 버려진다 (환각 시나리오)
  - 개최일 이후 마감, 18개월을 넘는 마감이 버려진다
  - `confidence: low`가 채택되지 않는다
  - 상위 소스가 이미 가진 단계를 `cfp-scrape`가 덮어쓰지 못한다
  - LLM 응답은 고정 픽스처로 대체한다 — 테스트는 API를 호출하지 않는다

## 11. 배포

`.github/workflows/build.yml`

**`build.yml`** (GitHub Actions) — 매일
- 트리거: `schedule` (`0 21 * * *` UTC = 06:00 KST) + `workflow_dispatch` + `push`
- 단계: pytest → `validate_scraped.py` → `build.py` →
  `conferences.json`이 변경됐으면 커밋 & 푸시
- **시크릿이 전혀 필요 없다.** 네트워크는 ccfddl·ai-deadlines의 공개 raw 파일만 탄다

**CFP 추출** — 주 1회, Claude Code 예약 실행
- GitHub Actions가 아니라 Claude Code의 `schedule`(routine)로 돌린다
- `.claude/commands/scrape-cfp.md`를 실행해 `data/scraped/`를 갱신하고 커밋한다
- 푸시가 `build.yml`을 깨우므로 사이트가 자동으로 따라온다
- 별도 API 키·종량 과금 없음. 예약이 안 돌아도 빌드는 기존 캐시로 정상 동작한다

Pages는 `docs/` 폴더에서 서빙한다.

## 12. 미결 사항

- ~~저장소 공개 범위~~ — **결정: public 저장소 + GitHub Pages**.
  일반인은 "AI Specialist"가 무엇인지 알 수 없으므로 노출 위험이 낮다고 판단.
  단 다음은 `.gitignore`로 제외한다:
  - `학술연수 학회 리스트/` (엑셀 원본)
  - `학술연수 파견자 처우기준/`, `학술연수 파견중 학회 참가 기준/` (사내 규정 사진, 빌드에 불필요)
- **`Proc.` / `Poster` / `Expert` 컬럼** — 판정 기준 자료 확보 후 재논의.
- **CFP 추출 대상 학회** — 1차 5개(CHI, UIST, SIGGRAPH, ACM MM, ISMAR) 시험 결과를 보고
  확대 여부를 정한다 (§7). 통과율이 낮은 학회는 자동화를 포기하고 `manual.yaml`로 돌린다.
- **추출 주체** — 현재는 Claude Code 예약 실행. 추출/검증이 분리돼 있으므로,
  나중에 완전 무인 CI가 필요해지면 추출 단계만 API 호출로 교체하면 된다.
- **제외된 60개 학회** — 현재 빌드에서 제외. 필요해지면 `fields.yaml`에서 되살린다.
