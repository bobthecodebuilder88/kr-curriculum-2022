#!/usr/bin/env python3
"""CI 스모크 테스트가 쓸 인용 문서를 data/ 에서 만들어 낸다 (stdlib only).

코드와 문장을 워크플로에 적어 두면 데이터를 다시 빌드할 때 그 자리만 낡는다.
문제는 낡는 방향이다 — 사라진 코드는 여전히 FAKE 로 잡히고 옛 진술문은 여전히
MISMATCH 라, 픽스처가 낡아도 게이트는 계속 초록이다. 아무것도 지키지 않게 된
것을 아무도 모르는 채로 통과한다. 그래서 매번 지금의 data/ 에서 새로 뽑는다.

인자로 받은 폴더에 다음을 쓴다.

  code.txt · statement.txt · school.txt · keyword.txt  골라 쓴 실재 성취기준
  fake-code.txt                                        data/ 에 없는 코드
  ok.md         정확한 인용 — verify.py 가 통과(exit 0)해야 한다
  fake.md       없는 코드를 인용 — FAKE
  mismatch.md   진술문을 한 글자 고침 — MISMATCH
  lvldiff.md    성취수준 서술문을 한 글자 고침 — LVLDIFF
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HANGUL_RUN = re.compile(r"[가-힣]{5,}")


def records():
    idx = json.loads((ROOT / "data/index.json").read_text(encoding="utf-8"))
    for f in idx["files"]:
        for line in (ROOT / f["path"]).read_text(encoding="utf-8").splitlines():
            if line.strip():
                yield json.loads(line)


def tamper(s):
    """한가운데 한 글자를 바꾼다.

    원문과 닮은 채로 다른 문장이라야 픽스처 구실을 한다. 통째로 다른 문장은
    '지어낸 문장' 규칙에 걸려서, 정작 검사하려던 '인용을 고쳐 썼다' 경로를
    지나쳐 버린다.
    """
    i = len(s) // 2
    return s[:i] + ("판" if s[i] != "판" else "톱") + s[i + 1:]


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    recs = list(records())
    codes = {r["code"] for r in recs}
    # 코드가 두 교과에 실재하면 lookup 이 경고 줄을 덧붙이고 verify 는 교과를
    # 골라야 한다. 스모크가 재려는 것은 그 분기가 아니라 인용 검증이라 피한다.
    dupes = {c for c, n in Counter(r["code"] for r in recs).items() if n > 1}
    pick = min(
        (r for r in recs
         if r["statement_verified"] is True          # 정확한 인용이 WARN 없이 통과해야 한다
         and r["code"] not in dupes
         and len(r["statement"] or "") >= 30
         and HANGUL_RUN.search(r["statement"] or "")  # 키워드 조회에 쓸 토막
         and max((len(t) for t in (r.get("levels") or {}).values()), default=0) >= 20),
        key=lambda r: r["code"])

    code, stmt = pick["code"], pick["statement"]
    grade = sorted(g for g, t in pick["levels"].items() if len(t) >= 20)[0]
    desc = pick["levels"][grade]
    # 실재하지 않는 코드: 같은 계열의 뒷번호부터 훑어 data/ 에 없는 첫 번호를 쓴다.
    fake = next(c for c in (re.sub(r"\d{2}$", f"{n:02d}", code) for n in range(99, 0, -1))
                if c not in codes)

    for name, text in [
        ("code.txt", code),
        ("statement.txt", stmt),
        ("school.txt", pick["school"]),
        ("keyword.txt", HANGUL_RUN.search(stmt).group()),
        ("fake-code.txt", fake),
        ("ok.md", f"- [{code}] {stmt}\n  - {grade}수준: {desc}\n"),
        ("fake.md", f"- [{fake}] {stmt}\n"),
        ("mismatch.md", f"- [{code}] {tamper(stmt)}\n"),
        ("lvldiff.md", f"- [{code}] {stmt}\n  - {grade}수준: {tamper(desc)}\n"),
    ]:
        (out / name).write_text(text, encoding="utf-8")
    print(f"fixtures from [{code}] ({pick['school']}·{pick['subject']}), "
          f"{grade}수준, 없는 코드 [{fake}] → {out}")


if __name__ == "__main__":
    main()
