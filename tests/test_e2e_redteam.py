"""환각 레드팀 — 이 스킬이 막겠다고 한 실패를 기계로 때려 본다.

픽스처는 전부 `data/index.json`에서 런타임에 뽑는다. 코드나 진술문을 적어 넣으면
데이터를 다시 빌드하는 순간 테스트가 깨지고, 깨진 테스트는 지워지고, 그러면 보증도
같이 사라진다. 이건 가정이 아니라 실측이다 — 이 태스크의 브리프가 예시로 적어 둔
가짜 코드 `9수03-12`는 실재하는 코드다. 손으로 적은 픽스처는 이렇게 썩는다.

이 파일은 처음에 네 건을 `xfail(strict=True)`로 남겼다 — 그때 이 도구가 못 막던 구멍이다.
넷 다 `scripts/verify.py`에서 막혔고(판정을 상대 유사도에서 verbatim 일치로 뒤집었다),
단언은 한 글자도 무르지 않은 채 마커만 걷어 냈다. 되돌아가면 여기서 터진다.
"""
import collections
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

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

# 옛 verify.py 가 "인용으로 볼 만한 길이"로 삼던 값. 지금은 verify.py 에 이 하한이
# 없다(길이와 무관하게 verbatim 으로 판정한다). 여기서는 옛 사각지대였던 짧은
# 진술문을 골라내는 기준으로만 남는다 — 그 82건이 이제 검사되는지를 재기 위해서다.
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
# 짧은 진술문은 변조해도 남는 글자가 적어 검출 여부가 데이터에 따라 갈린다. 여기서는
# 빼고 전용 테스트(test_short_statements_are_verified_at_all)로 따로 잰다.
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


def _verify_module():
    """태그 목록의 정본은 문서가 아니라 도구다 — 그래서 소스에서 직접 읽는다."""
    spec = importlib.util.spec_from_file_location("verify_under_test", ROOT / "scripts/verify.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _solo(pred):
    """조건에 맞으면서 코드가 한 교과에만 있는 레코드. 충돌 코드는 어느 레코드로
    판정될지가 인용문에 달려 있어, 태그를 하나로 고정하는 픽스처로 쓸 수 없다."""
    return next(r for r in RECORDS if len(BY_CODE[r["code"]]) == 1 and pred(r))


INVENTED_LEVEL = "모든 상황에서 완벽하게 수행하고 다른 학생을 지도할 수 있다."


def _tag_table(doc):
    """`| 표시 |`로 시작하는 표의 첫 열 집합. 본문 어딘가에서 태그를 한 번 언급한 것과
    표에 행으로 실린 것은 다르다 — 표를 찾아 읽지 않으면 행이 지워져도 검사가 통과한다."""
    lines = doc.splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("| 표시 "))
    out = set()
    for line in lines[start + 2:]:          # 헤더와 구분선을 건너뛴다
        if not line.startswith("|"):
            break
        out.add(line.split("`")[1])
    return out


def _tag_probes():
    """(태그, 검사받을 문서, `--school` 값) — 태그마다 그 태그가 나와야 하는 최소 문서."""
    def quotable(r):
        return r["statement"] and len(_norm(r["statement"])) >= MIN_QUOTE_LEN

    mism = _solo(quotable)
    nost = next(r for r in RECORDS if r["statement"] is None
                and not any(x["statement"] for x in BY_CODE[r["code"]]))
    lvl = _solo(lambda r: r["statement"] and r["school"] == "중")
    warn = _solo(lambda r: r.get("statement_verified") is False and quotable(r))
    diff = _solo(lambda r: (r.get("levels") or {}).get("A") and r["statement"])
    miss = _solo(lambda r: r.get("levels") and set("ABCDE") - set(r["levels"]) and r["statement"])
    nolv = _solo(lambda r: not r.get("levels") and r["statement"])
    absent = sorted(set("ABCDE") - set(miss["levels"]))[0]
    for r in (diff, miss):
        assert INVENTED_LEVEL not in json.dumps(r["levels"], ensure_ascii=False), \
            "지어낸 성취수준이 실제 데이터에 생겼다 — 픽스처를 바꿔라"
    return [
        ("FAKE", f"[{FABRICATED[0]}] 참고", None),
        ("MISMATCH", f"[{mism['code']}] {_tamper(mism['statement'])}", None),
        ("NOSTMT", f"성취기준: [{nost['code']}] 관련 활동을 수행한다.", None),
        ("LEVEL", f"[{lvl['code']}] {lvl['statement']}", "초"),
        ("WARN", f"[{warn['code']}] {warn['statement']}", None),
        ("LVLDIFF", f"[{diff['code']}] {diff['statement']}\n  - A수준: {INVENTED_LEVEL}", None),
        ("LVLMISS",
         f"[{miss['code']}] {miss['statement']}\n  - {absent}수준: {INVENTED_LEVEL}", None),
        ("LVLNONE", f"[{nolv['code']}] {nolv['statement']}\n  - A수준: {INVENTED_LEVEL}", None),
    ]


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


def test_small_tamper_is_reported_mismatch():
    """조사 하나(를→을)는 정규화 후 한 글자 차이다. 옛 판정은 유사도 0.92 미만만
    지적했는데 한 글자 치환의 유사도는 (n-1)/n 이라 길이와 무관하게 그 위였다 —
    구조적으로 검출 불가였다(코퍼스 전수: 조사 변조 3185건 중 검출 0건).

    지금은 유사도가 아니라 verbatim 일치로 판정하므로 길이에 묻히지 않는다.
    이건 인용자가 저지르는 가장 현실적인 오류이고, 문법이 멀쩡해서 사람이 읽어도
    안 걸리는 종류다.
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


def test_wholly_different_wording_under_a_real_code_is_caught():
    """2015 개정 혼입을 잡는다는 약속이 걸린 자리다. 옛 판정은 두 문장이 55%보다 덜
    닮으면 인용이 아니라 산문으로 보고 넘겼고, 같은 교과의 이웃 성취기준 문장을
    가져다 붙인 2991쌍 중 95.4%가 그렇게 통과했다.

    문턱을 낮추는 것으로는 못 고친다 — 코드만 언급한 산문을 MISMATCH로 부르게 되고
    그건 test_exact_quotation_is_never_accused 가 막는 실패다. 지금은 유사도가
    아니라 두 가지 증거로 판정한다: 그 자리에 다른 성취기준의 진술문이 통째로
    들어앉았거나(결정적), 코드에서 떨어진 자리에 완결된 서술문이 왔거나(인용 형식).
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


def test_short_statements_are_verified_at_all():
    """옛 `_ratio`는 15자 미만 조각을 -1.0으로 되돌려 보냈고, 그래서 진술문이 짧은
    성취기준 82건(2.5%)은 인용문을 통째로 지어내도 OK가 나왔다. 수학·과학 계열처럼
    문장이 짧은 교과에 몰려 있다. verbatim 판정에는 최소 길이가 없어 사각지대가
    사라졌다 — 82건 중 81건이 검출된다(남은 1건은 진술문이 `다` 한 글자로 손상된
    12중어04-03로, 데이터 쪽 결함이다)."""
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


def test_fabricated_achievement_level_is_detected():
    """평가 콘텐츠는 성취수준 서술문을 그대로 옮겨 쓰는 자리라 인용 위험은 진술문과
    같은데, 예전에는 기계 방어선이 하나도 없었다. 지금은 `A수준: …`처럼 등급을
    명시한 자리를 진술문과 같은 방식으로 검증한다.

    `lookup.py --format md`가 levels를 출력하지 않던 짝 문제도 같이 닫혔다 —
    이제 같은 `A수준: …` 형식으로 내보내므로 조회 결과를 그대로 인용하면 통과한다.
    """
    rec = next(r for r in RECORDS if (r.get("levels") or {}).get("A") and r["statement"])
    fabricated = "모든 상황에서 완벽하게 수행하고 다른 학생을 지도할 수 있다."
    assert fabricated not in json.dumps(rec["levels"], ensure_ascii=False)
    doc = f"[{rec['code']}] {rec['statement']}\n  - A수준: {fabricated}\n"
    r = run("scripts/verify.py", "-", stdin=doc)
    assert r.returncode == 1, f"성취수준 서술문을 통째로 지어냈는데 통과: {r.stdout}"


def test_level_checking_is_disclosed_and_enumerated():
    """이 자리는 원래 `성취수준은 검사하지 않는다`가 SKILL.md에 있는지 보는 고백이었다.
    이제 검사하므로 단언을 지우지 않고 반대로 뒤집는다 — 없는 보증을 있다고 말하는 것과
    있는 보증을 없다고 말하는 것은 똑같이 문서가 거짓말을 하는 것이고, 후자는 사용자가
    기계 검증을 놔두고 손으로 대조하게 만든다.

    세 가지를 함께 고정한다. ①옛 거짓 문장이 어떤 문서에도 없다 ②`verify.py`가 낼 수
    있는 태그 전부가 두 문서의 표에 있고, 표에만 있고 못 내는 태그는 없다 ③등급 배정이
    틀렸을 수 있는 성취수준이 코드·등급까지 나열돼 인용 전에 대조할 수 있다.

    태그 목록은 `scripts/verify.py`에서 뽑는다. 손으로 적으면 태그가 늘 때 같이 늙는다.
    ②의 '못 내는 태그는 없다' 쪽은 문서를 읽어서는 알 수 없어, 태그마다 실제로 그
    태그가 나오는 문서를 만들어 돌려 본다.

    목록에는 이 데이터셋이 다루지 않는 과목(과학고·보건·예술 계열 등)의 코드도
    섞여 있다 — 성취수준표는 파싱했지만 별책 고시본이 없어 수록하지 않은 과목이다.
    그 코드는 조회할 대상 자체가 없으므로 대조 가능성은 수록된 코드로만 잰다.
    """
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    docs = [("SKILL.md", skill), ("README.md", readme)]

    # ① 사실이 아니게 된 옛 문장이 어떤 형태로도 남아 있으면 안 된다.
    for name, doc in docs:
        assert "성취수준은 검사하지 않는다" not in doc, \
            f"{name}: verify.py가 성취수준을 검사하는데 안 한다고 적혀 있다"

    # ② 태그 표가 도구와 일치하는가.
    tags = set(_verify_module()._LABEL)
    assert {"LVLDIFF", "LVLMISS", "LVLNONE"} <= tags, \
        f"성취수준 태그가 사라졌다 — verify.py를 확인하라: {sorted(tags)}"
    for name, doc in docs:
        table = _tag_table(doc)
        assert table == tags, (f"{name}의 태그 표가 도구와 어긋난다 — "
                               f"표에 빠진 태그 {sorted(tags - table)}, "
                               f"도구가 못 내는데 실린 태그 {sorted(table - tags)}")
    emitted = set()
    for tag, doc, school in _tag_probes():
        r = run("scripts/verify.py", "-", *(("--school", school) if school else ()), stdin=doc)
        seen = {l.split("[", 1)[0].strip() for l in r.stdout.splitlines() if "[" in l} & tags
        assert tag in seen, f"{tag}가 나와야 할 문서에서 안 나온다: {r.stdout}"
        emitted |= seen
    assert emitted == tags, f"문서에 적혀 있으나 도구가 내지 못하는 태그: {sorted(tags - emitted)}"

    # ②' 예약 슬롯 규칙은 사용자의 정상 문서를 지적할 수 있어, 무엇이 걸리고 무엇을 대신
    # 써야 하는지까지 SKILL.md의 제 절에 있어야 한다. 없으면 이 규칙은 함정이 된다.
    # (본문에 낱말이 스쳐 나오는 것으로는 부족해 절을 통째로 떼어 내 검사한다.)
    heading = "### 코드 바로 뒤 한 칸은 원문 자리다"
    assert heading in skill.splitlines(), "예약 슬롯 규칙 절이 SKILL.md에서 사라졌다"
    slot = skill.split(heading, 1)[1].split("\n## ", 1)[0]
    assert "MISMATCH" in slot and "verify.py" in slot, "규칙을 어겼을 때의 실제 출력 예시가 없다"
    assert "줄을 나눈다" in slot, "MISMATCH를 피하는 방법이 그 절에 적혀 있지 않다"

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
