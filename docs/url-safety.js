// 링크 주소는 제3자 저장소(ai-deadlines, ccfddl, registry.yaml/manual.yaml에
// 붙는 PR)에서 온다. scripts/build.py가 http/https가 아닌 스킴을 걸러
// conferences.json에 싣지 않지만, 커밋된 JSON은 사람이 손으로도 고칠 수
// 있고 화면에 실제로 href를 꽂는 쪽은 이 페이지이므로 여기서 한 번 더
// 막는다. javascript: 같은 값이 anchor의 href에 그대로 들어가면 클릭
// 한 번으로 실행되기 때문이다.
//
// DOM에 의존하지 않는다 - base를 인자로 받아 node --test로 바로 검증한다.
export function safeHref(url, base) {
  if (!url) return null;
  try {
    const parsed = new URL(url, base);
    return parsed.protocol === "http:" || parsed.protocol === "https:" ? parsed.href : null;
  } catch {
    return null;
  }
}
