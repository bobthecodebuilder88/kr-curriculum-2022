"""성취수준 문서 파서: 성취기준 코드별 A~E 수준 진술문 수집.

원문은 두 계열로 나온다.
  표 계열  — 마크다운 파이프 표(초1~2, 중 대부분, 고 일부). 엑셀 변환본(NaN 셀)도 여기.
  흘림 계열 — 표가 평문 줄로 풀린 형태(초3~4·5~6, 고 대부분). 61개 중 34개가 이쪽이다.

두 계열 모두 같은 규칙으로 묶는다: **한 코드의 수준 문자는 A쪽으로 되감기지 않는다.**
문자가 되감기면(E→A, C→A …) 거기서 새 코드 묶음이 시작된다. 코드 셀은 병합 셀이라
묶음의 첫 줄에 없을 수 있으므로(고등학교8. 역사과는 가운데 줄에 찍힌다) 묶음 전체에서 찾는다.

코드를 못 찾은 묶음은 통째로 버린다. 영역별 성취수준·일반적 특성 표에도 A~E 행이
있는데 이들은 코드가 없다 — 앞 코드에 얹으면 그 코드에 남의 진술문이 붙는다.
"""
import json
import re
from pathlib import Path

from pipeline.clean import clean_cell, load_text
from pipeline.codes import find_codes, find_codes_with_spans

_LETTERS = "ABCDE"
_ONLY_LETTER = re.compile(r"^[A-E]$")
# 셀 끝에 홀로 남은 수준 문자. 중등 영어는 "A<br>B"처럼 두 수준을 한 칸에 병합한다.
_TRAILING_LETTERS = re.compile(r"(?:^|\s)((?:[A-E]\s+)*[A-E])$")
# 쪽 넘김 때 본문 사이에 끼어드는 머리말·쪽번호·되풀이된 표 열 이름
_FURNITURE = re.compile(
    r"^(?:\d{1,4}"
    r"|[Ⅰ-Ⅿ]+.{0,40}"
    r"|.{0,20}2022\s*개정\s*교육과정.{0,60}"
    r"|(?:성취기준|영역)\s*별?\s*성취수준"
    r"|성취기준|영역|성취수준)$"
)


def _cells(line):
    """표 한 줄을 칸으로 나눈다. 앞뒤 파이프는 한 개씩만 떼어 빈 선두 칸을 살린다."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return s.split("|")


# 절 제목의 글머리(가./1./Ⅲ.). 한글 글머리를 '[가-하]' 범위로 쓰면 한글 음절 1만 자가
# 걸려 모든 줄이 제목이 되므로 실제로 쓰이는 글자만 나열한다.
_HEADING = re.compile(
    r"^(?:#+\s*)?\**\s*(?:[가나다라마바사아자차카타파하]|\d{1,2}|[Ⅰ-Ⅿ]+)\s*[.．]?\s*\**\s*(?=\S)"
)
_IN_REGION = re.compile(r"성취기준\s*별\s*성취수준")
_OUT_REGION = re.compile(r"영역\s*별\s*성취수준|예시\s*평가\s*도구")


def _region(line):
    """구역 표지면 (구역, 강한 표지인가), 아니면 None.

    표 머리행은 약한 표지다. 예시 평가 도구 절이 대상 성취기준의 수준표를 통째로
    다시 실으면서 똑같은 머리행을 쓰기 때문에(러시아어본은 한 코드가 7번 나온다),
    절 제목이 한 번이라도 나온 문서에서는 머리행으로 구역을 바꾸지 않는다."""
    s = line.strip()
    strong = True
    if s.startswith("#"):
        pass
    elif s.startswith("|"):
        strong = False
    elif len(s) <= 40 and _HEADING.match(s):
        pass
    else:
        return None
    if _OUT_REGION.search(s) or "_영역별" in s or " 영역별" in s:
        return False, strong
    if _IN_REGION.search(s) or "_성취기준별" in s:
        return True, strong
    return None


# 흘림 계열에서 진술문 블록을 끊는 것들
#   "(3) 쓰기"            영역 제목
#   "\U000f02b2세 자리 수…"  단원 제목. 보충면 사용자 영역 글자가 글머리표다
#                          (BMP 사용자 영역 글자는 수식 기호로 본문에 쓰이므로 제외)
#   "<탐구 활동>", "• …"    성취기준 칸에 딸린 주석. 수준 진술문이 아니다
_AREA_HEADING = re.compile(r"^(?:\(\s*\d{1,2}\s*\)\s*\S|[\U000F0000-\U0010FFFD]|<\s*탐구\s*활동\s*>|[•▪]\s)")
_ORDINAL = re.compile(r"^(?:\d{1,2}|[가나다라마바사아자차카타파하])$")
_HANGUL = re.compile(r"[가-힣]")
# 흘림 계열에서 빈 줄 2줄 이상은 쪽 넘김이다. 넘긴 뒤 나오는 표 열 이름('번호',
# '평가 도구 유형' …)은 종류가 끝이 없어 목록으로 거를 수 없으므로, 앞이 이미
# 문장으로 끝났으면 거기서 진술문을 닫는다. 문장이 안 끝났으면 쪽을 넘어 이어 붙인다.
_SENTENCE_END = re.compile(r"[다음임][.．]\s*$")


# 문장이 끝나자마자 공백 없이 다음 글자가 붙은 자리. 쪽이 갈릴 때 두 단이 서로
# 끼어든 흔적이다(12고대01-04 A 안에 B 진술문이 통째로 박혀 있다).
_WELD = re.compile(r"[다음임][.．](?=[가-힣])")


def _usable(desc):
    """진술문으로 쓸 수 있는 칸인가.

    쪽이 갈린 자리에서 변환기가 머리행과 데이터행을 한 행으로 뭉개 놓거나(3. 보건과
    중학교 L823: 수준 문자 칸이 'B C', 진술문 칸이 '**성취기준별 성취수준**' + B진술문
    + C진술문) 두 단을 서로 끼워 놓은 표가 있다. 어느 수준의 것인지 가를 수 없으니
    지어내지도, 남의 것을 얹지도 말고 버린다."""
    return (bool(_HANGUL.search(desc))
            and not _IN_REGION.search(desc)
            and not _WELD.search(desc))


def _merge_split_headings(lines):
    """흘림 계열은 절 제목을 '1' / '성취기준별 성취수준' 두 줄로 흘려 놓는다.
    맨몸 '성취기준별 성취수준' 은 쪽마다 되풀이되는 표 열 이름이기도 해서
    앞줄이 글머리 번호일 때만 절 제목으로 본다."""
    out = list(lines)
    for i in range(1, len(out)):
        s = out[i].strip()
        if (_IN_REGION.fullmatch(s) or _OUT_REGION.fullmatch(s)) and _ORDINAL.match(out[i - 1].strip()):
            out[i] = out[i - 1].strip() + ". " + s
    return out


def _split_code(text):
    """(코드, 코드 뒤 진술문). 코드가 없으면 (None, "")."""
    spans = find_codes_with_spans(text)
    if not spans:
        return None, ""
    code, _, end = spans[0]
    tail = text[end:spans[1][1]] if len(spans) > 1 else text[end:]
    return code, tail.lstrip("] ").strip()  # 끝은 손대지 않는다 — 마침표도 원문이다


def _join(raw_lines):
    """PDF 줄바꿈 복원. 원문 줄이 공백으로 끝났으면 낱말 경계, 아니면 낱말 중간이다.
    ('…점검·조정' + '하며 …' 를 공백으로 이으면 원문에 없는 띄어쓰기가 생긴다)"""
    out, gap = "", False
    for ln in raw_lines:
        s = clean_cell(ln)
        if not s:
            continue
        out = s if not out else out + (" " if gap else "") + s
        gap = ln.rstrip("\n").endswith((" ", "\t", " "))
    return out


def _group(entries):
    """[(코드후보텍스트, [수준문자], 진술문)] → 레코드. 문자가 되감기면 새 묶음.
    수준 문자가 빈 항목은 쪽이 갈리며 잘린 앞 진술문의 뒷부분이다."""
    recs, cur, last, open_letter = [], None, "", None
    for code_text, letters, desc in entries:
        if not letters:
            # 앞 진술문이 문장으로 끝나 있으면 이어짐이 아니다 — 붙이지 않는다
            if cur and open_letter and desc and _usable(desc) \
                    and not _SENTENCE_END.search(cur["levels"][open_letter]):
                cur["levels"][open_letter] += " " + desc
            continue
        if cur is None or letters[0] <= last:
            cur = {"code": None, "statement_in_table": "", "levels": {}, "_extra": []}
            recs.append(cur)
        last = letters[-1]
        if code_text:
            code, stmt = _split_code(code_text)
            if code and cur["code"] is None:
                cur["code"], cur["statement_in_table"] = code, stmt
            elif code and code != cur["code"]:
                cur["_extra"].append(code)
        open_letter = None
        if desc and _usable(desc):
            for letter in letters:
                cur["levels"].setdefault(letter, desc)
            open_letter = letters[-1] if cur["levels"].get(letters[-1]) == desc else None
    for r in recs:
        r["extra_codes"] = sorted(set(r.pop("_extra")))
    return [r for r in recs if r["code"] and r["levels"]]


def _table_entries(lines):
    entries, keep, strong_seen = [], False, False
    for line in lines:
        mark = _region(line)
        if mark is not None and (mark[1] or not strong_seen):
            keep = mark[0]
            strong_seen = strong_seen or mark[1]
        if not keep or not line.lstrip().startswith("|"):
            continue
        cells = [clean_cell(c) for c in _cells(line)]
        letters = desc = None
        li = -1
        for i, c in enumerate(cells):
            m = _TRAILING_LETTERS.search(c) if c else None
            if not m:
                continue
            nxt = next((x for x in cells[i + 1:] if x), "")
            if nxt:
                letters, desc, li = m.group(1).split(), nxt, i
                break
        code_text = next(
            (c for i, c in enumerate(cells) if c and i != li + 1 and find_codes(c)), ""
        )
        if letters:
            entries.append((code_text, letters, desc))
        elif code_text:  # 수준 문자 없는 코드 행 — 다음 묶음의 코드로만 쓴다
            entries.append((code_text, [], ""))
        else:
            # 쪽이 갈리며 진술문 칸만 남은 행(1-1. 정보과 L749 '|||위해 다차원 …|')
            tail = next((c for c in cells[1:] if c), "")
            if tail:
                entries.append(("", [], tail))
    return entries


def _flowed_entries(lines):
    entries, pending, keep, i = [], [], False, 0
    while i < len(lines):
        line = lines[i]
        mark = _region(line)
        if mark is not None:
            keep = mark[0]
            pending = []
            i += 1
            continue
        s = line.strip()
        if keep and _ONLY_LETTER.match(s):
            seg, j, blanks = [], i + 1, 0
            while j < len(lines):
                t = lines[j].strip()
                if (_ONLY_LETTER.match(t) or _region(lines[j]) is not None
                        or _AREA_HEADING.match(t) or find_codes(t)):
                    break
                if not t:
                    blanks += 1
                else:
                    if blanks >= 2 and seg and _SENTENCE_END.search(seg[-1]):
                        break
                    blanks = 0
                    if not _FURNITURE.match(t):
                        seg.append(lines[j])
                j += 1
            entries.append((_join(pending), [s], _join(seg)))
            pending, i = [], j
            continue
        if keep and s and not _FURNITURE.match(s):
            pending.append(line)
        i += 1
    return entries


def extract_from_text(text: str) -> list:
    lines = _merge_split_headings(text.split("\n"))
    entries = _table_entries(lines)
    if not entries:
        entries = _flowed_entries(lines)
    # 문자 없는 코드 행은 뒤따르는 묶음에 코드만 넘겨준다
    merged = []
    carry = ""
    for code_text, letters, desc in entries:
        if not letters:
            if code_text:
                carry = code_text
            else:
                merged.append(("", [], desc))
            continue
        merged.append((code_text or carry, letters, desc))
        carry = ""
    return _group(merged)


def main():
    from pipeline.sources import LEVEL_DOCS

    out = Path(__file__).resolve().parent.parent / "data" / "raw"
    out.mkdir(parents=True, exist_ok=True)
    n, empty = 0, []
    with open(out / "levels.jsonl", "w", encoding="utf-8") as f:
        for e in LEVEL_DOCS:
            recs = extract_from_text(load_text(e["path"]))
            if not recs:
                empty.append(e["path"].name)
            for r in recs:
                r["school"] = e["school"]
                r["doc"] = e["path"].name
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                n += 1
    print(f"levels.jsonl: {n} records from {len(LEVEL_DOCS)} docs")
    print(f"0건 문서 {len(empty)}개: " + ("; ".join(empty) if empty else "없음"))


if __name__ == "__main__":
    main()
