#!/usr/bin/env python3
"""2022 개정 교육과정 성취기준 조회 CLI (stdlib only).

사용례:
  lookup.py --code 9수01-01
  lookup.py --subject 수학 --school 중 --keyword 소인수분해
  lookup.py --course 화법과 언어 --format md
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

NO_STATEMENT = "진술문 미수록 — 원문 고시본 확인 필요 (지어내지 말 것)"
NO_LEVELS = "성취수준 미수록 — 원문 성취수준표 확인 필요 (등급을 지어내지 말 것)"


def load_all(school=None, subject=None):
    idx = json.loads((ROOT / "data/index.json").read_text(encoding="utf-8"))
    for f in idx["files"]:
        if school and f["school"] != school:
            continue
        if subject and subject not in f["subject"]:
            continue
        for line in (ROOT / f["path"]).read_text(encoding="utf-8").splitlines():
            if line.strip():
                yield json.loads(line)


def subjects_of(school=None):
    idx = json.loads((ROOT / "data/index.json").read_text(encoding="utf-8"))
    return sorted({f["subject"] for f in idx["files"] if not school or f["school"] == school})


def trust(r):
    """진술문을 그대로 인용해도 되는지를 한 줄로 알린다. 교차검증은 별책 고시본과
    성취수준표라는 서로 독립된 두 출처가 같은 문장을 담고 있는지를 뜻한다."""
    if r["statement"] is None:
        return "원문 미확보"
    verified = r.get("statement_verified")
    if verified is True:
        note = "교차검증됨"
    elif verified is False:
        note = "교차검증 불일치(인용 전 원문 고시본 확인)"
    else:
        note = "단일 출처(교차검증 불가)"
    if r.get("needs_review"):
        note += "·검토 필요"
    return note + "·" + str(r.get("statement_source") or "출처 미상")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--code")
    ap.add_argument("--school", choices=["초", "중", "고"])
    ap.add_argument("--subject")
    ap.add_argument("--course")
    ap.add_argument("--keyword")
    ap.add_argument("--format", choices=["json", "md"], default="json")
    a = ap.parse_args()

    code = a.code.strip("[]").strip() if a.code else None
    hits = []
    for r in load_all(a.school, a.subject):
        if code and r["code"] != code:
            continue
        if a.course and a.course not in (r.get("course") or ""):
            continue
        if a.keyword:
            haystack = (r["statement"] or "") + (r.get("course") or "") + json.dumps(
                r.get("levels") or {}, ensure_ascii=False)
            if a.keyword not in haystack:
                continue
        hits.append(r)

    if not hits:
        print("NOT FOUND — 해당 조건의 성취기준이 2022 개정 교육과정 데이터에 없습니다. "
              "코드를 만들어내지 말고, --keyword 또는 --subject로 재검색하세요.")
        if a.subject and a.subject not in subjects_of(a.school):
            print("이 데이터셋의 교과명: " + ", ".join(subjects_of(a.school)))
        sys.exit(1)

    if code and len({h["subject"] for h in hits}) > 1:
        # JSON 출력은 한 줄 한 레코드라 경고를 섞으면 파싱이 깨진다 — stderr로 뺀다.
        print(f"# 주의: [{code}]는 교과가 다른 성취기준 {len(hits)}개에 실재한다. "
              f"대상 교과를 확인하고 골라 쓰라.",
              file=sys.stdout if a.format == "md" else sys.stderr)

    if a.format == "md":
        for r in hits:
            where = "·".join(x for x in (r["school"], r["subject"], r.get("course")) if x)
            print(f"- **[{r['code']}]** {r['statement'] or NO_STATEMENT} ({where}) — {trust(r)}")
            # 성취수준도 인용문이다. 조회 결과에 안 보이면 인용하는 쪽이 기억으로 채운다.
            # `A수준: …` 형식은 verify.py 가 그대로 되읽어 검증하는 형식이기도 하다.
            levels = r.get("levels") or {}
            for g in sorted(levels):
                print(f"  - {g}수준: {levels[g]}")
            if not levels:
                print(f"  - {NO_LEVELS}")
    else:
        for r in hits:
            print(json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    main()
