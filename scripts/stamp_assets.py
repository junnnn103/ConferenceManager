"""정적 자원 URL에 내용 해시를 붙여 브라우저 캐시를 무효화한다.

GitHub Pages는 style.css / app.js를 10분간 캐시하라고 응답한다. 파일을 고쳐
배포해도 브라우저가 옛 사본을 계속 쓰므로, 사용자가 강력 새로고침을 하기
전까지 바뀐 화면을 볼 수 없다 - 실제로 색을 고치고도 그대로라는 보고를 받았다.

파일 내용이 바뀌면 해시가 바뀌고 URL이 달라져 브라우저가 새로 받는다.
내용이 그대로면 URL도 그대로라 캐시가 그대로 쓰인다.

해시는 "자기 내용 + 자기가 참조하는 자원들의 해시"로 계산한다. app.js 자체는
그대로인데 lib.js만 고친 경우, app.js 해시까지 바뀌지 않으면 브라우저가
캐시된 옛 app.js를 계속 써서 새 lib.js를 영영 받지 못하기 때문이다.
"""

import hashlib
import re
from pathlib import Path

DOCS = Path(__file__).parents[1] / "docs"

# 자원 -> 그 자원이 참조하는 자원들. 의존 방향이며, 순환이 없어야 한다.
DEPENDENCIES = {
    "style.css": [],
    "lib.js": [],
    "url-safety.js": [],
    "app.js": ["lib.js", "url-safety.js"],
    "index.html": ["style.css", "app.js"],
}

_QUERY = re.compile(r'(["\'])(\./)?([\w.-]+\.(?:js|css))\?v=[a-f0-9]+\1')


def _own_text(name: str) -> str:
    """이미 붙어 있는 ?v= 를 지운 내용.

    쿼리를 포함해 해시하면 값이 자기 자신에 의존해 매번 흔들린다.
    """
    return _QUERY.sub(r"\1\2\3\1", (DOCS / name).read_text(encoding="utf-8"))


def content_hash(name: str, _seen: frozenset[str] = frozenset()) -> str:
    if name in _seen:
        raise RuntimeError(f"순환 참조: {name}")
    parts = [_own_text(name)]
    for dep in DEPENDENCIES.get(name, []):
        parts.append(content_hash(dep, _seen | {name}))
    return hashlib.sha1("\x00".join(parts).encode("utf-8")).hexdigest()[:8]


def stamp() -> list[str]:
    changed = []
    for referrer, deps in DEPENDENCIES.items():
        path = DOCS / referrer
        before = path.read_text(encoding="utf-8")
        after = before
        for dep in deps:
            digest = content_hash(dep)
            pattern = re.compile(
                r'(["\'])(\./)?' + re.escape(dep) + r'(?:\?v=[a-f0-9]+)?\1'
            )
            after = pattern.sub(rf"\g<1>\g<2>{dep}?v={digest}\g<1>", after)
        if after != before:
            path.write_text(after, encoding="utf-8")
            changed.append(referrer)
    return changed


if __name__ == "__main__":
    for name in stamp():
        print(f"  {name} 갱신")
    print("정적 자원 버전 도장 완료")
