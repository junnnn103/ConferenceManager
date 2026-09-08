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

**`paperswithcode/ai-deadlines`(aideadlin.es)는 사용하지 않는다.** 데이터가 2024년에
멈춰 있고 2026년 항목이 0건이다. `huggingface/ai-deadlines`가 살아있는 후계 저장소다.

### 병합 규칙

한 학회의 **한 회차(연도)**에 대해 **소스를 통째로 하나 고른다**. 필드 단위로 섞지 않는다 —
소스 간 값이 어긋났을 때 어느 값이 어디서 왔는지 추적이 불가능해지기 때문이다.

우선순위: `manual` > `ai-deadlines` > `ccfddl`

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
      "editions": [
        {
          "year": 2026,
          "date_text": "June 3-7, 2026",
          "start": "2026-06-03",
          "end": "2026-06-07",
          "place": "Denver USA",
          "link": "https://cvpr.thecvf.com/Conferences/2026/CallForPapers",
          "deadlines": [
            {"type": "abstract", "label": "Abstract", "date": "2025-11-07T23:59:59", "timezone": "AoE"},
            {"type": "paper",    "label": "Paper",    "date": "2025-11-13T23:59:59", "timezone": "AoE"}
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

`place` 정규화: ai-deadlines는 `city` / `country` / `venue`를 따로 주고 ccfddl은
`place` 한 줄을 준다. `"{city} {country}"` 형태로 통일하고, 둘 중 하나가 비면 있는 쪽만
쓴다. ccfddl의 `place`는 쉼표를 공백으로 바꿔 그대로 쓴다 (`Bari, Italy` → `Bari Italy`).
레퍼런스와 같은 표기다.

## 6. UI

### 컬럼

| 학회 ⇅ | 분야 ⇅ | 등급 ⇅ | 개최일 ▲ | 장소 ⇅ | 제출마감 ⇅ |

- **학회** — 약어(굵게) + full name(작게). 클릭 시 공식 CFP 링크. AI Specialist 해당 시 배지
- **분야** — 색상 배지 (레퍼런스1 스타일)
- **등급** — 최우수(금) / 우수(은) 배지. 정렬 시 최우수 > 우수
- **개최일** — `Oct 24-29, 2026`. 기본 정렬 키(오름차순)
- **장소** — `Budapest Hungary`
- **제출마감** — 날짜 + 아래 D-day.
  - 미래: `D-42`, 강조색
  - 과거: 취소선 + `D+106`, 회색
  - 미상: `미정` + `(전년: Oct 4 2025)` 회색 소자

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

## 7. 저장소 구조

```
ConferenceManager/
├─ 학술연수 학회 리스트/          # 원본 엑셀 (빌드 입력, 그대로 유지)
├─ data/
│  ├─ fields.yaml               # 분야 정의 + 학회→분야 매핑 + enabled 플래그
│  ├─ aliases.yaml              # 약어 → ai-deadlines id / ccfddl id
│  └─ manual.yaml               # 수기 일정 (HRI, ASRU, Humanoids)
├─ scripts/
│  ├─ build.py                  # 엔트리포인트
│  ├─ registry.py               # 엑셀 2개 → 학회 레지스트리
│  ├─ merge.py                  # 소스 병합 + 회차 선택
│  └─ sources/
│     ├─ aideadlines.py
│     ├─ ccfddl.py
│     └─ manual.py
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

**엑셀을 빌드마다 직접 읽는다.** 엑셀이 학회 목록·등급의 원본이고,
`data/*.yaml`은 매핑과 수동 데이터만 갖는다. 내년 엑셀로 교체하면 사이트가 따라온다.
매칭되지 않는 새 약어는 빌드 경고로 뜬다.

## 8. 빌드 파이프라인

`scripts/build.py`:

1. 엑셀 2개 로드 → 99개 레지스트리 (약어, full name, 등급, AI Specialist 여부)
2. `fields.yaml` 적용 → 비활성 분야 제거 → 39개
3. `aliases.yaml`로 소스 조회, 각 소스에서 회차 목록 수집
4. 병합(§3) + 회차 선택(§4)
5. `docs/data/conferences.json` 기록
6. 미해결 항목을 stderr와 GitHub Actions job summary에 리포트

### 실패 처리

- 한 소스 fetch 실패 → 해당 소스만 건너뛰고 나머지로 빌드, 경고
- 두 소스 모두 실패 → 기존 `conferences.json`을 그대로 두고 `exit 1`.
  사이트는 어제 데이터로 계속 뜨고, Actions만 빨간불이 된다
- 개별 학회 파싱 실패 → 그 학회만 `unresolved`로 보내고 빌드는 계속

## 9. 테스트

pytest. **네트워크를 타지 않는다** — 소스 응답은 `tests/fixtures/`의 고정 YAML로 대체한다.

- 엑셀 파서: 99행을 읽고, 등급 값이 `{최우수, 우수}`에 속함
- 분야 매핑: 활성 학회 전부가 정확히 하나의 분야를 가짐 (누락·중복 없음)
- alias 완전성: 활성 39개 전부가 소스 매핑 또는 manual 항목을 가짐
- 소스 파서: 픽스처 → 정규화된 회차 목록
- 병합 우선순위: manual > ai-deadlines > ccfddl, 그리고 중복 시 경고 발생
- 회차 선택: 기준 날짜를 주입해 upcoming / past / unknown 세 분기를 각각 검증
- 출력 JSON이 §5 스키마를 만족

## 10. 배포

`.github/workflows/build.yml`

- 트리거: `schedule` (`0 21 * * *` UTC = 06:00 KST) + `workflow_dispatch` + `push`
- 단계: pytest → build → `conferences.json`이 변경됐으면 커밋 & 푸시
- Pages는 `docs/` 폴더에서 서빙

## 11. 미결 사항

- **저장소 공개 범위** — GitHub Pages는 public 저장소면 URL을 아는 누구나 접근한다.
  회사 내부 기준(우수 학회 등급, AI Specialist 인정 여부)이 사이트에 노출되므로,
  public / private+Pages(유료) / 로컬 전용 중 선택이 필요하다.
- **`Proc.` / `Poster` / `Expert` 컬럼** — 판정 기준 자료 확보 후 재논의.
- **제외된 60개 학회** — 현재 빌드에서 제외. 필요해지면 `fields.yaml`에서 되살린다.
