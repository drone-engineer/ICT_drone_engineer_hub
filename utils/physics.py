# 드론 공학 공식 모음 (UI 없음). 단위: 중량 g, 전류 A, 전력 W, 에너지 Wh, 시간 min


def required_thrust(empty_g, payload_g, n_motors, twr=2.0):
    auw = empty_g + payload_g
    total = auw * twr
    return {"auw": auw, "total_thrust": total,
            "per_motor_max": total / n_motors,
            "per_motor_hover": auw / n_motors,
            "hover_throttle_ratio": 1.0 / twr}


def twr(n_motors, thrust_per_motor_g, auw_g):
    return n_motors * thrust_per_motor_g / auw_g


def twr_grade(value):
    if value < 1.0:
        return "🔴 이륙 불가 (추력비 1 미만)"
    if value < 1.8:
        return "🟡 추력 여유 부족 (1.8 미만)"
    if value <= 2.5:
        return "🟢 일반 상용/임무용 최적 (1.8-2.5)"
    return "🔵 고기동/레이싱/특수 목적 (2.5 초과)"


def i_max(capacity_mah, c_rate):
    """배터리 최대 방전 허용 전류 (A)"""
    return capacity_mah / 1000 * c_rate


def hover_time_current(capacity_mah, dod, n_motors, i_hover_a):
    """전류 기반 호버링 시간 (분)"""
    return capacity_mah / 1000 * dod / (n_motors * i_hover_a) * 60


def battery_wh(voltage_v, capacity_mah, dod=1.0):
    return voltage_v * capacity_mah / 1000 * dod


def hover_time_efficiency(auw_g, energy_wh, eff_gw):
    """효율(g/W) 기반 호버링 시간 (분). 사용 가능 에너지(Wh)를 넘긴다."""
    power = auw_g / eff_gw
    return energy_wh / power * 60


def reverse_design(base_g, battery_g, wh_per_kg, dod, target_min, n_motors):
    """목표 체공시간 달성에 필요한 효율/전력 역산 (배터리 무게 포함 실질 AUW)"""
    total = base_g + battery_g
    energy = battery_g / 1000 * wh_per_kg * dod
    power_total = energy / (target_min / 60)
    return {"auw": total, "energy_wh": energy, "power_total": power_total,
            "power_per_motor": power_total / n_motors,
            "required_eff": total / power_total}


def interp_curve(points, thrust_g):
    """추력-스로틀-전력 시험 곡선 선형 보간. 범위 밖이면 None.
    points: [{'throttle':%, 'thrust_g':g, 'power_w':W}, ...]"""
    pts = sorted(points, key=lambda p: p["thrust_g"])
    if not pts or thrust_g < pts[0]["thrust_g"] or thrust_g > pts[-1]["thrust_g"]:
        return None
    for a, b in zip(pts, pts[1:]):
        if a["thrust_g"] <= thrust_g <= b["thrust_g"]:
            span = b["thrust_g"] - a["thrust_g"]
            f = 0 if span == 0 else (thrust_g - a["thrust_g"]) / span
            thr = a["throttle"] + f * (b["throttle"] - a["throttle"])
            pw = a["power_w"] + f * (b["power_w"] - a["power_w"])
            return {"throttle": thr, "power_w": pw, "eff_gw": thrust_g / pw}
    return None
