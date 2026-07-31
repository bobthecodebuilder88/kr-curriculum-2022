import json
import subprocess
import sys

def run(*args, stdin=None):
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, input=stdin)

def _all_records():
    idx = json.load(open("data/index.json", encoding="utf-8"))
    for f in idx["files"]:
        for line in open(f["path"], encoding="utf-8"):
            if line.strip():
                yield json.loads(line)

def _any_real():
    idx = json.load(open("data/index.json", encoding="utf-8"))
    path = idx["files"][0]["path"]
    return json.loads(open(path, encoding="utf-8").readline())

def test_lookup_by_code_exact():
    rec = _any_real()
    r = run("scripts/lookup.py", "--code", rec["code"])
    assert r.returncode == 0
    assert rec["statement"] in r.stdout

def test_lookup_missing_code_is_honest():
    r = run("scripts/lookup.py", "--code", "9수99-99")
    assert r.returncode == 1
    assert "NOT FOUND" in r.stdout

def _tampered(stmt):
    """앞부분은 원문 그대로 두고 뒤를 그럴듯하게 바꾼다 — 실제 환각 인용의 모양이다.
    무관한 산문을 붙이는 것은 '변형 인용'이 아니라 그냥 문장이라 검출 대상이 아니다."""
    return stmt[: int(len(stmt) * 0.7)] + "교사가 제시한 기준에 따라 스스로 평가하도록 한다."

def test_verify_flags_fake_code_and_tampered_statement():
    rec = _any_real()
    doc = (f"이 수업은 [{rec['code']}] {rec['statement']} 에 근거한다.\n"
           f"또한 [9수99-99] 존재하지 않는 성취기준과\n"
           f"[{rec['code']}] {_tampered(rec['statement'])}\n")
    r = run("scripts/verify.py", "-", stdin=doc)
    assert r.returncode == 1
    assert "9수99-99" in r.stdout          # 미존재 코드 검출
    assert "MISMATCH" in r.stdout           # 변형 인용 검출

def test_verify_does_not_flag_ordinary_prose_after_a_code():
    """코드를 언급만 하고 인용하지 않은 문장까지 MISMATCH를 내면 아무도 안 쓴다."""
    rec = _any_real()
    doc = f"[{rec['code']}]을 중심으로 차시를 구성하고 모둠 활동과 형성평가를 배치하였다.\n"
    r = run("scripts/verify.py", "-", stdin=doc)
    assert "MISMATCH" not in r.stdout
    assert r.returncode == 0

def test_verify_clean_doc_passes():
    rec = _any_real()
    r = run("scripts/verify.py", "-", stdin=f"[{rec['code']}] {rec['statement']}")
    assert r.returncode == 0
    assert "OK" in r.stdout

def _colliding_code():
    """교과가 다른데 코드가 같은 실제 사례를 데이터에서 찾는다."""
    idx = json.load(open("data/index.json", encoding="utf-8"))
    seen = {}
    for f in idx["files"]:
        for line in open(f["path"], encoding="utf-8"):
            r = json.loads(line)
            if r["code"] in seen and seen[r["code"]]["subject"] != r["subject"]:
                return seen[r["code"]], r
            seen[r["code"]] = r
    return None, None

def test_lookup_returns_all_subjects_for_colliding_code():
    a, b = _colliding_code()
    assert a is not None, "충돌 코드가 데이터에 없다 — 12스문/12심독 9건이 사라졌는지 확인하라"
    r = run("scripts/lookup.py", "--code", a["code"], "--format", "md")
    assert r.returncode == 0
    assert a["subject"] in r.stdout and b["subject"] in r.stdout
    assert "주의" in r.stdout

def test_verify_matches_the_right_subject_for_colliding_code():
    a, b = _colliding_code()
    if not (a and a["statement"] and b["statement"]):
        return
    # b 교과의 진술문을 정확히 인용했다면 a 쪽과 다르다고 MISMATCH를 내면 안 된다.
    r = run("scripts/verify.py", "-", stdin=f"[{b['code']}] {b['statement']}")
    assert r.returncode == 0, f"충돌 코드에서 정확한 인용을 오탐: {r.stdout}"
    # 반대 방향도 같아야 한다 — 어느 쪽 교과를 인용해도 정본이다.
    r = run("scripts/verify.py", "-", stdin=f"[{a['code']}] {a['statement']}")
    assert r.returncode == 0, f"충돌 코드에서 정확한 인용을 오탐: {r.stdout}"

def test_verify_reports_missing_statement_without_calling_it_fake():
    idx = json.load(open("data/index.json", encoding="utf-8"))
    null_rec = None
    for f in idx["files"]:
        for line in open(f["path"], encoding="utf-8"):
            r = json.loads(line)
            if r["statement"] is None:
                null_rec = r
                break
        if null_rec:
            break
    if null_rec is None:
        return  # 진술문 미수록 레코드가 없으면 검사할 것도 없다
    r = run("scripts/verify.py", "-", stdin=f"[{null_rec['code']}] 아무 문장")
    assert "FAKE" not in r.stdout, "실재하는 코드를 FAKE로 판정하면 안 된다"
    assert "NOSTMT" in r.stdout

def test_lookup_prints_explicit_notice_for_missing_statement():
    """진술문이 없을 때 빈칸을 내보이면 에이전트가 그 칸을 지어 채운다."""
    null_rec = next((r for r in _all_records() if r["statement"] is None), None)
    if null_rec is None:
        return
    r = run("scripts/lookup.py", "--code", null_rec["code"], "--format", "md")
    assert r.returncode == 0
    assert "진술문 미수록 — 원문 고시본 확인 필요" in r.stdout

def test_verify_detects_every_code_shape_in_the_dataset():
    """로마숫자 꼬리(12영Ⅰ-01-01)와 괄호 약어(9사(일사)01-01)까지 인식해야 한다 —
    못 읽는 표기가 있으면 그 표기로 지어낸 코드는 조용히 통과한다."""
    shapes = {}
    for r in _all_records():
        key = "".join("D" if c.isdigit() else ("H" if "가" <= c <= "힣" else c) for c in r["code"])
        shapes.setdefault(key, r["code"])
    missed = []
    for code in shapes.values():
        # 실재 코드는 FAKE로 보고되면 안 되고, 아예 인식 못 해도 안 된다.
        # 두 요약문("검사한 코드 N개" / "검사 코드 N개") 모두 "코드 1개"를 담는다.
        out = run("scripts/verify.py", "-", stdin=f"[{code}] 참고").stdout
        if "FAKE" in out or "코드 1개" not in out:
            missed.append(code)
    assert not missed, f"인식하지 못한 코드 표기: {missed}"
