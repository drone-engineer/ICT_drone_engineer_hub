# 비행 안전 판정 단일 소스. 기준 변경은 이 파일에서만 한다.
WIND_CAUTION = 7.0      # m/s 이상: 주의
WIND_DANGER = 10.0      # m/s 이상: 금지
GUST_CAUTION = 10.0
GUST_DANGER = 13.0
TEMP_MIN_C = 0.0        # 이하: 금지 (LiPo 전압강하)
PRECIP_DANGER = 40      # % 이상: 금지
LEGAL_ALT_M = 150       # 지표면 기준 법정 한계 고도
KP_CAUTION = 4.0
KP_DANGER = 5.0

LEVELS = {0: ("🟢", "비행 안전"), 1: ("🟡", "비행 주의"), 2: ("🔴", "비행 금지 / 위험")}


def grade_wind(wind, gust=None, temp=None, precip=None):
    """반환: {'level': 0|1|2, 'icon':..., 'label':..., 'reasons': [...]}"""
    level, reasons = 0, []

    def bump(lv, msg):
        nonlocal level
        level = max(level, lv)
        reasons.append(msg)

    if wind >= WIND_DANGER:
        bump(2, f"풍속 {wind:.1f} m/s (기준 {WIND_DANGER} 이상)")
    elif wind >= WIND_CAUTION:
        bump(1, f"풍속 {wind:.1f} m/s (기준 {WIND_CAUTION} 이상)")
    if gust is not None:
        if gust >= GUST_DANGER:
            bump(2, f"돌풍 {gust:.1f} m/s (기준 {GUST_DANGER} 이상)")
        elif gust >= GUST_CAUTION:
            bump(1, f"돌풍 {gust:.1f} m/s (기준 {GUST_CAUTION} 이상)")
    if temp is not None and temp <= TEMP_MIN_C:
        bump(2, f"기온 {temp:.1f}℃ (LiPo 급격 전압강하)")
    if precip is not None and precip >= PRECIP_DANGER:
        bump(2, f"강수확률 {precip:.0f}% (쇼트 위험)")
    icon, label = LEVELS[level]
    return {"level": level, "icon": icon, "label": label, "reasons": reasons}


def grade_kp(kp):
    if kp >= KP_DANGER:
        return {"level": 2, "icon": "🔴", "label": "GPS 멀티패스/수신 불량 경고"}
    if kp >= KP_CAUTION:
        return {"level": 1, "icon": "🟡", "label": "지자기 주의"}
    return {"level": 0, "icon": "🟢", "label": "지자기 양호"}
