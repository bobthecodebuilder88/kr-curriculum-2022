"""별책 원문에서 [코드] 진술문 추출. 진술문은 '다.' 종결까지 줄 연결."""
import json
import re
from pathlib import Path
from pipeline.clean import load_text
from pipeline.codes import canonical

# codes.py의 괄호 허용 문자와 동일 집합 — OCR이 망가뜨린 대괄호 변형까지 흡수.
_OPEN_LIKE = r"[\[\(\{〔【［|]"
_CLOSE_LIKE = r"[\]\)\}〕】］|]"
# 목록 불릿(•, -, ⋅ 및 그 조합). 실제 별책 원문에서 성취기준 "본문" 항목 앞에 흔히 붙는다.
# '*'/'©'는 일부러 제외: 제2외국어(별책16) 실측 결과 이 두 기호는 "이 성취기준은…" 해설/
# 고려사항 재등장에만 쓰이고 본문에는 전혀 안 쓰인다. 포함하면 본문 파싱 실패 시 dedupe가
# 해설 문장을 진술문으로 잘못 승격시킬 위험이 생긴다 — verbatim 진술문 원칙에 위배.
_BULLET = r"(?:[•\-⋅]\s*)*"
# 줄 앞머리 코드 탐지용 사전 필터. 괄호는 양쪽 다 optional:
#   - 2단 코드(9수01-01)는 괄호 인접이 없으면 canonical()이 None을 돌려주므로 여기서 걸러도 안전.
#   - 3단 고교 공통과목 코드(10공국1-01-01)는 원문 자체가 괄호 없이 등장한다.
# 최종 채택 여부는 항상 canonical()이 판정 — 여기서 codes.py의 판별 로직을 재구현하지 않는다.
_CODE_AT_START = re.compile(
    rf"^\s*{_BULLET}{_OPEN_LIKE}?\s*(?P<code>\d{{1,2}}[가-힣ⅠⅡI\d]{{1,6}}-?\d{{0,2}}-\d{{2}})\s*{_CLOSE_LIKE}?"
)
# '다.' 뒤에 공백/줄끝/여는대괄호 또는 흔한 닫는 괄호·인용부호가 오면 문장 종결로 인정.
_TERMINATOR = re.compile(r"(다\.)(?=\s|$|[\[〔【［)\]〕】］\"'”’」』])")
_MAX_LOOKAHEAD = 12  # 빈 줄/잡음 줄 건너뛰기를 감안해 브리프 기본값(6)보다 여유를 둠

def extract_from_text(text: str, subject: str, source_label: str) -> list:
    lines = text.split("\n")
    n = len(lines)
    recs, i = [], 0
    while i < n:
        m = _CODE_AT_START.match(lines[i])
        code = canonical(m.group("code")) if m else None
        if not code:
            i += 1
            continue
        # 진술문: 코드 뒤 텍스트부터 '다.' 종결까지 줄 연결. 이미 시작된 진술문은 빈 줄/잡음
        # 줄을 건너뛰고 이어붙이되, 다음 코드 시작 줄은 소비하지 않고 남겨 바깥 루프가 처리한다.
        buf = lines[i][m.end():].strip()
        j = i
        while not _TERMINATOR.search(buf) and j + 1 < n and (j - i) < _MAX_LOOKAHEAD:
            if _CODE_AT_START.match(lines[j + 1]):
                break  # 다음 레코드 경계 — 이 줄은 소비하지 않는다
            if not buf and not lines[j + 1].strip():
                break  # 아직 한 글자도 못 모았는데 빈 줄 — 표가 깨져 코드만 나열된 경우
                       # (예: 별책16 (5)문화 표) 엉뚱한 뒷줄을 진술문으로 잘못 붙이는 사고 방지
            j += 1
            nxt = lines[j].strip()
            if nxt:
                buf += " " + nxt
            # else: 이미 진술문이 시작된 뒤의 빈 줄 — 건너뛰고 계속 탐색
        tm = _TERMINATOR.search(buf)
        if tm:
            statement = re.sub(r"\s+", " ", buf[: tm.end(1)]).strip()
        else:
            # 스캔 가능한 범위를 다 썼는데도 '다.'를 못 찾음. OCR이 종결 마침표만 지운
            # 경우(문장 자체는 온전히 '다'로 끝남)라면 있는 그대로 회수하되, 명시적 종결자를
            # 못 찾았다는 사실 자체는 needs_review=True로 계속 남겨 사람이 다시 보게 한다.
            collapsed = re.sub(r"\s+", " ", buf).strip()
            statement = collapsed if collapsed.endswith("다") else None
        recs.append({"code": code, "subject": subject,
                     "statement": statement, "source": source_label,
                     "needs_review": tm is None})
        i = j + 1
    # 같은 코드 첫 등장(본문)만 유지 — 해설/고려사항 재등장 제거.
    # 단, 첫 등장이 진술문 없이 끝났으면 진술문 있는 재등장으로 대체.
    seen = {}
    for r in recs:
        prev = seen.get(r["code"])
        if prev is None or (prev["statement"] is None and r["statement"]):
            seen[r["code"]] = r
    return list(seen.values())

def main():
    from pipeline.sources import BYLAWS
    out = Path(__file__).resolve().parent.parent / "data" / "raw"
    out.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(out / "standards.jsonl", "w", encoding="utf-8") as f:
        for e in BYLAWS:
            for r in extract_from_text(load_text(e["path"]), e["subject"], e["source_label"]):
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                n += 1
    print(f"standards.jsonl: {n} records")

if __name__ == "__main__":
    main()
