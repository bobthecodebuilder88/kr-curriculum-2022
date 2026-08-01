"""코퍼스가 있어야만 도는 테스트를 위한 공용 게이트.

이 저장소는 추출 '결과물'(data/)만 싣고, 그걸 만들어 낸 부처 고시 원문(93MB)은
싣지 않는다. 그래서 원문을 직접 읽는 테스트는 fresh clone·CI 에서 돌 수 없다.
그 테스트들은 `corpus` 픽스처를 인자로 받아 원문이 없으면 스스로 skip 한다.

새로 원문을 읽는 테스트를 쓴다면 인자에 `corpus` 를 추가하기만 하면 된다.
조건은 여기 한 곳에만 있다.
"""
import pytest

from pipeline.sources import SOURCE_DIR

# 한 줄로 둔다 — pytest 요약(-rs)은 reason 을 첫 줄까지만 보여준다. 줄을 나누면
# "고장이 아니다"라는 정작 중요한 말이 CI 로그에서 잘린다.
_WHY = (
    f"원본 코퍼스 없음: {SOURCE_DIR} — "
    "이 저장소는 추출 결과물(data/)만 싣고 부처 고시 원문(약 93MB)은 싣지 않는다. "
    "원문 없이 clone 하면 원문을 직접 읽는 테스트는 건너뛴다(정상이며 고장이 아니다). "
    "원문을 따로 구했다면 환경 변수 KR_CURRICULUM_SOURCE_DIR 로 그 폴더를 가리켜 "
    "실행한다(README 「추출을 다시 돌리려면」)."
)


@pytest.fixture(scope="session")
def corpus():
    """부처 고시 원문 폴더. 없으면 요청한 테스트만 skip 한다.

    폴더가 있는데 그 안의 파일이 빠졌다면 skip 하지 않는다 — 그건 코퍼스가 깨진
    것이라 조용히 넘기지 말고 실패로 드러나야 한다.
    """
    if not SOURCE_DIR.is_dir():
        pytest.skip(_WHY)
    return SOURCE_DIR
