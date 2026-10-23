import requests

URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"


def parse_kp(js):
    """배열형/딕셔너리형 응답 모두 처리. (시각, Kp) 반환"""
    if not js:
        raise ValueError("빈 응답")
    last = js[-1]
    if isinstance(last, dict):
        kp = last.get("Kp", last.get("kp_index", last.get("kp")))
        return last.get("time_tag"), float(kp)
    return last[0], float(last[1])


def fetch_kp():
    r = requests.get(URL, timeout=10)
    r.raise_for_status()
    return parse_kp(r.json())
