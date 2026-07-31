# Codex CLI에서 사용하기

## 설치

```bash
git clone https://github.com/<YOUR_GITHUB_ID>/kr-curriculum-2022 ~/kr-curriculum-2022
```

Codex는 Claude Code처럼 스킬을 자동 발동하지 않는다. 규칙을 `AGENTS.md`에 직접 적어야 한다.
작업 중인 프로젝트의 `AGENTS.md`(없으면 새로 만든다)에 아래를 추가한다.

```markdown
## 교육과정 성취기준 규칙

한국 초·중·고 성취기준(`[9수01-01]` 같은 코드)을 다루는 모든 작업에서:

1. `~/kr-curriculum-2022/SKILL.md`를 먼저 읽고 그 규칙을 따른다.
2. 성취기준 코드와 진술문은 `scripts/lookup.py` 조회 결과만 verbatim 인용한다.
   기억으로 쓰지 않는다 — 지어낸 코드가 이 규칙이 막으려는 사고다.
3. 조회 결과가 없으면 없다고 답한다. 비슷한 문장을 만들어 채우지 않는다.
4. 산출물을 내기 전에 `scripts/verify.py`로 검증하고 exit 0을 확인한다.
```

`~` 경로를 그대로 두면 Codex가 홈 디렉터리 밖을 못 읽는 설정에서 막힌다.
그럴 땐 프로젝트 안에 clone하고 경로를 상대경로로 바꾼다.

## 예시 프롬프트

> 중2 수학 '소인수분해' 단원 수행평가 계획을 `수행평가계획.md`로 만들어줘.
> AGENTS.md의 교육과정 성취기준 규칙을 따르고, 마지막에 verify.py 결과를 붙여줘.

Codex가 실행할 명령:

```bash
python3 ~/kr-curriculum-2022/scripts/lookup.py \
  --school 중 --subject 수학 --keyword 소인수분해 --format md

python3 ~/kr-curriculum-2022/scripts/verify.py 수행평가계획.md --school 중
```

## CI 게이트로 쓰기

`verify.py`는 문제가 없으면 exit 0, 하나라도 있으면 exit 1이다. 사람이 쓴 문서든
에이전트가 쓴 문서든 똑같이 검사할 수 있어서, 교육 콘텐츠 리포의 CI에 그대로 걸린다.

```bash
for f in 지도안/*.md; do
  python3 ~/kr-curriculum-2022/scripts/verify.py "$f" || exit 1
done
```
