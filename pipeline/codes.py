"""성취기준 코드 인식·정규화. 관찰된 표기 변형 전부 흡수한다."""
import re

# 과목약어: 한글 1~4자 + 로마숫자(Ⅰ Ⅱ) 또는 ASCII I/II 꼬리 허용
_ABBR = r"[가-힣]{1,4}(?:[ⅠⅡ]|I{1,2})?"
# OCR 손상된 괄호 포함: 정상 및 손상된 열기/닫기 괄호류
_OPEN_LIKE = r"[\[\(\{〔【［|]"
_CLOSE_LIKE = r"[\]\)\}〕】］|]"
# 영역-일련번호 구분자. PDF 변환이 하이픈을 en/em 대시로 바꿔 놓는 줄이 있다
# (별책7:1035 "[4사01–02] 주변의 여러 장소를…" — 본문 목록인데 대시가 U+2013).
_DASH = r"[-–—‒−]"
# 2단: 9수01-01 / 12화언01-05  (내부 공백·<br> 허용)
# 등급은 (10|12|[2469])로 지정하여 앞의 숫자에 탐욕적으로 소비되지 않음
_TWO = re.compile(rf"({_OPEN_LIKE})?(10|12|[2469])({_ABBR})\s*(?:<br>)?\s*(\d{{2}}){_DASH}\s*(?:<br>)?\s*(\d{{2}})({_CLOSE_LIKE})?")
# 3단(고교 공통과목): 10공국1-01-01
_THREE = re.compile(rf"(1[02])([가-힣]{{2}}\d){_DASH}(\d{{2}}){_DASH}(\d{{2}})")
# 2단 매치 바로 뒤에 "-01"이 더 붙으면 그건 2단 코드가 아니라 3단 코드의 머리다
# (별책9:3126 "[10과탐02-01-03]" — 영역 자리 "2"가 "02"로 잘못 찍혀 _THREE가 놓친다).
_THIRD_GROUP = re.compile(rf"{_DASH}\d{{2}}")

def find_codes_with_spans(text: str) -> list:
    """[(코드, 시작오프셋, 끝오프셋), ...] 등장 순서대로. 끝오프셋은 닫는 괄호가
    있으면 그 다음 위치(진술문 후보 텍스트의 시작점으로 바로 쓸 수 있게)."""
    text = text.replace("\x00", "")
    found = []  # (위치, 코드, 끝위치)
    for m in _THREE.finditer(text):
        found.append((m.start(), f"{m.group(1)}{m.group(2)}-{m.group(3)}-{m.group(4)}", m.end()))
    taken = [(s, e) for s, _, e in found]  # 3단이 우선, 겹침 방지
    for m in _TWO.finditer(text):
        if any(a <= m.start() < b for a, b in taken):
            continue
        opened = m.group(1) is not None
        closed = m.group(6) is not None
        if not (opened or closed):
            continue
        if not closed and _THIRD_GROUP.match(text, m.end()):
            continue  # 3단 코드의 앞 두 마디를 잘라 온 것 — 코드가 아니다
        code = f"{m.group(2)}{m.group(3)}{m.group(4)}-{m.group(5)}"
        found.append((m.start(), code, m.end()))
    return [(c, s, e) for s, c, e in sorted(found)]

def find_codes(text: str) -> list:
    return [c for c, _, _ in find_codes_with_spans(text)]

def canonical(code: str):
    hits = find_codes(code)
    if len(hits) == 1:
        return hits[0]
    # Try wrapping in brackets for plain code input
    hits = find_codes(f"[{code}]")
    return hits[0] if len(hits) == 1 else None

_BANDS = {"2": "초1-2", "4": "초3-4", "6": "초5-6", "9": "중1-3", "10": "고(공통)", "12": "고(선택)"}

def grade_band(code: str):
    c = canonical(code)
    if c is None:
        return None
    prefix = "10" if c.startswith("10") else ("12" if c.startswith("12") else c[0])
    return _BANDS.get(prefix)
