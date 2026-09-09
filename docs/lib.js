// DOM에 의존하지 않는 순수 로직. node --test로 검증한다.
//
// D-day와 회차 선택을 브라우저의 현재 날짜로 계산하는 것이 핵심이다.
// 빌드가 며칠 밀려도 표시가 어긋나지 않아야 하기 때문이다.

const MS_PER_DAY = 86400000;
const GRADE_RANK = { 최우수: 0, 우수: 1 };

// primary_deadline을 고를 때 "본 논문 마감"으로 인정하는 타입.
// scripts/models.py의 PAPER_TYPES와 반드시 같아야 한다 — 여기서 다르게
// 고르면 build가 계산한 primary_deadline과 브라우저가 고르는 다음 회차가
// 서로 다른 기준으로 어긋나게 된다.
const PAPER_TYPES = new Set(["paper", "submission"]);

function startOfDay(value) {
  const d = new Date(value);
  return Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
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
 * 후보는 논문 마감 타입(paper, submission)으로 한정한다 — 실제 데이터에는
 * 같은 deadlines 배열에 등록/리뷰공개/통보/camera-ready 같은 행정 일정도
 * 섞여 있어서(WACV, SIGGRAPH, ECCV), 타입을 가리지 않고 날짜순으로만 고르면
 * "다음 마감"이 논문 제출과 무관한 통보일이나 camera-ready로 뽑힐 수 있다.
 */
export function nextDeadline(edition, now) {
  const all = (edition?.deadlines ?? []).filter((d) => PAPER_TYPES.has(d.type));
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
  const text = new Date(chosen.date).toLocaleDateString("en-US", {
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
