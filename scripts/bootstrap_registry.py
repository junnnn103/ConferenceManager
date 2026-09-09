"""엑셀 2개를 data/registry.yaml로 변환한다.

이 스크립트는 빌드가 아니다. 엑셀이 갱신될 때 사람이 직접 실행한다.
변환이 끝나면 빌드는 registry.yaml만 읽으므로, 엑셀 원본을
.gitignore에 두어도 CI가 정상 동작한다.

사용법:
    python scripts/bootstrap_registry.py            # 새로 생성
    python scripts/bootstrap_registry.py --diff     # 기존과 비교만
"""

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
REGISTRY_PATH = ROOT / "data" / "registry.yaml"
EXCEL_DIR = ROOT / "학술연수 학회 리스트"
GRADE_XLSX = EXCEL_DIR / "26년 우수 학회 List.xlsx"
AI_XLSX = EXCEL_DIR / "260406_AI_Specialist_인정학회리스트.xlsx"

# 엑셀에서 유도할 수 없는 큐레이션 매핑. 99개 전부를 덮는다.
FIELD_ASSIGNMENT = {
    "cvpr": "CV", "nips": "ML", "iclr": "ML", "iccv/eccv": "CV", "icml": "ML",
    "aaai": "ML", "acl": "NLP", "emnlp": "NLP", "ijcai": "ML", "naacl": "NLP",
    "chi": "HCI", "icassp": "Speech", "kdd": "DM/IR", "icra": "Robotics",
    "sp": "Security", "www": "DM/IR", "interspeech": "Speech", "wacv": "CV",
    "uss": "Security", "siggraph": "Graphics", "sigir": "DM/IR", "mm": "Multimedia",
    "miccai": "Medical", "ccs": "Security", "cikm": "DM/IR", "corl": "Robotics",
    "iros": "Robotics", "icse": "SE/PL", "infocom": "Network", "wsdm": "DM/IR",
    "icc": "Network", "vldb": "DB", "ndss": "Security", "sigmod": "DB",
    "asplos": "Architecture", "icde": "DB", "isscc": "Circuits", "rss": "Robotics",
    "icip": "CV", "sigcomm": "Network", "globecom": "Network", "eurocrypt": "Security",
    "isca": "Architecture", "nsdi": "Network", "fse": "SE/PL", "crypto": "Security",
    "micro": "Architecture", "mlsys": "ML", "isit": "InfoTheory", "ase": "SE/PL",
    "hri": "Robotics", "osdi": "OS/HPC", "bigdataconf": "DM/IR", "UbiComp": "HCI",
    "recsys": "DM/IR", "iui": "HCI", "dac": "Architecture", "pldi": "SE/PL",
    "uist": "HCI", "hpca": "Architecture", "sc": "OS/HPC", "icdcs": "OS/HPC",
    "embc": "Medical", "eurosys": "OS/HPC", "ICME": "Multimedia", "vtc": "Network",
    "issta": "SE/PL", "asru/slt": "Speech", "vr": "AR/VR", "vlsi": "Circuits",
    "fpga": "Architecture", "sigmetrics": "OS/HPC", "sosp": "OS/HPC",
    "sensys": "Network", "mobisys": "Network", "cav": "SE/PL", "APEC": "RF/Power",
    "conext": "Network", "bibm": "Medical", "ismar": "AR/VR", "EuCAP": "RF/Power",
    "mmsys": "Network", "ccnc": "Network", "IMS": "RF/Power", "humanoids": "Robotics",
    "mobicom": "Network", "RFIC": "Circuits", "siggrapha": "Graphics",
    "SID": "Display/Optics", "iTherm": "Thermal", "SPIEarvrmr": "Display/Optics",
    "SPIEopto": "Display/Optics", "ACS": "Materials", "APS": "Materials",
    "EFFT": "Food", "ict": "Thermal", "IIR": "Thermal", "MRS": "Materials",
    "IFT": "Food",
}

# 두 엑셀이 같은 학회를 다르게 적는다. 우수 학회 List의 약어 -> AI Specialist
# List의 약어. 이 표가 없으면 NeurIPS나 SIGKDD 같은 학회가 인정 목록에 있는데도
# ai_specialist=False 로 잘못 표시된다.
AI_SPECIALIST_ALIASES = {
    "nips": "neurips",
    "kdd": "sigkdd",
    "mm": "acmmm",
    "bigdataconf": "bigdata",
    "siggrapha": "siggraphasia",
    "nsdi": "usenixnsdi",
    "osdi": "usenixosdi",
}


def normalize_abbr(raw: str) -> str:
    """약어를 비교 가능한 형태로 정규화한다.

    'VLDB/PVLDB' 같은 별칭 표기는 앞쪽만 취하고, 공백과 기호를 지운다.
    두 엑셀이 같은 학회를 다르게 적는 경우(NeurIPS vs nips)를 흡수하기 위함이다.
    """
    first = str(raw).split("/")[0]
    return re.sub(r"[^a-z0-9]", "", first.lower())


def _read_grade_rows(path: Path) -> list[tuple[str, str, str]]:
    import openpyxl

    ws = openpyxl.load_workbook(path, data_only=True)["Sheet1"]
    out = []
    for row in ws.iter_rows(min_row=5, values_only=True):
        abbr, full_name = row[3], row[4]
        if not abbr:
            continue
        out.append((str(abbr).strip(), str(row[2]).strip(), str(full_name or "").strip()))
    return out


def _read_ai_specialist_abbrs(path: Path) -> set[str]:
    import openpyxl

    ws = openpyxl.load_workbook(path, data_only=True)["Sheet1"]
    found = set()
    for row in ws.iter_rows(min_row=5, values_only=True):
        if not row[3]:
            continue
        for part in str(row[3]).split("/"):
            found.add(normalize_abbr(part))
    return found


def build_registry(grade_xlsx: Path, ai_xlsx: Path) -> list[dict]:
    ai_abbrs = _read_ai_specialist_abbrs(ai_xlsx)
    entries = []
    for abbr, grade, full_name in _read_grade_rows(grade_xlsx):
        # 결합 행('iccv/eccv')은 구성원이 전부 목록에 있을 때만 True로 본다.
        parts = [normalize_abbr(p) for p in abbr.split("/")]
        raw_parts = [p.strip() for p in abbr.split("/")]
        entries.append({
            "abbr": abbr,
            # 표시명. 기본값은 엑셀 약어이고, 사람이 'CVPR'처럼 다듬는다.
            "display": abbr,
            "full_name": full_name,
            "grade": grade,
            "ai_specialist": all(
                AI_SPECIALIST_ALIASES.get(p, p) in ai_abbrs for p in parts
            ),
            "field": FIELD_ASSIGNMENT.get(abbr),
            "homepage": None,
            # 결합 행(격년 교대 학회 쌍)만 members를 갖는다.
            # 병합 단계가 구성원을 각각 조회한 뒤 차기 회차가 이른 쪽을 대표로 삼는다.
            "members": (
                [{"display": p, "sources": {"ai_deadlines": None, "ccfddl": None}}
                 for p in raw_parts]
                if len(raw_parts) > 1 else None
            ),
            "sources": {"ai_deadlines": None, "ccfddl": None},
        })
    return entries


def load_registry(path: Path = REGISTRY_PATH) -> list[dict]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data["conferences"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--diff", action="store_true",
                        help="파일을 쓰지 않고 기존 registry와의 차이만 출력")
    args = parser.parse_args()

    if not GRADE_XLSX.exists():
        print(f"엑셀을 찾을 수 없습니다: {GRADE_XLSX}", file=sys.stderr)
        print("이 스크립트는 엑셀이 로컬에 있을 때만 실행합니다.", file=sys.stderr)
        return 1

    entries = build_registry(GRADE_XLSX, AI_XLSX)
    unmapped = [e["abbr"] for e in entries if not e["field"]]
    if unmapped:
        print(f"분야 매핑이 없는 약어: {unmapped}", file=sys.stderr)
        print("FIELD_ASSIGNMENT에 추가한 뒤 다시 실행하세요.", file=sys.stderr)
        return 1

    if args.diff:
        if not REGISTRY_PATH.exists():
            print("기존 registry.yaml이 없습니다. --diff 없이 실행하세요.")
            return 0
        old = {e["abbr"]: e for e in load_registry()}
        new = {e["abbr"]: e for e in entries}
        for abbr in sorted(new.keys() - old.keys()):
            print(f"  추가: {abbr} ({new[abbr]['grade']})")
        for abbr in sorted(old.keys() - new.keys()):
            print(f"  삭제: {abbr}")
        for abbr in sorted(old.keys() & new.keys()):
            if old[abbr]["grade"] != new[abbr]["grade"]:
                print(f"  등급 변경: {abbr} {old[abbr]['grade']} -> {new[abbr]['grade']}")
            if old[abbr]["ai_specialist"] != new[abbr]["ai_specialist"]:
                print(f"  AI Specialist 변경: {abbr} -> {new[abbr]['ai_specialist']}")
        print("\nhomepage와 sources는 손으로 붙인 값이라 자동 반영하지 않습니다.")
        return 0

    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(
        yaml.safe_dump({"conferences": entries}, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    print(f"{len(entries)}개 학회를 {REGISTRY_PATH}에 기록했습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
