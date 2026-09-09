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

/**
 * 종료일이 오늘 이후인 회차 중 가장 이른 것. 없으면 가장 최근에 지난 회차.
 *
 * 날짜가 없어도 아직 지나지 않은 마감(primary_deadline)이 있는 회차는
 * '차기' 후보로 인정한다 - scripts/merge.py의 select_editions와 같은
 * 규칙이다. build가 이미 직전 1개/차기 1개로 추려서 넘기지만, 브라우저는
 * 자신의 '오늘'로 다시 골라야 날짜 경계를 넘어가도 어긋나지 않으므로
 * 여기서도 같은 기준을 써야 한다 - 안 그러면 MLSys처럼 날짜 없이 마감만
 * 확정된 회차가 브라우저에서 다시 탈락하고, 이미 끝난 이전 회차가 대신
 * 뽑혀 종료된 것처럼 보인다.
 */
export function pickEdition(editions, now) {
  if (!editions || editions.length === 0) return null;
  const dated = editions.filter((e) => e.end || e.start);
  const undatedWithDeadline = editions.filter(
    (e) => !(e.end || e.start) && e.primary_deadline
  );
  if (dated.length === 0 && undatedWithDeadline.length === 0) {
    return editions[editions.length - 1];
  }

  const today = startOfDay(now);
  const upcoming = [
    ...dated
      .filter((e) => startOfDay(e.end || e.start) >= today)
      .map((e) => [startOfDay(e.start || e.end), e]),
    ...undatedWithDeadline
      .filter((e) => startOfDay(e.primary_deadline) >= today)
      .map((e) => [startOfDay(e.primary_deadline), e]),
  ].sort((a, b) => a[0] - b[0]);
  if (upcoming.length > 0) return upcoming[0][1];

  if (dated.length > 0) {
    return dated
      .slice()
      .sort((a, b) => startOfDay(a.end || a.start) - startOfDay(b.end || b.start))
      .pop();
  }
  return editions[editions.length - 1];
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
  const deadlines = edition?.deadlines ?? [];
  const all = paperCandidates(deadlines);
  if (all.length === 0) {
    // 두 경우는 답이 다르다. deadlines가 아예 비어 있으면(마감 배열 없이
    // primary_deadline만 있는 소스) primary_deadline으로 합성해서 보여주는
    // 수밖에 없고, 그래도 안전하다 - extraDeadlines가 뺄 실제 항목이 배열에
    // 없기 때문이다. 하지만 deadlines에 항목은 있는데 그중 paper/submission
    // 타입이 하나도 없다면(예: notification과 camera_ready만 있는 경우),
    // primary_deadline으로 합성한 객체는 deadlines의 그 무엇과도 같은 참조가
    // 아니라서 extraDeadlines가 아무것도 못 빼고, 셀에 뜬 마감이 펼침
    // 목록에도 중복으로 나타난다. 게다가 notification/camera_ready 날짜를
    // "제출마감"이라 부르는 것 자체가 틀렸다 - paper-over-submission
    // 우선순위와 같은 판단이다. 이 경우 null을 돌려주면 셀은 미정으로
    // 뜨고, 모든 단계가 그대로 펼침 목록에 남는다.
    if (deadlines.length > 0) return null;
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

/**
 * 회차의 모든 단계를 시간순으로 돌려준다. 셀에 뜨는 주 마감을 포함해
 * 아무것도 빼지 않는다 - 토글을 펼쳤을 때 보여줄 전체 일정표다.
 *
 * 예전 이름은 extraDeadlines였고 nextDeadline이 고른 항목을 뺐다. 그런데
 * ECCV(12단계 중 11개만 노출), UbiComp(4개 중 3개), WACV(11개 중 10개)처럼
 * 뺀 항목이 하필 가장 중요한 '본 마감'이라, 펼쳤을 때 일정표에 정작 지금
 * 다가오는 마감이 빠진 구멍이 생겼다. 어느 게 대표인지는 렌더러가
 * isFeaturedDeadline로 표시만 하고, 목록 자체는 항상 전부를 보여준다.
 *
 * now를 받지 않는다 - 정렬은 날짜값 비교만으로 끝나고 '오늘'과 무관하며,
 * 무엇을 뺄지 판단하던 로직(그게 now를 썼던 유일한 이유)이 이제 없다.
 */
export function allDeadlines(edition) {
  if (!edition || !edition.deadlines) return [];
  return edition.deadlines
    .slice()
    .sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));
}

/**
 * 이 단계가 셀에 뜨는 대표 마감(nextDeadline이 고른 바로 그 항목)인지
 * 판단한다. 날짜 값이 아니라 참조 동일성으로 비교한다 - 같은 시각에 걸린
 * 서로 다른 두 단계가 있어도(예: HRI 2027의 Short Contributions와
 * alt.HRI가 둘 다 10-01) 날짜만으로는 어느 쪽이 대표인지 구분할 수 없기
 * 때문이다. extraDeadlines가 쓰던 것과 같은 판단 기준을 그대로 옮겼다.
 *
 * nextDeadline은 edition.deadlines가 완전히 비어 있을 때만 primary_deadline
 * 으로 새 객체를 합성해 돌려준다 - 그 객체는 deadlines의 어떤 원소와도
 * 동일한 참조가 아니므로 이 함수는 항상 false를 돌려주게 된다. 이 함수를
 * 부르는 쪽(allDeadlines가 목록을 채운 경우)은 deadlines가 비어 있지
 * 않다는 뜻이라 그 경로를 절대 타지 않아야 맞지만, 가정에 기대는 대신
 * 여기서 단언해 어긋나면 콘솔에 드러나게 한다.
 */
export function isFeaturedDeadline(deadline, edition, now) {
  console.assert(
    (edition?.deadlines?.length ?? 0) > 0,
    "isFeaturedDeadline: edition.deadlines가 비어 있다 - nextDeadline이 " +
      "합성한 객체와 비교하게 되어 항상 false만 나온다. allDeadlines가 이미 " +
      "빈 목록을 돌려줘야 할 상황인데 이 함수가 불렸다는 뜻이다."
  );
  return deadline === nextDeadline(edition, now);
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
 * 표시 중인 회차가 이미 끝났는가. pickEdition은 다가오는 회차를 우선하므로,
 * 이것이 참이면 예정된 회차가 아예 없다는 뜻이다.
 * 정렬(하단으로 밀기)과 표시(회색 처리)가 같은 판단을 쓰도록 한 곳에 둔다.
 */
export function isEnded(conf, now) {
  const edition = pickEdition(conf.editions, now);
  const end = edition?.end || edition?.start;
  if (!end) return false;
  const today = startOfDay(now);
  return startOfDay(end) < today;
}

/**
 * 정렬 비교자. 이미 지난 회차는 정렬 키와 무관하게 항상 아래로 민다 —
 * 가까운 미래가 맨 위에 오는 것이 이 표의 목적이기 때문이다.
 */
export function compareBy(key, direction, now) {
  const sign = direction === "desc" ? -1 : 1;

  return (a, b) => {
    const pastA = isEnded(a, now);
    const pastB = isEnded(b, now);
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
    // 셀에 실제로 뜨는 값(nextDeadline)으로 판단해야 한다. primary_deadline은
    // deadlines 배열에 있는 모든 타입 중 가장 늦은 것의 최댓값이라 - CVPR,
    // ACL, SIGGRAPH 2027처럼 deadlines에 paper/submission 타입이 하나도
    // 없이 poster/workshop/demo 등만 있는 회차에서는 nextDeadline이 null(셀:
    // 미정)을 돌려주는데도 primary_deadline은 그 workshop 마감으로 값을
    // 가진다. 그러면 셀은 미정인데 hidePast는 그 마감을 기준으로 판단해
    // 필터와 화면이 서로 다른 근거로 어긋난다.
    const edition = pickEdition(conf.editions, now);
    const chosen = nextDeadline(edition, now);
    const delta = dayDelta(chosen?.date, now);
    if (delta === null || delta < 0) return false;
  }

  const query = (filters.query || "").trim().toLowerCase();
  if (query) {
    const haystack = `${conf.abbr} ${conf.full_name}`.toLowerCase();
    if (!haystack.includes(query)) return false;
  }
  return true;
}
