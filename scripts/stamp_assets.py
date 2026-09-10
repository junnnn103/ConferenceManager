"""정적 자원 URL에 내용 해시를 붙여 브라우저 캐시를 무효화한다.

GitHub Pages는 style.css / app.js를 10분간 캐시하라고 응답한다. 파일을 고쳐
배포해도 브라우저가 옛 사본을 계속 쓰므로, 사용자가 강력 새로고침을 하기
전까지 바뀐 화면을 볼 수 없다 - 실제로 색을 고치고도 그대로라는 보고를 받았다.

파일 내용이 바뀌면 해시가 바뀌고 URL이 달라져 브라우저가 새로 받는다.
내용이 그대로면 URL도 그대로라 캐시가 그대로 쓰인다.

ES 모듈 import 경로(app.js -> lib.js)도 같은 이유로 붙여야 한다. 손으로
관리하면 반드시 빠뜨리므로 빌드에서 자동으로 처리한다.
"""

import hashlib
import re
from pathlib import Path

DOCS = Path(__file__).parents[1] / "docs"
# (파일, 그 파일을 참조하는 파일들)
ASSETS = {
    "style.css": ["index.html"],
    "app.js": ["index.html"],
    "lib.js": ["app.js"],
    "url-safety.js": ["app.js"],
}


def content_hash(name: str) -> str:
    """쿼리 문자열을 뺀 내용으로 해시를 낸다.

    lib.js처럼 자신도 참조당하고 남을 참조하기도 하는 파일이 있어, 이미 붙은
    ?v=를 포함해 해시하면 값이 매번 흔들린다.
    """
    raw = (DOCS / name).read_text(encoding="utf-8")
    stripped = re.sub(r'(["\'])(\./)?([\w.-]+\.(?:js|css))\?v=[a-f0-9]+\1', r"\1\2\3\1", raw)
    return hashlib.sha1(stripped.encode("utf-8")).hexdigest()[:8]


def stamp() -> list[str]:
    changed = []
    for asset, referrers in ASSETS.items():
        digest = content_hash(asset)
        pattern = re.compile(
            r'(["\'])(\./)?' + re.escape(asset) + r'(?:\?v=[a-f0-9]+)?\1'
        )
        for referrer in referrers:
            path = DOCS / referrer
            before = path.read_text(encoding="utf-8")
            after = pattern.sub(rf'\g<1>\g<2>{asset}?v={digest}\g<1>', before)
            if after != before:
                path.write_text(after, encoding="utf-8")
                changed.append(f"{referrer}: {asset}?v={digest}")
    return changed


if __name__ == "__main__":
    for line in stamp():
        print(f"  {line}")
    print("정적 자원 버전 도장 완료")
