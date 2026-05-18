import streamlit as st
from datetime import datetime
import db_service as db
import ui_tabs

def init_session_state():
    if "bootcamp_mode" not in st.session_state:
        st.session_state.bootcamp_mode = False
    if "football_drills" not in st.session_state:
        st.session_state.football_drills = []
    if "cardio_drills" not in st.session_state:
        st.session_state.cardio_drills = []
    if "weight_sets" not in st.session_state:
        st.session_state.weight_sets = []
    if "master_weight" not in st.session_state:
        st.session_state.master_weight = 77.5

def main():
    st.set_page_config(page_title="Data of the light", page_icon="⚽", layout="wide")
    init_session_state()
    
    st.sidebar.title("⚙️ 설정 및 모드")
    bootcamp_mode = st.sidebar.checkbox("🪖 31사단 훈련소 모드 활성화", value=st.session_state.bootcamp_mode)
    st.session_state.bootcamp_mode = bootcamp_mode
    
    today_date = st.sidebar.date_input("📅 날짜 선택", datetime.today()).strftime('%Y-%m-%d')
    
    if bootcamp_mode:
        st.title("🪖 제31사단 기량유지 데이터 볼트")
        st.caption("인터넷 제한 환경 및 훈련소 일과 속에서도 콤팩트하게 신체 및 훈련 데이터를 잠그는 특수 보관소")
    else:
        # 연혁님이 지정하신 타이틀 복구
        st.title("⚽ Data of the light")
        st.caption("2027년 북유럽 1~2부 리그 진출을 위한 곽연혁 선수의 순수 피지컬/영양/수면 데이터베이스")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 신체&수면 과학", 
        "🧠 트레이닝 세션", 
        "🥗 초고속 영양 로깅", 
        "📋 제미나이 프롬프트 센터"
    ])
    
    with tab1:
        ui_tabs.render_body_tab(today_date)
    with tab2:
        ui_tabs.render_workout_tab(today_date, bootcamp_mode)
    with tab3:
        ui_tabs.render_diet_tab(today_date, bootcamp_mode)
    with tab4:
        ui_tabs.render_report_tab()

if __name__ == "__main__":
    main()
