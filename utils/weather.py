import math
import time
from datetime import datetime, timedelta, timezone

import requests

from utils.safety_rules import grade_wind, LEGAL_ALT_M

URL = "https://api.open-meteo.com/v1/forecast"
ALTS = [10, 40, 80, 120, 180]
HOURLY = ["wind_speed_10m", "wind_speed_80m", "wind_speed_120m", "wind_speed_180m",
          "wind_gusts_10m", "temperature_2m", "precipitation_probability"]


def interp_40m(v10, v80):
    """10m/80m 풍속으로 40m 풍속 추정 (풍속 멱법칙, 불가하면 선형)"""
    if v10 > 0 and v80 > 0:
        alpha = math.log(v80 / v10) / math.log(80 / 10)
        return v10 * (40 / 10) ** alpha
    return v10 + (v80 - v10) * (40 - 10) / (80 - 10)


def parse(js, now_utc=None):
    """Open-Meteo 응답 → 현재 시각 기준 고도별 풍속/판정 (네트워크 없는 순수 함수)"""
    h = js["hourly"]
    off = js.get("utc_offset_seconds", 0)
    now_utc = now_utc or datetime.now(timezone.utc)
    local = now_utc + timedelta(seconds=off)
    stamp = local.strftime("%Y-%m-%dT%H:00")
    idx = h["time"].index(stamp) if stamp in h["time"] else 0

    def at(name, default=None):
        v = h.get(name, [None])[idx]
        return default if v is None else v

    winds = {10: at("wind_speed_10m", 0.0), 80: at("wind_speed_80m", 0.0),
             120: at("wind_speed_120m", 0.0), 180: at("wind_speed_180m", 0.0)}
    winds[40] = interp_40m(winds[10], winds[80])
    gust, temp, precip = at("wind_gusts_10m"), at("temperature_2m"), at("precipitation_probability")

    rows = []
    for alt in ALTS:
        g = grade_wind(winds[alt], gust=gust, temp=temp, precip=precip)
        note = "보간 추정" if alt == 40 else ""
        if alt > LEGAL_ALT_M:
            note = f"법정 한계 {LEGAL_ALT_M}m 초과(참고용)"
        rows.append({"alt": alt, "wind": winds[alt], "level": g["level"],
                     "icon": g["icon"], "label": g["label"],
                     "reasons": g["reasons"], "note": note})
    return {"time": h["time"][idx], "temp": temp, "precip": precip, "gust": gust, "rows": rows}


def fetch(lat, lon, retries=2):
    params = {"latitude": lat, "longitude": lon, "hourly": ",".join(HOURLY),
              "wind_speed_unit": "ms", "timezone": "auto", "forecast_days": 1}
    last = None
    for _ in range(retries + 1):
        try:
            r = requests.get(URL, params=params, timeout=10)
            r.raise_for_status()
            return parse(r.json())
        except Exception as e:
            last = e
            time.sleep(1)
    raise RuntimeError(f"Open-Meteo 호출 실패: {last}")
