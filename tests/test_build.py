import json
from pipeline.build import merge, statement_agree, find_sequence_gaps, find_abbr_outliers

def test_statement_agree_tolerates_ocr_noise():
    a = "소인수분해의 뜻을 알고, 자연수를 소인수분해 할 수 있다."
    b = "소인수분해의  뜻을 알고, 자연수를 소인수분해 할 수 있다"  # 공백·마침표 차이
    assert statement_agree(a, b)
    assert not statement_agree(a, "소인수분해를 이용하여 최대공약수를 구할 수 있다.")

def test_merge_prefers_bylaw_statement_and_flags_conflicts():
    standards = [{"code": "9수01-01", "subject": "수학",
                  "statement": "소인수분해의 뜻을 알고, 자연수를 소인수분해 할 수 있다.",
                  "source": "[별책8]", "needs_review": False}]
    levels = [{"code": "9수01-01", "school": "중",
               "statement_in_table": "소인수분해의 뜻을 알고, 자연수를 소인수분해 할 수 있다",
               "levels": {"A": "…", "C": "…"}},
              {"code": "9수99-99", "school": "중", "statement_in_table": "가짜", "levels": {"A": "x"}}]
    merged, report = merge(standards, levels)
    rec = next(r for r in merged if r["code"] == "9수01-01")
    assert rec["levels"] == {"A": "…", "C": "…"}
    assert rec["school"] == "중" and rec["grade_band"] == "중1-3"
    assert rec["needs_review"] is False
    assert "9수99-99" in report["levels_only"]      # 별책에 없는 코드는 본데이터에 안 들어감
    assert all(r["code"] != "9수99-99" for r in merged)

def test_find_sequence_gaps_reports_ocr_destroyed_codes():
    from pipeline.build import find_sequence_gaps
    # 별책16 실제 사례: 12독문01-03은 원문에 문자열로 존재하지 않는다(OCR이 파괴).
    by_code = {c: {} for c in ["12독문01-01", "12독문01-02", "12독문01-04",
                               "12독문01-05", "9수01-01", "9수01-02"]}
    assert find_sequence_gaps(by_code) == ["12독문01-03"]

def test_find_sequence_gaps_quiet_when_complete():
    by_code = {c: {} for c in ["9수01-01", "9수01-02", "9수02-01"]}
    assert find_sequence_gaps(by_code) == []

def test_find_abbr_outliers_flags_ocr_corrupted_abbreviation():
    from pipeline.build import find_abbr_outliers
    # 별책16 실제 사례: 생프 시리즈가 여럿인데 성프는 딱 하나 — OCR 오독.
    by_code = {c: {} for c in ["9생프01-01", "9생프01-02", "9생프02-07",
                               "9성프02-07", "9수01-01", "9수01-02", "9수01-03"]}
    assert find_abbr_outliers(by_code) == ["9성프02-07"]

def test_find_abbr_outliers_quiet_for_genuinely_rare_subject():
    # 약어가 하나뿐이어도 편집거리 1인 이웃이 없으면 손상이 아니다.
    by_code = {c: {} for c in ["9한문01-01", "9수01-01", "9수01-02", "9수01-03"]}
    assert find_abbr_outliers(by_code) == []

def test_every_prefix_has_course_name():
    rows = json.load(open("index/subjects.json", encoding="utf-8"))
    missing = [r["abbr"] for r in rows if not r["course_name"]]
    assert missing == [], f"course_name 미기입: {missing}"

def test_golden_counts():
    idx = json.load(open("data/index.json", encoding="utf-8"))
    by_school = {}
    for f in idx["files"]:
        by_school[f["school"]] = by_school.get(f["school"], 0) + f["count"]
    assert by_school["초"] == 611
    assert by_school["중"] == 704
    assert by_school["고"] == 1979
    assert idx["total"] == 3294

def test_code_shared_by_two_subjects_keeps_both_standards():
    """약어는 교과 안에서만 유일하다. 코드만으로 키를 잡으면 진짜 성취기준이
    조용히 하나씩 사라진다 — 그 회귀를 여기서 막는다."""
    idx = json.load(open("data/index.json", encoding="utf-8"))
    found = {}
    for f in idx["files"]:
        for line in open(f["path"], encoding="utf-8"):
            r = json.loads(line)
            if r["code"] in ("12스문01-01", "12심독01-01"):
                found[(r["subject"], r["code"])] = r["course"]
    assert found == {("체육", "12스문01-01"): "스포츠 문화",
                     ("제2외국어", "12스문01-01"): "스페인어권 문화",
                     ("영어", "12심독01-01"): "심화 영어 독해와 작문",
                     ("제2외국어", "12심독01-01"): "심화 독일어"}
