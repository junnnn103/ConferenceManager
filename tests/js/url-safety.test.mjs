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
