# kr-curriculum-2022

**2022 개정 교육과정 성취기준 3294건 — 조회 데이터베이스 · 인용 검증 CLI · AI 에이전트 스킬**

> Korean 2022 Revised National Curriculum achievement standards (grades 1–12) as a
> queryable dataset, a citation verifier, and an agent skill — so an LLM looks a
> curriculum code up instead of inventing one.

[![CI](https://github.com/<YOUR_GITHUB_ID>/kr-curriculum-2022/actions/workflows/ci.yml/badge.svg)](https://github.com/<YOUR_GITHUB_ID>/kr-curriculum-2022/actions/workflows/ci.yml)
![standards](https://img.shields.io/badge/standards-3294-blue)
![license](https://img.shields.io/badge/code-MIT-informational)

---

## LLM은 성취기준을 지어낸다

"중2 수학 소인수분해 수업에 성취기준을 달아줘"라고 시키면 모델은 대체로 둘 중 하나를 한다.
**형식만 그럴듯한 없는 코드를 만들어 붙이거나, 실재하는 코드에 원문과 미묘하게 다른 문장을 붙인다.**
아래는 그 두 가지를 한 줄씩 넣은 문서를 이 저장소의 `verify.py`로 검사한 실제 출력이다.

```
$ python3 scripts/verify.py 수업지도안.md --school 중
MISMATCH [9수01-01] — 진술문이 원문과 다름
  원문: 소인수분해의 뜻을 알고, 자연수를 소인수분해 할 수 있다.
FAKE  [9수05-08] — 이 데이터셋에 없는 코드. 지어낸 코드이거나, 이 데이터셋이 다루지 않는 과목(전문 교과·교양 등)이다. 원문 고시본으로 확인하기 전에는 인용하지 마라

문제 2건 발견 (검사 코드 2개)
$ echo $?
1
```

`알고`가 `이해하고`로 바뀐 첫 줄은 소리 내어 읽어도 걸리지 않는다. 둘째 줄의 `9수05-08`은
중학교 수학에 05 영역 자체가 없으니(01~04뿐) 존재할 수 없는 코드인데, 자릿수와 모양이
멀쩡해서 그대로 결재까지 올라간다. 수업지도안·평가계획·생기부 문구에서 이건 치명적이다.

이 저장소가 하는 일은 세 가지다.

1. **조회** — 성취기준 3294건(초 611 · 중 704 · 고 1979)을 코드·진술문·성취수준(A~E)까지 담은 데이터셋
2. **인용** — 에이전트가 기억이 아니라 조회 결과만 verbatim 인용하도록 강제하는 [`SKILL.md`](SKILL.md)
3. **검증** — 이미 쓰인 문서의 가짜 코드·변형 진술문을 잡아내는 `verify.py` (exit code로 CI 게이트)

## 설치

**Claude Code (스킬):**

```bash
git clone https://github.com/<YOUR_GITHUB_ID>/kr-curriculum-2022 ~/.claude/skills/kr-curriculum-2022
```

`SKILL.md`의 description을 보고 교육과정 관련 작업에서 자동으로 발동한다.

**Codex · Cursor · 그 밖의 에이전트:** 리포를 clone하고 `AGENTS.md`나 규칙 파일에
"성취기준을 다룰 때 `kr-curriculum-2022/SKILL.md`를 먼저 읽고 따르라"를 추가한다.
설정 예시는 [`examples/`](examples/) — [Claude Code](examples/claude-code.md) ·
[Codex](examples/codex.md) · [Cursor](examples/cursor.md).

**터미널을 안 쓰는 사람:** [`browse/`](browse/README.md)에 교과별 표가 있다.
브라우저에서 열고 Ctrl+F로 찾으면 된다. 설치도 파이썬도 필요 없다.

의존성은 없다. 파이썬 3.9+ 표준 라이브러리만 쓴다.

## 빠른 사용

```bash
# 조회 — 주제에서 출발해 찾는다
python3 scripts/lookup.py --school 중 --subject 수학 --keyword 소인수분해 --format md

# 검증 — 다 쓴 문서를 검사한다 (문제 0건이면 exit 0, 있으면 exit 1)
python3 scripts/verify.py 수업지도안.md --school 중
```

첫 명령의 실제 출력:

```
- **[9수01-01]** 소인수분해의 뜻을 알고, 자연수를 소인수분해 할 수 있다. (중·수학·수학) — 교차검증됨·별책
- **[9수01-02]** 소인수분해를 이용하여 최대공약수와 최소공배수를 구할 수 있다. (중·수학·수학) — 교차검증됨·별책
```

줄 끝의 `— 교차검증됨·별책`이 **신뢰 등급**이다. 이 저장소는 모든 문장에 이 등급을 붙인다.

## 무엇이 들어 있나

| 학교급 | 성취기준 | 교과 |
|---|---:|---|
| 초 | 611 | 국어, 사회, 수학, 과학, 영어, 도덕, 체육, 음악, 미술, 실과·기술가정·정보, 통합교과 (11개) |
| 중 | 704 | 위 11개에서 통합교과를 빼고 한문, 제2외국어, 중학교 선택을 더한 13개 |
| 고 | 1979 | 중학교와 같은 13개에서 중학교 선택을 뺀 12개. 공통 과목과 선택 과목(일반·진로·융합)을 모두 포함 |
| **합계** | **3294** | 데이터 파일 36개 |

레코드 하나는 코드·진술문·출처·학교급·학년군·과목·성취수준(A~E)·검증 플래그를 갖는다.
성취수준이 붙은 것이 3113건, 별책에만 있어 성취수준이 없는 것이 181건이다.

| 경로 | 내용 |
|---|---|
| `data/<학교급>/<교과>.jsonl` | 성취기준 레코드 (1줄 1건), 목록은 `data/index.json` |
| `scripts/lookup.py` · `scripts/verify.py` | 조회 · 인용 검증 CLI (의존성 없음) |
| [`SKILL.md`](SKILL.md) | 에이전트용 지침 |
| [`browse/`](browse/README.md) | 사람이 읽는 교과별 표 |
| [`validation-report.md`](validation-report.md) | 교차검증 전수 결과 · 결손 목록 |
| [`references/sources.md`](references/sources.md) | 출처 고시 · 제외 자료와 사유 |
| `pipeline/` | 원문 PDF에서 여기까지 온 추출 코드 전체 |

## 이 데이터를 믿어도 되는 근거

**출처는 교육부 고시 제2022-33호 별책 5~18**, 즉 고시 원문 PDF다. 블로그나 문제집 같은
2차 자료를 긁어 온 것이 아니다. 다만 여기 실린 문장은 그 PDF를 기계로 변환·추출한
결과물이지 고시 원문 그 자체가 아니다 — 변환에서 생긴 손상이 아래에 정리돼 있다.

**서로 독립된 두 문서로 교차검증했다.** 별책 고시본과, 교육부·한국교육과정평가원(KICE)이
따로 만든 『성취수준』 문서는 같은 진술문을 각각 싣는다. 두 문장을 **글자 단위로** 대조한
결과가 모든 레코드의 `statement_verified` 필드다.

| `statement_verified` | 건수 | 뜻 |
|---|---:|---|
| `true` | 2849 (86.5%) | 두 문서가 글자까지 같은 문장을 싣는다 |
| `false` | 252 (7.7%) | 두 문서가 **다른** 문장을 싣는다 — 어느 쪽이 원문인지 이 데이터로는 판정 불가 |
| `null` | 193 | 대조할 독립 출처가 없다(154) + 진술문 자체가 없다(39) |

기준을 '비슷하면 통과'가 아니라 '글자까지 같음'으로 잡았다. 유사도로 재던 때는
`6도04-01`(한쪽은 '안', 다른 쪽은 '법')처럼 문법적으로 멀쩡해서 읽어도 안 걸리는 손상이
'검증됨'으로 통과했기 때문이다. 그런 걸 잡으라고 두는 장치가 그걸 놓치면 의미가 없다.

**어긋난 자리는 덮지 않고 전부 공개한다.** [`validation-report.md`](validation-report.md)에
불일치 252건의 양쪽 문장을 나란히 싣고, 번호가 끊긴 자리 26개와 이 데이터셋에 없는
코드 1141개(다루지 않는 과목 1095개 + 다루는 과목인데 결손된 46개)를 전부 나열한다.
파이프라인 코드도 `pipeline/`에 그대로 있어 같은 결과를 다시 만들어 볼 수 있다.

**추출 파이프라인은 테스트로 고정돼 있다.** `python3 -m pytest tests/ -v`로 확인할 수 있고,
CI가 푸시마다 같은 것을 돌린다(맨 위 배지).

### 그리고 믿으면 안 되는 것

이 데이터셋은 **완전하지도 공식적이지도 않다.** 교육부가 배포한 것이 아니라, 공개된 고시
PDF를 기계로 추출한 결과물이고 오류율을 스스로 공개한 것뿐이다.

- **사람이 확인해야 하는 레코드 391건(11.9%)** — `needs_review: true`. 이 중 278건이
  제2외국어 하나에 몰려 있다(별책16의 PDF 변환 품질이 눈에 띄게 나쁘다). 나머지 13개 교과는
  2723건 중 113건(4.1%)이다.
- **진술문이 아예 없는 레코드 39건** — 코드는 실재하는데 PDF 변환에서 문장이 파괴돼
  복구하지 못했다. 조회하면 빈칸 대신 "진술문 미수록"이라고 답한다. **비워 두는 쪽을 택했다.**
- **번호가 끊긴 자리 26개** — 고시에는 있으나 원문에서 코드 마커가 파손돼 추출되지 않았다.
  조회 결과가 없다고 해서 "그런 성취기준은 없다"로 읽으면 안 되는 이유다.
- **OCR 잔재 50건**, 별책이 손상돼 성취수준표에서 문장을 가져온 것 152건.
- **성취수준(A~E) 서술문은 위 신뢰 등급의 검증 대상이 아니다.** `statement_verified`는
  진술문만 대조한 값이고, `verify.py`도 성취수준은 검사하지 않는다. 원문에서 그대로 찾을 수
  없어 등급 배정이 의심스러운 서술문이 56건 있고, 그중 35건이 이 데이터셋의 성취기준
  22개에 걸린다(나머지는 여기 싣지 않은 과목의 것이다).
- **`true`도 고시 원문과 같다는 보장은 아니다.** 두 문서가 같은 오류를 물려받은 자리는
  이 방법으로 잡히지 않는다.

공문서·평가계획처럼 정확성이 곧 책임인 문서라면, 최종 확인은 언제나 고시 원문이다.
이 저장소는 그 확인을 없애 주는 물건이 아니라, **어디를 확인해야 하는지 짚어 주는 물건이다.**

## 여기에 없는 것

찾다가 없어서 헛수고하지 않도록 미리 적는다. 아래는 조회해도 결과가 나오지 않는다.

- **특성화고 전문교과(NCS)** — 별책 23~39. `[성직 01-01]` 형식의 별도 코드 체계라 미수록.
- **과학고·체고·예고의 계열 전문 교과와 고등학교 교양 교과** — 정보·보건·환경·연극·영화·
  사진·무용·문예 창작 등. 해당 별책 고시본이 원자료에 없어 고시 원문으로 문장을 확인할 수
  없었고, **확인할 수 없는 문장은 싣지 않기로 했다.** 여기 해당하는 코드가 1095개다.
- **2015 개정 교육과정** — 코드 형식이 비슷하지만 다른 교육과정이다. 이 저장소는 2022 개정 전용.
- **한국어 교육과정(별책41)** — 교육부 고시 제2017-131호라 2022 개정이 아니다.

전체 목록과 사유는 [`references/sources.md`](references/sources.md)와
[`validation-report.md`](validation-report.md)의 「수록하지 않은 코드 전체 목록」에 있다.

## In English

`kr-curriculum-2022` is a machine-extracted, cross-verified dataset of the **3294 achievement
standards (성취기준) of Korea's 2022 Revised National Curriculum** — 611 elementary, 704 middle,
1979 high school — plus the A–E achievement levels (성취수준) for 3113 of them.

It ships as an **agent skill**: `SKILL.md` instructs an LLM to look codes up rather than recall
them, `scripts/lookup.py` queries the dataset, and `scripts/verify.py` scans a finished document
for fabricated codes and altered statements, exiting non-zero so it can gate CI. Stdlib-only,
no dependencies.

Sources are the Ministry of Education's official 고시 (Notice No. 2022-33, appendices 5–18),
cross-checked character-by-character against the independently produced KICE achievement-level
documents. It is **not official and not complete**: 2849 statements agree across both sources,
252 disagree, 193 could not be cross-checked, and 39 codes exist with no recoverable statement
at all. Every discrepancy is enumerated in `validation-report.md` rather than smoothed over.

Topics: `korean-curriculum` `education` `k12` `claude-skill` `agent-skills` `llm-hallucination`
`dataset` `korea` `edtech`

## 로드맵

아직 안 된 것들이다.

- [ ] 특성화고 NCS 전문교과 (별책 23~39)
- [ ] 진술문 미수록 39건·번호 공백 26개를 고시 원문으로 메우기
- [ ] 2015 개정 코드 → 2022 개정 매핑 테이블

## 기여

오류 신고를 가장 환영한다. 진술문이 고시 원문과 다른 자리를 찾았다면 **코드와 원문 출처
(별책 번호·쪽수)**를 이슈에 적어 달라. 데이터 파일은 손으로 고치지 않는다 —
`pipeline/`이 다시 생성하므로 파이프라인이나 `pipeline/exceptions.json`을 고쳐야 한다.

## 라이선스·출처

코드는 **MIT**([LICENSE](LICENSE)).

`data/`와 `browse/`의 데이터는 **교육부 고시 문서의 verbatim 추출물**이며, 원문은
「공공저작물 자유이용허락(공공누리)」 대상 공공저작물이다. 이 저장소는 교육부 고시 원문에
대해 어떤 저작권도 주장하지 않는다. 출처 표기와 문서별 대응은
[`references/sources.md`](references/sources.md)를 참조하고, 데이터를 재사용할 때는
교육부·한국교육과정평가원(KICE)을 원출처로 함께 밝혀 달라.

이 저장소는 교육부·한국교육과정평가원과 아무 관련이 없는 비공식 프로젝트다.
