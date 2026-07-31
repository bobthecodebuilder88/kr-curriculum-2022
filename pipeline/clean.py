"""원문 로딩·정제. 모든 파서는 반드시 이 모듈을 통해 원문을 읽는다."""
import re
import unicodedata
from pathlib import Path

def load_text(path: Path) -> str:
    raw = Path(path).read_bytes().replace(b"\x00", b"")
    text = raw.decode("utf-8", errors="replace")
    return unicodedata.normalize("NFC", text)

_STRIKE = re.compile(r"~~[^~]*~~")

def clean_cell(s: str) -> str:
    s = s.replace("<br>", " ")
    s = _STRIKE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return "" if s == "NaN" else s
