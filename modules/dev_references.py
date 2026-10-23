import streamlit as st

from utils.ui import key

M = "ref"
REFS = {
    "비행 소프트웨어": [
        ("PX4 Autopilot 문서", "https://docs.px4.io/", "PX4 공식 사용자·개발자 가이드, 파라미터 레퍼런스"),
        ("ArduPilot 문서", "https://ardupilot.org/copter/", "ArduCopter 설정·튜닝·파라미터"),
        ("QGroundControl 가이드", "https://docs.qgroundcontrol.com/", "지상국 설정, 캘리브레이션"),
    ],
    "통신·미들웨어": [
        ("MAVLink 개발자 가이드", "https://mavlink.io/en/", "메시지·프로토콜 정의"),
        ("ROS 2 문서", "https://docs.ros.org/", "Humble 등 배포판별 문서"),
        ("Micro XRCE-DDS", "https://micro-xrce-dds.docs.eprosima.com/", "PX4-ROS 2 브리지 에이전트/클라이언트"),
    ],
    "컴퓨터비전·온보드": [
        ("NVIDIA Jetson 문서", "https://developer.nvidia.com/embedded/jetson-developer-kits", "Jetson 개발 키트 자료"),
        ("TensorRT 문서", "https://docs.nvidia.com/deeplearning/tensorrt/", "엔진 변환·최적화"),
        ("Ultralytics YOLO 문서", "https://docs.ultralytics.com/", "YOLO 학습·내보내기"),
    ],
    "국내 규정·공역": [
        ("드론원스톱 민원서비스", "https://drone.onestop.go.kr/", "비행 승인·촬영 허가 신청"),
        ("브이월드(V-World)", "https://www.vworld.kr/", "국토 공간정보 오픈플랫폼"),
        ("국가법령정보센터", "https://www.law.go.kr/", "항공안전법 조문 확인"),
    ],
}


def render():
    st.header("📚 개발자 필수 레퍼런스")
    st.caption("주소는 제가 확인하지 못한 시점에 바뀌었을 수 있으니, 열리지 않으면 검색으로 공식 페이지를 찾으세요.")
    q = st.text_input("검색", key=key(M, "q")).strip().lower()
    for group, items in REFS.items():
        shown = [it for it in items if not q or q in (it[0] + it[2] + group).lower()]
        if not shown:
            continue
        st.subheader(group)
        for i, (name, url, desc) in enumerate(shown):
            c1, c2 = st.columns([1, 3])
            with c1:
                st.link_button(name, url, use_container_width=True)
            with c2:
                st.write(desc)
