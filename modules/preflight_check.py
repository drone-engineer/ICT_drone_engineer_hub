import streamlit as st

from utils.ui import key

M = "pre"
ITEMS = [
    ("기체", "프레임·암·랜딩기어 체결 상태와 볼트 풀림 확인"),
    ("기체", "프로펠러 크랙·변형·날 끝 손상 없음"),
    ("기체", "프로펠러 장착 방향(CW/CCW)과 고정 너트 확인"),
    ("기체", "모터 고정 상태, 손으로 돌렸을 때 걸림·소음 없음"),
    ("전원", "배터리 셀 전압 밸런스 (셀 간 편차 허용 범위 내)"),
    ("전원", "배터리 충전량과 커넥터·전원선 체결·극성 확인"),
    ("전원", "배터리 외관 팽창·손상·발열 없음"),
    ("센서", "IMU 댐핑(진동 흡수) 상태와 FC 고정 확인"),
    ("센서", "지자기(나침반) 캘리브레이션 및 방향 정상"),
    ("센서", "GPS 위성 수·HDOP 양호, 홈 포인트 설정"),
    ("통신", "페일세이프(링크 두절 시 동작) 설정 확인"),
    ("통신", "MAVLink 텔레메트리 연결 및 패킷 손실률 정상"),
    ("통신", "조종기 링크 품질(RSSI)과 스틱·스위치 동작 확인"),
    ("운용", "비행 모드, ARM 조건, 경고 메시지 없음 확인"),
    ("운용", "비행 구역의 기상(풍속·돌풍)과 공역·승인 여부 확인"),
    ("운용", "이륙 구역 안전 확보 (주변 인원·장애물 없음)"),
]


def _reset():
    for i in range(len(ITEMS)):
        st.session_state[key(M, f"item_{i}")] = False


def render():
    st.header("✅ 비행 전 16대 안전 점검표")
    done = 0
    cat = None
    for i, (c, text) in enumerate(ITEMS):
        if c != cat:
            cat = c
            st.subheader(c)
        if st.checkbox(f"{i+1}. {text}", key=key(M, f"item_{i}")):
            done += 1
    st.progress(done / len(ITEMS), text=f"점검 진행도 {done} / {len(ITEMS)}")
    if done == len(ITEMS):
        st.success("🟢 16개 항목 전수 확인 완료. 이륙 승인 가능 (최종 판단은 조종자 책임)")
    else:
        st.info(f"남은 항목 {len(ITEMS) - done}개")
    st.button("점검표 초기화", key=key(M, "reset"), on_click=_reset)
    st.caption("법정 필수 점검의 전부가 아닙니다. 기체·임무별 추가 점검과 항공안전법 준수는 별도로 확인하세요.")
