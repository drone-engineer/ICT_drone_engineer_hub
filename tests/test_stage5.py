from io import BytesIO

import pandas as pd
import pytest

from utils import ops_export, scraper


def test_block_internal():
    for bad in ["http://127.0.0.1/x", "http://localhost:8501", "http://192.168.0.1", "ftp://example.com", "javascript:1"]:
        with pytest.raises(ValueError):
            scraper.check_url(bad)


def test_extract_and_markdown():
    html = ("<html><head><title> T-Motor  테스트 </title></head><body>"
            "<table><tr><th>KV</th><th>추력</th></tr><tr><td>400</td><td>5|0kg</td></tr>"
            "<tr><td>600</td><td>3kg</td></tr></table></body></html>")
    assert scraper.page_title(html) == "T-Motor 테스트"
    tables = scraper.extract_tables(html)
    assert len(tables) == 1
    md = scraper.build_markdown("https://example.com/p", "제목", tables)
    assert "| KV | 추력 |" in md and "5/0kg" in md and "## 표 1" in md


def test_no_tables():
    assert scraper.extract_tables("<html><body>표 없음</body></html>") == []


def test_slug():
    assert scraper.slug("https://www.a.com/x/y?z=1") == "www_a_com_x_y"


def test_excel_three_sheets():
    log = [
        {"일시": "t1", "질문": "q1", "경로": "manual", "페르소나": "p", "계통": "", "결선주의": True, "답변요약": "a"},
        {"일시": "t2", "질문": "q2", "경로": "compare", "페르소나": "p", "계통": "", "결선주의": False, "답변요약": "b"},
        {"일시": "t3", "질문": "q3", "경로": "web", "페르소나": "p", "계통": "", "결선주의": False, "답변요약": "c"},
    ]
    x = pd.ExcelFile(BytesIO(ops_export.to_excel_bytes(log)))
    assert x.sheet_names == ["전체이력", "결선주의질의", "비교검증질의"]
    assert len(x.parse("전체이력")) == 3
    assert len(x.parse("결선주의질의")) == 1
    assert len(x.parse("비교검증질의")) == 1


def test_excel_empty():
    x = pd.ExcelFile(BytesIO(ops_export.to_excel_bytes([])))
    assert len(x.sheet_names) == 3
