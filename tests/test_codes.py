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
