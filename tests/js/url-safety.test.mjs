import assert from "node:assert/strict";
import { test } from "node:test";

import { safeHref } from "../../docs/url-safety.js";

const BASE = "https://example.com/";

test("safeHref keeps http and https URLs", () => {
  assert.equal(safeHref("https://cvpr.thecvf.com/", BASE), "https://cvpr.thecvf.com/");
  assert.equal(safeHref("http://example.org/x", BASE), "http://example.org/x");
});

test("safeHref rejects javascript: URLs", () => {
  assert.equal(safeHref("javascript:alert(1)", BASE), null);
});

test("safeHref rejects data: and other non-http schemes", () => {
  assert.equal(safeHref("data:text/html,<script>alert(1)</script>", BASE), null);
  assert.equal(safeHref("file:///etc/passwd", BASE), null);
  assert.equal(safeHref("mailto:a@b.com", BASE), null);
  assert.equal(safeHref("vbscript:msgbox(1)", BASE), null);
});

test("safeHref rejects javascript: regardless of case or padding", () => {
  assert.equal(safeHref("JaVaScRiPt:alert(1)", BASE), null);
  assert.equal(safeHref("  javascript:alert(1)  ", BASE), null);
});

test("safeHref does not resolve relative URLs against base", () => {
  // base가 주어지면 new URL()은 이 셋을 전부 base 기준으로 절대화해 버린다.
  // "//evil.com/path"는 base의 스킴만 빌려 완전히 다른 사이트로 가는
  // 살아있는 링크가 되고, "evil.com"과 "/relative/path"는 base 도메인
  // 위의 존재하지 않는 경로가 된다. 이 프로젝트의 링크는 항상 절대
  // http(s) 주소이므로 상대 해석 자체를 막아야 한다.
  assert.equal(safeHref("//evil.com/path", BASE), null);
  assert.equal(safeHref("evil.com", BASE), null);
  assert.equal(safeHref("/relative/path", BASE), null);
});

test("safeHref returns null for missing or empty values", () => {
  assert.equal(safeHref(null, BASE), null);
  assert.equal(safeHref(undefined, BASE), null);
  assert.equal(safeHref("", BASE), null);
});

test("safeHref returns null for unparseable strings", () => {
  // 상대 경로처럼 보이는 스킴 없는 문자열은 base에 대해 절대화되어
  // http(s)가 될 수도 있으므로, 아예 파싱이 깨지는 값으로 확인한다.
  assert.equal(safeHref("http://", BASE), null);
});
