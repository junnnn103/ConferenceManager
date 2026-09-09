import assert from "node:assert/strict";
import { test } from "node:test";

import {
  allDeadlines,
  compareBy,
  dayDelta,
  formatDeadline,
  isEnded,
  isFeaturedDeadline,
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

// MLSys 2027: date는 TBD지만 마감(primary_deadline)은 확정되어 있다.
// scripts/merge.py의 select_editions와 같은 규칙으로, 날짜가 없어도 아직
// 지나지 않은 마감이 있으면 '차기'로 뽑아야 한다.
test("pickEdition picks an undated edition with a future primary_deadline over an already-ended dated one", () => {
  const editions = [
    edition(2026, "2026-03-01", "2026-03-05", null), // 이미 끝난 회차
    edition(2027, null, null, "2026-10-30T23:59:59"), // 날짜 미상, 마감만 확정
  ];
  assert.equal(pickEdition(editions, NOW).year, 2027);
});

test("pickEdition ignores an undated edition whose primary_deadline already passed", () => {
  const editions = [
    edition(2026, "2026-03-01", "2026-03-05", null),
    edition(2027, null, null, "2025-01-01T23:59:59"),
  ];
  assert.equal(pickEdition(editions, NOW).year, 2026);
});

test("isEnded is false for an undated edition with a future primary_deadline", () => {
  // pickEdition이 이 회차를 고른 뒤, isEnded는 end/start가 없으므로 '종료'로
  // 판단하지 않아야 한다 - 회색 처리되면 안 된다.
  const conf1 = conf({
    abbr: "MLSYS",
    editions: [
      edition(2026, "2026-03-01", "2026-03-05", null),
      edition(2027, null, null, "2026-10-30T23:59:59"),
    ],
  });
  assert.equal(isEnded(conf1, NOW), false);
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

test("isEnded is true when the displayed edition already ended", () => {
  const past = conf({ abbr: "A", editions: [edition(2026, "2026-01-05", "2026-01-09", null)] });
  assert.equal(isEnded(past, NOW), true);
});

test("isEnded is false when there is an upcoming edition", () => {
  const upcoming = conf({ abbr: "A", editions: [edition(2026, "2026-10-24", "2026-10-29", null)] });
  assert.equal(isEnded(upcoming, NOW), false);
});

test("isEnded is false when no edition has dates", () => {
  const undated = conf({
    abbr: "A",
    editions: [{ year: 2026, date_text: null, start: null, end: null, place: null, link: null, deadlines: [], primary_deadline: null, source: "ccfddl" }],
  });
  assert.equal(isEnded(undated, NOW), false);
});

test("isEnded is false when the edition ends exactly today", () => {
  const endsToday = conf({ abbr: "A", editions: [edition(2026, "2026-09-04", "2026-09-08", null)] });
  assert.equal(isEnded(endsToday, NOW), false);
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

test("matchesFilters hidePast follows nextDeadline, not primary_deadline, when they diverge", () => {
  // SIGGRAPH/CVPR/ACL 2027처럼 deadlines에 paper/submission 타입이 전혀
  // 없이 workshop 등만 있으면 셀에는 미정이 뜬다(nextDeadline이 null을
  // 돌려주므로). 하지만 primary_deadline은 그 workshop 마감 날짜를 그대로
  // 갖고 있어 아직 미래처럼 보인다. hidePast가 primary_deadline을 기준으로
  // 판단하면, 화면엔 미정이라고 써 있는 학회가 "곧 마감"인 것처럼 필터를
  // 통과해 버린다 - 셀과 같은 근거(nextDeadline)를 써야 한다.
  const workshopOnly = conf({
    editions: [{
      year: 2027,
      date_text: "2027",
      start: "2027-07-01",
      end: "2027-07-05",
      place: "Somewhere",
      link: null,
      deadlines: [
        { type: "workshop", label: "Workshop Proposal", date: "2026-12-01T23:59:59", source: "cfp-scrape" },
      ],
      primary_deadline: "2026-12-01T23:59:59",
      source: "ccfddl",
    }],
  });
  const filters = { fields: new Set(), grades: new Set(), aiOnly: false, hidePast: true, query: "" };
  assert.equal(matchesFilters(workshopOnly, filters, NOW), false);
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

// --- allDeadlines: 토글에 보여줄 전체 일정 ---
//
// 예전 이름 extraDeadlines는 셀에 뜨는 항목(nextDeadline의 선택)을 뺐다.
// 하지만 그게 펼친 목록에서 가장 중요한 항목(본 마감)이 통째로 사라지는
// 결과였다(ECCV 12개 중 11개, UbiComp 4개 중 3개, WACV 11개 중 10개만
// 보이던 문제). allDeadlines는 아무것도 빼지 않고 시간순으로 전부 돌려주고,
// 어느 것이 대표인지는 isFeaturedDeadline이 참조 동일성으로 따로 표시한다.

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

test("allDeadlines includes the stage the cell shows too — nothing is dropped", () => {
  const types = allDeadlines(multiStage).map((d) => d.type);
  assert.deepEqual(types, ["abstract", "paper", "notification", "poster"]);
});

test("allDeadlines sorts chronologically", () => {
  const dates = allDeadlines(multiStage).map((d) => d.date);
  assert.deepEqual(dates, [...dates].sort());
});

test("allDeadlines returns the single stage as-is when only one deadline exists", () => {
  // 마감이 하나뿐이면 목록도 그 하나뿐이다(빈 배열이 아니다) - 토글을 달지
  // 말지는 호출하는 쪽(app.js)이 길이로 판단한다.
  const single = { ...multiStage, deadlines: [multiStage.deadlines[1]] };
  assert.deepEqual(allDeadlines(single).map((d) => d.type), ["paper"]);
});

test("allDeadlines handles an edition with no deadlines", () => {
  assert.deepEqual(allDeadlines({ deadlines: [], primary_deadline: null }), []);
  assert.deepEqual(allDeadlines(null), []);
});

// --- isFeaturedDeadline: 어느 단계가 셀과 같은 대표 마감인지 ---

test("isFeaturedDeadline marks by identity, not by date — a shared date does not mark two stages", () => {
  // 날짜값으로 비교하면 같은 시각에 걸린 두 단계가 둘 다 '대표'로 잘못
  // 표시될 수 있다. nextDeadline은 특정 객체 하나(여기선 "paper" 항목)를
  // 고르므로, 그 객체만 current여야 한다.
  const sharedDate = "2025-11-13T23:59:59";
  const sharedDateEdition = {
    year: 2026,
    date_text: "June 3-7, 2026",
    start: "2026-06-03",
    end: "2026-06-07",
    place: "Denver USA",
    link: null,
    primary_deadline: sharedDate,
    source: "ai-deadlines",
    deadlines: [
      { type: "paper", label: "Paper", date: sharedDate, source: "ai-deadlines" },
      { type: "abstract", label: "Also due", date: sharedDate, source: "ai-deadlines" },
    ],
  };
  const flags = allDeadlines(sharedDateEdition).map(
    (d) => [d.type, isFeaturedDeadline(d, sharedDateEdition, NOW)]
  );
  assert.deepEqual(flags, [["paper", true], ["abstract", false]]);
});

// --- nextDeadline must not synthesize a featured deadline out of thin air
// when deadlines exist but none is paper/submission typed ---
//
// The empty-deadlines fallback (primary_deadline only, no deadlines array)
// synthesizes a { type: "paper", ... } object that isn't a member of
// edition.deadlines — harmless there, since allDeadlines has nothing to list
// in that case (edition.deadlines is empty). But if deadlines is non-empty
// and simply has no paper/submission entry (e.g. only notification/
// camera_ready survived, which is what an LLM-extracted CFP could plausibly
// produce), isFeaturedDeadline must not somehow match one of them to that
// synthesized object — none of them is "featured".

const noPaperTypeEdition = () => ({
  year: 2026,
  date_text: "2026-05-01 ~ 2026-06-05",
  start: "2026-05-01",
  end: "2026-06-05",
  place: "Somewhere",
  link: null,
  deadlines: [
    { type: "notification", label: "Decisions", date: "2026-05-01T23:59:59", source: "cfp-scrape" },
    { type: "camera_ready", label: "Camera Ready", date: "2026-06-01T23:59:59", source: "cfp-scrape" },
  ],
  primary_deadline: "2026-05-01T23:59:59",
  source: "cfp-scrape",
});

test("nextDeadline returns null when deadlines exist but none is paper/submission typed", () => {
  assert.equal(nextDeadline(noPaperTypeEdition(), NOW), null);
});

test("allDeadlines shows every stage without duplication when nextDeadline finds no featured deadline", () => {
  const types = allDeadlines(noPaperTypeEdition()).map((d) => d.type);
  assert.deepEqual(types, ["notification", "camera_ready"]);
});

test("isFeaturedDeadline marks nothing as current when nextDeadline finds no featured deadline", () => {
  const edition = noPaperTypeEdition();
  const flags = allDeadlines(edition).map((d) => isFeaturedDeadline(d, edition, NOW));
  assert.deepEqual(flags, [false, false]);
});
