"""환각 레드팀 — 이 스킬이 막겠다고 한 실패를 기계로 때려 본다.

픽스처는 전부 `data/index.json`에서 런타임에 뽑는다. 코드나 진술문을 적어 넣으면
데이터를 다시 빌드하는 순간 테스트가 깨지고, 깨진 테스트는 지워지고, 그러면 보증도
같이 사라진다. 이건 가정이 아니라 실측이다 — 이 태스크의 브리프가 예시로 적어 둔
가짜 코드 `9수03-12`는 실재하는 코드다. 손으로 적은 픽스처는 이렇게 썩는다.

`xfail`로 표시한 세 건은 이 도구가 지금 못 막는 구멍이다. 통과시키려고 단언을 무르지
않았다. `strict=True`라 구멍이 막히면 XPASS로 터지므로, 고친 사람이 이 파일을 같이
고치게 된다.
"""
import collections
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def run(*args, stdin=None):
    return subprocess.run([sys.executable, *args], capture_output=True, text=True,
                          input=stdin, cwd=ROOT)


# --- 데이터에서 뽑는 픽스처 ------------------------------------------------

def _index():
    return json.loads((ROOT / "data/index.json").read_text(encoding="utf-8"))


def _records():
    for f in _index()["files"]:
        for line in (ROOT / f["path"]).read_text(encoding="utf-8").splitlines():
            if line.strip():
                yield json.loads(line)


RECORDS = list(_records())
CODES = {r["code"] for r in RECORDS}
BY_CODE = collections.defaultdict(list)
for _r in RECORDS:
    BY_CODE[_r["code"]].append(_r)
COLLISIONS = sorted(c for c, v in BY_CODE.items() if len({x["subject"] for x in v}) > 1)

# verify.py 가 인용 여부를 판정하는 정규화·최소 길이와 같은 값. 여기가 어긋나면
# 아래 두 테스트가 재는 대상이 달라지므로 scripts/verify.py 를 고칠 때 같이 본다.
_NORM = re.compile(r"[\s.,·\]\)〕】］|」』》]+")
MIN_QUOTE_LEN = 15


def _norm(s):
    return _NORM.sub("", s or "")


def _one_per_file():
    """파일마다 진술문이 있는 첫 레코드. 무작위가 아니라 데이터 순서로 고정한다."""
    out, seen = [], set()
    for f in _index()["files"]:
        for line in (ROOT / f["path"]).read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r["statement"] and r["code"] not in seen:
                out.append(r)
                seen.add(r["code"])
                break
    return out


SAMPLE = _one_per_file()
# 정규화 15자 미만 진술문은 verify.py 가 아예 인용으로 보지 않는다(→ 아래 전용 테스트).
QUOTABLE = [r for r in SAMPLE if len(_norm(r["statement"])) >= MIN_QUOTE_LEN]


def _shape(code):
    return "".join("D" if c.isdigit() else ("H" if "가" <= c <= "힣" else c) for c in code)


def _fabricate(code):
    """실재 코드의 영역·번호를 99로 갈아 끼운 가짜. 표기법은 그대로 둔다."""
    return re.sub(r"\d{2}([-–—])\d{2}$", r"99\g<1>99", code)


def _one_code_per_notation():
    """데이터에 실재하는 표기법마다 대표 코드 하나. 인식기가 넓어질 때마다 자동으로 는다."""
    shapes = {}
    for r in RECORDS:
        shapes.setdefault(_shape(r["code"]), r["code"])
    return sorted(shapes.values())


NOTATIONS = _one_code_per_notation()
FABRICATED = [_fabricate(c) for c in NOTATIONS]


def _mismatched_codes(stdout):
    return {l.split("[", 1)[1].split("]", 1)[0] for l in stdout.splitlines()
            if l.startswith("MISMATCH")}


# --- 약속 1: 지어낸 코드는 FAKE -------------------------------------------

def test_fabricated_code_in_every_notation_is_fake():
    """인식기는 이 프로젝트에서 두 번 넓어졌고, 넓힐 때마다 구멍이 생길 자리였다.
    실재하는 표기법 전부에 대해 그 표기로 지어낸 코드가 잡히는지 본다."""
    assert not (set(FABRICATED) & CODES), "가짜로 쓴 코드가 실재한다 — 픽스처를 다시 뽑아라"
    assert len(NOTATIONS) >= 8, f"표기법이 {len(NOTATIONS)}종뿐 — 데이터가 줄었는지 확인하라"
    doc = "\n".join(f"성취기준: [{c}] 학습 활동을 수행한다." for c in FABRICATED)
    r = run("scripts/verify.py", "-", stdin=doc)
    assert r.returncode == 1
    missed = [c for c in FABRICATED if f"FAKE  [{c}]" not in r.stdout]
    assert not missed, f"이 표기로 지어낸 코드가 조용히 통과한다: {missed}"


def test_fabricated_code_survives_ocr_mangled_brackets():
    """`(12독문01-05|` 같은 OCR 파손 괄호도 실재 표기라 인식 대상이다. 이 모양으로
    감싸면 가짜가 빠져나가는지 확인한다."""
    doc = "\n".join(f"성취기준: ({c}| 학습 활동을 수행한다." for c in FABRICATED)
    r = run("scripts/verify.py", "-", stdin=doc)
    assert r.returncode == 1
    missed = [c for c in FABRICATED if f"FAKE  [{c}]" not in r.stdout]
    assert not missed, f"OCR 파손 괄호로 감싸면 통과한다: {missed}"


def test_invented_subject_abbreviation_is_fake():
    """실재하지 않는 과목 약어로 지은 코드 — 에이전트가 가장 흔히 만드는 모양이다."""
    invented = ["12코딩01-01", "9정보01-01", "12인공지능01-01", "12미디어01-01"]
    assert not (set(invented) & CODES), "이 약어가 실재하게 되었다 — 픽스처를 바꿔라"
    r = run("scripts/verify.py", "-", stdin="\n".join(f"[{c}] 참고" for c in invented))
    assert r.returncode == 1
    assert all(f"FAKE  [{c}]" in r.stdout for c in invented)


# --- 약속 2: 변형 인용은 MISMATCH, 정확한 인용은 절대 아님 -----------------

def test_exact_quotation_is_never_accused():
    """무고가 오탐보다 나쁘다. 정확히 옮긴 인용을 MISMATCH로 부르면 아무도 안 쓴다."""
    doc = "\n".join(f"- [{r['code']}] {r['statement']}" for r in SAMPLE)
    r = run("scripts/verify.py", "-", stdin=doc)
    assert not _mismatched_codes(r.stdout), f"정확한 인용을 오탐: {_mismatched_codes(r.stdout)}"
    assert "FAKE" not in r.stdout
    assert r.returncode == 0, r.stdout


TAMPER_TAIL = "교사가 안내한 절차에 따라 모둠별로 자료를 정리하여 발표하고 상호 평가한다."


def _tamper(stmt, keep=0.75):
    """뒤 4분의 1을 그럴듯한 다른 문장으로 갈아 끼운다 — 실제 환각 인용의 모양이다.
    길이에 비례해 자르므로 짧은 진술문에서도 변형 비율이 같다."""
    cut = int(len(stmt) * keep)
    return stmt[:cut] + (TAMPER_TAIL * 3)[: max(6, len(stmt) - cut)]


def test_tampered_statement_is_reported_mismatch():
    doc = "\n".join(f"- [{r['code']}] {_tamper(r['statement'])}" for r in QUOTABLE)
    r = run("scripts/verify.py", "-", stdin=doc)
    assert r.returncode == 1
    missed = [x["code"] for x in QUOTABLE if x["code"] not in _mismatched_codes(r.stdout)]
    assert not missed, f"뒷부분을 고쳐 쓴 인용이 통과한다: {missed}"


@pytest.mark.xfail(strict=True, reason="구멍: 유사도 문턱(0.92)이 상대값이라 "
                                       "한 글자·한 낱말 변조는 길이에 묻혀 통과한다")
def test_small_tamper_is_reported_mismatch():
    """조사 하나(를→을)는 정규화 후 한 글자 차이다. 유사도는 (n-1)/n 이고 인용으로
    인정되는 최소 길이가 15자라 이 값은 절대 0.92 아래로 못 내려간다 — 즉 한 글자
    변조는 구조적으로 검출 불가다. 긴 진술문에서는 낱말 하나를 통째로 떨어뜨려도
    마찬가지다(132자 진술문에서 9자 이상 바뀌어야 잡힌다).

    이건 인용자가 저지르는 가장 현실적인 오류이고, 문법이 멀쩡해서 사람이 읽어도
    안 걸린다. 고치려면 문턱을 상대값이 아니라 편집 거리 절대값으로 잡아야 한다.
    """
    particle = next(r for r in RECORDS if r["statement"] and "를 " in r["statement"])
    swapped = particle["statement"].replace("를 ", "을 ", 1)
    r = run("scripts/verify.py", "-", stdin=f"[{particle['code']}] {swapped}")
    assert r.returncode == 1, f"조사 한 글자를 바꿨는데 통과: {r.stdout}"

    longest = max((x for x in RECORDS if x["statement"]), key=lambda x: len(x["statement"]))
    words = longest["statement"].split()
    dropped = " ".join(words[:3] + words[4:])
    r = run("scripts/verify.py", "-", stdin=f"[{longest['code']}] {dropped}")
    assert r.returncode == 1, f"낱말 하나를 떨어뜨렸는데 통과: {r.stdout}"


@pytest.mark.xfail(strict=True, reason="구멍: 유사도 0.55 이하는 '인용이 아니다'로 "
                                       "처리돼, 많이 다른 문장은 검사조차 되지 않는다")
def test_wholly_different_wording_under_a_real_code_is_caught():
    """2015 개정 혼입을 잡는다는 약속이 걸린 자리다. 코드는 실재하고 진술문만 다른
    문서를 MISMATCH가 잡아 준다고 했지만, 두 문장이 55%보다 덜 닮으면 verify.py는
    그걸 인용이 아니라 산문으로 보고 넘긴다. 같은 교과의 이웃 성취기준 문장을
    가져다 붙이면 코퍼스 전체에서 95.5%가 이렇게 통과한다.

    문턱을 낮추는 것으로는 못 고친다 — 코드만 언급한 산문을 MISMATCH로 부르게 되고
    그건 test_exact_quotation_is_never_accused 가 막는 실패다. 인용인지 아닌지를
    유사도가 아니라 인용 부호·줄 구조로 판정해야 닫히는 구멍이다.
    """
    subject_recs = collections.defaultdict(list)
    for x in RECORDS:
        if x["statement"] and len(_norm(x["statement"])) >= MIN_QUOTE_LEN:
            subject_recs[(x["school"], x["subject"], x.get("course"))].append(x)
    pairs = [v for v in subject_recs.values() if len(v) >= 2][0]
    a, b = pairs[0], pairs[1]
    r = run("scripts/verify.py", "-", stdin=f"[{a['code']}] {b['statement']}")
    assert r.returncode == 1, (
        f"[{a['code']}]의 진술문 자리에 [{b['code']}]의 문장을 넣었는데 통과: {r.stdout}")


@pytest.mark.xfail(strict=True, reason="구멍: 정규화 15자 미만 진술문은 인용으로 "
                                       "인정되지 않아 어떤 문장을 붙여도 검사되지 않는다")
def test_short_statements_are_verified_at_all():
    """`_ratio`가 15자 미만 조각을 -1.0으로 되돌려 보내므로, 진술문이 짧은 성취기준은
    인용문을 통째로 지어내도 OK가 나온다. 지금 82건(2.5%)이 이 사각지대에 있고
    수학·과학 계열처럼 문장이 짧은 교과에 몰려 있다."""
    short = [r for r in RECORDS if r["statement"] and len(_norm(r["statement"])) < MIN_QUOTE_LEN]
    assert short, "짧은 진술문이 사라졌다면 이 구멍도 사라진 것 — 테스트를 지워라"
    victim = short[0]
    r = run("scripts/verify.py", "-", stdin=f"[{victim['code']}] 전혀 다른 내용을 지어내어 적은 문장이다.")
    assert r.returncode == 1, (
        f"[{victim['code']}] 진술문 {len(_norm(victim['statement']))}자 — "
        f"아무 문장이나 붙여도 통과한다: {r.stdout}")


# --- 약속 3: 진술문 없는 실재 코드은 NOSTMT, 절대 FAKE 아님 -----------------

def test_null_statement_codes_are_nostmt_never_fake():
    """실재하는 성취기준을 지어냈다고 몰아붙이는 것이 이 도구의 최악의 실패다."""
    nulls = [r for r in RECORDS if r["statement"] is None]
    assert nulls, "진술문 미수록 레코드가 사라졌다 — 데이터 빌드를 확인하라"
    doc = "\n".join(f"성취기준: [{r['code']}] 관련 활동을 수행한다." for r in nulls)
    r = run("scripts/verify.py", "-", stdin=doc)
    assert "FAKE" not in r.stdout, "실재 코드를 FAKE로 판정했다"
    assert r.returncode == 1
    # 같은 코드가 다른 교과에서 진술문을 갖고 있으면 그쪽으로 판정된다(의도된 동작).
    unresolvable = [r_["code"] for r_ in nulls
                    if not any(x["statement"] for x in BY_CODE[r_["code"]])]
    missed = [c for c in unresolvable if f"NOSTMT [{c}]" not in r.stdout]
    assert not missed, f"진술문 미수록인데 NOSTMT가 안 나온 코드: {missed}"


def test_lookup_refuses_to_leave_a_blank_for_a_missing_statement():
    """빈칸을 내보이면 에이전트가 그 칸을 지어 채운다."""
    victim = next(r for r in RECORDS if r["statement"] is None)
    r = run("scripts/lookup.py", "--code", victim["code"], "--format", "md")
    assert r.returncode == 0
    assert "지어내지 말 것" in r.stdout


# --- 약속 4: 같은 코드 다른 교과 --------------------------------------------

def test_collision_code_accepts_either_subject():
    """어느 교과를 인용해도 정본이다. 한쪽만 맞다고 굴면 나머지 교과 교사가 무고당한다."""
    assert len(COLLISIONS) >= 2, f"충돌 코드가 {len(COLLISIONS)}개뿐 — 데이터를 확인하라"
    accused = []
    for code in COLLISIONS:
        for rec in BY_CODE[code]:
            if not rec["statement"]:
                continue
            r = run("scripts/verify.py", "-", stdin=f"[{code}] {rec['statement']}")
            if r.returncode != 0:
                accused.append((code, rec["subject"], r.stdout.strip()))
    assert not accused, f"충돌 코드의 정확한 인용을 오탐: {accused}"


def test_lookup_surfaces_every_subject_of_a_collision_with_a_warning():
    for code in COLLISIONS:
        subjects = {x["subject"] for x in BY_CODE[code]}
        r = run("scripts/lookup.py", "--code", code, "--format", "md")
        assert r.returncode == 0
        assert "주의" in r.stdout, f"[{code}] 충돌 경고 없음"
        missing = [s for s in subjects if s not in r.stdout]
        assert not missing, f"[{code}] 조회 결과에 빠진 교과: {missing}"
        # JSON 출력은 한 줄 한 레코드라 경고가 stdout에 섞이면 파싱이 깨진다.
        j = run("scripts/lookup.py", "--code", code)
        assert "주의" in j.stderr and "주의" not in j.stdout
        assert len(j.stdout.strip().splitlines()) == len(BY_CODE[code])


def test_prefix_neighbour_of_a_collision_is_not_a_collision():
    """접두어가 같다고 전부 충돌하는 것이 아니다(12심독02-03은 영어에만 있다).
    범위로 뭉뚱그려 경고하면 경고가 값을 잃는다."""
    def abbr(c):
        return re.match(r"\d{1,2}[^\d]+", c).group(0)

    prefixes = {abbr(c) for c in COLLISIONS}
    solo = sorted(c for c in CODES if abbr(c) in prefixes and c not in COLLISIONS)
    assert solo, "충돌 접두어에 단독 코드가 없다 — 이 구별을 검사할 대상이 없다"
    for code in solo[:5]:
        r = run("scripts/lookup.py", "--code", code, "--format", "md")
        assert r.returncode == 0
        assert "주의" not in r.stdout, f"[{code}]는 단독 코드인데 충돌 경고가 붙는다"


# --- 약속 5: 종료 코드가 CI 계약 --------------------------------------------

def test_exit_code_contract():
    clean = next(r for r in QUOTABLE if r.get("statement_verified") is True)
    r = run("scripts/verify.py", "-", stdin=f"[{clean['code']}] {clean['statement']}")
    assert r.returncode == 0 and r.stdout.startswith("OK")

    fake = FABRICATED[0]
    r = run("scripts/verify.py", "-", stdin=f"[{fake}] 참고")
    assert r.returncode == 1

    # 성취기준이 하나도 없는 문서는 문제 0건이므로 통과여야 한다(CI가 헛돌지 않게).
    r = run("scripts/verify.py", "-", stdin="성취기준 인용이 없는 평범한 문서다.\n")
    assert r.returncode == 0

    # 조회 실패도 같은 계약을 따른다.
    r = run("scripts/lookup.py", "--code", fake)
    assert r.returncode == 1 and "NOT FOUND" in r.stdout


# --- 약속 6 + 알려진 한계 ----------------------------------------------------

def test_bare_code_passes_but_school_flag_catches_the_level():
    """문장 없이 코드만 적으면 실재 여부만 확인된다 — 주변 산문이 엉뚱한 교과·학교급을
    말해도 OK다. SKILL.md가 이걸 보장 밖이라고 밝히고 있는지까지 함께 고정한다.
    유일한 기계적 방어선은 `--school`이다."""
    rec = next(r for r in RECORDS if r["school"] == "중" and r["statement"])
    other = next(s for s in ["초", "중", "고"] if s != rec["school"])
    doc = f"{other}등학교 **음악** 수업이다. 관련 성취기준은 [{rec['code']}]이다.\n"

    r = run("scripts/verify.py", "-", stdin=doc)
    assert r.returncode == 0, "코드만 적힌 문서는 실재 여부만 본다(설계상 통과)"

    r = run("scripts/verify.py", "-", "--school", other, stdin=doc)
    assert r.returncode == 1 and f"LEVEL [{rec['code']}]" in r.stdout

    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "교과 오인" in skill and "문장 없는 인용" in skill, \
        "verify.py가 못 잡는 것을 SKILL.md가 밝히지 않으면 OK가 거짓 보증이 된다"


@pytest.mark.xfail(strict=True, reason="구멍: 성취수준(A~E) 서술문은 어느 검증 경로도 "
                                       "보지 않는다 — 통째로 지어내도 OK가 나온다")
def test_fabricated_achievement_level_is_detected():
    """`statement_verified`는 진술문만 검증한 값이고 verify.py도 성취수준은 안 본다.
    평가 콘텐츠는 성취수준 서술문을 그대로 옮겨 쓰는 자리라 인용 위험은 진술문과
    같은데, 기계 방어선만 없다. 레코드에 `levels_verified`에 해당하는 필드조차 없다.

    덤: `lookup.py --format md`는 levels를 아예 출력하지 않는다. SKILL.md가 권하는
    출력 형식이 인용하라고 지시한 문장을 보여 주지 않는 셈이라, 조회한 에이전트가
    A~E를 기억으로 채우기 딱 좋다.
    """
    rec = next(r for r in RECORDS if (r.get("levels") or {}).get("A") and r["statement"])
    fabricated = "모든 상황에서 완벽하게 수행하고 다른 학생을 지도할 수 있다."
    assert fabricated not in json.dumps(rec["levels"], ensure_ascii=False)
    doc = f"[{rec['code']}] {rec['statement']}\n  - A수준: {fabricated}\n"
    r = run("scripts/verify.py", "-", stdin=doc)
    assert r.returncode == 1, f"성취수준 서술문을 통째로 지어냈는데 통과: {r.stdout}"


def test_level_blind_spot_is_disclosed_and_enumerated():
    """구멍을 못 막으면 최소한 숨기지는 말아야 한다. 등급 배정이 틀렸을 수 있는
    성취수준 서술문이 코드·등급까지 나열돼, 인용 전에 대조할 수 있는지 본다.

    목록에는 이 데이터셋이 다루지 않는 과목(과학고·보건·예술 계열 등)의 코드도
    섞여 있다 — 성취수준표는 파싱했지만 별책 고시본이 없어 수록하지 않은 과목이다.
    그 코드는 조회할 대상 자체가 없으므로 대조 가능성은 수록된 코드로만 잰다.
    """
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    assert "성취수준은 검사하지 않는다" in skill

    report = (ROOT / "validation-report.md").read_text(encoding="utf-8")
    section = report.split("## 원문 대조 실패 성취수준 서술문", 1)
    assert len(section) == 2, "성취수준 대조 실패 목록이 리포트에서 사라졌다"
    listed = re.findall(r"^- \[([^\]]+)\] ([A-E])등급", section[1], re.M)
    assert listed, "목록이 비었다 — 코드와 등급까지 적혀 있어야 대조가 가능하다"

    in_dataset = [(c, g) for c, g in listed if c in CODES]
    assert in_dataset, "수록된 코드가 하나도 없다 — 목록이 데이터와 끊겼다"
    unreachable = [(c, g) for c, g in in_dataset
                   if not any(g in (x.get("levels") or {}) for x in BY_CODE[c])]
    assert not unreachable, f"목록이 가리키는 등급이 레코드에 없어 대조 불가: {unreachable}"


def test_unverified_statements_are_discoverable_not_silently_trusted():
    """교차검증에 실패한 252건을 아무 표시 없이 내보내면 '검증된 데이터셋'이 거짓말이 된다."""
    disputed = next(r for r in RECORDS
                    if r.get("statement_verified") is False
                    and r["statement"] and len(_norm(r["statement"])) >= MIN_QUOTE_LEN)
    r = run("scripts/verify.py", "-", stdin=f"[{disputed['code']}] {disputed['statement']}")
    assert "WARN" in r.stdout, "두 출처가 어긋난 문장을 그냥 통과시켰다"
    assert r.returncode == 0, "인용자의 잘못이 아니므로 종료 코드는 건드리지 않는다"
    assert "교차검증 불일치" in run("scripts/lookup.py", "--code", disputed["code"],
                                "--format", "md").stdout

    single = next(r for r in RECORDS
                  if r.get("statement_verified") is None
                  and r["statement"] and len(_norm(r["statement"])) >= MIN_QUOTE_LEN)
    r = run("scripts/verify.py", "-", stdin=f"[{single['code']}] {single['statement']}")
    assert "WARN" in r.stdout and "독립 출처가 없어" in r.stdout


# --- 오탐 방지: 한국어 표기가 손상으로 오인되면 안 된다 ---------------------

def test_korean_typography_is_not_treated_as_a_defect():
    """`준언어⋅비언어적`의 가운뎃점, `8⋅15 광복과 6⋅25 전쟁`의 날짜 표기, `고려 사항`
    같은 평범한 산문은 전부 정상 표기다. 이 프로젝트에서 이미 네 번 오탐을 냈다."""
    probes = [r for r in RECORDS if r["statement"] and (
        "⋅" in r["statement"] or "고려 사항" in r["statement"])]
    assert probes, "가운뎃점이 든 진술문이 사라졌다 — 데이터 정제가 지워 버렸는지 확인하라"
    dated = [r for r in probes if re.search(r"\d⋅\d", r["statement"])]
    assert dated, "8⋅15 같은 날짜 표기가 사라졌다 — 가운뎃점을 구분자로 오인해 쪼갰는지 보라"

    doc = "\n".join(f"- [{r['code']}] {r['statement']}" for r in probes)
    r = run("scripts/verify.py", "-", stdin=doc)
    assert not _mismatched_codes(r.stdout), f"정상 표기를 변형 인용으로 오탐: {r.stdout}"
    assert "FAKE" not in r.stdout, "가운뎃점 앞뒤를 코드로 오인했다"


# --- 데이터 자체의 최소 건전성 ----------------------------------------------

def test_records_are_schema_complete():
    """학교급마다 첫 파일 첫 레코드가 스키마를 채우는지 — 빌드가 반쯤 깨진 채로
    배포되면 위 모든 검사가 무의미해진다."""
    idx = _index()
    for school in ["초", "중", "고"]:
        f = next(x for x in idx["files"] if x["school"] == school)
        rec = json.loads((ROOT / f["path"]).read_text(encoding="utf-8").splitlines()[0])
        assert rec["code"] and rec["grade_band"] and rec["source"]
        assert rec["school"] == school and rec["subject"] == f["subject"]
        assert rec["statement"] is None or rec["statement"].endswith("다.")
        assert "statement_verified" in rec and "levels" in rec


def test_index_counts_match_the_files():
    """index.json이 실제 파일과 어긋나면 조회가 조용히 일부를 못 본다."""
    idx = _index()
    for f in idx["files"]:
        n = sum(1 for line in (ROOT / f["path"]).read_text(encoding="utf-8").splitlines()
                if line.strip())
        assert n == f["count"], f"{f['path']}: 실제 {n}건 ≠ index {f['count']}건"
    assert sum(f["count"] for f in idx["files"]) == idx["total"] == len(RECORDS)
