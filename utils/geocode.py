import requests

# 대략적인 좌표 (비행 전 실제 이륙 지점으로 다시 지정 권장)
PRESETS = {
    "영월": (37.18, 128.46), "화성(시화)": (37.30, 126.74), "판교": (37.40, 127.11),
    "광나루(서울)": (37.55, 127.12), "단양": (36.98, 128.37), "이천": (37.27, 127.43),
    "인제": (38.07, 128.17), "철원": (38.15, 127.31), "태안": (36.75, 126.30),
    "새만금": (35.80, 126.70), "고흥": (34.61, 127.28), "영암": (34.80, 126.70),
    "제주": (33.50, 126.53), "김천": (36.14, 128.11), "안동": (36.57, 128.73),
    "강릉": (37.75, 128.88), "대전": (36.35, 127.38), "부산": (35.18, 129.08),
    "광주": (35.16, 126.85), "수원": (37.26, 127.03),
}
HEADERS = {"User-Agent": "drone-hub/1.0 (https://github.com/drone-engineer/ICT_drone_engineer_hub)"}


def find_preset(query):
    q = query.strip().replace(" ", "")
    for name, (lat, lon) in PRESETS.items():
        if q and (q == name.replace(" ", "") or q in name.replace(" ", "")):
            return name, lat, lon
    return None


def geocode(query):
    """프리셋 우선, 없으면 Nominatim. (이름, 위도, 경도) 또는 None"""
    p = find_preset(query)
    if p:
        return p
    r = requests.get("https://nominatim.openstreetmap.org/search", headers=HEADERS, timeout=10,
                     params={"q": query, "format": "json", "limit": 1,
                             "countrycodes": "kr", "accept-language": "ko"})
    r.raise_for_status()
    js = r.json()
    if not js:
        return None
    return js[0]["display_name"], float(js[0]["lat"]), float(js[0]["lon"])
