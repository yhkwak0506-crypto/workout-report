import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import json

# ⭕ 구글 시트 고유 ID만 깔끔하게 따서 완벽하게 매칭했습니다!
MY_SHEET_URL = "https://docs.google.com/spreadsheets/d/1N4KGhJf1ta1M0CATs0XcJayTe9ULsNGhL_9u8Rdbo_Q/edit"

# 브라우저 탭 이름 설정
st.set_page_config(page_title="Workout Report", layout="wide")

# ==========================================
# 🔒 보안 로그인 시스템
# ==========================================
MY_PASSWORD = "1234"

if "login_success" not in st.session_state:
    st.session_state.login_success = False

if not st.session_state.login_success:
    st.title("🔒 Workout Report - Login")
    st.info("접근 권한이 필요합니다. 비밀번호를 입력해 주세요.")
    pwd_input = st.text_input("비밀번호", type="password")
    
    if st.button("로그인"):
        if pwd_input == MY_PASSWORD:
            st.session_state.login_success = True
            st.rerun()
        else:
            st.error("❌ 비밀번호가 틀렸습니다.")
    st.stop()

# ==========================================
# ☁️ 구글 시트 무선 연결 세팅
# ==========================================
@st.cache_resource
def init_connection():
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    try:
        secret_info = dict(st.secrets["gcp"])
        creds = Credentials.from_service_account_info(secret_info, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error("🚨 스트림릿 금고(Secrets) 세팅을 확인해 주세요!")
        st.stop()

gc = init_connection()

try:
    doc = gc.open_by_url(MY_SHEET_URL)
    # 🔥 [치트키] 탭 이름이 뭐든 상관없이, 무조건 구글 시트의 '첫 번째 탭'을 강제로 가져옵니다!
    sheet = doc.get_worksheet(0)
except Exception as e:
    st.error("🚨 구글 시트 주소가 올바르지 않거나 탭을 로드할 수 없습니다.")
    st.stop()

# ==========================================
# 📊 Workout Report 메인 화면
# ==========================================
st.title("📊 Workout Report")

if 'football_drills' not in st.session_state: st.session_state.football_drills = []
if 'weight_sets' not in st.session_state: st.session_state.weight_sets = []

# --- 0. 공복 체중 및 웰니스 입력 ---
st.subheader("🧠 오늘의 공복 체중 및 웰니스")
col_w1, col_w2, col_w3 = st.columns(3)
with col_w1: weight_today = st.number_input("⚖️ 공복 체중 (kg)", min_value=0.0, max_value=150.0, value=77.5, step=0.1)
with col_w2: pre_condition = st.slider("🏃 운동 전 컨디션 (1:최악 ~ 10:최상)", 1, 10, 5)
with col_w3: post_condition = st.slider("🥵 운동 후 체감 피로도 (1:완전탈진 ~ 10:매우상쾌)", 1, 10, 5)

time_of_day = st.radio("⏰ 훈련 시간대", ("☀️ 오전 훈련", "🌤️ 오후 훈련", "🌙 저녁/야간 훈련"), horizontal=True)
st.write("---")

# --- 1. 훈련 종류 선택 ---
workout_type = st.selectbox("👇 메인 훈련 종류 선택", ("개인 축구 훈련", "유산소/조깅", "실전 경기", "웨이트 트레이닝"))
st.write("---")

today = datetime.now().strftime("%Y-%m-%d")

def save_to_master_sheet(row_dict):
    columns_order = [
        "날짜", "공복 체중", "훈련 볼륨", "평균 심박", "최대 심박", 
        "심박 회복량(HRR)", "상세 훈련 내용 (SOP 및 실전 역학)", "생리학적 분석 및 영양/비고"
    ]
    row_values = [str(row_dict.get(col, "")) for col in columns_order]
    sheet.append_row(row_values)

# --- 개인 축구 훈련 ---
if workout_type == "개인 축구 훈련":
    st.subheader("⚽ 개인 축구 훈련 디테일")
    location = st.selectbox("📍 훈련 장소", ["전주 용와초등학교 잔디구장", "천변 풋살장", "직접 입력"])
    if location == "직접 입력": location = st.text_input("장소 입력")
    
    st.write("📝 **세부 훈련 루틴 담기**")
    c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
    with c1:
        drill_opts = ["40/20 풀코트 인터벌", "15/5 드리블+슈팅 믹스", "기본기(리프팅/컨트롤)", "슈팅 연습", "직접 입력"]
        drill = st.selectbox("📋 훈련 종목", drill_opts)
        if drill == "직접 입력": drill = st.text_input("훈련 내용을 입력하세요")
    with c2: reps = st.number_input("반복 횟수", min_value=1, step=1, key='f_rep')
    with c3: sets = st.number_input("세트 수", min_value=1, step=1, key='f_set')
    with c4: rest = st.text_input("휴식(예: 2분)", key='f_rest')
    
    if st.button("➕ 순서 추가"):
        st.session_state.football_drills.append(f"{drill}({reps}회/{sets}세트/휴식{rest})")
            
    if st.session_state.football_drills:
        st.info("👉 **현재 루틴:** " + " ➡️ ".join(st.session_state.football_drills))
        if st.button("🗑️ 순서 비우기"): st.session_state.football_drills = []; st.rerun()
            
    col1, col2, col3, col4 = st.columns(4)
    with col1: distance = st.number_input("🏃 뛴 거리 (km)", min_value=0.0, step=0.1)
    with col2: hr_avg = st.number_input("❤️ 평균 심박수", min_value=0, step=1)
    with col3: hr_max = st.number_input("🔥 최대 심박수", min_value=0, step=1)
    with col4: hr_recovery = st.text_input("📉 심박 회복량(HRR)")
    
    if st.button("💾 구글 시트로 저장하기"):
        sop_text = f"[{time_of_day}] 장소: {location} | 루틴: {' ➡️ '.join(st.session_state.football_drills)}"
        analysis_text = f"웰니스(전:{pre_condition}/후:{post_condition}) | 필드 기동 세션 완료."
        data = {
            "날짜": today, "공복 체중": f"{weight_today}kg", "훈련 볼륨": f"{distance}km",
            "평균 심박": hr_avg, "최대 심박": hr_max, "심박 회복량(HRR)": hr_recovery,
            "상세 훈련 내용 (SOP 및 실전 역학)": sop_text, "생리학적 분석 및 영양/비고": analysis_text
        }
        save_to_master_sheet(data)
        st.session_state.football_drills = []
        st.success("구글 시트에 성공적으로 저장되었습니다!")
        st.rerun()

# --- 유산소/조깅 ---
elif workout_type == "유산소/조깅":
    st.subheader("🏃 유산소 및 조깅 기록")
    col1, col2 = st.columns(2)
    with col1:
        location = st.selectbox("📍 코스", ["전주천변 (평지 위주)", "천변 오르막 코스", "트랙", "직접 입력"])
        if location == "직접 입력": location = st.text_input("코스 직접 입력")
        distance = st.number_input("🏃 거리 (km)", min_value=0.0, step=0.1)
        pace = st.text_input("⏱️ 페이스 (예: 4:51)")
        cadence = st.number_input("👣 케이던스 (spm)", min_value=0, step=1)
    with col2:
        hr_avg = st.number_input("❤️ 평균 심박수", min_value=0, step=1)
        hr_max = st.number_input("🔥 최대 심박수", min_value=0, step=1)
        hr_recovery = st.text_input("📉 심박 회복량(HRR)")
        
    if st.button("💾 유산소 기록 저장하기"):
        sop_text = f"[{time_of_day}] 코스: {location} | 페이스: {pace} | 케이던스: {cadence}spm"
        analysis_text = f"웰니스(전:{pre_condition}/후:{post_condition}) | 심폐 조율 세션 완료."
        data = {
            "날짜": today, "공복 체중": f"{weight_today}kg", "훈련 볼륨": f"{distance}km",
            "평균 심박": hr_avg, "최대 심박": hr_max, "심박 회복량(HRR)": hr_recovery,
            "상세 훈련 내용 (SOP 및 실전 역학)": sop_text, "생리학적 분석 및 영양/비고": analysis_text
        }
        save_to_master_sheet(data)
        st.success("구글 시트에 성공적으로 저장되었습니다!")
        st.rerun()

# --- 실전 경기 ---
elif workout_type == "실전 경기":
    st.subheader("🏟️ 실전 경기 기록")
    col1, col2 = st.columns(2)
    with col1:
        match_type = st.selectbox("📍 경기 형태", ["11대11 정규구장", "풋살 (5vs5 ~ 6vs6)", "미니게임"])
        location = st.text_input("경기장 이름")
        distance = st.number_input("🏃 뛴 거리 (km)", min_value=0.0, step=0.1)
    with col2:
        hr_avg = st.number_input("❤️ 평균 심박수", min_value=0, step=1)
        hr_max = st.number_input("🔥 최대 심박수", min_value=0, step=1)
        hr_recovery = st.text_input("📉 심박 회복량(HRR)")
        
    memo = st.text_area("📝 경기 리뷰 (SOP 분석)")
    
    if st.button("💾 실전 경기 저장하기"):
        sop_text = f"[{time_of_day}] {match_type} 경기 | 장소: {location} | 리뷰: {memo}"
        analysis_text = f"웰니스(전:{pre_condition}/후:{post_condition}) | 실전 매치 데이터 반영."
        data = {
            "날짜": today, "공복 체중": f"{weight_today}kg", "훈련 볼륨": f"{distance}km",
            "평균 심박": hr_avg, "최대 심박": hr_max, "심박 회복량(HRR)": hr_recovery,
            "상세 훈련 내용 (SOP 및 실전 역학)": sop_text, "생리학적 분석 및 영양/비고": analysis_text
        }
        save_to_master_sheet(data)
        st.success("구글 시트에 성공적으로 저장되었습니다!")
        st.rerun()

# --- 웨이트 트레이닝 ---
elif workout_type == "웨이트 트레이닝":
    st.subheader("🏋️ 웨이트 세션 기록")
    ex_name = st.text_input("운동 이름")
    c1, c2, c3 = st.columns(3)
    with c1: weight = st.number_input("무게 (kg)", min_value=0.0, step=2.5)
    with c2: reps = st.number_input("반복 횟수", min_value=0, step=1)
    with c3: sets = st.number_input("세트 수", min_value=1, step=1)
    if st.button("➕ 세트 추가"):
        st.session_state.weight_sets.append({"운동명": ex_name, "무게": weight, "횟수": reps, "세트수": sets})

    if st.session_state.weight_sets:
        st.dataframe(pd.DataFrame(st.session_state.weight_sets))
        if st.button("💾 웨이트 세션 전체 저장하기"):
            weight_list = [f"{s['운동명']}({s['무게']}kg x {s['횟수']}회 {s['세트수']}세트)" for s in st.session_state.weight_sets]
            sop_text = f"[{time_of_day}] " + ", ".join(weight_list)
            data = {
                "날짜": today, "공복 체중": f"{weight_today}kg", "훈련 볼륨": f"{len(st.session_state.weight_sets)}개 종목",
                "평균 심박": 0, "최대 심박": 0, "심박 회복량(HRR)": "-",
                "상세 훈련 내용 (SOP 및 실전 역학)": sop_text, "생리학적 분석 및 영양/비고": f"웰니스(전:{pre_condition}/후:{post_condition}) | 스트랭스 완료."
            }
            save_to_master_sheet(data)
            st.session_state.weight_sets = [] 
            st.success("구글 시트에 성공적으로 저장되었습니다!")
            st.rerun()

# ==========================================
# 📊 실시간 구글 시트 라이브 데이터베이스
# ==========================================
st.write("---")
st.header("📊 구글 시트 연동 라이브 데이터베이스")

all_data = sheet.get_all_values()
if len(all_data) > 1:
    df = pd.DataFrame(all_data[1:], columns=all_data[0]).fillna("")
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    if st.button("🔄 표 변경사항 최종 반영"):
        sheet.clear()
        sheet.update([edited_df.columns.values.tolist()] + edited_df.values.tolist())
        st.success("구글 시트 원본이 업데이트되었습니다!")
        st.rerun()
else:
    st.info("아직 구글 시트에 데이터가 없습니다!")

if st.button("🔒 안전하게 로그아웃"):
    st.session_state.login_success = False
    st.rerun()