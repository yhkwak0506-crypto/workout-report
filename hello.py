import streamlit as st
from datetime import datetime
import ui_tabs

st.set_page_config(page_title="Data of the Light", layout="wide")

# ==========================================
# 🔒 보안 로그인 및 초기화
# ==========================================
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "1306") 
if "login_success" not in st.session_state: st.session_state.login_success = False

if not st.session_state.login_success:
    st.title("🔒 Workout Report - Login")
    pwd_input = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        if pwd_input == APP_PASSWORD: st.session_state.login_success = True; st.rerun()
        else: st.error("❌ 비밀번호가 틀렸습니다.")
    st.stop()

# 상태 관리 초기화
if 'football_drills' not in st.session_state: st.session_state.football_drills = []
if 'cardio_drills' not in st.session_state: st.session_state.cardio_drills = []
if 'weight_sets' not in st.session_state: st.session_state.weight_sets = []

today = datetime.now().strftime("%Y-%m-%d")

# ==========================================
# 🪖 사이드바 & 탭 구성
# ==========================================
st.sidebar.title("🎖️ 라이브 링크 설정")
bootcamp_mode = st.sidebar.toggle("🪖 31사단 훈련소 모드 활성화", value=False)
if bootcamp_mode: st.sidebar.success("훈련소 모드가 작동 중입니다.")

st.title("⚡ Data of the Light")

tab_body, tab_workout, tab_diet, tab_report = st.tabs([
    "📊 신체 데이터", "🏋️ 운동 데이터", "🥗 식단 데이터", "📈 데이터/리포팅 센터"
])

# ui_tabs.py에서 렌더링 함수들을 호출
with tab_body:
    ui_tabs.render_body_tab(today)

with tab_workout:
    ui_tabs.render_workout_tab(today, bootcamp_mode)

with tab_diet:
    ui_tabs.render_diet_tab(today, bootcamp_mode)

with tab_report:
    ui_tabs.render_report_tab()

st.write("---")
if st.button("🔒 안전하게 로그아웃"):
    st.session_state.login_success = False
    st.rerun()