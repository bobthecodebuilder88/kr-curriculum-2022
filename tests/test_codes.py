from pipeline.codes import find_codes, canonical, grade_band

def test_standard_two_part():
    assert find_codes("[9수01-01] 소인수분해의 뜻을 알고") == ["9수01-01"]
    assert find_codes("[2국01-01] 중요한 내용") == ["2국01-01"]

def test_split_bracket_and_inner_space():
    # 여는 괄호가 앞 줄로 분리된 경우 + 코드 내부 공백
    assert find_codes("…설명한다.\n12독작01-06] 독서는") == ["12독작01-06"]
    assert find_codes("[12화언 01-05] 화법") == ["12화언01-05"]

def test_three_part_high_school_common():
    assert find_codes("10공국1-01-01 글을 읽고") == ["10공국1-01-01"]
    assert find_codes("[10통과2-02-03]") == ["10통과2-02-03"]

def test_br_inside_table_cell():
    assert find_codes("|[9기가01-<br>02] 기술|A|…|") == ["9기가01-02"]

def test_rejects_noise():
    assert find_codes("[자료1] [수타기] 93쪽-12 1998-2001") == []

def test_canonical_and_grade_band():
    assert canonical("12화언 01-05") == "12화언01-05"
    assert canonical("hello") is None
    assert grade_band("2국01-01") == "초1-2"
    assert grade_band("4과01-01") == "초3-4"
    assert grade_band("6사01-01") == "초5-6"
    assert grade_band("9수01-01") == "중1-3"
    assert grade_band("10공수1-01-01") == "고(공통)"
    assert grade_band("12대수01-01") == "고(선택)"

def test_grade_digit_not_swallowed():
    # PDF artifact glues a stray digit onto the code; the code must still be recovered
    assert find_codes("19생독04-01]") == ["9생독04-01"]
    assert canonical("19생독04-01") == "9생독04-01"

def test_rejects_code_shaped_prose():
    assert find_codes("주소: 경기 동두천시 평화로2910번길 96-63") == []
    assert find_codes("2022년 개정 12차 회의 자료 96-63 참조") == []

def test_ocr_corrupted_brackets_still_recognized():
    # 별책16:10292 — PDF OCR mangled [ ] into ( | on a real standard in the
    # sequential list 12독문01-01..07; the code must survive.
    assert find_codes("(12독문01-05| 독일어권 문화를 해석한다.") == ["12독문01-05"]


def test_middle_school_social_studies_parenthesised_qualifier():
    # 중학교 사회는 지리·일반사회를 한 별책 안에서 괄호로 나눈다. 이 모양을 놓치면
    # 중학교 사회 74개 성취기준 전체가 데이터베이스에서 사라진다.
    # 별책7:1707
    assert find_codes("[9사(지리)01-01] 세계 여러 지역의 특성을 해당 지역의 위치와") == ["9사(지리)01-01"]
    # 별책7:2216
    assert find_codes("[9사(일사)01-01] 사회화의 의미를 일상생활의") == ["9사(일사)01-01"]
    assert grade_band("9사(지리)01-01") == "중1-3"
    assert canonical("9사(일사)03-02") == "9사(일사)03-02"


def test_roman_numeral_abbreviation_with_dashed_area():
    # 로마숫자 약어 과목은 영역 번호 앞에도 대시를 쓴다(무대시형은 코퍼스에 0회).
    # 고등학교_3. 영어과 선택과목 성취수준 현장 보급본-성취기준.md:621
    assert find_codes("[12영Ⅰ-01-01] 말이나 글의 세부 정보를 파악한다.") == ["12영Ⅰ-01-01"]
    # 같은 파일:3599 — 변환기가 Ⅱ를 ASCII II로 떨어뜨린 줄. 이 줄이 그 성취기준의
    # 성취수준 A~E를 유일하게 실어 나르므로 반드시 인식해야 한다.
    assert find_codes("[12영II-01-01] 다양한 주제에 대한 말") == ["12영II-01-01"]
    # 고등학교_2. 수학과 선택과목 성취수준 현장 보급본-성취기준.md:3840, 9388
    assert find_codes("[12미적Ⅰ-01-01] 함수의 극한의 뜻을 알고") == ["12미적Ⅰ-01-01"]
    assert find_codes("[12미적Ⅱ-01-01] 수열의 극한") == ["12미적Ⅱ-01-01"]
    assert grade_band("12영Ⅱ-02-09") == "고(선택)"


def test_rejects_specialised_high_school_ncs_codes():
    # 특성화고 NCS 코드는 Phase 2 범위다. 학년 접두가 없다는 점만이 이들을 막고
    # 있으므로, 3단 패턴을 넓힐 때 이 60,818건이 조용히 딸려 들어오지 않는지 지킨다.
    # 별책23:1754 외
    assert find_codes("[상경 01-01-01] 경제 활동의 주체와 객체를 구분하고") == []
    assert find_codes("[성직 01-01]") == []
    assert find_codes("[도자기 01-01-01]") == []
    assert find_codes("[세원 01-01-02] [제선 01-01-03]") == []


def test_rejects_stray_hyphen_variant_of_plain_abbreviation():
    # 부처 원문이 해설·표에서 대시를 잘못 끼워 넣은 자리(고물·동역·물실 합계 5회).
    # 정본은 무대시형이고(각 30·70·44회) 그쪽이 진술문과 성취수준을 모두 싣고 있어,
    # 대시형까지 받으면 한 성취기준이 코드 두 개로 갈라진다. 별책7:6414 / 과고:1964
    assert find_codes("• [12동역-01-01] 역사 탐구의 방식으로서") == []
    assert find_codes("[12고물-01-04] 뉴턴의 운동 법칙과 케플") == []
    # 같은 성취기준의 정본 표기는 그대로 인식된다.
    assert find_codes("[12동역01-01] 역사 기행을 통한 탐구의 방법을") == ["12동역01-01"]
    assert find_codes("[12고물01-04] 뉴턴의 운동 법칙과") == ["12고물01-04"]
