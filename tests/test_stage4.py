import re
import zlib

import numpy as np

from utils import chat_engine as ce
from utils import rag_engine as rag
from utils import router


def test_router():
    assert router.classify("Pixhawk 6C 전원 모듈 배선 시 VCC와 GND 핀 순서는?") == "manual"
    assert router.classify("PX4와 ArduPilot의 EKF 고도 추정 방식 차이는?") == "compare"
    assert router.classify("T-Motor 최신 롱레인지 모터 사양 및 출시 가격은?") == "web"
    assert router.wiring_warning("VCC와 GND 순서") is True
    assert router.wiring_warning("프로펠러 방향") is False


def test_fix_md():
    assert ce.fix_md("10~15kg 그리고 3 ~ 5분") == "10-15kg 그리고 3-5분"


def test_split_text():
    t = "".join(chr(97 + i % 26) for i in range(2500))
    parts = rag.split_text(t, 1000, 100)
    assert all(len(p) <= 1000 for p in parts)
    assert parts[0][-100:] == parts[1][:100]
    assert rag.split_text("짧은 글", 1000, 100) == ["짧은 글"]


def test_parts_roundtrip(tmp_path):
    data = bytes(range(256)) * 100
    n = rag.save_parts(tmp_path, "x.bin", data, part=1000)
    assert n == 26
    assert rag.read_parts(tmp_path, "x.bin") == data


def _fake_embed(texts, retries=4):
    out = []
    for t in texts:
        v = np.zeros(rag.DIMS, dtype="float32")
        for w in re.findall(r"\w+", t.lower()):
            v += np.random.RandomState(zlib.crc32(w.encode())).randn(rag.DIMS).astype("float32")
        out.append(v)
    return np.array(out)


def _pdf(path, pages):
    """영문 텍스트 PDF를 직접 만든다 (외부 PDF 라이브러리 불필요)"""
    path.parent.mkdir(parents=True, exist_ok=True)
    objs = []
    n = len(pages)
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(n))
    objs.append(f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode())
    font_id = 3 + 2 * n
    for i, text in enumerate(pages):
        stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                    f"/Contents {4 + 2 * i} 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> >>".encode())
        objs.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    out = b"%PDF-1.4\n"
    offs = []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for o in offs:
        out += f"{o:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    path.write_bytes(out)


def test_build_load_search(tmp_path, monkeypatch):
    proj = tmp_path / "proj"
    monkeypatch.setattr(rag, "ROOT", proj)
    monkeypatch.setattr(rag, "MANUALS", proj / "manuals")
    monkeypatch.setattr(rag, "INDEX", proj / "index")
    monkeypatch.setattr(rag, "embed", _fake_embed)
    _pdf(proj / "manuals" / "01_비행제어기_FC" / "a.pdf",
         ["Pixhawk power module VCC GND wiring order", "Pixhawk telemetry port baudrate settings"])
    _pdf(proj / "manuals" / "03_변속기_ESC" / "b.pdf",
         ["Hobbywing ESC DShot calibration steps here", "ESC throttle range calibration procedure"])
    meta = rag.build(max_cost=1.0, work=tmp_path / "work", log=lambda *a: None)
    assert meta["files"] == 2 and meta["chunks"] == 4
    store = rag.load()
    hits = rag.search(store, "pixhawk power VCC wiring", k=2)
    assert hits[0]["file"] == "a.pdf" and hits[0]["page"] == 1
    assert (proj / "manual_catalog.json").exists()


def test_build_cost_guard(tmp_path, monkeypatch):
    proj = tmp_path / "proj"
    monkeypatch.setattr(rag, "ROOT", proj)
    monkeypatch.setattr(rag, "MANUALS", proj / "manuals")
    monkeypatch.setattr(rag, "INDEX", proj / "index")
    monkeypatch.setattr(rag, "embed", _fake_embed)
    _pdf(proj / "manuals" / "01_비행제어기_FC" / "a.pdf", ["Pixhawk power module VCC GND wiring order"])
    try:
        rag.build(max_cost=0.0, work=tmp_path / "work", log=lambda *a: None)
        assert False, "비용 한도 초과인데 중단되지 않음"
    except RuntimeError as e:
        assert "한도" in str(e)
