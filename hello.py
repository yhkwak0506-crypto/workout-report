import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timedelta
import gspread
from google.oauth2.service_account import Credentials
import os

# --- 🧠 제미나이 AI 두뇌 연결 세팅 (V9.1 스마트 키 파인더 및 에러 스캐너 탑재) ---
try:
    import google.generativeai as genai
    
    # 1. 기본 위치에서 키 찾기
    if "GEMINI_API_KEY" in st.secrets:
        GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    # 2. 혹시 [gcp] 구역 안으로 빨려 들어갔는지 확인 (스마트 파인더)
    elif "gcp" in st.secrets and "GEMINI_API_KEY" in st.secrets["gcp"]:
        GEMINI_API_KEY = st.secrets["gcp"]["GEMINI_API_KEY"]
    else:
        GEMINI_API_KEY = ""

    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        HAS_AI = True
        AI_ERROR = ""
    else:
        HAS_AI = False
        AI_ERROR = "스트림릿 금고(Secrets)에서 API 키를 찾지 못했습니다."
except Exception as e:
    HAS_AI = False
    AI_ERROR = f"AI 모듈 설치 또는 로딩 에러: {str(e)}"

# ⭕ 구글 시트 주소
MY_SHEET_URL = "https://docs.google.com/spreadsheets/d/1N4KGhJf1ta1MOcATsOXcJayTe9ULsNGhL_9u8Rdbo_Q/edit"

st.set_page_config(page_title="S-Tier Performance AMS v9.1", layout="wide")

# ==========================================
# 🔒 보안 로그인
# ==========================================
MY_PASSWORD = "1306"
if "login_success" not in st.session_state: st.session_state.login_success = False
if not st.session_state.login_success:
    st.title("🔒 Workout Report - Login")
    pwd_input = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        if pwd_input == MY_PASSWORD: st.session_state.login_success = True; st.rerun()
        else: st.error("❌ 비밀번호가 틀렸습니다.")
    st.stop()

# ==========================================
# ☁️ 구글 시트 연결
# ==========================================
@st.cache_resource
def init_connection():
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    secret_info = dict(st.secrets["gcp"])
    creds = Credentials.from_service_account_info(secret_info, scopes=scopes)
    return gspread.authorize(creds)

try:
    gc = init_connection()
    doc = gc.open_by_url(MY_SHEET_URL)
    try: sheet_workout = doc.worksheet("운동로그")
    except: sheet_workout = doc.get_worksheet(0)
    try: sheet_diet = doc.worksheet("식단로그")
    except: sheet_diet = doc.add_worksheet(title="식단로그", rows="1000", cols="7")
    try: sheet_sleep = doc.worksheet("수면/컨디션로그")
    except: sheet_sleep = doc.add_worksheet(title="수면/컨디션로그", rows="1000", cols="10")
except Exception as e:
    st.error(f"🚨 구글 시트 연동 실패: {e}")
    st.stop()

if 'football_drills' not in st.session_state: st.session_state.football_drills = []
if 'cardio_drills' not in st.session_state: st.session_state.cardio_drills = []
if 'weight_sets' not in st.session_state: st.session_state.weight_sets = []

today = datetime.now().strftime("%Y-%m-%d")

st.title("⚡ S-Tier AI Coach System (v9.1)")

# 🚨 AI 상태 진단 경고창
if not HAS_AI:
    st.warning(f"⚠️ 제미나이 AI 연결 대기 중... (에러 원인: {AI_ERROR})")

tab_morning, tab_workout, tab_diet, tab_report = st.tabs([
    "🌅 모닝 바이오메트릭스", "🏋️ 운동 대시보드", "🥗 AI 식단 관리", "📊 AI 수석 코치 레포트"
])

# ------------------------------------------
# 🌅 TAB 1: 모닝 바이오메트릭스
# ------------------------------------------
with tab_morning:
    st.header("🌅 과학적 수면 & 컨디션 로그")
    st.info("수면 잠복기(20분)와 수면 효율(90%)을 적용해 실제 딥슬립 시간을 AI가 자동 연산합니다.")
    
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        m_weight = st.