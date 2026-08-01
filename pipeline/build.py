"""standards(SSOT) + levels 병합, 교차검증 리포트, data/ 최종 산출."""
import difflib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from pipeline.codes import grade_band

ROOT = Path(__file__).resolve().parent.parent

# 가운뎃점은 문서마다 다른 코드포인트로 찍힌다(별책 ⋅ U+22C5, 성취수준표 · U+00B7,
# 보급본 ･ U+FF65, 고시 원문 ㆍ U+318D). 같은 글자의 조판 변형일 뿐이라 대조에서
# 뺀다. 이걸 안 빼면 '가치･태도'와 '가치⋅태도'가 서로 다른 문장으로 잡힌다.
_NOISE = re.compile(r"[\s.⋅·･ㆍ・‧•]+")

def _norm(s: str) -> str:
    return _NOISE.sub("", s or "")

def statement_identical(a: str, b: str) -> bool:
    """두 출처가 글자까지 같은 문장을 싣고 있는가."""
    return _norm(a) == _norm(b)

def statement_agree(a: str, b: str) -> bool:
    return difflib.SequenceMatcher(None, _norm(a), _norm(b)).ratio() >= 0.90

_TABLE_NOTE = re.compile(r"\s*(?:※|<\s*탐구\s*활동\s*>).*$", re.S)

def table_statement(s: str) -> str:
    """성취수준 표 첫 열에서 성취기준 문장만 떼어 낸다.

    표는 성취기준 뒤에 편집 주석을 덧붙인다 — `※ 내용 체계표의 가치･태도 요소를
    포함하여 성취수준 개발`(106건)과 `<탐구 활동>• …`(191건)이다. 이걸 붙인 채로
    별책과 대조하면 문장이 글자까지 같은데도 불일치로 잡히고(초기 측정 327건 중
    다수), 별책이 손상돼 이 열을 진술문으로 쓸 때는 주석이 성취기준 본문인 것처럼
    실린다. 둘 다 이 프로젝트가 막으려는 종류의 오류다.
    """
    return _TABLE_NOTE.sub("", s or "").strip()

def _diff_fragments(bylaw: str, table: str, limit: int = 3) -> str:
    """두 문장이 어디서 갈리는지만 뽑아 준다. 긴 문장 두 개를 나란히 놓고 사람이
    눈으로 찾게 하면 정작 한 글자 차이를 놓친다."""
    a, b = _norm(bylaw), _norm(table)
    out = [f"별책 `{a[i1:i2] or '(없음)'}` ↔ 표 `{b[j1:j2] or '(없음)'}`"
           for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b).get_opcodes()
           if op != "equal"]
    return "; ".join(out[:limit]) + (" 외" if len(out) > limit else "")

def _school_of(code: str) -> str:
    b = grade_band(code) or ""
    return "초" if b.startswith("초") else ("중" if b.startswith("중") else "고")

def verify_descriptors_against_source(levels: list) -> list:
    """성취수준 서술문이 원문에 그대로 있는지 확인한다.

    실증: 페이지 경계에서 A등급 서술문의 꼬리가 C등급 머리로 넘어간 사례가
    20,606건 중 56건(0.272%) 있다(예: 9과17-04). 원문에 없는 서술문은
    등급을 잘못 붙였거나 잘린 것이므로 조용히 싣지 말고 드러낸다.

    훑는 대상은 levels 원본 전체라 이 데이터셋이 싣지 않는 과목의 것도 함께
    걸린다(56건 중 21건). 리포트는 둘을 갈라 적는다 — main() 참조.
    """
    from pipeline.clean import load_text
    from pipeline.sources import SOURCE_DIR
    by_name = {p.name: p for p in SOURCE_DIR.rglob("*.md")}
    cache, bad = {}, []
    for r in levels:
        p = by_name.get(r.get("doc", ""))
        if p is None:
            continue
        if p not in cache:
            cache[p] = re.sub(r"\s+", "", load_text(p).replace("<br>", "").replace("~~", ""))
        haystack = cache[p]
        for lv, txt in (r.get("levels") or {}).items():
            if re.sub(r"\s+", "", txt) not in haystack:
                bad.append({"code": r["code"], "level": lv, "doc": r["doc"], "text": txt})
    return bad

_ROMAN = {"Ⅰ": "I", "Ⅱ": "II", "Ⅲ": "III"}

def alias_key(code: str) -> str:
    """같은 성취기준의 두 표기를 하나로 모은다.

    원문이 로마숫자를 유니코드(Ⅱ)와 ASCII(II) 두 가지로 적어서, 같은 성취기준이
    표기별로 데이터를 나눠 갖는 사례가 있다. 실증: `12영II-01-01`은 성취수준
    A~E를 유일하게 싣고 `12영Ⅱ-01-01`은 진술문을 싣는다 — 어느 쪽도 버릴 수
    없다. 인식기에서 정규화하면 원문에 실재하는 표기를 잃으므로(코퍼스 회귀
    게이트 위반), 병합 시점에만 합친다. 출력 코드는 정본 표기를 유지한다.
    """
    out = code
    for uni, ascii_ in _ROMAN.items():
        out = out.replace(uni, ascii_)
    return out.replace("-", "")

def _attach_levels(rec, key, code, lv, tbl_stmt, report):
    """성취수준 한 벌을 해당 성취기준에 붙이고, 표의 진술문과 대조한다."""
    rec["levels"] = lv
    # 별책 진술문이 OCR 손상으로 비어 있으면 성취수준 표를 2차 출처로 쓴다.
    # 제2외국어처럼 별책 표가 붕괴한 문서를 상당수 되살린다.
    if not rec["statement"] and len(tbl_stmt) >= 10:
        rec["statement"] = tbl_stmt
        rec["statement_source"] = "성취수준표"
        rec["needs_review"] = False
        report["statement_filled_from_levels"].append(code)
    # 성취수준 문서는 각 성취기준을 첫 열에 다시 적어 둔다 — 별책과 독립된
    # 제2의 권위 있는 출처다. 이게 이 파이프라인에서 유일하게 한글이 한글로
    # 깨진 손상(낱말→날말 73건)과 단어 누락(문법적으로 멀쩡하지만 틀린 문장)을
    # 잡아낼 수 있는 수단이다. Latin 문자 탐지로는 전혀 보이지 않는다.
    # `statement_verified: true`는 '독립 출처가 이 문장을 글자까지 똑같이 다시
    # 실었다'는 뜻이어야 한다. 유사도 0.90으로 판정하면 한 단어가 다르거나
    # 통째로 빠진 문장까지 '검증됨'이 된다. 실증: `6도04-01`은 한쪽이 '안',
    # 다른 쪽이 '법'이고 `12데과01-03`은 한쪽에 '데이터'가 없는데 둘 다 0.97로
    # 통과했다 — 문법적으로 멀쩡해서 사람 눈에도 안 걸리는 바로 그 손상이다.
    if len(tbl_stmt) >= 15 and rec["statement"]:
        if statement_identical(rec["statement"], tbl_stmt):
            rec["statement_verified"] = True
        else:
            rec["statement_verified"] = False
            rec["needs_review"] = True
            # 문장 자체가 다른 것(불일치)과 단어 몇 개가 다른 것(어긋남)은
            # 사용자가 할 일이 달라서 따로 센다.
            bucket = ("statement_word_diffs" if statement_agree(rec["statement"], tbl_stmt)
                      else "statement_conflicts")
            report[bucket].append({"code": code, "subject": key[0],
                                   "bylaw": rec["statement"], "table": tbl_stmt})

def merge(standards: list, levels: list):
    # 키는 반드시 (교과, 코드) 복합 키다. 과목 약어는 교과 안에서만 유일해서
    # 서로 다른 교과의 진짜 성취기준이 같은 코드 문자열을 쓴다. 실증(별책 대조 완료):
    #   12스문01-01 = 체육 '스포츠 문화'          / 제2외국어 '스페인어권 문화'
    #   12심독01-01 = 영어 '심화 영어 독해와 작문' / 제2외국어 '심화 독일어'
    # 이런 코드가 10개(체육·제2외국어 3, 영어·제2외국어 7) 있다. 코드만으로 키를
    # 잡으면 그 10자리에서 진짜 성취기준 하나가 조용히 사라진다.
    by_key = {}
    for r in standards:
        by_key[(r["subject"], r["code"])] = {
            **r, "school": _school_of(r["code"]),
            "grade_band": grade_band(r["code"]),
            "course": None, "area": None, "levels": None,
            "statement_source": "별책" if r["statement"] else None,
            "statement_verified": None}
    report = {"levels_only": [], "statement_conflicts": [], "statement_word_diffs": [],
              "bylaw_only_no_levels": 0, "statement_filled_from_levels": []}
    lv_by_code = defaultdict(list)
    for l in levels:
        lv_by_code[l["code"]].append(l)
    # 표기 별칭(로마숫자 유니코드/ASCII)을 무시하고 매칭한다 — alias_key 참조.
    alias_index = defaultdict(list)
    for k in by_key:
        alias_index[alias_key(k[1])].append(k)
    # 성취수준 문서가 어느 교과의 것인지 알아낸다. 코드가 두 교과에 걸릴 때
    # 진술문 유사도로 고르면 한쪽 진술문이 OCR로 비어 있는 자리에서 반드시 진다
    # — 실증: 독일어 성취수준이 영어 '심화 영어 독해와 작문'에 붙었다. 어느 문서에
    # 실렸는지가 유사도보다 강한 증거다.
    # 한 문서가 여러 교과를 담기도 하므로(중학교 전과목·초등 학년군) 교과 하나가
    # 아니라 집합으로 잡되, 한 건짜리는 넣지 않는다. 코드가 두 교과에 실재하는데
    # 한쪽 별책이 깨져 다른 한쪽만 남으면 그 코드 하나가 남의 교과를 이 문서의
    # 교과인 양 등록한다(실증: 독일어 문서 39건 중 `12심독02-03` 하나가 '영어'를).
    doc_votes = defaultdict(Counter)
    for l in levels:
        ms = alias_index.get(alias_key(l["code"]), [])
        if len(ms) == 1:
            doc_votes[l.get("doc")][ms[0][0]] += 1
    # 비율로 자르면 안 된다. 초등 학년군 문서처럼 여러 교과가 섞인 문서에서 편수가
    # 적은 교과(5~6학년군의 도덕 13건)가 통째로 빠져 성취수준을 잃는다.
    doc_subjects = {d: {s for s, n in c.items() if n >= 2} for d, c in doc_votes.items()}

    for code, ls in lv_by_code.items():
        matches = alias_index.get(alias_key(code), [])
        if not matches:
            report["levels_only"].append(code)
            continue
        # 성취수준 행은 제 교과의 문서에서 온 것만 받는다. 코드가 두 교과에 실재하면
        # 행도 교과별로 따로 있으므로 각자 제 교과 성취기준에 붙인다. 하나만 골라
        # 붙이면 나머지 교과가 성취수준을 잃고, 잘못 고르면 남의 교과 성취수준이
        # 붙는다(실증: 독일어 성취수준이 영어 '심화 영어 독해와 작문'에 붙던 자리).
        for key in matches:
            rows = [l for l in ls
                    if key[0] in (doc_subjects.get(l.get("doc")) or {key[0]})]
            if not rows:
                continue
            best = max(rows, key=lambda l: len(l["levels"]))
            _attach_levels(by_key[key], key, code, best["levels"],
                           table_statement(best.get("statement_in_table")), report)

    report["bylaw_only_no_levels"] = sum(1 for r in by_key.values() if r["levels"] is None)
    codes = {k[1] for k in by_key}
    # 약어가 실재하는지는 두 출처를 합쳐 판정한다. 별책 추출물만 세면 별책 쪽 OCR이
    # 한 과목을 거의 통째로 삼킨 자리에서 살아남은 코드 한 개가 유령으로 몰린다.
    # 실증: `12스회01-07`(스페인어권 생활과 문화)은 별책16에서 하나만 살아남았지만
    # 성취수준 문서에는 01-05~01-10 여섯 개가 실려 있다 — 실재하는 약어다.
    report["abbr_outliers"] = find_abbr_outliers(codes | set(lv_by_code))
    # 유령 약어는 자기 자신 말고도 앞번호 전부를 '빠진 성취기준'으로 만들어 낸다
    # (`9성프02-07` 하나가 02-01~02-06 여섯 자리를 만든다). 실재하지 않는 계열의
    # 결번을 원문 확인 대상이라고 알리면 리포트가 그만큼 못 믿을 것이 된다.
    phantom = {_abbr_of(c) for c in report["abbr_outliers"]}
    report["sequence_gaps"] = [g for g in find_sequence_gaps(codes)
                               if _abbr_of(g) not in phantom]
    report["garbled"] = []
    for key, rec in by_key.items():
        if key[1] in report["abbr_outliers"]:
            rec["needs_review"] = True
        if is_garbled(rec["statement"], rec["subject"]):
            rec["needs_review"] = True
            report["garbled"].append({"code": key[1], "subject": key[0],
                                      "statement": rec["statement"]})
    return list(by_key.values()), report

# 영어·제2외국어 진술문에는 라틴 문자가 정당하게 들어간다. 나머지 교과에서
# 라틴 문자 덩어리는 사실상 전부 OCR 잔재다.
_LATIN_RUN = re.compile(r"[A-Za-z]{2,}")
_FOREIGN_SUBJECTS = {"영어", "제2외국어"}
# 사용자 정의 영역(PUA). 원문 PDF에 심어진 수식 글꼴이 변환에서 사설 코드포인트로
# 떨어져 나온 자리다. 실증: 수학 12건 — `10공수2-03-04`는 '유리함수 □ 의 그래프를
# 그릴 수 있고'가 되어 정작 어떤 함수인지가 문장에서 사라진다.
_PUA = re.compile(r"[-]")

def is_garbled(statement, subject) -> bool:
    """OCR 쓰레기가 섞인 채 '추출 성공'으로 남은 진술문을 찾는다.

    실증: 별책16의 `12스문01-03` → '스페인어권의 문화 wee 조사하고, 정보를
    분석ㆍ정리한다'. 이런 문장을 공식 성취기준이라며 그대로 인용하면 교사에게
    손상된 문장을 권위 있는 것처럼 전달하게 된다. 누락보다 더 나쁘다.
    영어·제2외국어는 라틴 문자가 정상이라 한글 비율로 판정한다.
    """
    if not statement:
        return False
    if _PUA.search(statement):
        return True
    if subject in _FOREIGN_SUBJECTS:
        hangul = sum(1 for c in statement if "가" <= c <= "힣")
        letters = sum(1 for c in statement if c.isalpha())
        return letters > 0 and hangul / letters < 0.80
    return bool(_LATIN_RUN.search(statement))

# 학년 접두어를 약어에 포함해 둔다. 접두어를 떼면 9생프와 12생프처럼 학교급만
# 다른 정상 약어끼리 편집거리 0으로 붙어 버린다.
_ABBR_OF = re.compile(r"^(\d{1,2}[가-힣]{1,4}[ⅠⅡI]{0,2})\d?-?\d{2}-\d{2}$")

def _abbr_of(code):
    m = _ABBR_OF.match(code)
    return m.group(1) if m else None

def find_abbr_outliers(by_code) -> list:
    """OCR이 과목 약어 한 글자를 바꿔 만든 유령 코드를 찾는다.

    실증: 별책16의 `9성프02-07`. 같은 파일이 `생프`를 일관되게 쓰는데 `성프`는
    딱 한 번 나온다 — OCR이 '생'을 '성'으로 읽은 것이다. 이런 코드는 실재하지
    않는 성취기준이므로 그대로 두면 이 프로젝트가 막으려는 바로 그 '가짜 코드'가
    데이터에 들어앉는다. 약어가 코퍼스 전체에서 단 1개 코드에만 쓰였는데 편집
    거리 1인 약어가 여러 코드에 쓰였다면 손상 후보로 표시한다.

    '코드 1개' 조건은 일부러 좁게 잡았다. 이 조건을 '독립 출처에 없는 약어'로
    넓히면 `12한문`(14개)·`12한고`(9개)·`12언한`(10개)·`10한사`(26개)처럼 한 글자만
    다른 진짜 이웃 과목들이 서로를 유령으로 지목한다. 실재하는 성취기준을 가짜라고
    부르는 쪽이 유령을 놓치는 쪽보다 나쁘므로 좁은 조건을 유지한다.
    알려진 한계: 손상이 코드 여러 개를 만든 자리는 놓친다(`12심증` 2개, `9생증`
    5개 — 둘 다 성취수준 문서에 한 번도 없고 제 짝 `심중`·`생중`은 22·17회 나온다).
    다만 이 7건은 전부 진술문이 null이라 문장이 지어내어질 위험은 없다.
    """
    codes_by_abbr = defaultdict(list)
    for code in by_code:
        m = _ABBR_OF.match(code)
        if m:
            codes_by_abbr[m.group(1)].append(code)
    outliers = []
    for abbr, codes in codes_by_abbr.items():
        if len(codes) != 1:
            continue
        for other, others in codes_by_abbr.items():
            if other != abbr and len(others) >= 3 and len(other) == len(abbr) \
                    and sum(a != b for a, b in zip(abbr, other)) == 1:
                outliers.append(codes[0])
                break
    return sorted(outliers)

# 코드에서 학년 접두어와 과목 약어를 떼어 낸다(subjects.json 조인 키).
_PREFIX = re.compile(r"^(\d{1,2})(.*?)-?(\d{2})-(\d{2})$")

def code_prefix(code):
    """코드를 (학년 접두어, 과목 약어)로 쪼갠다.

    3단 코드(`10공국1-01-01`의 약어는 `공국1`)와 로마숫자 꼬리(`12미적Ⅰ`)까지
    한 규칙으로 다뤄야 한다. 약어를 `\\d{2}-` 앞까지로 잡으면 분권 번호가 붙은
    공통 과목이 통째로 매칭에서 빠져 과목명을 못 받는다(실증: 314건).
    """
    m = _PREFIX.match(code)
    return (m.group(1), m.group(2)) if m else (None, None)

_SEQ = re.compile(r"^(.*?)(\d{2})-(\d{2})$")

def find_sequence_gaps(by_code) -> list:
    """번호가 끊긴 자리를 찾는다.

    원문 PDF의 OCR이 코드 마커를 통째로 파괴하는 경우가 있다(예: 별책16의
    12독문01-03은 파일 어디에도 문자열로 존재하지 않는다). 그런 성취기준은
    추출물에서 그냥 '없는' 상태가 되어 완전한 데이터처럼 보인다. 번호가 끊긴
    자리를 명시적으로 보고해 사용자가 원문 고시본을 확인할 수 있게 한다.
    """
    groups = defaultdict(set)
    for code in by_code:
        m = _SEQ.match(code)
        if m:
            groups[(m.group(1), m.group(2))].add(int(m.group(3)))
    gaps = []
    for (prefix, area), nums in sorted(groups.items()):
        missing = sorted(set(range(1, max(nums) + 1)) - nums)
        for n in missing:
            gaps.append(f"{prefix}{area}-{n:02d}")
    return gaps

def main():
    standards = [json.loads(l) for l in open(ROOT / "data/raw/standards.jsonl", encoding="utf-8")]
    levels = [json.loads(l) for l in open(ROOT / "data/raw/levels.jsonl", encoding="utf-8")]
    exceptions = json.loads((ROOT / "pipeline/exceptions.json").read_text(encoding="utf-8"))
    merged, report = merge(standards, levels)
    report["levels_only"] = [c for c in report["levels_only"]
                             if c not in exceptions.get("known_levels_only", [])]

    # 원문에 없는 성취수준 서술문을 찾아 해당 레코드를 needs_review 로 표시한다.
    report["bad_descriptors"] = verify_descriptors_against_source(levels)
    # 이 검사는 levels 원본 전체를 훑으므로 이 데이터셋이 싣지 않는 과목(과학고·예고
    # 계열, 고등학교 교양 등)의 서술문까지 걸린다. 둘을 한 숫자로 합치면 우리가 실제로
    # 배포하는 데이터의 결함을 실제보다 크게 말하게 된다 — 실린 것과 아닌 것을 가른다.
    shipped = {(r["code"], lv) for r in merged for lv in (r["levels"] or {})}
    bad_shipped = [b for b in report["bad_descriptors"]
                   if (b["code"], b["level"]) in shipped]
    bad_elsewhere = [b for b in report["bad_descriptors"]
                     if (b["code"], b["level"]) not in shipped]
    flagged = {(b["code"], b["level"]) for b in bad_shipped}
    for r in merged:
        if any((r["code"], lv) in flagged for lv in (r["levels"] or {})):
            r["needs_review"] = True

    # 과목명 조인. 키에 교과가 들어가야 한다 — 12스문은 체육에서 '스포츠 문화',
    # 제2외국어에서 '스페인어권 문화'라 약어만으로는 한쪽이 틀린 이름을 받는다.
    subjects = json.loads((ROOT / "index/subjects.json").read_text(encoding="utf-8"))
    course_of = {(s["grade_prefix"], s["abbr"], s["subject"]): s["course_name"] for s in subjects}
    for r in merged:
        r["course"] = course_of.get((*code_prefix(r["code"]), r["subject"]))

    groups = defaultdict(list)
    for r in merged:
        groups[(r["school"], r["subject"])].append(r)
    index = {"files": [], "total": 0}
    for (school, subject), rows in sorted(groups.items()):
        d = ROOT / "data" / school
        d.mkdir(parents=True, exist_ok=True)
        rel = f"data/{school}/{subject.replace('/', '·')}.jsonl"
        with open(ROOT / rel, "w", encoding="utf-8") as f:
            for r in sorted(rows, key=lambda x: x["code"]):
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        index["files"].append({"path": rel, "school": school, "subject": subject, "count": len(rows)})
        index["total"] += len(rows)
    (ROOT / "data/index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    n_review = sum(1 for r in merged if r["needs_review"])
    n_true = sum(1 for r in merged if r["statement_verified"] is True)
    n_null = sum(1 for r in merged if r["statement_verified"] is None and r["statement"])
    n_nostmt = sum(1 for r in merged if not r["statement"])
    doc_of = {l["code"]: l["doc"] for l in levels}
    # 싣지 못한 코드를 두 부류로 가른다. 같은 과목의 다른 코드를 이미 싣고 있다면
    # 그 과목은 다루는 범위 안이고 이 코드만 빠진 것(원문·추출 손상)이다. 그 과목
    # 코드를 하나도 안 싣고 있다면 애초에 다루지 않는 과목이다. 사용자가 할 일이
    # 다르므로 한 덩어리로 뭉쳐 놓으면 안 된다.
    covered = {code_prefix(r["code"]) for r in merged}
    out_of_scope = [c for c in report["levels_only"] if code_prefix(c) not in covered]
    in_scope_gap = [c for c in report["levels_only"] if code_prefix(c) in covered]
    scope_gaps = Counter(doc_of.get(c, "(출처 미상)") for c in out_of_scope)

    lines = [
        "# 교차검증 리포트 (자동 생성)", "",
        "이 파일은 `python3 -m pipeline.build`가 매번 새로 쓴다. 손으로 고치지 마라.",
        "이 데이터셋이 무엇을 알고 무엇을 모르는지를 숨기지 않고 적는 것이 목적이다.",
        "", "## 이 데이터셋이 다루는 범위", "",
        f"수록한 성취기준은 **{index['total']}건**이다. 출처는 교육부 고시 제2022-33호 별책 5~18,",
        "즉 초·중·고 공통 교과와 고등학교 선택 과목이다.",
        "",
        f"**다루지 않는 과목**: 성취수준 문서에만 있는 코드가 {len(report['levels_only'])}개인데,",
        f"그중 **{len(out_of_scope)}개**는 이 데이터셋이 아예 다루지 않는 과목의 것이다. 과학·체육·예술",
        "계열 전문 교과(과학고·체고·예고)와 고등학교 교양 교과가 여기 해당한다. 해당 별책",
        "고시본이 원자료에 없어서 성취기준 문장을 고시 원문으로 확인할 수 없었고, 확인할 수",
        "없는 문장은 싣지 않기로 했다. 이 과목을 찾는다면 이 데이터셋에는 답이 없다 —",
        "없는 것을 지어내지 않기 위한 선택이다.",
        "", "다루지 않는 과목의 코드가 나온 문서와 개수:", ""]
    lines += [f"- {d}: {n}개" for d, n in scope_gaps.most_common()]
    lines += ["",
              f"나머지 **{len(in_scope_gap)}개**는 이 데이터셋이 다루는 과목인데 그 코드만 빠진 것이다.",
              "성취수준 문서에는 있고 별책 쪽에서 추출되지 않았다. 원문 PDF에서 코드 마커가",
              "손상된 자리로 보인다. 아래 '번호가 끊긴 자리'와 겹치는 코드가 많다.", "",
              "  " + ", ".join(sorted(in_scope_gap))]
    lines += [
        "", "## 요약", "",
        f"- 총 성취기준: {index['total']}",
        f"- 사람이 확인해야 함(needs_review): {n_review} ({n_review / index['total']:.1%})",
        f"- 진술문 없음(원문 손상으로 문장을 복구 못 함): {n_nostmt}",
        f"- 성취수준(A~E) 병합됨: {index['total'] - report['bylaw_only_no_levels']}",
        f"- 성취수준 없음(별책에만 존재): {report['bylaw_only_no_levels']}",
        "", "### 독립 출처 대조 결과", "",
        "성취수준 문서는 각 성취기준을 표 첫 열에 다시 싣는다. 별책과 따로 만들어진",
        "문서라 서로를 검산할 수 있다. `statement_verified`는 그 결과다.",
        "",
        f"- `true` — 두 문서가 **글자까지 같은** 문장을 싣는다: {n_true}",
        f"- `false` — 두 문서가 **다른** 문장을 싣는다(사람이 봐야 함): "
        f"{len(report['statement_conflicts']) + len(report['statement_word_diffs'])}",
        f"    - 단어 수준 어긋남(문장 골격은 같음): {len(report['statement_word_diffs'])}",
        f"    - 문장 수준 불일치: {len(report['statement_conflicts'])}",
        f"- `null` — 대조할 독립 출처가 없다(검증 안 됨, 틀렸다는 뜻은 아니다): {n_null}",
        f"- 진술문 자체가 없어 대조할 것이 없다: {n_nostmt}",
        "",
        "`true`의 기준을 '비슷하면 통과'가 아니라 '글자까지 같음'으로 잡은 이유가 있다.",
        "유사도 0.90으로 재던 때는 `6도04-01`(한쪽 '안', 다른 쪽 '법')이나 `12데과01-03`",
        "('데이터'가 한쪽에만 있음)까지 '검증됨'으로 통과했다. 문법적으로 멀쩡해서 읽어도",
        "안 걸리는 이런 손상을 잡아내라고 두는 장치가 그걸 놓치면 안 된다.",
        "",
        "다만 `true`가 '고시 원문과 같다'는 보장은 아니다. 두 문서가 같은 오류를 물려받은",
        "자리는 이 방법으로 잡히지 않는다. 확실히 하려면 고시 원문을 봐야 한다.",
        "", "### 그 밖의 점검", "",
        f"- 별책 진술문이 손상돼 성취수준표에서 문장을 가져온 건: {len(report['statement_filled_from_levels'])}",
        f"- OCR 잔재가 남은 진술문: {len(report['garbled'])}",
        f"- 약어 손상으로 생긴 유령 코드 의심: {len(report['abbr_outliers'])}",
        f"- 출처 문서에서 그대로 찾을 수 없는 성취수준 서술문: {len(bad_shipped)}"
        f" / 이 데이터셋이 싣는 서술문 {len(shipped)}"
        f" (같은 검사에 걸렸으나 여기 싣지 않는 과목의 것 {len(bad_elsewhere)}건은 뺐다)",
        f"- 번호가 끊긴 자리: {len(report['sequence_gaps'])}",
        ""]
    by_subj = defaultdict(lambda: [0, 0])
    for r in merged:
        by_subj[r["subject"]][0] += 1
        by_subj[r["subject"]][1] += bool(r["needs_review"])
    lines += ["### 교과별 needs_review", "", "| 교과 | 성취기준 | 확인 필요 | 비율 |",
              "|---|---:|---:|---:|"]
    lines += [f"| {s} | {t} | {n} | {n / t:.1%} |"
              for s, (t, n) in sorted(by_subj.items(), key=lambda kv: -kv[1][1] / kv[1][0])]
    f_total, f_review = by_subj["제2외국어"]
    rest_t, rest_r = index["total"] - f_total, n_review - f_review
    lines += ["",
              f"확인 필요 {n_review}건 중 {f_review}건이 제2외국어 하나에서 나온다. 별책16의 PDF 변환",
              "품질이 나머지 별책보다 눈에 띄게 나빠서, 문장 중간에 라틴 문자 덩어리가 박히거나",
              "낱말이 통째로 날아간 자리가 많다. 이 교과를 쓸 때는 원문 확인을 권한다.",
              f"제2외국어를 뺀 나머지 13개 교과는 {rest_t}건 중 {rest_r}건({rest_r / rest_t:.1%})이다.", ""]
    if report["statement_word_diffs"]:
        lines += ["## 두 출처가 단어에서 어긋나는 성취기준",
                  "문장 골격은 같은데 낱말이 다르거나 빠졌다. 어느 쪽이 고시 원문인지는",
                  "이 데이터만으로 판정할 수 없어 양쪽을 그대로 싣는다. `statement` 필드에는",
                  "별책 쪽을 넣어 두었다. 인용 전에 원문 고시본을 확인하라.", ""]
        for c in report["statement_word_diffs"]:
            lines += [f"- **{c['code']}** ({c['subject']}) — {_diff_fragments(c['bylaw'], c['table'])}",
                      f"    - 별책: {c['bylaw']}",
                      f"    - 성취수준표: {c['table']}"]
        lines += [""]
    if bad_shipped:
        lines += ["## 원문 대조 실패 성취수준 서술문",
                  f"아래 {len(bad_shipped)}건은 출처 문서에서 그대로 찾을 수 없다. 페이지 경계에서",
                  "한 등급의 문장 끝이 다음 등급 머리로 넘어간 사례가 대부분이다.",
                  "등급 배정이 틀렸을 수 있으니 원문 고시본을 확인하라.",
                  f"이 데이터셋이 싣는 성취기준 {len({b['code'] for b in bad_shipped})}개에 걸리며,",
                  "그 레코드는 `needs_review: true`다.", ""]
        lines += [f"- [{b['code']}] {b['level']}등급 ({b['doc']}) {b['text'][:60]}…"
                  for b in bad_shipped]
        lines += [""]
    if bad_elsewhere:
        lines += ["### 이 데이터셋이 싣지 않는 과목의 것",
                  f"같은 검사에 {len(bad_elsewhere)}건이 더 걸렸다. 다만 성취수준 문서에만 있고",
                  "별책 고시본이 없어 싣지 못한 과목의 서술문이라 `data/`에 존재하지 않는다.",
                  "위 숫자에 넣으면 이 데이터셋의 결함을 실제보다 크게 말하는 것이 되므로",
                  "따로 적는다. 아래 코드로 조회하면 결과가 나오지 않는다.", ""]
        lines += [f"- [{b['code']}] {b['level']}등급 ({b['doc']}) {b['text'][:60]}…"
                  for b in bad_elsewhere]
        lines += [""]
    if report["garbled"]:
        lines += ["## OCR 잔재가 섞인 진술문",
                  "추출은 됐지만 원문 PDF 변환 과정의 문자 노이즈가 남아 있다.",
                  "그대로 인용하면 손상된 문장을 공식 성취기준으로 전달하게 되므로",
                  "`needs_review: true`로 표시했다. 원문 고시본 확인 대상이다.", ""]
        lines += [f"- [{g['code']}] ({g['subject']}) {g['statement']}" for g in report["garbled"]]
        lines += [""]
    if report["abbr_outliers"]:
        lines += ["## 약어 손상 의심 코드",
                  "과목 약어가 코퍼스 전체에서 단 한 번만 쓰였고, 편집 거리 1인 약어가",
                  "여러 번 쓰인다. OCR 오독으로 만들어진 유령 코드일 가능성이 높다.", ""]
        lines += [f"- {c}" for c in report["abbr_outliers"]] + [""]
    if report["statement_conflicts"]:
        lines += ["## 두 출처가 서로 다른 문장을 싣는 성취기준",
                  "단어 몇 개가 아니라 문장이 다르다. 한쪽 문서의 문장이 잘렸거나, 변환 과정에서",
                  "다른 성취기준의 문장이 섞여 들어온 자리다. `statement` 필드에는 별책 쪽을",
                  "넣어 두었다. 인용 전에 원문 고시본을 확인하라.", ""]
        for c in report["statement_conflicts"]:
            lines += [f"- **{c['code']}** ({c['subject']})",
                      f"    - 별책: {c['bylaw']}",
                      f"    - 성취수준표: {c['table']}"]
        lines += [""]
    if report["sequence_gaps"]:
        lines += ["## 번호 시퀀스 공백",
                  "아래 코드는 번호 순서상 존재해야 하지만 원문에서 추출되지 않았다.",
                  "PDF 변환 과정에서 코드 마커가 파손된 자리로 추정된다(실증: 별책16의",
                  "`12독문01-03`은 파일 어디에도 문자열로 존재하지 않는다). 해당 성취기준이",
                  "필요하면 원문 고시본을 확인하라.", ""]
        lines += [f"- {c}" for c in report["sequence_gaps"]] + [""]
    if report["levels_only"]:
        lines += ["## 수록하지 않은 코드 전체 목록",
                  "위 '이 데이터셋이 다루는 범위'에서 설명한, 별책 고시본이 원자료에 없어",
                  "싣지 못한 코드들이다. 이 코드로 조회하면 결과가 나오지 않는다.", ""]
        by_doc = defaultdict(list)
        for c in report["levels_only"]:
            by_doc[doc_of.get(c, "(출처 미상)")].append(c)
        for d, cs in sorted(by_doc.items()):
            lines += [f"**{d}** ({len(cs)}개)", "", ", ".join(sorted(cs)), ""]
    (ROOT / "validation-report.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in report.items()},
                     ensure_ascii=False), "| total:", index["total"])

if __name__ == "__main__":
    main()
