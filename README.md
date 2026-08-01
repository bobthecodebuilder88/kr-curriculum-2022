# kr-curriculum-2022

**2022 개정 교육과정 성취기준 3,294건을 찾아보고, 문서에 인용한 성취기준이 진짜인지 확인하는 도구입니다.**

> Korean 2022 Revised National Curriculum achievement standards (grades 1–12) as a
> queryable dataset, a citation verifier, and an agent skill — so an LLM looks a
> curriculum code up instead of inventing one.

[![CI](https://github.com/bobthecodebuilder88/kr-curriculum-2022/actions/workflows/ci.yml/badge.svg)](https://github.com/bobthecodebuilder88/kr-curriculum-2022/actions/workflows/ci.yml)
![standards](https://img.shields.io/badge/standards-3294-blue)
![license](https://img.shields.io/badge/code-MIT-informational)

---

## 왜 만들었나

챗GPT나 클로드에게 "중2 수학 소인수분해 수업에 성취기준 달아줘"라고 시켜 보신 적 있으실 겁니다.
그럴듯한 답이 나옵니다. 문제는 그 답이 **둘 중 하나인 경우가 많다**는 것입니다.

**첫째, 없는 성취기준을 만들어 냅니다.**
예를 들어 `[9수05-08]`. 중학교 수학에는 05 영역 자체가 없습니다(01~04뿐입니다).
그런데 자릿수와 모양이 멀쩡해서, 결재 서류에 그대로 올라가도 아무도 눈치채지 못합니다.

**둘째, 실재하는 성취기준의 문장을 슬쩍 바꿉니다.**

> 원문: 소인수분해의 뜻을 **알고**, 자연수를 소인수분해 할 수 있다.
> AI: 소인수분해의 뜻을 **이해하고**, 자연수를 소인수분해 할 수 있다.

`알고`가 `이해하고`로 바뀌었습니다. 소리 내어 읽어도 걸리지 않습니다.
하지만 수업지도안·평가계획·생기부 문구처럼 **정확성이 곧 책임인 문서**에서는 문제가 됩니다.

이 저장소는 그걸 막으려고 만들었습니다. 교육부 고시 원문에서 성취기준 3,294건을 그대로 옮겨
담고, 문서에 쓰인 성취기준이 진짜인지 확인해 주는 도구를 함께 넣었습니다.

---

## 1. 설치 없이 찾아보기 — 가장 간단한 방법

**프로그램을 깔 필요도, 명령어를 칠 필요도 없습니다.** 브라우저에서 바로 보시면 됩니다.

👉 **[교과별 성취기준 목록 보기](browse/README.md)**

학교급과 교과를 고르면 그 교과의 성취기준이 표로 정리돼 있습니다.
`Ctrl+F`(맥은 `⌘+F`)로 원하는 단어를 찾으시면 됩니다.

예시: [중학교 수학](browse/중/수학.md) · [초등 국어](browse/초/국어.md) · [고등 통합사회](browse/고/사회.md)

표에는 성취기준 코드, 문장, 과목, 그리고 **신뢰 등급**이 함께 있습니다.
신뢰 등급이 무엇인지는 [아래](#이-데이터를-믿어도-되는-근거)에서 설명드립니다.

---

## 2. 다 쓴 문서 검사하기

이미 작성한 수업지도안이나 평가계획에 성취기준을 인용해 두었다면, 그 문서를 통째로 넣어
한 번에 확인할 수 있습니다. 파이썬만 있으면 됩니다(맥에는 기본으로 깔려 있습니다).

**준비 — 한 번만 하시면 됩니다.**

```bash
git clone https://github.com/bobthecodebuilder88/kr-curriculum-2022
cd kr-curriculum-2022
```

**검사하기**

```bash
python3 scripts/verify.py 수행평가계획.md --school 중
```

문제가 없으면 이렇게 나옵니다.

```
OK — 검사한 코드 3개 모두 정상
```

문제가 있으면 어느 성취기준이 왜 잘못됐는지 알려 줍니다.

```
MISMATCH [9수01-01] — 진술문이 원문과 다름
  원문: 소인수분해의 뜻을 알고, 자연수를 소인수분해 할 수 있다.
FAKE  [9수05-08] — 이 데이터셋에 없는 코드. 지어낸 코드이거나, 이 데이터셋이 다루지 않는 과목(전문 교과·교양 등)이다. 원문 고시본으로 확인하기 전에는 인용하지 마라

문제 2건 발견 (검사 코드 2개)
```

`MISMATCH`는 **코드는 맞는데 문장이 다르다**는 뜻이고, `FAKE`는 **그런 코드가 없다**는 뜻입니다.
표시는 모두 여덟 가지인데, 크게 두 부류입니다.

| 반드시 고쳐야 하는 것 | 뜻 |
|---|---|
| `FAKE` | 데이터에 없는 코드입니다. 지어냈거나, 이 저장소가 다루지 않는 과목입니다 |
| `MISMATCH` | 코드는 맞지만 문장이 고시 원문과 다릅니다 |
| `NOSTMT` | 코드는 실재하는데 원문 손상으로 문장을 싣지 못해, 확인해 드릴 수 없습니다 |
| `LEVEL` | 지정하신 학교급과 그 성취기준의 학교급이 다릅니다 |
| `LVLDIFF` | 성취수준(A~E) 서술문이 원문과 다릅니다 |
| `LVLMISS` | 그 성취기준에 없는 등급을 인용하셨습니다 |

| 알아만 두시면 되는 것 | 뜻 |
|---|---|
| `WARN` | 인용은 정확한데, 그 문장을 대조할 다른 출처가 없어 교차검증을 못 했습니다 |
| `LVLNONE` | 성취수준이 수록되지 않은 성취기준이라 등급을 확인할 수 없습니다 |

> **주의**: `LEVEL`은 학교급(초·중·고), `LVL...`로 시작하는 것은 성취수준(A~E)입니다.
> 이름이 비슷하지만 다른 검사입니다.

### 주제어로 찾기

거꾸로 처음부터 찾아 쓰실 때는 이렇게 하시면 됩니다.

```bash
python3 scripts/lookup.py --school 중 --subject 수학 --keyword 소인수분해 --format md
```

```
- **[9수01-01]** 소인수분해의 뜻을 알고, 자연수를 소인수분해 할 수 있다. (중·수학·수학) — 교차검증됨·별책
  - A수준: 소인수분해의 뜻을 설명하고, 자연수를 소인수분해 할 수 있다.
  - C수준: 소인수분해의 뜻을 알고, 자연수를 소인수의 곱으로 표현할 수 있다.
  - E수준: 소인수를 알고, 안내된 절차에 따라 자연수를 소인수의 곱으로 표현할 수 있다.
```

`A수준`, `C수준` 같은 줄이 성취수준입니다(이 성취기준은 A·C·E 세 등급만 있습니다).
줄 끝의 `— 교차검증됨·별책`이 신뢰 등급과 출처입니다.

---

## 3. AI 도구가 성취기준을 지어내지 않게 하기

클로드 코드 같은 AI 도구를 쓰신다면, 이 저장소를 물려 두면 AI가 **기억에 의존하지 않고
반드시 조회한 결과만** 인용하게 됩니다.

**클로드 코드:**

```bash
git clone https://github.com/bobthecodebuilder88/kr-curriculum-2022 ~/.claude/skills/kr-curriculum-2022
```

이렇게만 해 두면 교육과정 관련 작업에서 알아서 발동합니다.

**Codex · Cursor 등 다른 도구:** 저장소를 내려받은 뒤 규칙 파일(`AGENTS.md` 등)에
"성취기준을 다룰 때는 `kr-curriculum-2022/SKILL.md`를 먼저 읽고 따르라"를 추가하시면 됩니다.
도구별 설정 예시는 [`examples/`](examples/) 폴더에 있습니다 —
[클로드 코드](examples/claude-code.md) · [Codex](examples/codex.md) · [Cursor](examples/cursor.md).

AI에게 주는 지침 자체가 궁금하시면 [`SKILL.md`](SKILL.md)를 열어 보시면 됩니다.

---

## 4. 교육 콘텐츠를 개발하신다면

생성한 콘텐츠를 배포하기 전에 자동으로 걸러 낼 수 있습니다.
`verify.py`는 문제가 없으면 0, 있으면 1을 반환하므로 배포 스크립트나 CI에 그대로 붙습니다.

```bash
python3 scripts/verify.py 생성된_학습지.md || exit 1
```

폴더를 통째로 검사하시려면:

```bash
for f in 자료/*.md; do
  python3 scripts/verify.py "$f" >/dev/null 2>&1 || echo "문제: $f"
done
```

외부 라이브러리를 쓰지 않습니다. 파이썬 3.9 이상이면 그대로 돌아갑니다.

---

## 이럴 때는 도움이 되지 않습니다

찾다가 헛수고하지 않으시도록 미리 밝혀 둡니다.

- **특성화고 전문교과(NCS) 성취기준** — 수록하지 않았습니다.
- **2015 개정 교육과정 문서 검수** — 코드 형식이 비슷해서 코드 자체는 통과하지만 문장이 달라
  `MISMATCH`가 뜹니다. 이 저장소는 **2022 개정 전용**입니다.
- **수업 설계가 타당한지 판단하는 일** — 이 도구는 성취기준이 진짜인지만 봅니다.
  수업이 좋은지 나쁜지는 봐 드리지 못합니다.

---

## 무엇이 들어 있나

| 학교급 | 성취기준 | 교과 |
|---|---:|---|
| 초 | 611 | 국어, 사회, 수학, 과학, 영어, 도덕, 체육, 음악, 미술, 실과·기술가정·정보, 통합교과 (11개) |
| 중 | 704 | 위 11개에서 통합교과를 빼고 한문, 제2외국어, 중학교 선택을 더한 13개 |
| 고 | 1,979 | 중학교와 같은 13개에서 중학교 선택을 뺀 12개. 공통 과목과 선택 과목(일반·진로·융합) 모두 |
| **합계** | **3,294** | |

성취기준 하나마다 코드, 문장, 출처, 학교급, 학년군, 과목, 성취수준(A~E), 검증 결과가 붙어 있습니다.
성취수준까지 있는 것이 3,113건, 별책에만 실려 성취수준이 없는 것이 181건입니다.

| 폴더·파일 | 내용 |
|---|---|
| [`browse/`](browse/README.md) | **사람이 읽는 교과별 표** — 설치 없이 여기부터 보시면 됩니다 |
| [`validation-report.md`](validation-report.md) | 검증 결과 전부와 빠진 것 목록 |
| [`SKILL.md`](SKILL.md) | AI 도구에 주는 지침 |
| `scripts/lookup.py` · `scripts/verify.py` | 찾기 · 검사 도구 |
| `data/<학교급>/<교과>.jsonl` | 원본 데이터(프로그램이 읽는 형식) |
| [`references/sources.md`](references/sources.md) | 출처 고시 목록과 제외한 자료 |
| `pipeline/` | 고시 PDF에서 이 데이터를 뽑아낸 코드 전부 |

---

## 이 데이터를 믿어도 되는 근거

교육 자료에서 정확성은 곧 책임이니, 이 데이터가 어디까지 믿을 만한지 솔직하게 적습니다.

### 출처는 고시 원문입니다

**교육부 고시 제2022-33호 별책 5~18**에서 뽑았습니다. 블로그나 문제집 같은 2차 자료를 긁어
모은 것이 아닙니다. 다만 여기 실린 문장은 그 PDF를 **기계로 변환·추출한 결과물**이지
고시 원문 그 자체는 아닙니다. 변환 과정에서 생긴 손상은 아래에 그대로 적어 두었습니다.

### 서로 다른 두 문서로 대조했습니다

교육부 별책 고시본과, 한국교육과정평가원(KICE)이 따로 만든 『성취수준』 문서는
**같은 성취기준 문장을 각각 싣습니다.** 이 둘을 글자 단위로 맞춰 본 결과가 신뢰 등급입니다.

| 신뢰 등급 | 건수 | 뜻 |
|---|---:|---|
| **교차검증됨** | 2,849건 (86.5%) | 두 문서가 글자까지 똑같은 문장을 싣고 있습니다 |
| **출처 불일치** | 252건 (7.7%) | 두 문서의 문장이 다릅니다. 어느 쪽이 맞는지 이 데이터로는 판정할 수 없습니다 |
| **단일 출처** | 193건 | 대조할 다른 문서가 없었습니다(154건) + 문장 자체가 없습니다(39건) |

'비슷하면 통과'가 아니라 **'글자까지 같아야 통과'**로 잡았습니다.
유사도로 재던 때는 `6도04-01`처럼 한쪽은 '안', 다른 쪽은 '법'인 손상이
문법적으로 멀쩡해서 그냥 통과했기 때문입니다. 그런 걸 잡으라고 둔 장치가 그걸 놓치면
있으나 마나 합니다.

### 어긋난 자리를 숨기지 않았습니다

[`validation-report.md`](validation-report.md)에 불일치 252건의 양쪽 문장을 나란히 싣고,
번호가 끊긴 자리 26개와 이 저장소에 없는 코드 1,141개를 전부 나열했습니다.
데이터를 뽑아낸 코드도 `pipeline/`에 그대로 공개해 두어, 같은 결과를 직접 다시 만들어 보실 수 있습니다.

### 그래도 이건 알아 두셔야 합니다

이 데이터는 **공식 자료가 아니고, 완전하지도 않습니다.** 교육부가 배포한 것이 아니라
공개된 고시 PDF를 기계로 추출한 결과물이고, 오류율을 스스로 밝힌 것뿐입니다.

- **사람이 확인해야 하는 것 391건(11.9%)** — 이 중 278건이 제2외국어 하나에 몰려 있습니다
  (별책16의 PDF 변환 품질이 유독 나쁩니다). 나머지 13개 교과는 2,723건 중 113건(4.1%)입니다.
- **문장이 아예 없는 것 39건** — 코드는 실재하는데 PDF 변환에서 문장이 깨져 복구하지
  못했습니다. 조회하시면 빈칸 대신 "진술문 미수록"이라고 답합니다. **비워 두는 쪽을 택했습니다.**
- **번호가 끊긴 자리 26개** — 고시에는 있는데 원문 손상으로 뽑아내지 못했습니다.
  **그래서 "조회 결과가 없다"를 "그런 성취기준은 없다"로 읽으시면 안 됩니다.**
- **성취수준(A~E) 서술문은 위 신뢰 등급의 대상이 아닙니다.** 신뢰 등급은 성취기준 문장만
  대조한 값입니다. 원문에서 그대로 찾을 수 없어 등급 배정이 의심스러운 서술문이 35건 있습니다.
- **'교차검증됨'도 고시 원문과 같다는 보장은 아닙니다.** 두 문서가 같은 오류를 물려받은
  자리는 이 방법으로 잡히지 않습니다.

공문서나 평가계획처럼 정확성이 곧 책임인 문서라면, **최종 확인은 언제나 고시 원문입니다.**
이 저장소는 그 확인을 없애 주는 물건이 아니라, **어디를 확인해야 하는지 짚어 주는 물건입니다.**

### 초록 배지는 무엇을 보증하나

저장소 위쪽 CI 배지는 코드를 고칠 때마다 자동으로 도는 검사가 통과했다는 뜻입니다.
검사는 모두 104개인데, 그중 **97개가 자동으로 돕니다.**
나머지 7개는 고시 원문(약 93MB)을 직접 읽어야 해서, 원문을 저장소에 싣지 않은 탓에 건너뜁니다.

- **배지가 보증하는 것** — 찾기·검사 도구가 지어낸 코드와 변조된 문장을 제대로 잡아내고,
  교과별 표가 원본 데이터와 어긋나지 않는다는 것.
- **배지가 보증하지 않는 것** — `data/`의 문장이 고시 원문에 그대로 있다는 것.
  그걸 재는 가장 강한 검사 7개가 여기 해당합니다. 이 데이터는 원문이 있는 환경에서 그 7개를
  통과시킨 뒤 올린 것이지만, 배지가 매번 다시 재는 것은 아닙니다.

---

## 여기에 없는 것

- **특성화고 전문교과(NCS)** — 별책 23~39. `[성직 01-01]` 형식의 다른 코드 체계라 수록하지 않았습니다.
- **과학고·체고·예고의 계열 전문 교과와 고등학교 교양 교과** — 정보·보건·환경·연극·영화·
  사진·무용·문예 창작 등입니다. 해당 별책 고시본을 구하지 못해 문장을 원문으로 확인할 수
  없었고, **확인할 수 없는 문장은 싣지 않기로 했습니다.** 여기 해당하는 코드가 1,095개입니다.
- **2015 개정 교육과정** — 코드 형식이 비슷하지만 다른 교육과정입니다.
- **한국어 교육과정(별책41)** — 교육부 고시 제2017-131호라 2022 개정이 아닙니다.

전체 목록과 사유는 [`references/sources.md`](references/sources.md)와
[`validation-report.md`](validation-report.md)에 있습니다.

---

## In English

`kr-curriculum-2022` is a machine-extracted, cross-verified dataset of the **3,294 achievement
standards (성취기준) of Korea's 2022 Revised National Curriculum** — 611 elementary, 704 middle,
1,979 high school — plus the A–E achievement levels (성취수준) for 3,113 of them.

It ships as an **agent skill**: `SKILL.md` instructs an LLM to look codes up rather than recall
them, `scripts/lookup.py` queries the dataset, and `scripts/verify.py` scans a finished document
for fabricated codes, altered statements, and altered or invented A–E level descriptors, exiting
non-zero so it can gate CI. Stdlib-only, no dependencies.

Sources are the Ministry of Education's official 고시 (Notice No. 2022-33, appendices 5–18),
cross-checked character-by-character against the independently produced KICE achievement-level
documents. It is **not official and not complete**: 2,849 statements agree across both sources,
252 disagree, 193 could not be cross-checked, and 39 codes exist with no recoverable statement
at all. Every discrepancy is enumerated in `validation-report.md` rather than smoothed over.

Topics: `korean-curriculum` `education` `k12` `claude-skill` `agent-skills` `llm-hallucination`
`dataset` `korea` `edtech`

---

## 앞으로 할 일

- [ ] 특성화고 NCS 전문교과 (별책 23~39) 추가
- [ ] 문장이 없는 39건과 번호가 끊긴 26개를 고시 원문으로 메우기
- [ ] 2015 개정 코드 → 2022 개정 대응표

## 오류를 발견하셨다면

**오류 신고를 가장 환영합니다.** 문장이 고시 원문과 다른 자리를 찾으셨다면
**성취기준 코드와 원문 출처(별책 번호·쪽수)**를 이슈에 적어 주시면 됩니다.
교과 전문성이 있으신 분의 지적이 이 데이터를 가장 빠르게 좋게 만듭니다.

데이터 파일은 손으로 고치지 않습니다. `pipeline/`이 다시 생성하므로
파이프라인이나 `pipeline/exceptions.json`을 고쳐야 합니다.

### 추출을 다시 돌리려면

고시 원문 문서(약 93MB)가 있어야 합니다. 저작권 문제가 아니라 크기 때문에 저장소에 싣지
않았습니다 — 출처와 문서 목록은 [`references/sources.md`](references/sources.md)에 있습니다.
원문을 구하셨다면 폴더 경로를 환경 변수로 넘기시면 됩니다.

```bash
export KR_CURRICULUM_SOURCE_DIR=/원문/폴더/경로
python3 -m pipeline.extract_bylaws    # → data/raw/standards.jsonl
python3 -m pipeline.extract_levels    # → data/raw/levels.jsonl
python3 -m pipeline.build             # → data/, validation-report.md
python3 -m pipeline.generate_views    # → browse/
```

원문이 없으면 원문을 직접 읽는 검사 7개는 알아서 건너뜁니다. 나머지 97개는 그대로 돕니다.

## 라이선스·출처

코드는 **MIT**([LICENSE](LICENSE)).

`data/`와 `browse/`의 데이터는 **교육부 고시 문서에서 글자 그대로 옮긴 것**이며,
원문은 「공공저작물 자유이용허락(공공누리)」 대상 공공저작물입니다.
이 저장소는 교육부 고시 원문에 대해 어떤 저작권도 주장하지 않습니다.
출처 표기와 문서별 대응은 [`references/sources.md`](references/sources.md)를 참조하시고,
데이터를 다시 쓰실 때는 교육부·한국교육과정평가원(KICE)을 원출처로 함께 밝혀 주시기 바랍니다.

이 저장소는 교육부·한국교육과정평가원과 아무 관련이 없는 비공식 프로젝트입니다.
