# 학회 일정 트래커

AI/HCI 인접 학회의 개최일과 논문 제출마감을 추적하는 정적 사이트입니다.
현재 `data/registry.yaml`에 등록된 99개 학회 중, 활성화된 10개 분야(ML, CV,
NLP, Speech, Robotics, DM/IR, HCI, Graphics, Multimedia, AR/VR)에 속하고
일정이 확인된 38개 학회 + 미확인 1개(Humanoids, 소스에 회차 정보 없음)를
보여줍니다. 이 수치는 회차가 넘어가거나 분야를 더 켜면 바뀝니다.

사이트는 `docs/index.html` + `app.js` + `lib.js` + `url-safety.js` +
`style.css`로 이루어진 정적 페이지이고, 데이터는 매일 자동으로 갱신되는
`docs/data/conferences.json` 하나를 읽습니다.

## 데이터 출처와 병합 우선순위

- **`data/manual.yaml`** — 아래 두 공개 소스가 다루지 않는 학회의 수동 입력
  (HRI, Humanoids, 홀수해 ASRU/SLT). 최우선 소스.
- **[huggingface/ai-deadlines](https://github.com/huggingface/ai-deadlines)** —
  다단계 마감, 개최지. 공개 raw 파일을 그대로 읽는다.
- **[ccfddl/ccf-deadlines](https://github.com/ccfddl/ccf-deadlines)** — CS
  전반을 다루는 CCF 학회 목록. 공개 raw 파일을 그대로 읽는다.
- **`data/scraped/`** — 학회 CFP 페이지에서 추출한 poster/LBW/workshop 등
  세부 트랙 일정. `scripts/validate_scraped.py`의 원문 대조 게이트를 통과한
  것만 여기 들어간다 (자세한 내용은 아래 "CFP 검증 게이트" 참고).

병합은 **회차(연도) 단위로 소스를 통째로 고른다** — 필드 단위로 값을 섞지
않는다. 그래야 값이 어긋났을 때 어느 값이 어느 소스에서 왔는지 추적할 수
있다. 우선순위는

```
manual > ai-deadlines > ccfddl
```

이며, `cfp-scrape`만 예외로 상위 소스가 갖지 않은 **단계만** 채운다 (이미
있는 타입은 절대 덮어쓰지 않는다). 예를 들어 ai-deadlines가 `paper` 마감만
갖고 있으면, `data/scraped/`에서 뽑은 `poster` 마감이 함께 표시된다.

ICCV/ECCV, ASRU/SLT처럼 격년으로 번갈아 여는 결합 학회는 `data/registry.yaml`
에 하나의 그룹 키로 등록돼 있고, 빌드 시점에 차기 회차가 더 이른 쪽(없으면
가장 최근에 열린 쪽)을 대표로 골라 보여준다.

## 로컬에서 돌리기

```bash
pip install -e ".[dev]"
python -m scripts.build
python -m http.server 8000 --directory docs
```

`python -m scripts.build`는 위 네 소스를 다시 읽어(공개 GitHub raw 파일에
네트워크로 접근) `docs/data/conferences.json`을 새로 쓴다. 사이트는 그 결과를
정적으로 서빙만 하므로 별도 백엔드가 없다.

## 테스트

```bash
python -m pytest -q     # 파이썬 (병합, 파서, 검증 게이트 등)
node --test tests/js/   # 프론트엔드 순수 로직 (lib.js, url-safety.js)
```

두 테스트 모두 네트워크를 타지 않는다. GitHub Actions는 매일 이 두 스위트를
통과해야만 빌드와 커밋을 진행한다.

## CFP 검증 게이트

`data/scraped/`에 들어가는 세부 트랙 일정은 모델이 CFP 페이지에서 추출한
것이므로, `scripts/validate_scraped.py`가 채택 여부를 최종 결정한다. 핵심은
원문 대조다 — 추출 결과의 `raw_text`가 실제 페이지 본문에 없거나, 그 안에
주장된 날짜가 적혀 있지 않으면 지어낸 것으로 보고 버린다. 이 스크립트는
네트워크도 모델도 쓰지 않는 순수 함수라, 매 빌드 전 CI에서 다시 돌려도
비용이 없고, 손으로 편집한 값이 게이트를 우회하는 것도 막는다.

## 엑셀 갱신 (`bootstrap_registry.py`)

빌드는 `data/registry.yaml`만 읽는다 — 엑셀은 빌드 입력이 **아니다**.
`data/registry.yaml`은 원래 두 개의 엑셀 파일(`26년 우수 학회 List.xlsx`,
`260406_AI_Specialist_인정학회리스트.xlsx`)에서 `scripts/bootstrap_registry.py`
로 한 번 변환해 만든 것이고, 그 엑셀들은 사내 자료라 이 저장소(public)에
커밋하지 않는다 — `.gitignore`에서 `학술연수 학회 리스트/` 등으로 제외돼
있다. 그래서 CI에는 엑셀이 전혀 없어도 정상 동작한다.

엑셀이 새로 갱신됐을 때만 사람이 직접 실행한다:

```bash
pip install -e ".[bootstrap]"
python scripts/bootstrap_registry.py --diff   # registry.yaml과 차이만 확인
python scripts/bootstrap_registry.py          # registry.yaml을 새로 생성
```

`homepage`와 각 학회의 소스 id 매핑(ai-deadlines/ccfddl 쪽 식별자)은 엑셀에서
유도할 수 없는 손으로 붙인 값이라, 재생성해도 자동으로 덮어쓰지 않는다.

## 분야(field) 되살리기

`data/registry.yaml`에는 99개 학회 전부가 들어 있어 엑셀 없이도 전체 목록을
확인할 수 있지만, `data/fields.yaml`에서 `enabled: false`인 분야에 속한
학회는 빌드 결과(`conferences.json`)와 사이트에서 제외된다. 현재 비활성 분야는
14개(DB, Security, SE/PL, OS/HPC, Architecture, Network, Medical, InfoTheory,
Circuits, RF/Power, Display/Optics, Materials, Thermal, Food)다.

되살리려면 `data/fields.yaml`에서 해당 항목의 `enabled`를 `true`로 바꾸고
다시 빌드하면 된다 — 엑셀도, 코드 수정도 필요 없다.

```yaml
  - id: Security
    label: Security
    color: "#64748b"
    enabled: true   # false였던 것을 true로
```

```bash
python -m scripts.build
```

## 자동 갱신 (GitHub Actions)

`.github/workflows/build.yml`이 매일 06:00 KST(21:00 UTC)에 위 네 소스를 다시
읽어 `docs/data/conferences.json`을 갱신하고, 바뀐 내용이 있을 때만 자동
커밋·푸시한다. 공개 GitHub raw 파일만 읽으므로 **시크릿이 전혀 필요 없다**.
`push` 이벤트로도 같은 워크플로가 돌고, 예약 실행과 겹칠 수 있어 `concurrency`
그룹으로 순서를 강제한다(둘 다 같은 파일을 밀면 push 충돌이 나기 때문).
