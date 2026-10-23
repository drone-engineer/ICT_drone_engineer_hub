import gzip
import hashlib
import json
import re
import time
from datetime import datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
MANUALS = ROOT / "manuals"
INDEX = ROOT / "index"
EMB_MODEL = "text-embedding-3-small"
DIMS = 512
PART_BYTES = 30 * 1024 * 1024
PRICE_PER_M = 0.02          # 달러 / 100만 토큰 (확인 필요)

DOMAIN_HINTS = {
    "01_비행제어기_FC": ["pixhawk", "cube", "px4", "ardupilot", "비행제어", "핀맵", "파라미터"],
    "02_모터_구동계": ["모터", "motor", "kv", "추력"],
    "03_변속기_ESC": ["esc", "변속기", "dshot", "blheli", "foc"],
    "04_프로펠러_공력": ["프로펠러", "propeller", "프롭"],
    "05_전원_배터리_PDB": ["배터리", "lipo", "pdb", "전원", "방전"],
    "06_센서_항법장치": ["gps", "gnss", "나침반", "lidar", "센서", "기압계"],
    "07_조종_데이터링크": ["elrs", "crossfire", "텔레메트리", "sik", "조종기"],
    "08_영상_FPV_짐벌": ["fpv", "짐벌", "gimbal", "카메라"],
    "09_프레임_페이로드": ["프레임", "페이로드", "frame", "payload"],
    "10_안전_비행규정": ["항공안전", "드론원스톱", "규정", "비행승인", "촬영허가", "법"],
    "11_온보드컴퓨터_임베디드": ["jetson", "orin", "raspberry", "온보드"],
    "12_미들웨어_통신_ROS": ["ros", "xrce", "dds", "미들웨어"],
    "13_컴퓨터비전_AI_YOLO": ["yolo", "tensorrt", "trtexec", "비전", "opencv"],
    "14_SLAM_경로계획_내비": ["slam", "fast-lio", "cartographer", "경로", "자율비행"],
}


# ---------- 파일 쪼개 저장 (GitHub 파일 크기 제한 대응) ----------
def save_parts(base, name, data, part=PART_BYTES):
    base.mkdir(parents=True, exist_ok=True)
    for old in base.glob(name + ".part*"):
        old.unlink()
    n = 0
    for i in range(0, max(len(data), 1), part):
        (base / f"{name}.part{n:03d}").write_bytes(data[i:i + part])
        n += 1
    return n


def read_parts(base, name):
    files = sorted(base.glob(name + ".part*"))
    if not files:
        raise FileNotFoundError(name)
    return b"".join(f.read_bytes() for f in files)


# ---------- 추출 / 청킹 ----------
def extract_pdf(path):
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            raise RuntimeError("암호가 걸린 PDF")
    pages = []
    for i, pg in enumerate(reader.pages, 1):
        try:
            t = pg.extract_text() or ""
        except Exception:
            t = ""
        t = t.encode("utf-8", errors="replace").decode("utf-8")   # 깨진 문자(서로게이트) 제거
        t = re.sub(r"[ \t]+", " ", t)
        t = re.sub(r"\n{3,}", "\n\n", t).strip()
        pages.append((i, t))
    return pages


def extract_any(path):
    if path.suffix.lower() == ".md":
        t = path.read_text(encoding="utf-8", errors="replace")
        t = t.encode("utf-8", errors="replace").decode("utf-8")
        return [(1, t.strip())]
    return extract_pdf(path)


def split_text(t, size, overlap):
    if len(t) <= size:
        return [t]
    out, i = [], 0
    while i < len(t):
        out.append(t[i:i + size])
        if i + size >= len(t):
            break
        i += size - overlap
    return out


def _etext(domain, file, page, text):
    return f"{domain} | {file} p.{page}\n{text}"


def _file_chunks(pdf, work, chunk, overlap):
    s = pdf.stat()
    rel = pdf.relative_to(MANUALS).as_posix()
    key = hashlib.sha1(f"{rel}|{s.st_size}|{s.st_mtime_ns}|{chunk}|{overlap}".encode()).hexdigest()[:16]
    cp = work / "chunks" / f"{key}.json"
    if cp.exists():
        try:
            return json.loads(cp.read_text(encoding="utf-8"))
        except Exception:
            cp.unlink()          # 깨진 캐시는 버리고 다시 추출
    res = {"key": key, "pages": 0, "empty": 0, "rows": [], "error": None}
    try:
        pages = extract_any(pdf)
        res["pages"] = len(pages)
        for no, t in pages:
            if len(t) < 30:
                res["empty"] += 1
                continue
            for piece in split_text(t, chunk, overlap):
                res["rows"].append([no, piece])
    except Exception as e:
        res["error"] = str(e)[:200]
    cp.parent.mkdir(parents=True, exist_ok=True)
    tmp = cp.with_suffix(".tmp")
    tmp.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
    tmp.replace(cp)              # 저장이 끝난 뒤에만 정식 파일로 교체
    return res


# ---------- 임베딩 ----------
def embed(texts, retries=4):
    from openai import OpenAI
    from utils.llm import secret
    client = OpenAI(api_key=secret("OPENAI_API_KEY"))
    for a in range(retries):
        try:
            r = client.embeddings.create(model=EMB_MODEL, input=texts, dimensions=DIMS)
            return np.array([d.embedding for d in r.data], dtype="float32")
        except Exception:
            if a == retries - 1:
                raise
            time.sleep(2 ** a)


def _norm(x):
    return x / (np.linalg.norm(x, axis=1, keepdims=True) + 1e-9)


# ---------- 빌드 ----------
def build(max_cost=3.0, chunk=1200, overlap=150, work=None, log=print):
    import faiss
    try:
        from tqdm.auto import tqdm
    except Exception:
        tqdm = lambda x, **k: x
    work = work or (ROOT.parent / "_drone_work")
    pdfs = sorted([*MANUALS.rglob("*.pdf"), *MANUALS.rglob("*.md")])
    if not pdfs:
        raise RuntimeError("manuals/ 아래에 PDF가 없습니다. 셀 3으로 복사하거나 폴더에 직접 넣으세요.")

    files, fdomains, rows, keys, catalog, errors, scanned = [], [], [], [], {}, [], []
    log(f"PDF {len(pdfs)}개 텍스트 추출 중 (처음 한 번만 오래 걸림)")
    for pdf in tqdm(pdfs):
        dom = pdf.parent.name
        r = _file_chunks(pdf, work, chunk, overlap)
        keys.append(r["key"])
        if r["error"]:
            errors.append((pdf.name, r["error"]))
            continue
        fid = len(files)
        files.append(pdf.name)
        fdomains.append(dom)
        for no, text in r["rows"]:
            rows.append([fid, no, text])
        catalog.setdefault(dom, []).append(
            {"file": pdf.name, "pages": r["pages"], "empty_pages": r["empty"], "chunks": len(r["rows"])})
        if r["pages"] and r["empty"] / r["pages"] > 0.5:
            scanned.append(pdf.name)

    n = len(rows)
    if n == 0:
        raise RuntimeError("추출된 텍스트가 없습니다 (스캔본 PDF만 있는 것 같습니다. OCR이 필요합니다).")
    chars = sum(len(_etext(fdomains[f], files[f], p, t)) for f, p, t in rows)
    tokens = chars / 3
    cost = tokens / 1e6 * PRICE_PER_M
    log(f"청크 {n:,}개, 약 {chars/1e6:.1f}M자, 추정 토큰 {tokens/1e6:.1f}M, 예상 임베딩 비용 약 ${cost:.2f}")
    if cost > max_cost:
        raise RuntimeError(f"예상 비용 ${cost:.2f} 가 한도 ${max_cost} 를 넘어 중단합니다. MAX_COST_USD를 올리거나 PDF를 줄이세요.")

    fp = hashlib.sha1(("|".join(keys) + f"|{chunk}|{overlap}|{DIMS}|{EMB_MODEL}").encode()).hexdigest()[:12]
    SHARD, BATCH = 1280, 64
    vecs = []
    for s in tqdm(range(0, n, SHARD)):
        sp = work / "emb" / f"{fp}_{s // SHARD:05d}.npy"
        if sp.exists():
            vecs.append(np.load(sp))
            continue
        part = []
        for b in range(s, min(s + SHARD, n), BATCH):
            batch = [_etext(fdomains[f], files[f], p, t) for f, p, t in rows[b:min(b + BATCH, s + SHARD, n)]]
            part.append(embed(batch))
        arr = np.vstack(part)
        sp.parent.mkdir(parents=True, exist_ok=True)
        np.save(sp, arr)
        vecs.append(arr)
    x = _norm(np.vstack(vecs)).astype("float32")

    index = faiss.IndexScalarQuantizer(DIMS, faiss.ScalarQuantizer.QT_8bit, faiss.METRIC_INNER_PRODUCT)
    index.train(x)
    index.add(x)

    INDEX.mkdir(parents=True, exist_ok=True)
    nf = save_parts(INDEX, "faiss.bin", faiss.serialize_index(index).tobytes())
    payload = json.dumps({"files": files, "fdomains": fdomains, "rows": rows}, ensure_ascii=False).encode("utf-8")
    nr = save_parts(INDEX, "rows.json.gz", gzip.compress(payload, 6))
    meta = {"model": EMB_MODEL, "dims": DIMS, "chunks": n, "files": len(files),
            "built": datetime.now().isoformat(timespec="seconds")}
    (INDEX / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "manual_catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=1), encoding="utf-8")

    size = sum(p.stat().st_size for p in INDEX.glob("*")) / 1e6
    log(f"✅ 인덱스 저장 완료: {size:.0f}MB (벡터 {nf}조각 + 본문 {nr}조각)")
    if size > 600:
        log("⚠ 인덱스가 600MB를 넘습니다. GitHub/Streamlit Cloud 용량 한도에 가까우니 PDF를 줄이거나 청크를 키우세요.")
    if scanned:
        log(f"⚠ 글자가 거의 추출되지 않은 파일(스캔본 추정, OCR 필요) {len(scanned)}개: {scanned[:10]}")
    if errors:
        log(f"⚠ 읽기 실패 {len(errors)}개: {errors[:5]}")
    return meta


# ---------- 로드 / 검색 ----------
def load(base=None):
    import faiss
    base = base or INDEX
    if not (base / "meta.json").exists():
        return None
    index = faiss.deserialize_index(np.frombuffer(read_parts(base, "faiss.bin"), dtype="uint8"))
    data = json.loads(gzip.decompress(read_parts(base, "rows.json.gz")))
    data["index"] = index
    data["meta"] = json.loads((base / "meta.json").read_text(encoding="utf-8"))
    return data


def domain_hints(query):
    q = query.lower()
    return {d for d, kws in DOMAIN_HINTS.items() if any(k in q for k in kws)}


def search(store, query, k=6):
    q = _norm(embed([query]))
    kk = min(k * 4, store["index"].ntotal)
    scores, ids = store["index"].search(q, kk)
    hints = domain_hints(query)
    best = {}
    for s, i in zip(scores[0], ids[0]):
        if i < 0:
            continue
        fid, page, text = store["rows"][i]
        dom = store["fdomains"][fid]
        sc = float(s) + (0.05 if dom in hints else 0.0)
        key = (fid, page)
        if key not in best or sc > best[key]["score"]:
            best[key] = {"domain": dom, "file": store["files"][fid], "page": page, "text": text, "score": sc}
    return sorted(best.values(), key=lambda h: -h["score"])[:k]
