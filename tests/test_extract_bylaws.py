from pipeline.sources import BYLAWS, LEVEL_DOCS
from pipeline.extract_bylaws import extract_from_text

def test_all_manifest_files_exist():
    for e in BYLAWS:
        assert e["path"].exists(), e["path"]
    assert len(LEVEL_DOCS) >= 55  # 초3 + 중16 + 고41 - 별책류 제외분

BYLAW_SAMPLE = """(1) 수와 연산

숕 소인수분해
[9수01-01] 소인수분해의 뜻을 알고, 자연수를 소인수분해 할 수
있다.
[9수01-02] 소인수분해를 이용하여 최대공약수와 최소공배수를 구할 수 있다.

(가) 성취기준 해설
• [9수01-01] 소인수분해 지도 시에는 …
"""

def test_extract_joins_wrapped_lines_and_dedupes_commentary():
    recs = extract_from_text(BYLAW_SAMPLE, subject="수학", source_label="[별책8]")
    by_code = {r["code"]: r for r in recs}
    assert set(by_code) == {"9수01-01", "9수01-02"}   # 해설 재등장은 새 레코드 아님
    assert by_code["9수01-01"]["statement"] == "소인수분해의 뜻을 알고, 자연수를 소인수분해 할 수 있다."
    assert by_code["9수01-01"]["subject"] == "수학"

# 실제 별책6(도덕) 발췌: 본문·해설 둘 다 "- [" 불릿을 쓴다(수학 fixture의 "•"와 다른 문자).
DASH_BULLET_SAMPLE = """- [9도01-01] 자신의 삶과 가치관에 대한 성찰을 통해 도덕적인 삶에 대한 의지를 기른다.
- [9도01-02] 일상에서 발생하는 부도덕한 행동의 여러 원인을 분석하여 이를 내면화하는 의지를 기른다.

(가) 성취기준 해설
- [9도01-02] 이 성취기준의 취지는 부도덕한 행동의 원인을 분석하도록 하는 것이다.
"""

def test_dash_bullet_prefix_recognized_and_first_occurrence_wins():
    recs = extract_from_text(DASH_BULLET_SAMPLE, subject="도덕", source_label="[별책6]")
    by_code = {r["code"]: r for r in recs}
    assert set(by_code) == {"9도01-01", "9도01-02"}
    assert by_code["9도01-02"]["statement"] == "일상에서 발생하는 부도덕한 행동의 여러 원인을 분석하여 이를 내면화하는 의지를 기른다."

# 실제 별책16(제2외국어) 1018~1040행 발췌(잡음 줄은 생략, 구조만 보존): PDF 표가 깨져 코드 4개가
# 본문 텍스트 없이 연달아 나열되고, 빈 줄 뒤에 진술문 3개짜리 블록이 붙는다. 코드-진술문 개수가
# 안 맞아 올바른 대응을 알 수 없으므로 넷 다 needs_review로 남아야지, 아무 진술문도 엉뚱한
# 코드에 붙으면 안 된다.
CULTURE_TABLE_SAMPLE = """(5) 문화

[9생독05-01
[9생독05-02
[9생독05-03
[9생독05-04

독일어권 주요 문화 내용을 이해한다.
독일어권 주요 문화 내용을 조사하여 설명한다.
독일어권 주요 문화 내용을 이해하여 독일어 의사소통 상황에 활용한다.
"""

def test_broken_table_does_not_misattach_statement_to_wrong_code():
    recs = extract_from_text(CULTURE_TABLE_SAMPLE, subject="제2외국어", source_label="[별책16]")
    by_code = {r["code"]: r for r in recs}
    assert set(by_code) == {"9생독05-01", "9생독05-02", "9생독05-03", "9생독05-04"}
    assert all(r["needs_review"] for r in by_code.values())
    assert all(r["statement"] is None for r in by_code.values())

# 실제 별책16 10286~10293행 발췌: 12독문01-03/01-04는 OCR로 코드 마커 자체가 사라져 본문에
# 전혀 등장하지 않는다(존재하지 않는 코드를 지어내면 안 된다). 01-02는 종결 마침표가 없는 채로
# '&'로 시작하는 OCR 잡음 줄을 거쳐 이어지고, 01-05는 괄호가 "(...|" 로 손상돼 있다.
ORPHAN_CODE_SAMPLE = """나. 성취기준

[12독문01-01] 독일어권 문화에 대한 다양한 내용을 이해한다.
[12독문01-02] 독일어권 문화에 대한 다양한 내용을

& 이해하여 독일어 의사소통 상황에 활용한다

(12독문01-05| 독일어권 문화에 대한 자료를 비판적으로 해석하여 다양한 관점을
공유한다
[12독문01-06]독일어권 문화와 우리 문화의 차이점과 공통점을 비교한다.
"""

def test_orphan_code_not_misattached_to_neighbors():
    recs = extract_from_text(ORPHAN_CODE_SAMPLE, subject="제2외국어", source_label="[별책16]")
    by_code = {r["code"]: r for r in recs}
    assert "12독문01-03" not in by_code  # 코드 마커 소실 — 지어내지 않는다
    assert "12독문01-04" not in by_code
    assert by_code["12독문01-01"]["statement"] == "독일어권 문화에 대한 다양한 내용을 이해한다."
    assert by_code["12독문01-02"]["needs_review"] is True   # 마침표 없이 끝남 — 검토로 남긴다
    assert by_code["12독문01-05"]["needs_review"] is True
    # 이웃(01-06)이 자기 것 아닌 문장을 흡수하지 않았는지 확인
    assert by_code["12독문01-06"]["statement"] == "독일어권 문화와 우리 문화의 차이점과 공통점을 비교한다."

# 실제 별책16 16544~16546행 발췌: 문장은 온전한데 OCR이 종결 마침표만 지운 경우.
# 다음 줄이 바로 다음 코드라 더 가져올 텍스트가 없다 — 있는 그대로 회수하되 needs_review는 유지.
MISSING_PERIOD_SAMPLE = """[12스어01-01] 발음 규칙에 유의하여 날말을 식별한다.
[12스어01-02] 날말이나 간단한 구, 문장을 듣고 의미를 이해한다
[12스어01-03] 간단한 의사소통 표현을 듣고 상황에 맞게 반응한다.
"""

def test_missing_trailing_period_recovered_but_flagged():
    recs = extract_from_text(MISSING_PERIOD_SAMPLE, subject="제2외국어", source_label="[별책16]")
    by_code = {r["code"]: r for r in recs}
    assert by_code["12스어01-01"]["needs_review"] is False  # 정상 종결 — 비교 대조군
    r = by_code["12스어01-02"]
    assert r["statement"] == "날말이나 간단한 구, 문장을 듣고 의미를 이해한다"  # 있는 그대로, 마침표 발명 안 함
    assert r["needs_review"] is True  # 명시적 종결자를 못 찾았다는 사실은 계속 표시
    assert by_code["12스어01-03"]["statement"] == "간단한 의사소통 표현을 듣고 상황에 맞게 반응한다."
