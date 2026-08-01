# Cursor에서 사용하기

## 설치

```bash
git clone https://github.com/bobthecodebuilder88/kr-curriculum-2022 ~/kr-curriculum-2022
```

프로젝트에 `.cursor/rules/kr-curriculum.mdc` 파일을 만든다.

```markdown
---
description: 한국 초·중·고 성취기준을 인용할 때의 규칙
globs: ["**/*.md"]
alwaysApply: false
---

# 교육과정 성취기준 규칙

`[9수01-01]` 같은 성취기준 코드를 다루는 모든 작업에서:

1. `~/kr-curriculum-2022/SKILL.md`를 먼저 읽고 그 규칙을 따른다.
2. 코드와 진술문은 `scripts/lookup.py` 조회 결과만 verbatim 인용한다.
   조사·어미·띄어쓰기까지 한 글자도 바꾸지 않는다.
3. 조회되지 않으면 없다고 답한다. 비슷한 문장을 지어내지 않는다.
4. 산출물은 `scripts/verify.py`로 검증하고 exit 0을 확인한다.
```

`globs`를 좁히면(예: `["지도안/**/*.md"]`) 그 폴더에서만 규칙이 붙는다.
구버전 Cursor라면 프로젝트 루트의 `.cursorrules`에 같은 내용을 넣어도 된다.

리포를 프로젝트 안에 두면 Cursor가 `data/`까지 인덱싱해 검색이 느려질 수 있다.
홈 디렉터리에 두고 경로로 참조하거나, `.cursorignore`에 `kr-curriculum-2022/data/`를 넣는다.

## 예시 프롬프트

> 중2 수학 '소인수분해' 단원 수행평가 계획을 만들어줘.
> 성취기준은 kr-curriculum-2022에서 조회해서 verbatim으로 달고,
> 터미널에서 verify.py까지 돌려서 결과를 보여줘.

Cursor의 에이전트 모드(터미널 실행 권한)에서 써야 조회·검증이 실제로 돌아간다.
채팅 전용 모드라면 조회 결과를 사람이 붙여 넣어야 하고, 그때는 아래처럼 직접 실행한다.

```bash
python3 ~/kr-curriculum-2022/scripts/lookup.py \
  --school 중 --subject 수학 --keyword 소인수분해 --format md
```

## 조회 없이 코드가 나오면

그건 규칙이 안 붙은 것이다. `.mdc`의 `globs`가 지금 편집 중인 파일과 맞는지 확인하거나,
`alwaysApply: true`로 바꾼다. 확인용으로 이렇게 물어보면 된다 — 조회하지 않고 답하면
규칙이 로드되지 않은 것이다.

> 지금 kr-curriculum-2022 규칙이 적용돼 있어? lookup.py로 9수01-01을 조회해서 보여줘.
