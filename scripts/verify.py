#!/usr/bin/env python3
"""문서 속 성취기준 인용 검증 CLI (stdlib only). exit 0=clean, 1=문제 발견.

사용례:  verify.py 수업지도안.md --school 중   /   cat doc.md | verify.py -
검사: ①코드 실재 ②진술문 verbatim 일치 ③성취수준(A~E) 서술문 ④학교급 일관성

판정 원칙 — 상대 유사도 하나로 "고쳐 쓴 인용"과 "코드만 언급한 산문"을 동시에
가를 수 없다. 정확한 인용이 통과할 만큼 문턱을 낮추면 한 글자 변조가 같이 통과하고
(길이 n 문장의 한 글자 치환은 유사도 (n-1)/n 이라 절대 낮아지지 않는다), 변조를
잡을 만큼 높이면 산문이 무고당한다. 그래서 기준을 유사도가 아니라 일치로 뒤집었다:

  1. 정규화 후 원문이 그대로 들어 있으면 정상. 길이와 무관하게 성립한다.
  2. 아니면 "인용을 시도한 자리인가"를 따로 판정한다 — ⓐ원문과 겹치는 도입부,
     ⓑ다른 성취기준의 진술문이 그 자리에 통째로 들어 있음, ⓒ코드가 문장에서
     떨어져 있고 뒤에 완결된 서술문이 온다(= 인용 형식 그 자체).
  3. 셋 중 아무것도 아니면 인용이 아니라 산문이다 — 건드리지 않는다.

무고는 미검출만큼 나쁘다. `[9수01-01]을 중심으로 차시를 구성하였다` 같은 산문은
반드시 통과해야 한다.
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

# --- 판정 상수 ---------------------------------------------------------------
WINDOW = 400          # 코드 뒤 진술문을 찾는 범위(원문 최장 150자 + 도입부 여유)
LEVEL_WINDOW = 1200   # 성취수준 서술문을 찾는 범위(코드 하나에 A~E 다섯 줄이 붙는다)
ALTERED = 0.55        # 이만큼 닮았으면 "이 진술문을 인용하려다 고쳤다"로 본다
HEAD_SLACK = 12       # `성취기준:` 같은 표지를 지나 인용이 시작될 수 있는 여유(정규화 기준)
EVIDENCE_MIN = 12     # 다른 성취기준의 문장으로 인정할 최소 길이
MIN_CLAIM = 15        # 인용 자리에 놓인 문장으로 인정할 최소 길이
MIN_LEVEL_CLAIM = 10  # `A수준:` 뒤 서술문으로 인정할 최소 길이

# 가운뎃점은 U+22C5·U+FF65·U+318D·U+00B7 네 가지가 원문에 섞여 있고 편집기·폰트에 따라
# 바뀐다. 공백과 함께 지워 흡수한다 — 이 프로젝트에서 이미 오탐을 낸 자리다
# (`준언어⋅비언어적`, `8⋅15 광복과 6⋅25 전쟁`). 그 밖의 문장 부호는 원문의 일부라 남긴다.
_NORM = re.compile(r"[\s·⋅･ㆍ・∙•]+")
# 코드를 감싼 닫는 괄호·백틱은 코드 표기의 일부지 인용문의 일부가 아니다.
_CLOSERS = "]})〕】］|`"
_HEAD_JUNK = re.compile(r"^[\s\]\})〕】］|`:：*>·⋅･ㆍ]+")
# 수업 계획의 낱말이되 진술문 3255건이 한 번도 쓰지 않는 것들(`학생`만 1건). 고시된
# 성취기준은 학습자를 주어로 부르지 않고 차시·평가 운영을 말하지 않는다. 이 낱말이 든
# 문장은 성취기준을 인용한 것이 아니라 성취기준을 놓고 쓴 산문이라, 인용 자리에 있어도
# 무고하지 않는다 — `[9수01-01] 학생들이 흥미를 느끼도록 실생활 사례를 활용한다.` 류.
# 데이터를 다시 빌드하면 이 목록의 전제(등장 0건)도 다시 재야 한다.
_META = ("성취기준", "성취수준", "차시", "단원", "지도안", "교사", "학생", "모둠",
         "교과서", "학습지", "활동지", "학습목표", "평가계획", "지필평가", "수행평가",
         "형성평가", "총괄평가", "채점", "루브릭", "피드백", "유의점", "준비물")
_LEVEL_LINE = re.compile(r"(?:^|[^A-Za-z])([A-Ea-e])\s*(?:수준|등급)\s*[:：]\s*(\S.*)")


def find_codes(text):
    """[(코드, 시작 오프셋, 끝 오프셋), ...] 등장 순서대로."""
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
    return [(c, s, e) for s, c, e in sorted(found)]


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
    return _NORM.sub("", unicodedata.normalize("NFC", s or ""))


def statement_index(D):
    """정규화 진술문의 앞머리 → [(정규화 진술문, 코드)]. 인용 자리에 다른 성취기준의
    문장이 통째로 들어앉은 경우를 잡는 데 쓴다 — 코드를 잘못 붙였다는 결정적 증거다."""
    idx = {}
    for code, recs in D.items():
        for r in recs:
            s = _norm(r["statement"])
            if len(s) >= EVIDENCE_MIN:
                idx.setdefault(s[:EVIDENCE_MIN], []).append((s, code))
    return idx


def _head(window):
    """인용문이 시작될 자리 — 코드를 감싼 닫는 괄호·표 구분자·여백을 지난 지점부터."""
    return _HEAD_JUNK.sub("", window)


def _stands_apart(window):
    """코드가 문장에 조사로 붙어 있지 않고 따로 떨어져 있는가.
    `[9수01-01]을 중심으로`는 언급, `[9수01-01] 소인수분해의…`는 인용 형식이다."""
    rest = window.lstrip(_CLOSERS)
    return bool(rest) and not rest[0].isalnum()


def _slot_sentence(window):
    """인용 자리에 놓인 완결된 서술문. 인용 형식이 아니면 None.

    성취기준 진술문은 3255건이 모두 `~다`로 끝난다(마침표는 OCR 손상으로 50건이 빠졌다).
    그 모양을 갖춘 문장이 코드에서 떨어진 바로 뒤 자리에 오면 그건 인용 형식이다 —
    원문과 얼마나 닮았는지와 무관하게. 이 판정이 없으면 "코드는 실재하는데 문장은
    통째로 딴것"(2015 개정 혼입, 짧은 진술문 사각지대)이 유사도 아래로 빠져나간다.
    대신 이 자리에 지도 메모를 적은 문서가 무고당한다 — 그 대가를 _META 로 줄인다."""
    if not _stands_apart(window):
        return None
    seg = _head(window).split("\n", 1)[0].strip()
    if seg.endswith("…") or seg.endswith("..."):
        return None  # 줄여 인용한 자리 — 원문과 다르다고 부를 수 없다
    body = seg.rstrip(" .。」』”’\"'|*)]}")
    if not body.endswith("다"):
        return None
    if any(w in seg for w in _META):
        return None  # 성취기준을 인용한 게 아니라 성취기준에 대해 쓴 문장이다
    return seg if len(_norm(seg)) >= MIN_CLAIM else None


def _quoted_elsewhere(head, code, sindex):
    """인용 자리에 다른 성취기준의 진술문이 그대로 들어 있으면 그 코드를 돌려준다."""
    for i in range(min(HEAD_SLACK, len(head)) + 1):
        for s2, code2 in sindex.get(head[i:i + EVIDENCE_MIN], ()):
            if code2 != code and head.startswith(s2, i):
                return code2, s2
    return None


def _match(rec, window):
    """(원문이 그대로 있는가, 도입부 유사도). 충돌 코드에서 어느 교과의 성취기준을
    인용했는지 고르는 점수이기도 하다."""
    s = _norm(rec["statement"])
    if not s:
        return (0, -1.0)
    if s in _norm(window):
        return (1, 1.0)
    head = _norm(_head(window))
    return (0, difflib.SequenceMatcher(None, s, head[: len(s)]).ratio())


def check_statement(rec, window, sindex):
    """(태그, 설명) 또는 None. 태그는 MISMATCH / WARN."""
    exact, ratio = _match(rec, window)
    if exact:
        if rec.get("statement_verified") is not True:
            # 인용은 맞았지만 그 원문 자체가 교차검증되지 않았다. 공문서에 옮기기 전에
            # 알아야 할 사실이라 알리되, 인용자의 잘못이 아니므로 종료 코드는 건드리지 않는다.
            src = ("두 출처가 서로 다른 문장을 싣고 있다"
                   if rec.get("statement_verified") is False
                   else "대조할 독립 출처가 없어 교차검증하지 못했다")
            return ("WARN", f"인용은 데이터셋 원문과 일치하나 그 원문이 미검증: {src}. "
                            f"공식 문서에 쓰기 전 고시본 확인 권장")
        return None
    if ratio >= ALTERED:
        return ("MISMATCH", "진술문이 원문과 다름")
    other = _quoted_elsewhere(_norm(_head(window)), rec["code"], sindex)
    if other:
        return ("MISMATCH", f"인용된 문장은 [{other[0]}]의 진술문이다 — 코드를 잘못 붙였거나 "
                            f"진술문을 잘못 가져왔다")
    if _slot_sentence(window):
        return ("MISMATCH", "코드 바로 뒤가 원문이 아닌 문장이다(2015 개정 진술문이거나 "
                            "지어낸 문장). 인용이라면 글자까지 원문과 같아야 하고, "
                            "지도 메모라면 코드에 붙이지 말고 줄을 나눠 적어라")
    return None


def check_levels(rec, region):
    """성취수준(A~E) 인용 검증. [(태그, 등급, 설명), ...]

    `A수준: …` 처럼 등급을 명시하고 콜론을 찍은 자리는 그 등급의 서술문을 인용하겠다는
    선언이라, 원문과 다르면 닮았는지와 무관하게 지적한다. 콜론이 없는 `A등급 (출처) …`
    같은 표기는 인용 선언이 아니라 목록 항목이라 건드리지 않는다."""
    out = []
    levels = rec.get("levels") or {}
    for line in region.split("\n"):
        m = _LEVEL_LINE.search(line)
        if not m:
            continue
        grade, claim = m.group(1).upper(), m.group(2).strip()
        if len(_norm(claim)) < MIN_LEVEL_CLAIM:
            continue
        if not levels:
            out.append(("LVLNONE", grade,
                        "이 성취기준에는 성취수준이 수록돼 있지 않아 인용을 검증할 수 없다. "
                        "원문 성취수준표를 확인하라"))
        elif grade not in levels:
            out.append(("LVLMISS", grade,
                        f"이 성취기준에 {grade}수준 서술문이 없다 "
                        f"(수록된 등급: {'·'.join(sorted(levels))}). 등급을 지어내지 마라"))
        elif _norm(levels[grade]) not in _norm(claim):
            swapped = next((g for g, t in levels.items()
                            if g != grade and _norm(t) and _norm(t) in _norm(claim)), None)
            why = f" — 실제로는 {swapped}수준 서술문이다" if swapped else ""
            out.append(("LVLDIFF", grade,
                        f"{grade}수준 서술문이 원문과 다름{why}\n  원문: {levels[grade]}"))
    return out


def verify(text, D, school=None):
    """[(태그, 코드, 교과, 메시지), ...]. WARN_ONLY 태그는 경고, 나머지는 문제."""
    sindex = statement_index(D)
    codes = find_codes(text)
    out = []
    said = set()  # 같은 코드를 여러 번 인용해도 같은 지적은 한 번만 낸다

    def say(key, tag, code, where, msg):
        if key not in said:
            said.add(key)
            out.append((tag, code, where, msg))

    for i, (code, _, end) in enumerate(codes):
        recs = D.get(code)
        if not recs:
            say(("FAKE", code), "FAKE", code, "",
                "이 데이터셋에 없는 코드. 지어낸 코드이거나, 이 데이터셋이 다루지 않는 "
                "과목(전문 교과·교양 등)이다. 원문 고시본으로 확인하기 전에는 인용하지 마라")
            continue
        # 검사 범위는 다음 코드가 나오기 전까지다. 여기서 자르지 않으면 옆 성취기준의
        # 진술문이 이 코드의 인용문으로 오인돼 무고가 난다.
        nxt = codes[i + 1][1] if i + 1 < len(codes) else len(text)
        window = text[end: min(nxt, end + WINDOW)]
        region = text[end: min(nxt, end + LEVEL_WINDOW)]
        # 같은 코드가 여러 교과에 실재하면 인용문과 가장 가까운 레코드로 판정한다
        # (예: 12심독01-01은 영어와 제2외국어 양쪽에 서로 다른 성취기준으로 존재).
        # 인용이 없어 비길 때는 진술문이 있는 쪽을 고른다 — 12스문01-01처럼 한쪽만
        # 진술문이 비어 있는 코드에서 엉뚱하게 NOSTMT를 내지 않기 위해서다.
        rec = max(recs, key=lambda r: _match(r, window) + (r["statement"] is not None,))
        where = f" ({rec['subject']})" if len(recs) > 1 else ""

        if school and all(r["school"] != school for r in recs):
            say(("LEVEL", code), "LEVEL", code, "",
                f"{recs[0]['school']} 성취기준인데 문서는 {school} 대상")
        if rec["statement"] is None:
            say(("NOSTMT", code), "NOSTMT", code, where,
                "코드는 실재하나 원문 손상으로 진술문 미수록. "
                "인용문을 검증할 수 없으니 원문 고시본을 확인하라")
        else:
            hit = check_statement(rec, window, sindex)
            if hit:
                msg = hit[1] + (f"\n  원문: {rec['statement']}" if hit[0] == "MISMATCH" else "")
                say((hit[0], code), hit[0], code, where, msg)
        for tag, grade, msg in check_levels(rec, region):
            say((tag, code, grade), tag, code, where, msg)
    return out


WARN_ONLY = {"WARN", "LVLNONE"}
_LABEL = {"FAKE": "FAKE ", "MISMATCH": "MISMATCH", "NOSTMT": "NOSTMT", "LEVEL": "LEVEL",
          "WARN": "WARN ", "LVLDIFF": "LVLDIFF", "LVLMISS": "LVLMISS", "LVLNONE": "LVLNONE"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="검사할 파일 경로 또는 - (stdin)")
    ap.add_argument("--school", choices=["초", "중", "고"])
    a = ap.parse_args()
    text = sys.stdin.read() if a.target == "-" else Path(a.target).read_text(encoding="utf-8")
    text = unicodedata.normalize("NFC", text.replace("\x00", ""))

    D = db()
    findings = verify(text, D, a.school)
    seen = {c for c, _, _ in find_codes(text)}
    problems = [f for f in findings if f[0] not in WARN_ONLY]
    warns = len(findings) - len(problems)
    for tag, code, where, msg in findings:
        print(f"{_LABEL[tag]} [{code}]{where} — {msg}")

    if not problems:
        tail = f" (미검증 인용 {warns}건은 WARN 참고)" if warns else ""
        print(f"OK — 검사한 코드 {len(seen)}개 모두 정상{tail}")
        sys.exit(0)
    print(f"\n문제 {len(problems)}건 발견 (검사 코드 {len(seen)}개)")
    sys.exit(1)


if __name__ == "__main__":
    main()
