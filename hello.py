import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timedelta
import gspread
from google.oauth2.service_account import Credentials
import requests
import json
import re

# --- 🧠 제미나이 AI 다이렉트 통신망 ---
if "GEMINI_API_KEY" in st.secrets:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
elif "gcp" in st.secrets and "GEMINI_API_KEY" in st.secrets["gcp"]:
    GEMINI_API_KEY = st.secrets["gcp"]["GEMINI_API_KEY"]
else:
    GEMINI_API_KEY = ""

HAS_AI = bool(GEMINI_API_KEY)

def ask_gemini(prompt):
    if not HAS_AI:
        raise Exception("API 키가 없습니다.")
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    list_resp = requests.get(list_url)
    target_model = "models/gemini-1.5-flash" 
    if list_resp.status_code == 200:
        for m in list_resp.json().get('models', []):
            name = m.get('name', '')
            if 'generateContent' in m.get('supportedGenerationMethods', []) and 'gemini' in name.lower() and 'vision' not in name.lower():
                target_model = name
                break 
    url = f"https://generativelanguage.googleapis.com/v1beta/{target_model}:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    else:
        raise Exception(f"통신 에러 ({response.status_code})")

# ⭕ 구글 시트 연결 세팅
MY_SHEET_URL = "https://docs.google.com/spreadsheets/d/1N4KGhJf1ta1MOcATsOXcJayTe9ULsNGhL_9u8Rdbo_Q/edit"

st.set_page_config(page_title="Data of the Light", layout="wide")

MY_PASSWORD = "1306"
if "login_success" not in st.session_state: st.session_state.login_success = False
if not st.session_state.login_success:
    st.title("🔒 Workout Report - Login")
    pwd_input = st.text_input("비밀번호", type="password")
    if st.button("로그인"):
        if pwd_input == MY_PASSWORD: st.session_state.login_success = True; st.rerun()
        else: st.error("❌ 비밀번호가 틀렸습니다.")
    st.stop()

@st.cache_resource
def init_connection():
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(dict(st.secrets["gcp"]), scopes=scopes)
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

@st.cache_data(ttl=5)
def get_cached_data(tab_name):
    try:
        if tab_name == "sleep": return sheet_sleep.get_all_values()
        elif tab_name == "workout": return sheet_workout.get_all_values()
        elif tab_name == "diet": return sheet_diet.get_all_values()
    except: return []
    return []

if 'football_drills' not in st.session_state: st.session_state.football_drills = []
if 'cardio_drills' not in st.session_state: st.session_state.cardio_drills = []
if 'weight_sets' not in st.session_state: st.session_state.weight_sets = []

today = datetime.now().strftime("%Y-%m-%d")

# ==========================================
# 🪖 💡 [V11.0 신설] 사이드바 설정 (훈련소 모드 스위치)
# ==========================================
st.sidebar.title("🎖️ 라이브 링크 설정")
bootcamp_mode = st.sidebar.toggle("🪖 31사단 훈련소 모드 활성화", value=False)
if bootcamp_mode:
    st.sidebar.success("훈련소 모드가 작동 중입니다. 입력 방식이 원클릭 패키지로 단순화됩니다.")

st.title("⚡ Data of the Light")

tab_body, tab_workout, tab_diet, tab_report = st.tabs([
    "📊 신체 데이터", "🏋️ 운동 데이터", "🥗 식단 데이터", "📈 데이터/리포팅 센터"
])

def extract_number(val):
    match = re.search(r'(\d+(?:\.\d+)?)', str(val))
    return float(match.group(1)) if match else 0.0

def parse_meal_cell(cell_value):
    if not cell_value: return "", "⏳ 미등록"
    if " | AI 분석:" in cell_value:
        parts = cell_value.split(" | AI 분석:")
        return parts[0].strip(), parts[1].strip()
    return cell_value, "⏳ 분석 대기 중"

def save_single_meal(col_idx, text_val):
    all_d_current = sheet_diet.get_all_values()
    row_idx = None
    for idx, r in enumerate(all_d_current):
        if r[0] == today:
            row_idx = idx + 1
            break
    if row_idx: sheet_diet.update_cell(row_idx, col_idx, text_val)
    else:
        new_row = [today, "0kcal", "", "", "", "", ""]
        new_row[col_idx - 1] = text_val
        sheet_diet.append_row(new_row)
    st.cache_data.clear()

# ------------------------------------------
# 📊 TAB 1: 신체 데이터
# ------------------------------------------
with tab_body:
    st.header("📊 수면 과학 및 신체 데이터 대시보드")
    
    # 💡 [V11.0 업데이트] 공복 체중 입력창 배치
    m_weight = st.number_input("⚖️ 오늘의 공복 체중 (kg) *하루 1번만 입력하면 운동 탭 자동 연동", min_value=0.0, max_value=150.0, value=77.5, step=0.1)
    # 다른 탭에서도 쓸 수 있게 세션에 고정
    st.session_state["master_weight"] = m_weight

    col_m2, col_m3 = st.columns(2)
    with col_m2: bed_time = st.time_input("🛏️ 불 끄고 누운 시간", value=time(23, 30))
    with col_m3: wake_time = st.time_input("☀️ 실제 일어난 시간", value=time(7, 30))
        
    dt_bed = datetime.combine(date.today(), bed_time)
    dt_wake = datetime.combine(date.today(), wake_time)
    if dt_wake < dt_bed: dt_wake += timedelta(days=1)
    total_bed_mins = (dt_wake - dt_bed).total_seconds() / 60
    calc_sleep_hours = round(max(0, (total_bed_mins - 20) * 0.9) / 60, 1)
    
    st.success(f"🤖 **AI 수면 연산:** 실제 회복 딥슬립 시간은 [{calc_sleep_hours}시간] 입니다.")

    col_m4, col_m5 = st.columns(2)
    with col_m4: m_quality = st.slider("⭐ 체감 수면의 질 (1-10)", 1, 10, 7)
    with col_m5: m_cond = st.slider("🏃 기상 직후 신체 컨디션 스코어", 1, 10, 7)
        
    with st.expander("📏 [선택 사항] 공복 신체 정밀 사이즈 측정"):
        c_size1, c_size2, c_size3, c_size4 = st.columns(4)
        with c_size1: chest_sz = st.number_input("가슴 (cm)", value=0.0, step=0.1)
        with c_size2: arm_sz = st.number_input("팔 (cm)", value=0.0, step=0.1)
        with c_size3: waist_sz = st.number_input("허리 (cm)", value=0.0, step=0.1)
        with c_size4: thigh_sz = st.number_input("허벅지 (cm)", value=0.0, step=0.1)

    if st.button("🚀 수면 및 신체 사이즈 데이터 저장"):
        sleep_row = [today, f"{m_weight}kg", f"{calc_sleep_hours}시간", f"{m_quality}점", f"{m_cond}점",
            f"{chest_sz}cm" if chest_sz > 0 else "-", f"{arm_sz}cm" if arm_sz > 0 else "-",
            f"{waist_sz}cm" if waist_sz > 0 else "-", f"{thigh_sz}cm" if thigh_sz > 0 else "-"]
        sheet_sleep.append_row(sleep_row)
        st.cache_data.clear() 
        st.success("데이터가 성공적으로 저장되었습니다!")
        st.rerun()
        
    all_s_for_body = get_cached_data("sleep")
    
    st.write("---")
    st.subheader("📈 엘리트 바디 컴포지션 멀티 대시보드")
    
    if len(all_s_for_body) > 1:
        df_s_body = pd.DataFrame(all_s_for_body[1:], columns=all_s_for_body[0])
        df_s_body['날짜'] = pd.to_datetime(df_s_body['날짜'], errors='coerce')
        df_s_body = df_s_body.dropna(subset=['날짜'])
        df_s_body['체중'] = df_s_body['공복 체중'].apply(extract_number)
        df_s_body = df_s_body[df_s_body['체중'] > 0]
        
        if len(df_s_body) >= 1:
            df_s_body['추정 골격근량(kg)'] = round(df_s_body['체중'] * 0.49, 1)
            df_s_body['추정 체지방률(%)'] = round(11.5 + (df_s_body['체중'] - 77.5) * 0.7, 1)
            df_s_body['추정 체지방량(kg)'] = round(df_s_body['체중'] * (df_s_body['추정 체지방률(%)'] / 100), 1)
            
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.markdown("##### ⚖️ 공복 체중 (kg)")
                st.line_chart(df_s_body.sort_values('날짜').set_index('날짜')['체중'], color="#1f77b4")
            with col_g2:
                st.markdown("##### 💪 추정 골격근량 (kg)")
                st.line_chart(df_s_body.sort_values('날짜').set_index('날짜')['추정 골격근량(kg)'], color="#2ca02c")
            
            st.markdown("##### 🩸 체지방 트렌드 (량/률)")
            st.line_chart(df_s_body.sort_values('날짜').set_index('날짜')[['추정 체지방량(kg)', '추정 체지방률(%)']], color=["#ff7f0e", "#d62728"])
            
            col_g3, col_g4 = st.columns(2)
            with col_g3:
                st.markdown("##### 💤 수면 시간 트렌드 (h)")
                df_s_body['수면시간(h)'] = df_s_body['수면 시간'].apply(extract_number)
                st.line_chart(df_s_body.sort_values('날짜').set_index('날짜')['수면시간(h)'], color="#9467bd")
            with col_g4:
                st.markdown("##### 📏 신체 정밀 사이즈 (cm)")
                df_s_body['가슴'] = df_s_body.iloc[:, 5].apply(extract_number)
                df_s_body['팔'] = df_s_body.iloc[:, 6].apply(extract_number)
                df_s_body['허리'] = df_s_body.iloc[:, 7].apply(extract_number)
                df_s_body['허벅지'] = df_s_body.iloc[:, 8].apply(extract_number)
                df_size = df_s_body[['날짜', '가슴', '팔', '허리', '허벅지']].replace(0, pd.NA).dropna(how='all', subset=['가슴', '팔', '허리', '허벅지'])
                if not df_size.empty:
                    st.line_chart(df_size.sort_values('날짜').set_index('날짜'))
    else:
        st.info("신체 데이터베이스가 비어 있습니다.")

# ------------------------------------------
# 🏋️ TAB 2: 운동 데이터
# ------------------------------------------
with tab_workout:
    st.header("🧠 오늘의 트레이닝 세션 로깅")
    
    # 💡 [V11.0 업데이트] 아침에 적은 몸무게가 있으면 자동으로 로드, 없으면 기본값 세팅
    saved_weight = st.session_state.get("master_weight", 77.5)
    m_weight_display = st.number_input("⚖️ 오늘의 공복 체중 (kg) *신체 탭 연동 완료", min_value=0.0, max_value=150.0, value=saved_weight, step=0.1)

    def save_workout(data_dict):
        cols = ["날짜", "공복 체중", "훈련 볼륨", "평균 심박", "최대 심박", "심박 회복량(HRR)", "상세 훈련 내용 (SOP 및 실전 역학)", "생리학적 분석 및 영양/비고"]
        sheet_workout.append_row([str(data_dict.get(c, "")) for c in cols])
        st.cache_data.clear()

    # 💡 [V11.0 업데이트] 훈련소 모드 활성화 시 분할 일과 간편 선택 UI 팝업
    if bootcamp_mode:
        st.subheader("🪖 제31사단 훈련소 일과 원클릭 등록")
        bc_time = st.radio("⏰ 세션 구분", ["오전/오후 메인 일과", "야간/점호 전 틈새 기량유지"])
        
        if bc_time == "오전/오후 메인 일과":
            bc_routine = st.selectbox("📋 오늘 진행한 메인 군사 훈련", ["일반 병영 일과(제식/정신전력 등)", "체력 측정 및 사단 알통 뜀걸음", "영외 전투 훈련(각개전투/사격/화생방)", "20km 주간/야간 완전군장 행군"])
            if st.button("💾 훈련소 일과 즉시 저장"):
                save_workout({"날짜": today, "공복 체중": f"{m_weight_display}kg", "훈련 볼륨": "훈련소일과", "평균 심박": 0, "최대 심박": 0, "심박 회복량(HRR)": "-", "상세 훈련 내용 (SOP 및 실전 역학)": f"[훈련소 메일일과] {bc_routine}", "생리학적 분석 및 영양/비고": "RPE:자동연산"})
                st.success("오늘의 군사 훈련 부하가 성공적으로 입력되었습니다!"); st.rerun()
        
        else:
            st.info("취침 전 관물대를 활용한 침상 틈새 기량유지 맨몸 루틴입니다. 수행한 종목을 체크하세요.")
            c_pull = st.checkbox("관물대 턱걸이 (Pull-up)")
            c_push = st.checkbox("침상 푸쉬업/딥스 (Push-up)")
            c_squat = st.checkbox("맨몸 스쿼트/런지 (Squat/Lunge)")
            c_core = st.checkbox("플랭크/레그레이즈 (Core)")
            
            if st.button("💾 틈새 맨몸운동 저장"):
                done_list = []
                if c_pull: done_list.append("턱걸이")
                if c_push: done_list.append("푸쉬업")
                if c_squat: done_list.append("스쿼트/런지")
                if c_core: done_list.append("코어앤플랭크")
                routine_str = ", ".join(done_list) if done_list else "맨몸 운동 미실시"
                save_workout({"날짜": today, "공복 체중": f"{m_weight_display}kg", "훈련 볼륨": "틈새운동", "평균 심박": 0, "최대 심박": 0, "심박 회복량(HRR)": "-", "상세 훈련 내용 (SOP 및 실전 역학)": f"[훈련소 침상운동] {routine_str}", "생리학적 분석 및 영양/비고": "근손실방어"})
                st.success("틈새 맨몸 자극 완료!"); st.rerun()

    else:
        # 기존 모드 (사회용 엘리트 훈련 UI)
        time_of_day = st.radio("⏰ 시간대", ("☀️ 오전", "🌤️ 오후", "🌙 저녁/야간"), horizontal=True)
        workout_type = st.selectbox("👇 세션 종류", ("개인 축구 훈련", "유산소/조깅", "실전 경기", "웨이트 트레이닝", "휴식(Recovery)"))
        st.write("---")

        if workout_type == "개인 축구 훈련":
            location = st.text_input("📍 장소 입력", "전주 용와초등학교 잔디구장")
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            with c1: drill = st.selectbox("📋 종목", ["40/20 하프라인 인터벌", "25/20 penalty box 인터벌", "15/15 매스템포런", "경기템포 훈련", "기본기", "슈팅", "직접 입력"])
            with c2: reps = st.number_input("횟수", min_value=1, step=1)
            with c3: sets = st.number_input("세트", min_value=1, step=1)
            with c4: rest = st.text_input("휴식", "2분")
            if st.button("➕ 루틴 추가"): st.session_state.football_drills.append(f"{drill}({reps}회/{sets}세트/휴식{rest})")
            if st.session_state.football_drills:
                st.info("👉 " + " ➡️ ".join(st.session_state.football_drills))
                if st.button("🗑️ 지우기"): st.session_state.football_drills = []; st.rerun()
            col1, col2, col3, col4 = st.columns(4)
            with col1: dist = st.number_input("🏃 이동 거리(km)", min_value=0.0, step=0.1)
            with col2: h_avg = st.number_input("❤️ 평균 심박", min_value=0, step=1)
            with col3: h_max = st.number_input("🔥 최대 심박", min_value=0, step=1)
            with col4: hrr = st.text_input("📉 HRR")
            if st.button("💾 신규 운동 저장"):
                save_workout({"날짜": today, "공복 체중": f"{m_weight_display}kg", "훈련 볼륨": f"{dist}km", "평균 심박": h_avg, "최대 심박": h_max, "심박 회복량(HRR)": hrr, "상세 훈련 내용 (SOP 및 실전 역학)": f"[{time_of_day}] 장소:{location} | 루틴:{' ➡️ '.join(st.session_state.football_drills)}", "생리학적 분석 및 영양/비고": "-"})
                st.session_state.football_drills = []; st.success("저장 완료!"); st.rerun()

        elif workout_type == "유산소/조깅":
            c_drill = st.selectbox("📋 종목", ["러닝", "턱걸이", "딥스", "턱걸이 + 오르막 컴플렉스", "오르막길 스프린트", "15/15 매스템포런", "기타"])
            if c_drill == "러닝":
                col_r1, col_r2, col_r3 = st.columns(3)
                with col_r1: run_dist = st.number_input("🏃 거리 (km)", min_value=0.0, step=0.1, value=3.2)
                with col_r2: run_min = st.number_input("⏱️ 시간 (분)", min_value=0, step=1, value=12)
                with col_r3: run_sec = st.number_input("⏱️ 시간 (초)", min_value=0, max_value=59, step=1, value=50)
                if st.button("🤖 AI 페이스 분석 및 세션 추가"):
                    total_mins = run_min + (run_sec / 60)
                    if run_dist > 0 and total_mins > 0:
                        pace_min = int(total_mins // run_dist)
                        pace_sec = int((total_mins / run_dist - pace_min) * 60)
                        pace_str = f"{pace_min}분 {pace_sec}초/km"
                        if HAS_AI:
                            with st.spinner("기록 분석 중..."):
                                prompt = f"엘리트 축구 선수가 {run_dist}km를 {run_min}분 {run_sec}초에 돌파(페이스: {pace_str}). 프로 경기체력 향상 측면에서 강도 분석 및 칭찬/팩폭 코멘트 짧게 해줘."
                                ai_eval = ask_gemini(prompt)
                                st.success(f"🎯 평균 페이스: **{pace_str}**")
                                st.markdown(f"> **AI 코치 멘트:** {ai_eval}")
                                st.session_state.cardio_drills.append(f"러닝({run_dist}km, {run_min}분{run_sec}초, 페이스: {pace_str})")
                    else: st.error("거리와 시간을 적어주세요.")
            else:
                c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                with c1:
                    if c_drill == "오르막길 스프린트": c_drill = f"오르막 스프린트({st.slider('강도(%)',50,100,100,5)}%)"
                    elif c_drill == "턱걸이 + 오르막 컴플렉스": c_drill = f"턱걸이({st.number_input('개수',1,5,1)}개)+오르막({st.slider('강도(%)',50,100,100,5)}%)"
                with c2: c_dist = st.text_input("거리/시간", "5km")
                with c3: c_reps = st.number_input("반복", 1, step=1)
                with c4: c_sets = st.number_input("세트", 1, step=1)
                if st.button("➕ 세션 추가"): st.session_state.cardio_drills.append(f"{c_drill}({c_dist} x {c_reps}회 / {c_sets}세트)")

            if st.session_state.cardio_drills:
                st.warning("👉 " + " ➡️ ".join(st.session_state.cardio_drills))
                if st.button("🗑️ 지우기"): st.session_state.cardio_drills = []; st.rerun()
            col1, col2, col3, col4 = st.columns(4)
            with col1: dist = st.number_input("🏃 총 누적 거리(km)", 0.0, step=0.1)
            with col2: h_avg = st.number_input("❤️ 평균 심박", 0)
            with col3: h_max = st.number_input("🔥 최대 심박", 0)
            with col4: hrr = st.text_input("📉 HRR")
            if st.button("💾 신규 운동 저장"):
                save_workout({"날짜": today, "공복 체중": f"{m_weight_display}kg", "훈련 볼륨": f"{dist}km", "평균 심박": h_avg, "최대 심박": h_max, "심박 회복량(HRR)": hrr, "상세 훈련 내용 (SOP 및 실전 역학)": f"[{time_of_day}] 시퀀스:{' ➡️ '.join(st.session_state.cardio_drills)}", "생리학적 분석 및 영양/비고": "-"})
                st.session_state.cardio_drills = []; st.success("저장 완료!"); st.rerun()

        elif workout_type == "실전 경기":
            match_type = st.selectbox("📍 경기", ["11대11 정규", "풋살", "미니게임"])
            dist = st.number_input("거리(km)", 0.0, step=0.1)
            memo = st.text_area("📝 리뷰")
            if st.button("💾 신규 운동 저장"): save_workout({"날짜": today, "공복 체중": f"{m_weight_display}kg", "훈련 볼륨": f"{dist}km", "평균 심박": 0, "최대 심박": 0, "심박 회복량(HRR)": "-", "상세 훈련 내용 (SOP 및 실전 역학)": f"[{time_of_day}] {match_type} | 리뷰: {memo}", "생리학적 분석 및 영양/비고": "-"}); st.success("저장 완료!"); st.rerun()

        elif workout_type == "웨이트 트레이닝":
            ex_name = st.text_input("운동 이름")
            weight = st.number_input("무게(kg)", 0.0, step=2.5)
            reps = st.number_input("횟수", 0, step=1)
            sets = st.number_input("세트", 1, step=1)
            if st.button("➕ 추가"): st.session_state.weight_sets.append({"운동명": ex_name, "무게": weight, "횟수": reps, "세트수": sets})
            if st.session_state.weight_sets:
                st.dataframe(pd.DataFrame(st.session_state.weight_sets))
                if st.button("💾 신규 운동 저장"):
                    w_list = [f"{s['운동명']}({s['무게']}kg x{s['횟수']}회 {s['세트수']}세트)" for s in st.session_state.weight_sets]
                    save_workout({"날짜": today, "공복 체중": f"{m_weight_display}kg", "훈련 볼륨": "-", "평균 심박": 0, "최대 심박": 0, "심박 회복량(HRR)": "-", "상세 훈련 내용 (SOP 및 실전 역학)": f"[{time_of_day}] " + ", ".join(w_list), "생리학적 분석 및 영양/비고": "-"})
                    st.session_state.weight_sets = []; st.success("저장 완료!"); st.rerun()

        elif workout_type == "휴식(Recovery)":
            rec_act = st.multiselect("📋 활동", ["완전 휴식", "회복 걷기", "리커버리 조깅", "스트레칭", "폼롤러", "사우나"])
            rec_dist = st.number_input("거리(km)", 0.0, step=0.1)
            memo = st.text_area("📝 메모")
            if st.button("💾 신규 운동 저장"): save_workout({"날짜": today, "공복 체중": f"{m_weight_display}kg", "훈련 볼륨": f"회복{rec_dist}km", "평균 심박": 0, "최대 심박": 0, "심박 회복량(HRR)": "-", "상세 훈련 내용 (SOP 및 실전 역학)": f"[휴식] 활동:{','.join(rec_act)} | 메모:{memo}", "생리학적 분석 및 영양/비고": "-"}); st.success("저장 완료!"); st.rerun()

    all_w = get_cached_data("workout")
    st.write("---")
    st.subheader("🛠️ 운동 데이터베이스 (실시간 수정 가능)")
    if len(all_w) > 1:
        df_workout = pd.DataFrame(all_w[1:], columns=all_w[0])
        edited_workout = st.data_editor(df_workout, num_rows="dynamic", use_container_width=True, key="edit_workout")
        if st.button("🔄 수정한 운동 데이터를 구글 시트에 덮어쓰기"):
            sheet_workout.clear()
            sheet_workout.append_rows([edited_workout.columns.tolist()] + edited_workout.fillna("").astype(str).values.tolist())
            st.cache_data.clear()
            st.success("운동 로그 원본이 완벽하게 수정되었습니다!"); st.rerun()

# ------------------------------------------
# 🥗 TAB 3: 식단 데이터
# ------------------------------------------
with tab_diet:
    st.header("🥗 영양 섭취 및 실시간 매크로 코칭")
    
    all_d_current = get_cached_data("diet")
    raw_b, raw_l, raw_d, raw_s, raw_n = "", "", "", "", ""
    cal_b, cal_l, cal_d, cal_s, cal_n = "⏳ 미등록", "⏳ 미등록", "⏳ 미등록", "⏳ 미등록", "⏳ 미등록"
    
    if len(all_d_current) > 1:
        for r in all_d_current[1:]:
            if r[0] == today:
                if len(r) > 2: raw_b, cal_b = parse_meal_cell(r[2])
                if len(r) > 3: raw_l, cal_l = parse_meal_cell(r[3])
                if len(r) > 4: raw_d, cal_d = parse_meal_cell(r[4])
                if len(r) > 5: raw_s, cal_s = parse_meal_cell(r[5])
                if len(r) > 6: raw_n, cal_n = parse_meal_cell(r[6])
                break

    # 💡 [V11.0 업데이트] 훈련소 모드 활성화 시 식단 원클릭 배급식 입력 패키지 가동
    if bootcamp_mode:
        st.subheader("🪖 사단 훈련소 표준 배급식 등록")
        bc_meal_select = st.radio("🍴 해당 식사 선택", ["아침 병영식 정량", "점심 병영식 정량", "저녁 병영식 정량", "PX 군것질/증식"])
        if st.button("💾 훈련소 식사 원클릭 등록"):
            with st.spinner("표준 짬밥 영양소 연산 중..."):
                col_map = {"아침 병영식 정량": 3, "점심 병영식 정량": 4, "저녁 병영식 정량": 5, "PX 군것질/증식": 6}
                col_idx = col_map[bc_meal_select]
                final_val = f"{bc_meal_select} 섭취 완료 | AI 분석: 950kcal"
                save_single_meal(col_idx, final_val)
                st.success("훈련소 급식 저장 성공!"); st.rerun()
    else:
        # 일반 모드 (사회용 디테일 식단 등록)
        meals_config = [
            {"name": "🌅 아침 식단", "raw": raw_b, "cal": cal_b, "col_idx": 3},
            {"name": "☀️ 점심 식단", "raw": raw_l, "cal": cal_l, "col_idx": 4},
            {"name": "🌙 저녁 식단", "raw": raw_d, "cal": cal_d, "col_idx": 5},
            {"name": "🥤 간식/보충제", "raw": raw_s, "cal": cal_s, "col_idx": 6},
            {"name": "🌌 야식", "raw": raw_n, "cal": cal_n, "col_idx": 7}
        ]
        current_inputs = {}
        for m in meals_config:
            c_input, c_metric, c_btn = st.columns([3, 1, 1])
            with c_input: current_inputs[m["name"]] = st.text_area(f"{m['name']}", value=m["raw"], height=70, key=f"input_{m['col_idx']}")
            with c_metric: st.metric(label="예상 칼로리", value=m["cal"])
            with c_btn:
                st.write("") 
                if st.button(f"💾 등록", key=f"btn_{m['col_idx']}"):
                    meal_txt = current_inputs[m["name"]].strip()
                    if meal_txt:
                        with st.spinner("AI 칼로리 연산 중..."):
                            cal_prompt = f"'{meal_txt}' 이 식단의 총 칼로리만 숫자로 예측해서 '000kcal' 형식으로 답변해줘. 설명 금지."
                            try: kcal_res = ask_gemini(cal_prompt).strip()
                            except: kcal_res = "계산오류"
                            save_single_meal(m["col_idx"], f"{meal_txt} | AI 분석: {kcal_res}")
                            st.success("저장 완료!"); st.rerun()

    st.write("---")
    if st.button("🧠 현재까지의 영양소 크로스-매칭 및 다음 식사 추천"):
        if HAS_AI:
            all_w_for_diet = get_cached_data("workout")
            today_w_str = " | ".join([f"내용:{r[6]}" for r in all_w_for_diet[1:] if r[0] == today]) if len(all_w_for_diet)>1 else "기록없음"
            with st.spinner("분석 중..."):
                prompt = f"축구선수 오늘 운동량:[{today_w_str}], 아침:[{raw_b}], 점심:[{raw_l}], 저녁:[{raw_d}]. 훈련량 대비 남은 식사에서 채워야할 탄단지(g)와 구체적 메뉴를 추천해줘. 아직 비어있는 칸은 안 먹은 게 아니라 시간이 안 된 거니까 호들갑/경고 금지."
                st.markdown(ask_gemini(prompt))

    all_d = get_cached_data("diet")
    st.write("---")
    st.subheader("🛠️ 식단 데이터베이스 (실시간 수정 가능)")
    if len(all_d) > 1:
        df_diet = pd.DataFrame(all_d[1:], columns=all_d[0])
        edited_diet = st.data_editor(df_diet, num_rows="dynamic", use_container_width=True, key="edit_diet")
        if st.button("🔄 수정한 식단 데이터를 구글 시트에 덮어쓰기"):
            sheet_diet.clear()
            sheet_diet.append_rows([edited_diet.columns.tolist()] + edited_diet.fillna("").astype(str).values.tolist())
            st.cache_data.clear()
            st.success("식단 로그 원본이 완벽하게 수정되었습니다!"); st.rerun()

# ------------------------------------------
# 📈 TAB 4: 데이터/리포팅 센터 (💡 7/14/30 심층 거시 분석기 탑재)
# ------------------------------------------
with tab_report:
    st.header("📈 퍼포먼스 상관관계 및 AI 거시적 처방 센터")
    
    st.subheader("📊 최근 7일 회복 vs 컨디션 역학 그래프")
    all_w = get_cached_data("workout")
    all_s = get_cached_data("sleep")
    all_d = get_cached_data("diet")
    
    if len(all_s) > 2:
        df_s = pd.DataFrame(all_s[1:], columns=all_s[0])
        df_s['날짜'] = pd.to_datetime(df_s['날짜'], errors='coerce')
        df_s = df_s.dropna(subset=['날짜'])
        df_s['컨디션스코어'] = df_s['신체 컨디션'].apply(extract_number)
        df_s['수면시간(h)'] = df_s['수면 시간'].apply(extract_number)
        df_recent7 = df_s.sort_values('날짜').tail(7).set_index('날짜')
        st.bar_chart(df_recent7[['수면시간(h)', '컨디션스코어']], color=["#2ca02c", "#1f77b4"])
    else:
        st.info("상관관계 그래프를 분석하려면 최소 2일 이상의 데이터 누적이 필요합니다.")

    st.write("---")
    # 💡 [V11.0 업데이트] 사용자가 원하는 단위(7일/14일/30일)를 라디오 버튼으로 완벽 맵핑
    report_type = st.radio(
        "📋 분석을 진행할 거시적 사이클 선택", 
        ["⚡ 실시간 당일 브리핑 (Real-time)", "🔍 7일 주간 피지컬 총평 (Weekly)", "📊 14일 하프-매크로 사이클 평가 (14-Days)", "🏆 30일 월간 퍼포먼스 마스터 레포트 (Monthly)"], 
        horizontal=True
    )
    
    if st.button(f"🤖 S-Tier AI 분석 보고서 발행"):
        if HAS_AI:
            with st.spinner("구글 클라우드 시트 전 범위 데이터 딥-러닝 스캔 중..."):
                try:
                    # 라디오 선택에 맞춰 타겟 날짜 설정
                    day_map = {"Real-time": 1, "7일": 7, "14일": 14, "30일": 30}
                    selected_key = [k for k in day_map.keys() if k in report_type][0]
                    target_days = day_map[selected_key]
                    
                    recent_w = all_w[-target_days:] if len(all_w) > target_days else all_w[1:]
                    recent_s = all_s[-target_days:] if len(all_s) > target_days else all_s[1:]
                    recent_d = all_d[-target_days:] if len(all_d) > target_days else all_d[1:]
                    
                    w_context = " | ".join([f"{r[0]}(내용:{r[6]})" for r in recent_w if len(r) > 6])
                    s_context = " | ".join([f"{r[0]}(수면:{r[2]}, 컨디션:{r[4]}, 체중:{r[1]})" for r in recent_s if len(r) > 4])
                    d_context = " | ".join([f"{r[0]}(총량:{r[1]})" for r in recent_d if len(r) > 1])
                    
                    # 💡 기간에 맞춰 완전히 지능형으로 변경되는 매크로 프롬프트 엔진
                    prompt = f"""
                    너는 프로 축구팀의 수석 스포츠 사이언티스트이자 수석 피지컬 코어야. 
                    곽연혁 엘리트 축구 선수의 [{selected_key}]간 누적 데이터야.
                    - 운동 부하: {w_context}
                    - 수면 및 컨디션: {s_context}
                    - 식단 에너지: {d_context}
                    
                    이 데이터를 기반으로 다음 포맷에 맞춰 날카롭고 구체적인 거시 리포트를 작성해줘:
                    ### 🎯 1. [{selected_key}]간 신체/체성분 변화 트렌드 분석
                    (체중 변동 및 골격근/체지방 추이를 수학적, 생리학적으로 매칭해서 분석)
                    
                    ### 🧬 2. 수면/영양이 실제 운동 퍼포먼스에 미친 인과관계 스캔
                    (예: "몇 일차에 영양이 부족했을 때 페이스나 피로도가 어떻게 꼬였는지" 누적 데이터를 근거로 구체적으로 대조 및 분석)
                    
                    ### 🚀 3. 다음 매크로 사이클을 위한 맞춤형 피지컬/드릴 보완 솔루션
                    (훈련소 모드가 켜져 있다면 병영 생활 내 근손실 방어 전략 위주, 일반 모드라면 전술/심폐 고도화 위주 처방)
                    """
                    
                    report_text = ask_gemini(prompt)
                    st.success(f"✨ S-Tier [{selected_key}] 심층 분석 처방전이 발행되었습니다.")
                    st.markdown(report_text)
                except Exception as e: st.error(f"리포팅 에러: {e}")
        else:
            st.error("⚠️ AI API 설정이 필요합니다.")

st.write("---")
if st.button("🔒 안전하게 로그아웃"):
    st.session_state.login_success = False
    st.rerun()