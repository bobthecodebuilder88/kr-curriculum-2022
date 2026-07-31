#!/usr/bin/env python3
"""문서 속 성취기준 인용 검증 CLI (stdlib only). exit 0=clean, 1=문제 발견.

사용례:  verify.py 수업지도안.md --school 중   /   cat doc.md | verify.py -
검사: ①코드 실재 ②인접 진술문 verbatim 일치 ③학교급 일관성
"""
import argparse
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 코드 표기 변형 흡수 규칙은 pipeline/codes.py 와 같다. 배포본은 scripts/ 와 data/ 만
# 복사해도 돌아가야 해서 import 하지 않고 옮겨 적었다 — pipeline/codes.py 의 약어·대시
# 규칙을 고치면 여기도 같이 고쳐야 한다. 괄호 약어(9사(일사)01-01)와 로마숫자
# 꼬리(12영Ⅰ-01-01)를 빼면 실재 코드 150건을 못 읽고 지나친다.
_ABBR = r"[가-힣]{1,4}(?:\([가-힣]{1,4}\))?(?:[ⅠⅡ]|I{1,2})?"
_ABBR3 = r"[가-힣]{1,4}(?:[ⅠⅡ]|I{1,2})|[가-힣]{2}\d"
_DASH = r"[-–—‒−]"
_CLOSE_LIKE = r"[\]\)\}〕】］|]"
# 3단: 10공국1-01-01 / 12영Ⅰ-01-01
_THREE = re.compile(rf"(1[02])({_ABBR3}){_DASH}(\d{{2}}){_DASH}(\d{{2}})")
# 2단: 9수01-01 / 12화언01-05 / 9사(일사)01-01. pipeline 과 달리 약어와 영역 번호
# 사이 공백을 허용하지 않는다 — PDF 변환 산물이 아니라 사람이 쓴 문서를 읽기 때문이고,
# 허용하면 "12월 01-05" 같은 날짜를 코드로 오인한다.
_TWO = re.compile(rf"(10|12|[2469])({_ABBR})(\d{{2}}){_DASH}(\d{{2}})({_CLOSE_LIKE})?")
_THIRD_GROUP = re.compile(rf"{_DASH}\d{{2}}")


def find_codes(text):
    """[(코드, 진술문 후보 시작 오프셋), ...] 등장 순서대로."""
    found = []
    for m in _THREE.finditer(text):
        found.append((m.start(), f"{m.group(1)}{m.group(2)}-{m.group(3)}-{m.group(4)}", m.end()))
    taken = [(s, e) for s, _, e in found]  # 3단이 우선, 겹침 방지
    for m in _TWO.finditer(text):
        if any(a <= m.start() < b for a, b in taken):
            continue
        if m.group(5) is None and _THIRD_GROUP.match(text, m.end()):
            continue  # 3단 코드의 앞 두 마디를 잘라 온 것 — 코드가 아니다
        found.append((m.start(), f"{m.group(1)}{m.group(2)}{m.group(3)}-{m.group(4)}", m.end()))
    return [(c, e) for _, c, e in sorted(found)]


def db():
    """코드 하나에 레코드가 여럿일 수 있다 — 교과가 다르면 같은 코드가 실재한다."""
    idx = json.loads((ROOT / "data/index.json").read_text(encoding="utf-8"))
    out = {}
    for f in idx["files"]:
        for line in (ROOT / f["path"]).read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                out.setdefault(r["code"], []).append(r)
    return out


def _norm(s):
    return re.sub(r"[\s.,·\]\)〕】］|」』》]+", "", s or "")


def _ratio(rec, tail):
    """코드 뒤 텍스트가 이 레코드의 진술문을 인용한 정도. 인용이 아니면 -1."""
    if not rec["statement"]:
        return -1.0
    frag = _norm(tail)[: len(_norm(rec["statement"]))]
    if len(frag) < 15:
        return -1.0  # 인용이라 볼 만한 길이가 아니다
    return difflib.SequenceMatcher(None, _norm(rec["statement"]), frag).ratio()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="검사할 파일 경로 또는 - (stdin)")
    ap.add_argument("--school", choices=["초", "중", "고"])
    a = ap.parse_args()
    text = sys.stdin.read() if a.target == "-" else Path(a.target).read_text(encoding="utf-8")
    text = unicodedata.normalize("NFC", text.replace("\x00", ""))

    D = db()
    problems = 0
    warns = 0
    seen = set()
    said = set()  # 같은 코드를 여러 번 인용해도 같은 지적은 한 번만 낸다
    for code, end in find_codes(text):
        seen.add(code)
        recs = D.get(code)
        if not recs:
            if ("FAKE", code) not in said:
                said.add(("FAKE", code))
                print(f"FAKE  [{code}] — 이 데이터셋에 없는 코드. 지어낸 코드이거나, "
                      f"이 데이터셋이 다루지 않는 과목(전문 교과·교양 등)이다. "
                      f"원문 고시본으로 확인하기 전에는 인용하지 마라")
                problems += 1
            continue
        # 코드 뒤 200자 안에 진술문이 인용됐으면 verbatim 검사.
        # 같은 코드가 여러 교과에 실재하면 인용문과 가장 가까운 레코드로 판정한다
        # (예: 12심독01-01은 영어와 제2외국어 양쪽에 서로 다른 성취기준으로 존재).
        # 인용이 없어 비길 때는 진술문이 있는 쪽을 고른다 — 12스문01-01처럼 한쪽만
        # 진술문이 비어 있는 코드에서 엉뚱하게 NOSTMT를 내지 않기 위해서다.
        tail = text[end: end + 200]
        rec = max(recs, key=lambda r: (_ratio(r, tail), r["statement"] is not None))
        ratio = _ratio(rec, tail)
        where = f" ({rec['subject']})" if len(recs) > 1 else ""

        if a.school and all(r["school"] != a.school for r in recs):
            if ("LEVEL", code) not in said:
                said.add(("LEVEL", code))
                print(f"LEVEL [{code}] — {recs[0]['school']} 성취기준인데 문서는 {a.school} 대상")
                problems += 1
        if rec["statement"] is None:
            if ("NOSTMT", code) not in said:
                said.add(("NOSTMT", code))
                print(f"NOSTMT [{code}]{where} — 코드는 실재하나 원문 손상으로 진술문 미수록. "
                      f"인용문을 검증할 수 없으니 원문 고시본을 확인하라")
                problems += 1
        elif 0.55 < ratio < 0.92:
            if ("MISMATCH", code) not in said:
                said.add(("MISMATCH", code))
                print(f"MISMATCH [{code}]{where} — 진술문이 원문과 다름\n  원문: {rec['statement']}")
                problems += 1
        elif ratio >= 0.92 and rec.get("statement_verified") is not True:
            # 인용은 맞았지만 그 원문 자체가 교차검증되지 않았다. 공문서에 옮기기 전에
            # 알아야 할 사실이라 알리되, 인용자의 잘못이 아니므로 종료 코드는 건드리지 않는다.
            if ("WARN", code) not in said:
                said.add(("WARN", code))
                src = ("두 출처가 서로 다른 문장을 싣고 있다"
                       if rec.get("statement_verified") is False
                       else "대조할 독립 출처가 없어 교차검증하지 못했다")
                print(f"WARN  [{code}]{where} — 인용은 데이터셋 원문과 일치하나 그 원문이 미검증: "
                      f"{src}. 공식 문서에 쓰기 전 고시본 확인 권장")
                warns += 1

    if problems == 0:
        tail_note = f" (미검증 진술문 인용 {warns}건은 WARN 참고)" if warns else ""
        print(f"OK — 검사한 코드 {len(seen)}개 모두 정상{tail_note}")
        sys.exit(0)
    print(f"\n문제 {problems}건 발견 (검사 코드 {len(seen)}개)")
    sys.exit(1)


if __name__ == "__main__":
    main()
