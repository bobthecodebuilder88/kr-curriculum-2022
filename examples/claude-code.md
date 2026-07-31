# Claude Code에서 사용하기

## 설치

```bash
git clone https://github.com/<YOUR_GITHUB_ID>/kr-curriculum-2022 ~/.claude/skills/kr-curriculum-2022
```

이게 전부다. 별도 설정 파일도, 의존성 설치도 없다.

Claude Code는 `SKILL.md`의 `description`을 읽고 성취기준·수업지도안·평가계획 관련
작업에서 스스로 이 스킬을 발동한다. 확실히 하고 싶으면 프롬프트에 직접 적는다.

> kr-curriculum-2022 스킬을 사용해서 …

프로젝트 하나에만 붙이려면 `~/.claude/skills/` 대신 그 프로젝트의 `.claude/skills/`에 clone한다.

## 예시 프롬프트

> 중2 수학 '소인수분해' 단원 수행평가 계획을 만들어줘.
> 성취기준은 kr-curriculum-2022로 조회해서 코드와 진술문을 verbatim으로 달고,
> 성취수준(A~E)도 같이 넣어줘. 다 쓴 뒤에 verify.py로 검증해서 결과를 보여줘.

Claude가 하는 일:

1. `python3 scripts/lookup.py --school 중 --subject 수학 --keyword 소인수분해 --format md`로 조회
2. 조회 결과의 코드·진술문만 그대로 인용 (기억으로 쓰지 않는다)
3. 레코드의 `levels`에서 성취수준을 가져오되 **없는 등급은 만들지 않는다**
4. `python3 scripts/verify.py 수행평가계획.md --school 중`으로 자기 검증

`verify.py`가 exit 1이면 Claude는 문제를 고치고 다시 검증한다.

## 확인해야 할 신호

산출물에 아래가 보이면 스킬이 제대로 돌고 있는 것이다.

- 진술문 뒤에 `— 교차검증됨·별책` 같은 **신뢰 등급**이 언급된다
- 조회되지 않는 성취기준을 요구하면 지어내지 않고 "이 데이터셋에 없다"고 답한다
- 진술문 미수록 39건 중 하나에 걸리면 문장을 만들지 않고 원문 고시본 확인을 안내한다

반대로 **조회 없이 코드가 바로 나오면** 스킬이 발동하지 않은 것이다. 그때는 프롬프트에
스킬 이름을 명시하고 다시 시킨다.
