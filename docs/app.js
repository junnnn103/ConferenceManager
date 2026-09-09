import {
  compareBy,
  formatDateRange,
  formatDeadline,
  matchesFilters,
  pickEdition,
} from "./lib.js";

const STORAGE_KEY = "conference-manager-filters";

const state = {
  data: { conferences: [], fields: [], unresolved: [] },
  sortKey: "date",
  sortDir: "asc",
  filters: {
    fields: new Set(),
    grades: new Set(),
    aiOnly: false,
    hidePast: false,
    query: "",
  },
};

const el = {
  tbody: document.querySelector("#conference-table tbody"),
  fieldFilters: document.querySelector("#field-filters"),
  search: document.querySelector("#search"),
  count: document.querySelector("#count"),
  generatedAt: document.querySelector("#generated-at"),
  unresolved: document.querySelector("#unresolved"),
  unresolvedList: document.querySelector("#unresolved-list"),
  unresolvedCount: document.querySelector("#unresolved-count"),
};

// ---------- 필터 상태의 저장과 복원 ----------
// URL을 우선한다. 링크로 공유된 필터가 내 localStorage에 덮이면 안 되기 때문이다.

function readStateFromUrl() {
  const params = new URLSearchParams(location.search);
  if (!params.toString()) return false;
  state.filters.fields = new Set(params.getAll("field"));
  state.filters.grades = new Set(params.getAll("grade"));
  state.filters.aiOnly = params.get("ai") === "1";
  state.filters.hidePast = params.get("upcoming") === "1";
  state.filters.query = params.get("q") || "";
  state.sortKey = params.get("sort") || "date";
  state.sortDir = params.get("dir") === "desc" ? "desc" : "asc";
  return true;
}

function readStateFromStorage() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    if (!saved) return;
    state.filters.fields = new Set(saved.fields || []);
    state.filters.grades = new Set(saved.grades || []);
    state.filters.aiOnly = Boolean(saved.aiOnly);
    state.filters.hidePast = Boolean(saved.hidePast);
    state.filters.query = saved.query || "";
    state.sortKey = saved.sortKey || "date";
    state.sortDir = saved.sortDir || "asc";
  } catch {
    // 저장된 값이 깨졌으면 기본값으로 시작한다.
  }
}

function persistState() {
  const params = new URLSearchParams();
  state.filters.fields.forEach((f) => params.append("field", f));
  state.filters.grades.forEach((g) => params.append("grade", g));
  if (state.filters.aiOnly) params.set("ai", "1");
  if (state.filters.hidePast) params.set("upcoming", "1");
  if (state.filters.query) params.set("q", state.filters.query);
  if (state.sortKey !== "date") params.set("sort", state.sortKey);
  if (state.sortDir !== "asc") params.set("dir", state.sortDir);

  const qs = params.toString();
  history.replaceState(null, "", qs ? `?${qs}` : location.pathname);

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      fields: [...state.filters.fields],
      grades: [...state.filters.grades],
      aiOnly: state.filters.aiOnly,
      hidePast: state.filters.hidePast,
      query: state.filters.query,
      sortKey: state.sortKey,
      sortDir: state.sortDir,
    }));
  } catch {
    // 사파리 프라이빗 모드 등에서 실패할 수 있다. 기능에는 영향이 없다.
  }
}

// ---------- 렌더링 ----------

function fieldColor(id) {
  return state.data.fields.find((f) => f.id === id)?.color || "#64748b";
}

function fieldLabel(id) {
  return state.data.fields.find((f) => f.id === id)?.label || id;
}

function linkCell(conf, edition) {
  const cell = document.createElement("td");
  cell.className = "links-col";

  const home = document.createElement("a");
  home.textContent = "홈";
  home.className = "link-btn";
  home.title = "학회 공식 홈페이지";
  if (conf.homepage) {
    home.href = conf.homepage;
    home.target = "_blank";
    home.rel = "noopener";
  } else {
    home.classList.add("disabled");
  }
  cell.append(home);

  const cfp = document.createElement("a");
  cfp.textContent = "CFP";
  cfp.className = "link-btn";
  cfp.title = "이 회차의 논문 모집 공고";
  if (edition?.link) {
    cfp.href = edition.link;
    cfp.target = "_blank";
    cfp.rel = "noopener";
  } else {
    cfp.classList.add("disabled");
  }
  cell.append(cfp);
  return cell;
}

// 마감 라벨에서 정보가 없는 단어만 남는지 판단한다. 실제 데이터의 라벨 대부분
// (35개 중 29개)은 "Paper Submission Deadline" 류의 표현일 뿐이고, 그건 마감
// 칸이 이미 말하고 있는 내용이라 그대로 보여주면 캡션이 열 제목을 반복하게
// 된다. "fourth round"나 "Paper submission (short papers)"처럼 라운드/트랙을
// 구분해 주는 라벨만 남기기 위해, 정보가 없는 단어를 지우고 남는 게 있는지로
// 판단한다 — 문자열 전체를 통째로 비교하면 문구가 조금만 달라도(마침표, 어순,
// deadline 유무) 걸러지지 않기 때문이다.
const DEADLINE_LABEL_STOPWORDS = new Set([
  "full", "paper", "papers", "submission", "submissions",
  "deadline", "due", "research",
]);

function isGenericDeadlineLabel(label) {
  const words = label.toLowerCase().split(/[^a-z0-9]+/).filter(Boolean);
  return words.every((w) => DEADLINE_LABEL_STOPWORDS.has(w));
}

function renderRow(conf, now) {
  const edition = pickEdition(conf.editions, now);
  const row = document.createElement("tr");
  row.dataset.abbr = conf.abbr;

  const nameCell = document.createElement("td");
  nameCell.className = "name-col";
  const name = document.createElement(conf.homepage ? "a" : "span");
  name.className = "abbr";
  name.textContent = conf.abbr;
  if (conf.homepage) {
    name.href = conf.homepage;
    name.target = "_blank";
    name.rel = "noopener";
  }
  nameCell.append(name);
  if (conf.ai_specialist) {
    const badge = document.createElement("span");
    badge.className = "badge ai";
    badge.textContent = "AI Specialist";
    nameCell.append(badge);
  }
  const full = document.createElement("div");
  full.className = "full-name";
  full.textContent = conf.full_name;
  nameCell.append(full);
  row.append(nameCell);

  const fieldCell = document.createElement("td");
  const fieldBadge = document.createElement("span");
  fieldBadge.className = "badge field";
  fieldBadge.textContent = fieldLabel(conf.field);
  fieldBadge.style.setProperty("--badge-color", fieldColor(conf.field));
  fieldCell.append(fieldBadge);
  row.append(fieldCell);

  const gradeCell = document.createElement("td");
  const gradeBadge = document.createElement("span");
  gradeBadge.className = `badge grade ${conf.grade === "최우수" ? "top" : "good"}`;
  gradeBadge.textContent = conf.grade;
  gradeCell.append(gradeBadge);
  row.append(gradeCell);

  const dateCell = document.createElement("td");
  dateCell.textContent = formatDateRange(edition);
  row.append(dateCell);

  const placeCell = document.createElement("td");
  placeCell.textContent = edition?.place || "미정";
  row.append(placeCell);

  const deadlineCell = document.createElement("td");
  deadlineCell.className = "deadline-col";
  const info = formatDeadline(edition, now);
  const when = document.createElement("div");
  when.className = `deadline-date ${info.state}`;
  when.textContent = info.text;
  deadlineCell.append(when);
  if (info.dday) {
    const dday = document.createElement("div");
    dday.className = `dday ${info.state}`;
    dday.textContent = info.dday;
    deadlineCell.append(dday);
  }
  // info.label은 마감이 여러 라운드나 트랙으로 나뉜 학회에서 이 날짜가
  // 무엇의 마감인지 알려준다 (예: UbiComp의 "fourth round"). "Paper
  // Submission Deadline" 류의 정보 없는 라벨은 생략한다.
  if (info.label && !isGenericDeadlineLabel(info.label)) {
    const label = document.createElement("div");
    label.className = "deadline-label";
    label.textContent = info.label;
    deadlineCell.append(label);
  }
  row.append(deadlineCell);

  row.append(linkCell(conf, edition));
  return row;
}

function render() {
  const now = new Date();
  const visible = state.data.conferences
    .filter((c) => matchesFilters(c, state.filters, now))
    .sort(compareBy(state.sortKey, state.sortDir, now));

  el.tbody.replaceChildren(...visible.map((c) => renderRow(c, now)));
  el.count.textContent = `${visible.length} / ${state.data.conferences.length}개 표시`;

  document.querySelectorAll("#conference-table th[data-sort]").forEach((th) => {
    const active = th.dataset.sort === state.sortKey;
    th.querySelector(".arrow").textContent = active
      ? (state.sortDir === "asc" ? "▲" : "▼")
      : "⇅";
    th.classList.toggle("active", active);
  });

  document.querySelectorAll("[data-field]").forEach((chip) => {
    chip.classList.toggle("on", state.filters.fields.has(chip.dataset.field));
  });
  document.querySelectorAll("[data-grade]").forEach((chip) => {
    chip.classList.toggle("on", state.filters.grades.has(chip.dataset.grade));
  });
  document.querySelector("#ai-only").classList.toggle("on", state.filters.aiOnly);
  document.querySelector("#hide-past").classList.toggle("on", state.filters.hidePast);

  persistState();
}

function renderStatic() {
  el.generatedAt.textContent = state.data.generated_at
    ? `· ${state.data.generated_at.slice(0, 10)} 갱신`
    : "";

  el.fieldFilters.replaceChildren(...state.data.fields.map((f) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip";
    chip.dataset.field = f.id;
    chip.textContent = f.label;
    chip.style.setProperty("--badge-color", f.color);
    return chip;
  }));

  const unresolved = state.data.unresolved || [];
  if (unresolved.length > 0) {
    el.unresolved.hidden = false;
    el.unresolvedCount.textContent = `${unresolved.length}개`;
    el.unresolvedList.replaceChildren(...unresolved.map((u) => {
      const li = document.createElement("li");
      li.textContent = `${u.abbr} — ${u.reason}`;
      return li;
    }));
  }
}

// ---------- 이벤트 ----------

function toggleInSet(set, value) {
  if (set.has(value)) set.delete(value);
  else set.add(value);
}

function wireEvents() {
  document.querySelectorAll("#conference-table th[data-sort]").forEach((th) => {
    th.querySelector("button").addEventListener("click", () => {
      const key = th.dataset.sort;
      if (state.sortKey === key) {
        state.sortDir = state.sortDir === "asc" ? "desc" : "asc";
      } else {
        state.sortKey = key;
        state.sortDir = "asc";
      }
      render();
    });
  });

  el.fieldFilters.addEventListener("click", (event) => {
    const chip = event.target.closest("[data-field]");
    if (!chip) return;
    toggleInSet(state.filters.fields, chip.dataset.field);
    render();
  });

  document.querySelectorAll("[data-grade]").forEach((chip) => {
    chip.addEventListener("click", () => {
      toggleInSet(state.filters.grades, chip.dataset.grade);
      render();
    });
  });

  document.querySelector("#ai-only").addEventListener("click", () => {
    state.filters.aiOnly = !state.filters.aiOnly;
    render();
  });

  document.querySelector("#hide-past").addEventListener("click", () => {
    state.filters.hidePast = !state.filters.hidePast;
    render();
  });

  document.querySelector("#reset").addEventListener("click", () => {
    state.filters = {
      fields: new Set(), grades: new Set(),
      aiOnly: false, hidePast: false, query: "",
    };
    el.search.value = "";
    render();
  });

  el.search.addEventListener("input", (event) => {
    state.filters.query = event.target.value;
    render();
  });
}

async function main() {
  const response = await fetch("data/conferences.json", { cache: "no-cache" });
  state.data = await response.json();

  if (!readStateFromUrl()) readStateFromStorage();
  el.search.value = state.filters.query;

  renderStatic();
  wireEvents();
  render();
}

main();
