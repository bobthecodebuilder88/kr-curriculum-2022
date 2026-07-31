#!/usr/bin/env python3
"""사람용 브라우징 테이블 생성: browse/<학교급>/<교과>.md + browse/README.md.

터미널이 없는 사람이 이 저장소를 쓰는 유일한 경로다. 그래서 진술문만 싣지 않고
신뢰 등급을 같은 줄에 함께 싣는다 — JSON을 열지 않고도 이 문장을 그대로 인용해도
되는지 알 수 있어야 한다.
"""
import json
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
SCHOOLS = {"초": "초등학교", "중": "중학교", "고": "고등학교"}

NO_STATEMENT = "*(진술문 미수록 — 원문 고시본 확인 필요. 지어내지 말 것)*"

LEGEND = (
    "| 신뢰 | 뜻 |\n"
    "|---|---|\n"
    "| 교차검증 | 별책 고시본과 성취수준 문서가 글자까지 같은 문장을 싣는다 |\n"
    "| 불일치 | 두 문서가 다른 문장을 싣는다 — 인용 전 원문 고시본 확인 |\n"
    "| 단일 출처 | 대조할 독립 출처가 없다(틀렸다는 뜻은 아니다) |\n"
    "| 원문 미확보 | 코드는 실재하나 원문 손상으로 진술문을 싣지 못했다 |\n"
    "\n`·검토 필요`가 붙은 줄은 사람이 원문과 대조해야 하는 레코드다.\n"
)


def grade(r):
    """진술문을 그대로 인용해도 되는지를 한 칸에 담는다. 낱말은 scripts/lookup.py 의
    `trust()` 와 맞춰 둔다 — CLI 를 본 사람이 같은 말을 여기서도 읽어야 한다."""
    if r["statement"] is None:
        return "원문 미확보"
    verified = r.get("statement_verified")
    base = "교차검증" if verified is True else "불일치" if verified is False else "단일 출처"
    return base + ("·검토 필요" if r.get("needs_review") else "")


def cell(s):
    """표 칸 하나. 현재 데이터에 `|` 도 줄바꿈도 없지만, 하나라도 새로 들어오면
    표 전체가 깨져 조용히 잘못 렌더된다 — 깨지느니 이스케이프한다."""
    return str(s or "").replace("|", "\\|").replace("\n", " ")


def render(f, rows):
    counts = {}
    for r in rows:
        counts[grade(r).split("·")[0]] = counts.get(grade(r).split("·")[0], 0) + 1
    caveat = ", ".join(f"{k} {v}건" for k, v in counts.items())
    lines = [
        f"# {f['school']} · {f['subject']} — 성취기준 {f['count']}개",
        "",
        f"출처: 교육부 고시 제2022-33호 별책. 신뢰 등급 내역 — {caveat}.",
        "전수 검증 결과는 [validation-report.md](../../validation-report.md),",
        "인용 검증은 `python3 scripts/verify.py <문서> --school " + f["school"] + "`.",
        "",
        "| 코드 | 성취기준 | 과목 | 신뢰 |",
        "|---|---|---|---|",
    ]
    # 진술문은 반드시 코드 바로 다음 칸이다. verify.py 는 코드 뒤에 이어지는 텍스트를
    # 인용문으로 읽으므로, 사이에 과목명이 끼면 표 전체가 MISMATCH 로 잡힌다.
    # 이 순서 덕분에 생성된 표 자체를 verify.py 로 검사할 수 있다.
    for r in rows:
        stmt = cell(r["statement"]) if r["statement"] else NO_STATEMENT
        lines.append(f"| `[{r['code']}]` | {stmt} | {cell(r.get('course'))} | {grade(r)} |")
    lines += ["", "## 신뢰 등급 읽는 법", "", LEGEND]
    return "\n".join(lines) + "\n"


def main():
    idx = json.loads((ROOT / "data/index.json").read_text(encoding="utf-8"))
    written = []
    for f in idx["files"]:
        rows = [
            json.loads(line)
            for line in (ROOT / f["path"]).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        out = ROOT / "browse" / f["school"] / (Path(f["path"]).stem + ".md")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render(f, rows), encoding="utf-8")
        written.append((f, out))

    toc = [
        f"# 성취기준 브라우징 — 총 {idx['total']}개",
        "",
        "터미널 없이 성취기준을 찾아보는 표다. 교과 파일을 열고 브라우저 검색(Ctrl+F)으로 찾으면 된다.",
        "각 줄의 **신뢰** 칸을 반드시 함께 읽어라 — 이 저장소가 스스로 검증하지 못한 문장을 표시한 칸이다.",
        "",
    ]
    for school, label in SCHOOLS.items():
        files = [(f, o) for f, o in written if f["school"] == school]
        toc += [f"## {label}", ""]
        for f, o in sorted(files, key=lambda x: x[0]["subject"]):
            # 「중학교 선택.md」처럼 공백이 든 이름이 있어 URL 은 반드시 인코딩한다 —
            # 인코딩하지 않으면 공백 뒤가 링크 제목으로 잘려 링크가 죽는다.
            toc.append(f"- [{f['subject']}]({school}/{quote(o.name)}) — {f['count']}개")
        toc.append("")
    (ROOT / "browse/README.md").write_text("\n".join(toc) + "\n", encoding="utf-8")

    print(f"browse/ generated: {len(written)} subject tables + README.md")


if __name__ == "__main__":
    main()
