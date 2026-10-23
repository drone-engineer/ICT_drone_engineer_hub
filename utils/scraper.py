import ipaddress
import re
import socket
from datetime import datetime
from io import StringIO
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests

UA = "Mozilla/5.0 (compatible; drone-hub/1.0)"
MAX_BYTES = 2_000_000


def check_url(url):
    u = urlparse(url)
    if u.scheme not in ("http", "https") or not u.hostname:
        raise ValueError("http/https 주소만 사용할 수 있습니다.")
    for info in socket.getaddrinfo(u.hostname, None):
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise ValueError("내부망/예약 주소는 차단됩니다.")
    return url


def fetch_html(url, hops=3):
    for _ in range(hops + 1):
        check_url(url)
        r = requests.get(url, headers={"User-Agent": UA}, timeout=15, stream=True, allow_redirects=False)
        if r.status_code in (301, 302, 303, 307, 308):
            url = urljoin(url, r.headers.get("Location", ""))
            r.close()
            continue
        r.raise_for_status()
        buf = b""
        for chunk in r.iter_content(65536):
            buf += chunk
            if len(buf) > MAX_BYTES:
                break
        try:
            return url, buf.decode("utf-8")
        except UnicodeDecodeError:
            return url, buf.decode(r.encoding or "latin-1", errors="replace")
    raise ValueError("리다이렉트가 너무 많습니다.")


def page_title(html):
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def extract_tables(html, limit=20):
    try:
        tables = pd.read_html(StringIO(html))
    except ValueError:
        return []
    return [t for t in tables if t.shape[0] >= 2 and t.shape[1] >= 2][:limit]


def df_to_md(df):
    df = df.copy()
    df.columns = [" ".join(str(x) for x in c if "Unnamed" not in str(x)) if isinstance(c, tuple) else str(c)
                  for c in df.columns]
    df = df.fillna("").astype(str)

    def esc(s):
        return s.replace("|", "/").replace("\n", " ").strip()

    head = "| " + " | ".join(esc(c) or "-" for c in df.columns) + " |"
    sep = "|" + "|".join(["---"] * len(df.columns)) + "|"
    rows = ["| " + " | ".join(esc(v) for v in r) + " |" for r in df.values.tolist()]
    return "\n".join([head, sep, *rows])


def slug(url):
    u = urlparse(url)
    s = re.sub(r"[^a-zA-Z0-9]+", "_", (u.hostname or "") + u.path).strip("_")
    return s[:60] or "page"


def build_markdown(url, title, tables):
    parts = [f"# {title or url}", "", f"- 출처: {url}",
             f"- 수집일: {datetime.now().strftime('%Y-%m-%d')}", ""]
    for i, t in enumerate(tables, 1):
        parts += [f"## 표 {i}", "", df_to_md(t), ""]
    return "\n".join(parts)
