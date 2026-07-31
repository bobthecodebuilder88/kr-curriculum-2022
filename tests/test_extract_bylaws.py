from pipeline.sources import BYLAWS, LEVEL_DOCS
from pipeline.extract_bylaws import extract_from_text, drop_cross_references

def test_all_manifest_files_exist():
    for e in BYLAWS:
        assert e["path"].exists(), e["path"]
    assert len(LEVEL_DOCS) >= 55  # 초3 + 중16 + 고41 - 별책류 제외분

# 브리프 Step 3에 제시된 합성 fixture 그대로(실제 원문 발췌 아님, 브리프가 지정한 예시).
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

# 아래부터는 전부 실제 원문 100% 그대로(오탈자·OCR 잡음 포함, 수정 없음)의 발췌다. 생략한
# 줄이 있으면 각 fixture 주석에 정확히 어느 줄을 왜 뺐는지 밝힌다 — 포함한 줄은 한 글자도
# 고치지 않는다(이전 라운드에서 "간난한"→"간단한", "we"→"다양한" 식으로 조용히 고쳐 쓴 문제가
# 리뷰에서 지적됐다).

# 별책6(도덕) 296~312행. 300~308행(9도01-03~07)은 이 테스트와 무관해 생략 — 포함한 296/298/
# 310/312행은 원문 그대로(끝 공백 등 표기 차이 제외).
DASH_BULLET_SAMPLE = """- [9도01-01] 자신의 삶과 가치관에 대한 성찰을 통해 자아를 올바로 이해하고, 삶에서 도덕이 필요한 이유에 근거하여 도덕적인 삶에 대한 의지를 기른다.

- [9도01-02] 일상에서 발생하는 부도덕한 행동의 여러 원인을 분석하고, 도덕적 인격이 갖추어야 할 특성들을 파악하여 이를 내면화하는 의지를 기른다.

## (가) 성취기준 해설

- [9도01-02] 이 성취기준의 취지는 일상의 부도덕한 행동들이 옳고 그름을 분별하지 못하는 무지뿐만 아니라 자기정당화 기제를 포함한 도덕 심리학적 원인에서 비롯될 수 있음을 파 악하고, 이러한 부도덕한 행동의 원인을 극복한 훌륭한 인격자의 도덕적 특성들을 탐구함 으로써 도덕적 인격이 갖춰야 할 도덕성의 구성요소를 내면화하는 의지를 기르는 것이다.
"""

def test_dash_bullet_prefix_recognized_and_body_wins_over_commentary():
    recs = extract_from_text(DASH_BULLET_SAMPLE, subject="도덕", source_label="[별책6]")
    by_code = {r["code"]: r for r in recs}
    assert set(by_code) == {"9도01-01", "9도01-02"}
    assert by_code["9도01-02"]["statement"] == (
        "일상에서 발생하는 부도덕한 행동의 여러 원인을 분석하고, "
        "도덕적 인격이 갖추어야 할 특성들을 파악하여 이를 내면화하는 의지를 기른다."
    )
    assert by_code["9도01-02"]["needs_review"] is False

# 별책16(제2외국어) 1018~1040행. 1019~1032행(코드 등장 전의 OCR 잡음 줄: "oe,", "2", "~~ 2" 등)은
# 생략 — 코드가 하나도 없어 결과에 영향 없다. 1033행부터는 원문 그대로: PDF 표가 깨져 코드 4개가
# 본문 텍스트 없이 연달아 나열되고, 빈 줄 뒤에 진술문 3개짜리 블록(1040행 라틴 잡음 포함, 그대로)이
# 붙는다. 코드-진술문 개수가 안 맞아 올바른 대응을 알 수 없으므로 넷 다 None으로 남아야 한다.
CULTURE_TABLE_SAMPLE = """(5) 문화

[9생독05-01
[9생독05-02
[9생독05-03
[9생독05-04

독일어권 주요 문화 내용을 이해한다.
독일어권 주요 문화 내용을 조사하여 설명한다.
독일어권 주요 문화 내용을 이해하여 독일어 ee 1  Jao] 활용한다.
"""

def test_broken_table_does_not_misattach_statement_to_wrong_code():
    recs = extract_from_text(CULTURE_TABLE_SAMPLE, subject="제2외국어", source_label="[별책16]")
    by_code = {r["code"]: r for r in recs}
    assert set(by_code) == {"9생독05-01", "9생독05-02", "9생독05-03", "9생독05-04"}
    assert all(r["statement"] is None for r in by_code.values())
    assert all(r["needs_review"] for r in by_code.values())

# 별책16 10285~10294행, 원문 100% 그대로(오탈자·OCR 잡음 전부 보존: "we", "환용한다",
# "Hood", "ARS HAO", "비만적으로", "OPN", "SERS", "문회와" 등 전부 원문 표기 그대로).
# 12독문01-03/04는 이 구간에 코드 마커 자체가 없다(OCR로 소실 — 별도 fixture에서 04는 해설에서만
# 등장하는 경우를 다룬다). 01-02는 종결 마침표 없이 '&'로 시작하는 OCR 잡음 줄을 거쳐 이어지고,
# 01-05는 괄호가 "(...|"로 손상돼 있다.
ORPHAN_CODE_SAMPLE = """나. 성취기준

[12독문01-01] 독일어권 문화에 대한 다양한 내용을 이해한다.
[12독문01-02] 독일어권 문화에 대한 we 내용을

& 이하하여 독일어 의사소통 상황에 환용한다

(12독문01-05| 독일어권 Hood 대한 ARS HAO 비만적으로 해석하여 다양한 OPN Ho
공유한다
[12독문01-06]독일어권 문회와 우리 문화의 차이점과 SERS 비교한다.
"""

def test_orphan_code_not_misattached_to_neighbors():
    recs = extract_from_text(ORPHAN_CODE_SAMPLE, subject="제2외국어", source_label="[별책16]")
    by_code = {r["code"]: r for r in recs}
    assert "12독문01-03" not in by_code  # 코드 마커 소실 — 지어내지 않는다
    assert by_code["12독문01-01"]["statement"] == "독일어권 문화에 대한 다양한 내용을 이해한다."
    assert by_code["12독문01-02"]["needs_review"] is True   # 마침표 없이 끝남 — 검토로 남긴다
    assert "환용한다" in by_code["12독문01-02"]["statement"]  # 있는 그대로(오타까지) 회수
    assert by_code["12독문01-05"]["needs_review"] is True
    # 이웃(01-06)이 자기 것 아닌 문장을 흡수하지 않았는지: 원문 그대로의 자기 문장만 갖는다
    assert by_code["12독문01-06"]["statement"] == "독일어권 문회와 우리 문화의 차이점과 SERS 비교한다."

# 별책16 10284~10286, 10297, 10305~10307행, 원문 100% 그대로. 10287~10296행(01-02, 01-05~07 본문)과
# 10298~10304행(01-01, 01-02 해설)은 이 테스트와 무관해 생략 — 포함한 줄은 그대로.
# 12독문01-04는 본문에 전혀 등장하지 않고 해설(10305~10307)에만 "* [12독문01-04] …"로 등장한다.
COMMENTARY_ONLY_SAMPLE = """나. 성취기준

[12독문01-01] 독일어권 문화에 대한 다양한 내용을 이해한다.

(가) 성취기준 해설

* [12독문01-04] 이 성취기준은 관심 분야 또는 진로와
된 자료를 토대로 탐색하여 자신의 진로-학업과 연
로 교과 간 AA} 통합을 위해 설정하였다.
"""

def test_commentary_only_code_gets_null_not_promoted():
    """C2 재현: 본문 등장이 아예 없고 해설에서만 코드가 등장하는 경우.
    브리프의 "absence over fabrication" 원칙 — 존재는 기록하되(setdefault) 해설
    문장을 진술문으로 승격시키지 않는다."""
    recs = extract_from_text(COMMENTARY_ONLY_SAMPLE, subject="제2외국어", source_label="[별책16]")
    by_code = {r["code"]: r for r in recs}
    assert by_code["12독문01-01"]["statement"] == "독일어권 문화에 대한 다양한 내용을 이해한다."
    assert by_code["12독문01-01"]["statement_source"] == "body"
    assert by_code["12독문01-01"]["commentary_only"] is False
    assert "12독문01-04" in by_code  # 해설에서라도 등장은 했다 — 없었던 것처럼 지우지 않는다
    assert by_code["12독문01-04"]["statement"] is None  # 해설 문장을 진술문 자리에 채우지 않는다
    assert by_code["12독문01-04"]["statement_source"] is None
    assert by_code["12독문01-04"]["commentary_only"] is True
    assert by_code["12독문01-04"]["needs_review"] is True

# 별책16 36552행과 3953행, 원문 100% 그대로(OCR 잡음·깨진 마커 전부 보존). 두 코드 모두
# 별책16 어디에도 본문 목록 등장이 없고 해설에서만 나타난다. 실제 성취기준인데 PDF 변환이
# 본문을 지운 자리이므로, 레코드를 지우면 verify.py가 실재하는 코드를 FAKE로 몰아세운다.
COMMENTARY_ONLY_REAL_SAMPLE = """(가) 성취기준 해설

* [12아회01-01] 이 성취기준은 아랍어의 자음과 모음, 발음기호, 강세, 억양, 장

을 듣고 상황에 맞게 몸짓이나 말로

© 19생종04-02] 이 성취기준은 다양한 유형의 텍스트에서 요구되
"""

def test_commentary_only_codes_are_kept_with_flags_not_dropped():
    recs = extract_from_text(COMMENTARY_ONLY_REAL_SAMPLE, subject="제2외국어", source_label="[별책16]")
    by_code = {r["code"]: r for r in recs}
    for code in ("12아회01-01", "9생종04-02"):
        r = by_code[code]
        assert r["statement"] is None          # 해설 문장을 진술문으로 올리지 않는다
        assert r["statement_source"] is None
        assert r["commentary_only"] is True    # 왜 비었는지를 기록한다
        assert r["needs_review"] is True

# 별책12(음악) 518~528행, 원문 100% 그대로(끝 공백 제외). 한 줄에 코드 3개가 붙어 나오는 실제
# 사례(520행) + 그다음 코드가 별도 줄(522행) + 해설 재등장(526, 528행, "이 성취기준은…").
MUSIC_PACKED_LINE_SAMPLE = """## (3) 창작

[9음03-01] 음악적 의도나 아이디어를 여러 매체나 방법에 적용하여 자기 주도적으로 창작한다. [9음03-02] 오선보, 정간보 등의 기보법을 활용하여 조건에 따라 악곡의 일부를 바꾼다. [9음03-03] 음악의 요소와 특징을 활용하여 간단한 형식의 음악을 만든다.

[9음03-04] 생활 속의 영역과 연계하여 음악을 만들고 활용하며 책임감을 갖는다.

## (가) 성취기준 해설

- [9음03-01] 이 성취기준은 음악적 의도나 아이디어를 독창적으로 사고하고 자유롭게 발산 하는 능력을 기르도록 하기 위해 설정하였다. 음악의 소재나 주제에 따라 아이디어를 떠올려 보고, 창작에 사용되는 다양한 매체를 활용하여 노래나 연주, 신체표현 등 자신이 표현하고자 하는 방식으로 나타낼 수 있도록 주도적으로 계획하고 창작하도록 하는 데 중점을 둔다.

- [9음03-02] 이 성취기준은 다양한 기보법에 대한 이해를 바탕으로 음악 창작 능력을 기르도록 하기 위해 설정하였다. 음악 표현과 소통을 위한 기보의 필요성을 인식하고, 오선보나 정간보 등 기존의 기보법과 앱이나 프로그램 등 다양한 소프트웨어를 활용하여 음악 요소나 주제 등의 조건에 따라 악곡의 일부를 변형하며 새롭게 만들어보는 데 중점을 둔다.
"""

def test_packed_codes_on_one_line_all_extracted():
    """C1 재현: 줄 앞머리 스캔은 03-01만 읽고 03-02/03을 통째로 놓쳤다. span 기반 스캔이면
    한 줄에 붙어 나온 코드 전부를 자기 몫의 문장으로 읽어야 한다."""
    recs = extract_from_text(MUSIC_PACKED_LINE_SAMPLE, subject="음악", source_label="[별책12]")
    by_code = {r["code"]: r for r in recs}
    assert by_code["9음03-01"]["statement"] == "음악적 의도나 아이디어를 여러 매체나 방법에 적용하여 자기 주도적으로 창작한다."
    assert by_code["9음03-02"]["statement"] == "오선보, 정간보 등의 기보법을 활용하여 조건에 따라 악곡의 일부를 바꾼다."
    assert by_code["9음03-03"]["statement"] == "음악의 요소와 특징을 활용하여 간단한 형식의 음악을 만든다."
    assert by_code["9음03-04"]["statement"] == "생활 속의 영역과 연계하여 음악을 만들고 활용하며 책임감을 갖는다."
    assert all(r["needs_review"] is False for r in by_code.values())

# 별책16 7729~7743행, 원문 100% 그대로(오탈자·OCR 잡음 전부 보존). 9생베02-03의 진술문 후보
# 구간에 빈 줄로 시작되지 않는 잡음 줄들("af oT", "Sw &" 등)이 낀 뒤 "(가) 성취기준 해설" 헤더가
# 나오고, 그 헤더 너머에는 (파싱조차 안 되는 코드 마커긴 하지만) 완전히 다른 해설 문장이 있다.
SPEAKING_SPLICE_SAMPLE = """(2) 말하기

[9생베02-01] 날말이
[9생베02-02] 날말이
[9생베02-03] 상대방

af oT
Sw &
c
Ol
ott

(가) 성취기준 해설
+ (oasion-08 이 성취기준은 eet SoS Was Bae Ten SBA HE
소통의 SASS 깨닫고 적극적으로 말하기 활동에 참여하는 AS 의미한다. 이 과정에서
"""

def test_accumulation_stops_at_section_header_no_splice():
    """C4 재현: 이전 구현은 헤더에서 멈추지 않고 이어붙여 완전히 다른 문장과 접합된 진술문을
    만들어냈다(별책16 9생베02-03 실사고). 진술문을 못 찾더라도 None이 스플라이스보다 낫다."""
    recs = extract_from_text(SPEAKING_SPLICE_SAMPLE, subject="제2외국어", source_label="[별책16]")
    by_code = {r["code"]: r for r in recs}
    assert by_code["9생베02-03"]["statement"] is None
    assert by_code["9생베02-03"]["needs_review"] is True
    # 어떤 레코드의 진술문에도 헤더/해설 텍스트가 섞여 들어가지 않았는지 전수 확인
    assert all(r["statement"] is None or "성취기준 해설" not in r["statement"] for r in recs)
    assert all(r["statement"] is None or "eet SoS" not in r["statement"] for r in recs)

# 별책16 16544~16546행, 원문 100% 그대로(오탈자 "간난한", 잡음 "WHS"/"EAS" 포함, 수정 없음).
MISSING_PERIOD_SAMPLE = """[12스어01-01] 발음 규칙에 유의하여 날말을 식별한다.
[12스어01-02] 날말이나 간난한 구, WHS 듣고 의미를 이해한다
[12스어01-03] 간단한 의사소통 EAS 듣고 상황에 맞게 반응한다.
"""

def test_missing_trailing_period_recovered_but_flagged():
    recs = extract_from_text(MISSING_PERIOD_SAMPLE, subject="제2외국어", source_label="[별책16]")
    by_code = {r["code"]: r for r in recs}
    assert by_code["12스어01-01"]["needs_review"] is False  # 정상 종결 — 비교 대조군
    r = by_code["12스어01-02"]
    assert r["statement"] == "날말이나 간난한 구, WHS 듣고 의미를 이해한다"  # 있는 그대로, 마침표 발명 안 함
    assert r["needs_review"] is True  # 명시적 종결자를 못 찾았다는 사실은 계속 표시

# 별책8(수학) 808~809행, 원문 100% 그대로(줄바꿈 위치까지) — 단위 표기가 숫자에 공백 없이
# 바로 붙는 정상 사례.
UNIT_TOKEN_SAMPLE = """[4수03-15] 길이 단위 1mm와 1km를 알고, 이를 이용하여 길이를 측정하고 어림하며 수학의
유용성을 인식할 수 있다.
"""
# 별책8 810~811행, 원문 100% 그대로 — 단위가 인용부호와 공백 사이에 홀로 서고("‘몇 cm 몇 mm’")
# 뒤에 조사가 붙지 않는 정상 사례. "라틴 런 뒤에 조사가 없으면 잡음"이라는 규칙은 여기서 오탐을 냈다.
UNIT_QUOTED_SAMPLE = """[4수03-16] 1cm와 1mm, 1km와 1m의 관계를 이해하고, 길이를 ‘몇 cm 몇 mm’와 ‘몇 mm’,
‘몇 km 몇 m’와 ‘몇 m’로 다양하게 표현할 수 있다.
"""
# 별책16 원문 100% 그대로 — 한국어 낱말 자리를 라틴 잡음이 차지한 실제 사례("USS"←"자료를" 등).
REAL_GIBBERISH_SAMPLE = "[9생아05-01] 간략한 아랍 문화 USS 이해한다."

def test_ocr_garble_units_pass_real_gibberish_flagged():
    for sample in (UNIT_TOKEN_SAMPLE, UNIT_QUOTED_SAMPLE):
        rec = extract_from_text(sample, subject="수학", source_label="[별책8]")[0]
        assert rec["needs_review"] is False, rec["statement"]  # 단위·약어는 오탐 금지
    bad = extract_from_text(REAL_GIBBERISH_SAMPLE, subject="제2외국어", source_label="[별책16]")[0]
    assert bad["needs_review"] is True

# 별책6(도덕) 180~200행. 184~196행(해설 본문·고려 사항 본문·쪽 머리말)은 이 테스트와 무관해
# 생략하되 구조(해설 헤더 → 해설 항목 → 고려 사항 헤더 → 본문 재개 헤더)는 그대로 보존했다.
# 포함한 줄은 원문 그대로. 핵심: 본문이 재개되는 198행 "## (2) 타인과의 관계"에는 '성취기준'
# 이라는 낱말이 없고, 이 문서에는 "나. 성취기준" 류의 헤더가 단 하나도 없다.
BODY_RESUMES_WITHOUT_KEYWORD_SAMPLE = """- [6도01-03] 자기가 하고 싶은 일을 선택할 때 도덕적 고려의 필요성을 알고 자신의 특기와 적성을 탐색하여 진로계획을 수립한다.

## (가) 성취기준 해설

- [6도01-02] 이 성취기준의 취지는 자신의 행동에 대한 문제점을 확인하고 재정립하도록 하여 반성하는 태도를 기르기 위한 것이다. 학생이 스스로 자기 행동의 문제를 인식하고 개선하려 노력함으로써 바른 도덕 생활의 토대를 마련하도록 한다.

## (나) 성취기준 적용 시 고려 사항

- 학생이 성실하게 생활하면서도 자신의 삶에 대한 반성을 통해 도덕적인 삶으로 개선시켜 나갈 수 있도록 하는 것에 중점을 둘 필요가 있다.

## (2) 타인과의 관계

- [4도02-01] 효, 우애의 의미와 필요성을 명료하게 이해하고 가족의 행복을 위해 할 수 있는 일을 탐색 하여 실천 계획을 세운다.
"""

def test_commentary_section_ends_at_next_heading():
    """해설 구간을 '해설 헤더'로 열고 '성취기준' 낱말이 든 헤더로만 닫으면, 그런 헤더가 없는
    문서(별책6)는 첫 해설 이후 문서 전체가 해설로 잠겨 진술문을 전부 잃는다(실측 null 93%).
    해설 구간은 종류를 가리지 않고 '다음 섹션 헤더'에서 닫혀야 한다."""
    recs = extract_from_text(BODY_RESUMES_WITHOUT_KEYWORD_SAMPLE, subject="도덕", source_label="[별책6]")
    by_code = {r["code"]: r for r in recs}
    assert by_code["4도02-01"]["statement"] == (
        "효, 우애의 의미와 필요성을 명료하게 이해하고 가족의 행복을 위해 할 수 있는 일을 탐색 하여 실천 계획을 세운다."
    )
    assert by_code["4도02-01"]["needs_review"] is False
    # 해설에만 등장한 6도01-02는 여전히 해설 문장을 얻지 못한다
    assert by_code["6도01-02"]["statement"] is None

# 별책8(수학) 1319~1333행, 원문 100% 그대로. 원본 PDF의 해설 상자가 본문 목록 한가운데로
# 끼어들어(1324~1327행) 본문 재개를 알리는 헤더 없이 1328행부터 다시 본문이 이어진다.
# 이 문서에서 해설 항목은 "•" 불릿을 달고 본문 항목은 0열에서 시작한다.
INTERLEAVED_COMMENTARY_BOX_SAMPLE = """[9수03-05] 다각형의 성질을 이해하고 설명할 수 있다.


수학과 교육과정
38
(가) 성취기준 해설
• [9수03-01] 점, 선, 면, 각과 관련된 용어는 다양한 상황에서 직관적으로 이해하게 한다.
• [9수03-03] 주어진 삼각형과 합동인 삼각형을 작도하는 활동을 하고, 자신의 방법을 설명
하게 한다.
[9수03-06] 부채꼴의 중심각과 호의 관계를 이해하고, 이를 이용하여 부채꼴의 호의 길이와 넓이를
구할 수 있다.
숗 입체도형의 성질
[9수03-07] 구체적인 모형이나 공학 도구를 이용하여 다면체와 회전체의 성질을 탐구하고, 이를
설명할 수 있다.
"""

def test_body_resumes_at_column_zero_inside_interleaved_commentary_box():
    """해설 상자가 본문 목록에 끼어든 구간. 해설 항목(불릿)은 진술문 출처가 되지 않아야 하고,
    0열에서 시작하는 본문 항목은 해설 구간 안에 있어도 자기 진술문을 얻어야 한다."""
    recs = extract_from_text(INTERLEAVED_COMMENTARY_BOX_SAMPLE, subject="수학", source_label="[별책8]")
    by_code = {r["code"]: r for r in recs}
    assert by_code["9수03-06"]["statement"] == (
        "부채꼴의 중심각과 호의 관계를 이해하고, 이를 이용하여 부채꼴의 호의 길이와 넓이를 구할 수 있다."
    )
    assert by_code["9수03-07"]["statement"] == (
        "구체적인 모형이나 공학 도구를 이용하여 다면체와 회전체의 성질을 탐구하고, 이를 설명할 수 있다."
    )
    # 불릿 달린 해설 항목은 진술문을 공급하지 않는다
    assert by_code["9수03-01"]["statement"] is None
    assert by_code["9수03-03"]["statement"] is None
    # 진술문이 뒤따르는 소제목("숗 입체도형의 성질")을 삼키지 않았는지
    assert all(r["statement"] is None or "입체도형의 성질" not in r["statement"] for r in recs)

# 별책7(사회) 1032~1036행, 원문 100% 그대로 — 본문 목록인데 영역-일련번호 구분자가 하이픈이
# 아니라 en 대시(U+2013)다. 이 줄을 코드로 못 읽으면 두 성취기준의 본문 등장이 통째로 사라지고
# 해설 재등장만 남는다.
EN_DASH_CODE_SAMPLE = """(1) 우리가 사는 곳
[4사01–01] 주변 여러 장소에서의 경험과 느낌을 다양한 방식으로 표현하고, 장소감을 나누며 서로
존중하는 태도를 지닌다.
[4사01–02] 주변의 여러 장소를 살펴보고, 우리가 사는 곳을 더 살기 좋은 곳으로 만드는 방안을 탐
색한다.
(가) 성취기준 해설
• [4사01-01]은 학생들의 생활이 이루어지는 주변 여러 장소에서의 경험과 느낌을 글, 그림,
"""

def test_en_dash_separator_in_code_marker():
    recs = extract_from_text(EN_DASH_CODE_SAMPLE, subject="사회", source_label="[별책7]")
    by_code = {r["code"]: r for r in recs}
    assert set(by_code) == {"4사01-01", "4사01-02"}  # 코드는 하이픈으로 정규화
    assert by_code["4사01-01"]["statement"] == (
        "주변 여러 장소에서의 경험과 느낌을 다양한 방식으로 표현하고, 장소감을 나누며 서로 존중하는 태도를 지닌다."
    )
    assert by_code["4사01-01"]["needs_review"] is False

# 별책5(국어) 1723~1727행, 원문 100% 그대로 — 국어의 '고려 사항' 산문이 사회과 성취기준
# [6사12-02]를 인용한다. 국어 문서 어디에도 '사' 계열 코드의 본문 목록은 없다.
CROSS_SUBJECT_REFERENCE_SAMPLE = """(나) 성취기준 적용 시 고려 사항

• 지구가 처한 위기에 관련된 문제들을 찾아보고 일상에서 그러한 문제를 해결하기 위해 노
력하는 생태 소양을 함양하는 한편 융합적인 사고와 역량을 기를 수 있도록 지도한다. 예를
들어 사회과의 ‘지구촌을 위협하는 다양한 문제들을 파악하고, 지속가능한 미래를 위한 해
결 방안을 탐색’하는 성취기준([6사12-02])과 연계할 수 있는 문학 작품을 선정하여 교과
통합적 활동을 수행하도록 한다.
"""

# 별책7(사회) 1673~1674행, 원문 100% 그대로(줄바꿈 위치까지) — 위 인용이 가리키는 진짜 정의처.
SOCIAL_STUDIES_BODY_SAMPLE = """[6사12-02] 지구촌을 위협하는 다양한 문제들을 파악하고, 지속가능한 미래를 위한 해결 방안을 탐색
한다.
"""

def test_cross_subject_citation_excluded_but_real_definition_kept():
    """다른 교과의 성취기준을 인용한 것뿐인데 국어 레코드로 남기면 '국어가 6사12-02를
    정의한다'는 거짓이 된다. 진짜 정의는 사회에 있으므로 그쪽만 남는다."""
    korean = extract_from_text(CROSS_SUBJECT_REFERENCE_SAMPLE, subject="국어", source_label="[별책5]")
    social = extract_from_text(SOCIAL_STUDIES_BODY_SAMPLE, subject="사회", source_label="[별책7]")
    # 문서 하나만 봐서는 인용인지 OCR 구멍인지 알 수 없으므로 추출 단계에선 남긴다
    assert [r["code"] for r in korean] == ["6사12-02"]
    assert korean[0]["commentary_only"] is True
    # 코퍼스 전체를 대조하는 단계에서만 제외된다
    kept, cross = drop_cross_references(korean + social)
    assert [(r["subject"], r["code"]) for r in cross] == [("국어", "6사12-02")]
    assert [(r["subject"], r["code"]) for r in kept] == [("사회", "6사12-02")]
    assert kept[0]["statement"].startswith("지구촌을 위협하는")

def test_code_namespace_collision_is_not_a_cross_reference():
    """12심독은 제2외국어에선 '심화 독일어', 영어에선 '심화 영어 독해'로 서로 다른 성취기준이다.
    '다른 별책에 같은 코드가 있다'만으로 제외하면 제2외국어의 해설 전용 12심독02-02가
    영어 쪽 정의를 인용한 것으로 오판되어 사라진다."""
    foreign = [{"code": "12심독02-02", "subject": "제2외국어", "statement": None,
                "statement_source": None, "commentary_only": True, "needs_review": True},
               # 같은 문서에 12심독 본문 정의가 실제로 존재한다 — 이게 오판을 막는 신호
               {"code": "12심독01-01", "subject": "제2외국어", "statement": "독일어 문장을 읽고 이해한다.",
                "statement_source": "body", "commentary_only": False, "needs_review": False}]
    english = [{"code": "12심독02-02", "subject": "영어", "statement": "글의 목적을 파악한다.",
                "statement_source": "body", "commentary_only": False, "needs_review": False}]
    kept, cross = drop_cross_references(foreign + english)
    assert cross == []
    assert ("제2외국어", "12심독02-02") in [(r["subject"], r["code"]) for r in kept]

# 별책16 3680~3688행, 원문 100% 그대로(오탈자 "날말"/"간난하고", 표 파편 "ㅣ"/"적" 전부 보존).
# PDF 표가 세로로 조각나 9생중02-03의 본문 줄이 "간단한"에서 끊기고, 빈 줄 너머 3684행은
# 9생중02-02의 문장이다(성취수준 문서가 그렇게 귀속시킨다). 이어붙이면 부처가 그 코드로
# 발표한 적 없는 문장이 만들어진다.
SHREDDED_COLUMN_SAMPLE = """초적인
[9생중02-03] 간단한

날말이나 구, 간난하고 쉬운 문장을 활용하여 질문하거나 대답한다.
ㅣ

적
한 의사소통 표현을 상황에 맞게 자신감을 가지고 적극적으로 말한다.
"""

def test_short_fragment_does_not_bridge_blank_line():
    """F4 재현: 빈 줄 건너뛰기가 헤더 스플라이스와 다른 경로로 같은 날조를 만들었다.
    '간단한'(3자)은 진술문이 될 수 없는 조각이므로 건너뛰지 않는다. 인접 검사로는
    잡을 수 없다 — 접합된 문자열이 원문에 그대로 존재하기 때문이다."""
    recs = extract_from_text(SHREDDED_COLUMN_SAMPLE, subject="제2외국어", source_label="[별책16]")
    r = {x["code"]: x for x in recs}["9생중02-03"]
    assert r["statement"] is None       # 02-02의 문장을 가져오지 않는다
    assert r["needs_review"] is True
    assert all("질문하거나 대답한다" not in (x["statement"] or "") for x in recs)

# 별책18 716~718행, 원문 100% 그대로 — 쪽 경계에서 변환기가 "⋅"와 "-"를 끼워 넣었다.
# 조각이 50자라 이어붙이는 것 자체는 옳고, 끼어든 마크업만 떼어야 한다.
PAGE_BREAK_MARKUP_SAMPLE = """- [9보03-04] 성폭력⋅성매개감염병 등 성 건강 위험요소를 미디어 문해력 및 성문화와 관련지어 탐색하고 ⋅

- 건강하게 관리 옹호한다.
"""

def test_page_break_markup_stripped_and_flagged():
    r = extract_from_text(PAGE_BREAK_MARKUP_SAMPLE, subject="중학교 선택", source_label="[별책18]")[0]
    assert r["statement"] == (
        "성폭력⋅성매개감염병 등 성 건강 위험요소를 미디어 문해력 및 성문화와 관련지어 탐색하고 건강하게 관리 옹호한다."
    )  # 낱말 사이 "성폭력⋅성매개감염병"의 구분자는 그대로 남는다
    assert r["needs_review"] is True   # 조립 중 마크업을 뗐다 = 조립 자체가 의심스럽다

# ---------------------------------------------------------------------------
# 전 코퍼스 게이트. 위 fixture 테스트들이 규칙 하나하나를 지키는 반면, 아래 둘은
# 14개 별책 전체를 실제로 돌려 "지어내지 않는다"와 "빠뜨리지 않는다"를 동시에 건다.
# 전체 추출은 0.3초 정도라 매 실행에 포함해도 부담이 없다.
# ---------------------------------------------------------------------------
import re
from pipeline.clean import load_text
from pipeline.codes import find_codes

# 변환기가 쪽 경계에 끼워 넣은 홀로 선 불릿만 무시한다. 낱말 사이 구분자(성폭력⋅성매개감염병)는
# 앞뒤가 공백이 아니므로 그대로 남는다 — 즉 이 정규화는 마크업만 지우지 본문은 건드리지 않는다.
_MARKUP_TOKEN = re.compile(r"(?<=\s)[⋅•·∙\-–—*©§]+(?=\s)")

def _norm(text):
    return re.sub(r"\s+", " ", _MARKUP_TOKEN.sub(" ", text))

def _shipped():
    """main()이 실제로 써 내는 것과 같은 레코드 목록 + 과목별 정규화 원문."""
    recs, src = [], {}
    for e in BYLAWS:
        text = load_text(e["path"])
        recs += extract_from_text(text, e["subject"], e["source_label"])
        src[e["subject"]] = _norm(text)
    kept, cross = drop_cross_references(recs)
    return kept, cross, src

def test_every_statement_appears_verbatim_in_its_source():
    """공백·불릿 마크업 정규화 외에는 원문 그대로여야 한다. 섹션 헤더를 건너뛰어 이어붙이거나
    쪽 머리말을 삼키거나 다른 코드의 문장을 접합하면 정규화된 원문에서 그 문자열을 찾을 수
    없다 — 즉 이 한 줄이 '접합·지어냄 없음'을 코퍼스 전체에 대해 증명한다."""
    kept, _, src = _shipped()
    offenders = [(r["subject"], r["code"], r["statement"])
                 for r in kept if r["statement"] and _norm(r["statement"]) not in src[r["subject"]]]
    assert offenders == [], offenders[:5]

def test_fixtures_are_verbatim_from_the_corpus():
    """위 fixture들이 '원문 100% 그대로'라는 주장을 기계로 검증한다. 사람이 옮겨 적는 과정에서
    원문을 조용히 고치는 일이 두 번 있었다("간난한"→"간단한", "문회와"→"문화와") — 둘 다
    verbatim이 상품인 프로젝트에서 리뷰가 잡아냈다. 이제는 테스트가 잡는다."""
    import sys
    src = {l.strip() for e in BYLAWS for l in load_text(e["path"]).split("\n")}
    mod = sys.modules[__name__]
    drift = []
    for name in dir(mod):
        # BYLAW_SAMPLE은 브리프가 제시한 합성 예시라 원문 대조 대상이 아니다.
        if not name.endswith("_SAMPLE") or name == "BYLAW_SAMPLE":
            continue
        for line in getattr(mod, name).split("\n"):
            if line.strip() and line.strip() not in src:
                drift.append((name, line.strip()))
    assert drift == [], drift

def test_no_structural_markup_survives_in_any_statement():
    """불릿 글리프나 마커에서 떨어져 나온 선두 숫자는 부처 원문에 없다."""
    bullet = re.compile(r"(?:^|\s)[⋅•·∙©§*](?:\s|$)|(?:^|\s)-(?:\s|$)")
    lead_digit = re.compile(r"^\d(?:\s|$)")
    kept, _, _ = _shipped()
    bad = [(r["subject"], r["code"], r["statement"]) for r in kept if r["statement"]
           and (bullet.search(r["statement"]) or lead_digit.search(r["statement"]))]
    assert bad == [], bad[:5]

# 이 12개 교과는 원문이 온전해 진술문을 하나도 놓칠 이유가 없다. 제2외국어·도덕은 원문 자체가
# OCR로 뭉개진 구간이 있어 제외하되, 전체 null 비율에는 포함해 함께 건다.
_CLEAN_SUBJECTS = ["국어", "사회", "수학", "과학", "실과·기술가정·정보", "체육",
                   "음악", "미술", "영어", "통합교과", "한문", "중학교 선택"]

def test_coverage_no_nulls_in_clean_subjects_and_overall_under_10pct():
    kept, _, _ = _shipped()
    holes = {}
    for s in _CLEAN_SUBJECTS:
        nulls = [r["code"] for r in kept if r["subject"] == s and r["statement"] is None]
        if nulls:
            holes[s] = nulls
    assert holes == {}, holes
    assert sum(1 for r in kept if r["statement"] is None) / len(kept) < 0.10
    assert len(kept) >= 3144, len(kept)

def test_no_commentary_text_promoted_anywhere_in_corpus():
    """해설 문장이 진술문 자리에 올라오지 않았는지. 섹션 헤더 '자체'가 진술문에 섞였는지를 보되,
    '고려 사항'이라는 낱말만으로 걸지 않는다 — 별책18:1153 [9진로03-01]의 진짜 진술문이
    "진로의사결정의 방법과 고려 사항을 이해하고…"라서, 낱말 단위 검사는 정상 레코드를 잡는다."""
    headers = ("성취기준 해설", "성취기준 적용 시 고려 사항")
    kept, _, _ = _shipped()
    for r in kept:
        s = r["statement"]
        assert s is None or not s.startswith("이 성취기준"), (r["subject"], r["code"], s)
        assert s is None or not any(h in s for h in headers), (r["subject"], r["code"], s)

def test_no_unexplained_drops():
    """원문에서 인식된 코드는 그 문서의 과목으로 반드시 실려야 한다 — 유일한 예외는
    교차참조로 제외된 것뿐이고, 그건 제외 목록에 이유와 함께 남는다."""
    kept, cross, _ = _shipped()
    shipped = {(r["subject"], r["code"]) for r in kept}
    excluded = {(r["subject"], r["code"]) for r in cross}
    missing = set()
    for e in BYLAWS:
        for code in find_codes(load_text(e["path"])):
            if (e["subject"], code) not in shipped:
                missing.add((e["subject"], code))
    assert missing == excluded, {"설명 안 된 누락": missing - excluded}
    assert excluded == {("국어", "6사12-02")}, excluded
