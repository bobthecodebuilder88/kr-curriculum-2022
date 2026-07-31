import unicodedata
from pathlib import Path
from pipeline.clean import load_text, clean_cell

def test_load_text_strips_nul_and_normalizes_nfc(tmp_path):
    p = tmp_path / "s.md"
    # NUL 바이트 삽입 + NFD 한글 (원문에서 실제 관찰된 오염)
    raw = "12문\x00학01-01] 문학이".encode("utf-8") + "\x00\x00".encode() + unicodedata.normalize("NFD", "수학").encode("utf-8")
    p.write_bytes(raw)
    t = load_text(p)
    assert "\x00" not in t
    assert "12문학01-01]" in t
    assert "수학" in t  # NFC로 복원

def test_load_text_tolerates_invalid_utf8(tmp_path):
    p = tmp_path / "s.md"
    p.write_bytes(b"[9\xec\x88\x9801-01] \xff\xfe ok")  # 깨진 바이트 포함
    t = load_text(p)
    assert "[9수01-01]" in t and "ok" in t

def test_clean_cell():
    assert clean_cell("소인수분해의<br>뜻을  알고") == "소인수분해의 뜻을 알고"
    assert clean_cell("B<br>~~-~~") == "B"
    assert clean_cell("D<br>~~—~~") == "D"
    assert clean_cell(" NaN ") == ""   # 엑셀 변환 잔재는 빈 값 취급
