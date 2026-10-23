import base64
import hashlib
from urllib.parse import quote

import requests


def put_file(rel_path, data, message, token, repo, branch="main"):
    """repo: 'user/name'. 같은 내용이면 'same', 새로 올리면 'ok' 반환."""
    url = f"https://api.github.com/repos/{repo}/contents/{quote(rel_path, safe='/')}"
    h = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    r = requests.get(url, headers=h, params={"ref": branch}, timeout=20)
    sha = r.json().get("sha") if r.status_code == 200 else None
    if sha == hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest():
        return "same"
    body = {"message": message, "branch": branch, "content": base64.b64encode(data).decode()}
    if sha:
        body["sha"] = sha
    p = requests.put(url, headers=h, json=body, timeout=30)
    if p.status_code not in (200, 201):
        raise RuntimeError(f"GitHub 업로드 실패 ({p.status_code}): {p.json().get('message')}")
    return "ok"
