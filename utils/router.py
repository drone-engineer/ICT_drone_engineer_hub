COMPARE_HINTS = ["차이", "비교", " vs", "versus", "대비", "장단점", "어느 쪽", "뭐가 좋"]
WEB_HINTS = ["최신", "신제품", "출시", "가격", "얼마", "뉴스", "올해", "latest", "release", "price"]
WIRING_HINTS = ["vcc", "gnd", "쇼트", "단락", "5v", "12v", "역결선", "극성", "전원 모듈", "결선", "배선", "핀맵", "pinout", "wiring"]


def classify(query):
    q = " " + query.lower()
    if any(h in q for h in COMPARE_HINTS):
        return "compare"
    if any(h in q for h in WEB_HINTS):
        return "web"
    return "manual"


def wiring_warning(query):
    q = query.lower()
    return any(h in q for h in WIRING_HINTS)
