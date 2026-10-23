import math

# (이름, 위도, 경도, 반경km) - 개략 참고값. 실제 비행은 드론원스톱/V-World 확인 필수.
P_ZONES = [
    ("P-73 (서울 도심)", 37.55, 126.99, 8.0),
    ("고리 원전", 35.32, 129.29, 3.7), ("새울 원전", 35.39, 129.32, 3.7),
    ("월성 원전", 35.71, 129.48, 3.7), ("한빛 원전", 35.41, 126.42, 3.7),
    ("한울 원전", 37.09, 129.38, 3.7), ("한국원자력연구원(대전)", 36.43, 127.37, 3.7),
]
R_ZONES = [
    ("R-75 (수도권 북부 접경)", 37.95, 127.00, 15.0),
    ("R-100 (포천 훈련장)", 37.95, 127.35, 8.0),
    ("R-120 (서북도서)", 37.95, 124.70, 20.0),
    ("R-130 (안흥시험장)", 36.67, 126.33, 10.0),
]
CTR_KM = 9.3
AIRPORTS = [
    ("인천", 37.469, 126.451), ("김포", 37.558, 126.791), ("제주", 33.511, 126.493),
    ("김해", 35.179, 128.938), ("대구", 35.894, 128.659), ("청주", 36.717, 127.499),
    ("광주", 35.126, 126.809), ("양양", 38.061, 128.669), ("울산", 35.593, 129.352),
    ("여수", 34.842, 127.617), ("포항", 35.988, 129.420), ("사천", 35.088, 128.070),
    ("군산", 35.904, 126.616), ("원주", 37.438, 127.960), ("무안", 34.991, 126.383),
]
DISCLAIMER = "개략 참고용 위치/반경입니다. 실제 비행 전 드론원스톱·V-World에서 반드시 확인하세요."


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def _all():
    for n, la, lo, r in P_ZONES:
        yield "P", n, la, lo, r
    for n, la, lo, r in R_ZONES:
        yield "R", n, la, lo, r
    for n, la, lo in AIRPORTS:
        yield "CTR", f"{n}공항 관제권", la, lo, CTR_KM


def inside_zones(lat, lon):
    """현재 위치가 포함된 구역 목록 [(종류, 이름, 거리km)]"""
    hits = []
    for kind, name, la, lo, r in _all():
        d = haversine_km(lat, lon, la, lo)
        if d <= r:
            hits.append((kind, name, d))
    return hits


def build_map(lat, lon):
    import folium
    m = folium.Map(location=[lat, lon], zoom_start=9, tiles="OpenStreetMap")
    colors = {"P": "#DC2626", "R": "#F59E0B", "CTR": "#2563EB"}
    for kind, name, la, lo, r in _all():
        folium.Circle([la, lo], radius=r * 1000, color=colors[kind], weight=2,
                      fill=True, fill_opacity=0.15, tooltip=f"[{kind}] {name} (약 {r}km)").add_to(m)
    folium.Marker([lat, lon], tooltip="현재 위치", icon=folium.Icon(color="green")).add_to(m)
    return m
