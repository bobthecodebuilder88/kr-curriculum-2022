"""별책 원문에서 [코드] 진술문 추출.

줄 단위가 아니라 코드 "등장 위치(span)" 단위로 스캔한다. 한 줄에 코드가 여러 개
붙어 나오는 경우(예: 별책12:521 "[9음03-01] … [9음03-02] … [9음03-03] …")가
실제로 여러 과목에 걸쳐 있어, 줄 앞머리만 보는 방식은 뒤에 붙은 코드를 전부 놓친다.

각 코드의 진술문 후보 구간은 "자기 마커 끝 ~ (다음 코드 등장 | 다음 섹션 헤더) 중
먼저 오는 것"으로 자른다. 섹션 헤더를 건너뛰어 이어붙이지 않는다 — 그렇게 이어붙이면
다른 코드의 해설과 접합된, 원문에 없던 문장이 만들어진다(별책16 9생베02-03 인근).

원칙: 본문(성취기준 목록) 등장에서만 진술문을 취한다. 해설/고려 사항 재등장은
같은 코드의 중복 억제에만 쓰고, 진술문 출처로는 절대 쓰지 않는다 — 본문 파싱이
실패해도 해설 문장을 진술문 자리에 채워 넣지 않는다("없음"이 "지어냄"보다 낫다).
"""
import json
import re
import bisect
from pathlib import Path
from pipeline.clean import load_text
from pipeline.codes import find_codes, find_codes_with_spans, _CLOSE_LIKE

# 섹션 헤더 열거자: 마크다운/불릿 접두 뒤의 "(1)" "1." "(가)" "나." "Ⅰ." 형태.
# 실측상 본문 재개 헤더는 전부 이 형태다(예: "## (3) 창작", "## **나. 성취기준**",
# "## ⋅ (3) 사회 공동체와의 관계", "(2) 타인과의 관계").
_ENUM_HEADER = re.compile(
    r"^[\s#>*•\-⋅∙·©§○◦□■◇]*\**\s*"
    r"(?:\(?\d{1,2}\)|\d{1,2}\.|\(?[가-힣]\)|[가-힣]\.|[ⅠⅡⅢⅣⅤ]\.?|[①-⑳])"
    r"\s*\**\s*\S"
)
_MD_HEADING = re.compile(r"^\s*#{1,6}\s*\S")


def _header_kind(line: str):
    """None | 'commentary' | 'body'.

    해설/고려 사항 헤더는 commentary 구간을 연다. 그 구간은 "다음 헤더"에서 닫히는데,
    본문 재개 헤더는 '성취기준'이라는 낱말을 전혀 쓰지 않는 내용 영역 제목인 경우가
    대부분이라(별책6 도덕은 '나. 성취기준' 헤더가 아예 0개) 해설 헤더만 인식하면
    첫 해설 이후 문서 전체가 영구히 commentary로 잠긴다. 그래서 '헤더 일반'을 본다.
    """
    s = line.strip()
    if not s or len(s) > 40:
        return None
    # 진술문·해설 본문은 헤더가 아니다. 코드가 박힌 줄도 목록 항목이지 헤더가 아니다.
    if s.endswith("다.") or s.endswith("다") or find_codes(s):
        return None
    if "성취기준" in s and ("해설" in s or (("고려" in s or "고러" in s) and "사항" in s)):
        return "commentary"
    return "body" if _ENUM_HEADER.match(s) or _MD_HEADING.match(s) else None


# 해설 항목은 코드 뒤가 거의 항상 이 어구로 시작한다("이 성취기준은/의 …").
# 섹션 상태가 헤더를 놓쳤을 때를 위한 2차 안전망 — 상태와 독립으로 동작한다.
_COMMENTARY_PREFIX = re.compile(r"^이\s*성취기준")
_TERMINATOR = re.compile(r"(다\.)(?=\s|$|[\[〔【［)\]〕】］\"'”’」』])")
# 코드 마커의 닫는 괄호가 span 밖에 남는 경우(3단 코드는 괄호를 span에 포함하지 않음).
# OCR이 닫는 괄호를 숫자로 잘못 읽은 경우도 뗀다 — 별책16:16620 "[12스어04-048 간단한 …"의
# "8"이 그것. 숫자 뒤에 공백이 올 때만 떼므로 "1cm와 1mm…"(4수03-16)는 손대지 않는다.
# 줄바꿈은 절대 지우지 않는다 — 빈 줄은 구조적 중단 신호라서 지우면 표가 깨진 구간에서
# 뒤쪽 문장 블록을 앞쪽 코드에 잘못 붙인다(별책16 "(5) 문화" 4코드 3문장 사례).
_LEAD_JUNK = re.compile(rf"^(?:[ \t{_CLOSE_LIKE[1:-1]}]+|\d(?=\s))+")


# 불릿 글리프. 낱말 사이 구분자로도 쓰이므로(성폭력⋅성매개감염병) 조각의 양 끝에서만 뗀다.
_EDGE_MARKUP = r"[\s⋅•·∙\-–—*©§]"
_TRAILING_MARKUP = re.compile(rf"{_EDGE_MARKUP}+$")
_LEADING_MARKUP = re.compile(rf"^{_EDGE_MARKUP}+")
# 정상 12개 교과 진술문 2470건의 최단 길이(별책17 9한02-03 "글을 바르게 풀이한다." 12자).
# 이보다 짧은 조각은 진술문이 될 수 없으므로 빈 줄을 건너 이어붙이지 않는다.
_MIN_BRIDGE = 12


def _statement_in_window(window: str):
    """구간 안에서 '다.' 종결까지 문단을 이어붙인다.
    반환: (진술문, 명시적 종결자 여부, 조립 중 마크업을 떼어냈는지).

    빈 줄을 건너뛰어 잇는 것은 원문이 쪽·단 경계에서 진술문을 끊어 놓기 때문인데,
    별책16처럼 표가 세로로 조각난 문서에서는 빈 줄 너머가 *다른 코드*의 문장이다
    (별책16:3682 "[9생중02-03] 간단한" + 빈 줄 + 3684행은 9생중02-02의 문장).
    그래서 모아 둔 조각이 진술문이라 할 만한 길이가 됐을 때만 건넌다.
    """
    buf, stripped = "", False
    for para in re.split(r"\n[ \t]*\n", _LEAD_JUNK.sub("", window)):
        piece = re.sub(r"\s+", " ", para).strip()
        if not buf and not piece:
            break  # 아직 시작도 못했는데 문단 경계 — 구조적 중단
        if not piece:
            continue
        if buf:
            if not re.search(r"[가-힣]", piece) or len(buf) < _MIN_BRIDGE:
                # 내용 없는 조각이거나, 진술문이라기엔 너무 짧은 조각에서 건너뛰는 경우.
                # 이어붙이면 원문에 없던 문장이 만들어지므로 여기서 끊는다.
                break
            # 쪽 경계에 변환기가 끼워 넣은 불릿은 부처 원문이 아니다. 조각 양 끝의
            # 것만 떼고, 뗀 사실은 needs_review로 남긴다 — 조립 자체가 의심스럽다는 뜻.
            head, tail = _LEADING_MARKUP.sub("", piece), _TRAILING_MARKUP.sub("", buf)
            stripped = stripped or head != piece or tail != buf
            buf, piece = tail, head
        buf = f"{buf} {piece}".strip() if buf else piece
        tm = _TERMINATOR.search(buf)
        if tm:
            return re.sub(r"\s+", " ", buf[: tm.end(1)]).strip(), True, stripped
    if buf.endswith("다"):
        # OCR이 종결 마침표만 지운 경우 — 있는 그대로 회수하되 종결자를 못 찾았다는
        # 사실은 needs_review로 계속 남긴다(호출부에서 처리).
        return buf, False, stripped
    return None, False, stripped


_LATIN_RUN = re.compile(r"[A-Za-z]{2,}")
# 실측된 정상 라틴 토큰은 단위(cm, mm, km, kg, mL, pH)이거나 대문자 약어(DNA, SSI,
# ATP, LMO, ENSO, SDGs)뿐이다. 이 두 모양만 통과시킨다.
_UNIT_OR_ACRONYM = re.compile(r"^(?:[A-Z]{2,}s?|[A-Za-z]{1,2})$")


def _looks_garbled(statement: str, subject: str) -> bool:
    """OCR이 한글 단어를 통째로 삼키고 라틴 문자 잡음으로 대체한 흔적을 잡는다.

    실측 결과 라틴 런은 두 부류로만 나타난다. 수학·과학·사회에는 단위·약어(cm, kg,
    mL, pH, DNA, SDGs, SSI, ATP, LMO, ENSO)만 22건, 제2외국어에는 한국어 낱말을
    삼킨 잡음(LAS←느낌을, USS←자료를, SS←등을, FLAS, WHS …)만 148건 나오고 서로
    섞이지 않는다. 영어 진술문에는 라틴 런이 한 건도 없다.
    """
    if not statement:
        return False
    if subject in ("영어", "제2외국어"):
        # 이 두 과목의 진술문은 전부 한국어 문장이라 라틴 런 자체가 OCR 잡음이다.
        # (브리프는 이 두 과목에서 라틴이 정상이라 보고 한글 비율만 쓰라고 했으나,
        #  실측 148건 전수가 잡음이고 비율 테스트는 그중 18건만 잡는다 — §보고서 참조.)
        if _LATIN_RUN.search(statement):
            return True
        hangul = len(re.findall(r"[가-힣]", statement))
        latin = len(re.findall(r"[A-Za-z]", statement))
        return hangul + latin > 0 and (hangul / (hangul + latin)) < 0.80
    # 그 외 과목: 단위·약어 모양이 아닌 라틴 런만 잡음으로 본다. 단위는 숫자나 인용부호,
    # 위첨자(cm², 1m³)에 붙어 조사가 곧바로 오지 않는 경우가 많아 조사 유무로는 못 가린다.
    return any(not _UNIT_OR_ACRONYM.match(m.group()) for m in _LATIN_RUN.finditer(statement))


def extract_from_text(text: str, subject: str, source_label: str) -> list:
    spans = find_codes_with_spans(text)  # [(code, start, end), ...] 등장 순

    headers, pos = [], 0
    for line in text.split("\n"):
        kind = _header_kind(line)
        if kind:
            headers.append((pos, kind))
        pos += len(line) + 1

    boundaries = sorted({s for _, s, _ in spans} | {h for h, _ in headers} | {len(text)})

    def next_boundary_after(offset):
        i = bisect.bisect_right(boundaries, offset)
        return boundaries[i] if i < len(boundaries) else len(text)

    state, hi = "body", 0
    by_code = {}  # code -> {"statement": str|None, "term_found": bool, "body": bool}
    for code, start, end in spans:
        while hi < len(headers) and headers[hi][0] < start:
            state = headers[hi][1]
            hi += 1

        entry = by_code.setdefault(code, {"statement": None, "term_found": False,
                                          "body": False, "stripped": False})
        window = text[end:next_boundary_after(end)]
        head = re.sub(r"\s+", " ", _LEAD_JUNK.sub("", window)).strip()[:20]
        # 원문 PDF의 해설 상자가 본문 목록 한가운데로 끼어 들어간 문서가 있다(별책8:1324
        # — "(가) 성취기준 해설" 헤더 뒤 세 줄이 해설, 그 다음 줄부터 다시 본문인데 본문
        # 재개 헤더가 없다). 그런 문서에서 해설 항목은 예외 없이 불릿(•)을 달고 본문 항목은
        # 줄 맨 앞(0열)에 온다. 0열 등장은 섹션 상태와 무관하게 본문으로 본다.
        line_start = text.rfind("\n", 0, start) + 1
        at_col0 = not text[line_start:start].strip()
        if (state == "commentary" and not at_col0) or _COMMENTARY_PREFIX.match(head):
            # 해설/고려 사항 등장 — 존재만 기록(위 setdefault). 진술문 출처가 될 수 없다.
            continue
        entry["body"] = True

        if entry["statement"] is None:
            statement, term_found, stripped = _statement_in_window(window)
            if statement is not None:
                entry["statement"] = statement
                entry["term_found"] = term_found
                entry["stripped"] = stripped

    recs = []
    for code, info in by_code.items():
        statement, term_found = info["statement"], info["term_found"]
        recs.append({
            "code": code, "subject": subject, "statement": statement, "source": source_label,
            # 진술문은 본문 등장에서만 나온다 — 해설은 출처가 될 수 없으므로 null.
            "statement_source": "body" if statement else None,
            # 본문 목록에 한 번도 안 나오고 해설에서만 보인 코드. 진술문은 못 주지만
            # 코드의 존재는 원문이 증언하므로 레코드를 지우지는 않는다 — 지우면
            # verify.py가 실재하는 성취기준을 "FAKE"로 몰아세운다.
            "commentary_only": not info["body"],
            "needs_review": statement is None or not term_found or info["stripped"]
                            or _looks_garbled(statement, subject),
        })
    return recs


# 코드의 학년+약어 접두: 6사12-02 → 6사, 12심독02-02 → 12심독, 10공국1-01-01 → 10공국
_PREFIX = re.compile(r"^((?:10|12|[2469])\D+)")


def drop_cross_references(recs: list) -> tuple:
    """다른 별책이 본문 진술문으로 정의한 코드를 해설에서 인용만 한 레코드를 걷어낸다.

    별책5:1727 국어 고려 사항은 사회 성취기준 [6사12-02]를 인용한다 — 국어 레코드로
    남기면 "국어가 6사12-02를 정의한다"는 거짓이 되고, 진짜 정의는 이미 사회에 있다.

    두 가지를 모두 만족해야 인용으로 본다. (1) 그 코드를 다른 별책이 본문 진술문으로
    정의하고 있고, (2) 그 코드의 학년+약어 접두가 자기 문서 본문에는 한 번도 없다.
    (2)가 없으면 코드 네임스페이스 충돌에 걸린다 — 12심독은 제2외국어에서 '심화 독일어',
    영어에서 '심화 영어 독해'로 서로 다른 성취기준인데, 제2외국어의 12심독02-02가
    영어 쪽 정의를 인용한 것으로 오판되어 사라진다. 별책16에는 12심독 본문이 실제로
    있으므로 (2)가 이를 막는다.

    반대로 별책16의 해설 전용 코드들(12아회01-01, 9생종04-02 …)은 코퍼스 어디에도
    본문 정의가 없다 — 인용이 아니라 OCR이 본문 목록을 지운 자리이므로 남긴다.
    반환: (남길 레코드, 제외한 레코드).
    """
    def prefix(code):
        m = _PREFIX.match(code)
        return m.group(1) if m else code

    defined = {r["code"] for r in recs if r["statement"]}
    own = {(r["subject"], prefix(r["code"])) for r in recs if r["statement"]}

    def is_cross(r):
        return (r["commentary_only"] and r["code"] in defined
                and (r["subject"], prefix(r["code"])) not in own)

    return [r for r in recs if not is_cross(r)], [r for r in recs if is_cross(r)]


def main():
    from pipeline.sources import BYLAWS
    out = Path(__file__).resolve().parent.parent / "data" / "raw"
    out.mkdir(parents=True, exist_ok=True)
    recs = [r for e in BYLAWS
            for r in extract_from_text(load_text(e["path"]), e["subject"], e["source_label"])]
    # 교차참조 판정은 코퍼스 전체를 봐야 가능하다(한 문서만 봐서는 인용인지 OCR 구멍인지
    # 구별할 수 없다). 문서별 추출은 그대로 두고 여기서만 대조한다.
    kept, cross = drop_cross_references(recs)
    with open(out / "standards.jsonl", "w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    for r in cross:
        defined_in = sorted({o["subject"] for o in kept
                             if o["code"] == r["code"] and o["statement"]})
        print(f"교차참조 제외: {r['subject']} / {r['code']} — 본문 정의는 {defined_in}에 있음")
    print(f"standards.jsonl: {len(kept)} records ({len(cross)} excluded)")


if __name__ == "__main__":
    main()
