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
# 📊 TAB 1: 신체 데이터 (💡 5개 그래프 완벽 분할)
# ------------------------------------------
with tab_body:
    st.header("📊 수면 과학 및 신체 데이터 대시보드")
    
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
        sleep_row = [today, "-", f"{calc_sleep_hours}시간", f"{m_quality}점", f"{m_cond}점",
            f"{chest_sz}cm" if chest_sz > 0 else "-", f"{arm_sz}cm" if arm_sz > 0 else "-",
            f"{waist_sz}cm" if waist_sz > 0 else "-", f"{thigh_sz}cm" if thigh_sz > 0 else "-"]
        sheet_sleep.append_row(sleep_row)
        st.cache_data.clear() 
        st.success("데이터가 성공적으로 저장되었습니다!")
        st.rerun()
        
    all_w_for_body = get_cached_data("workout")
    all_s_for_body = get_cached_data("sleep")
    
    st.write("---")
    st.subheader("📈 엘리트 바디 컴포지션 멀티 대시보드")
    
    if len(all_w_for_body) > 1 and len(all_s_for_body) > 1:
        # 데이터 정제
        df_w_body = pd.DataFrame(all_w_for_body[1:], columns=all_w_for_body[0])
        df_w_body['날짜'] = pd.to_datetime(df_w_body['날짜'], errors='coerce')
        df_w_body = df_w_body.dropna(subset=['날짜'])
        df_w_body['체중'] = df_w_body['공복 체중'].apply(extract_number)
        df_w_body = df_w_body[df_w_body['체중'] > 0]
        
        df_s_body = pd.DataFrame(all_s_for_body[1:], columns=all_s_for_body[0])
        df_s_body['날짜'] = pd.to_datetime(df_s_body['날짜'], errors='coerce')
        df_s_body = df_s_body.dropna(subset=['날짜'])
        
        if len(df_w_body) >= 1:
            df_w_body['추정 골격근량(kg)'] = round(df_w_body['체중'] * 0.49, 1)
            df_w_body['추정 체지방률(%)'] = round(11.5 + (df_w_body['체중'] - 77.5) * 0.7, 1)
            df_w_body['추정 체지방량(kg)'] = round(df_w_body['체중'] * (df_w_body['추정 체지방률(%)'] / 100), 1)
            
            # 그래프 1 & 2: 체중과 근육량 (나란히 배치)
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                st.markdown("##### ⚖️ 공복 체중 (kg)")
                st.line_chart(df_w_body.sort_values('날짜').set_index('날짜')['체중'], color="#1f77b4")
            with col_g2:
                st.markdown("##### 💪 추정 골격근량 (kg)")
                st.line_chart(df_w_body.sort_values('날짜').set_index('날짜')['추정 골격근량(kg)'], color="#2ca02c")
            
            # 그래프 3: 체지방 (량/률)
            st.markdown("##### 🩸 체지방 트렌드 (량/률)")
            st.line_chart(df_w_body.sort_values('날짜').set_index('날짜')[['추정 체지방량(kg)', '추정 체지방률(%)']], color=["#ff7f0e", "#d62728"])
            
            # 그래프 4 & 5: 수면과 신체 사이즈
            col_g3, col_g4 = st.columns(2)
            with col_g3:
                st.markdown("##### 💤 수면 시간 트렌드 (h)")
                df_s_body['수면시간(h)'] = df_s_body.iloc[:, 2].apply(extract_number)
                st.line_chart(df_s_body.sort_values('날짜').set_index('날짜')['수면시간(h)'], color="#9467bd")
            with col_g4:
                st.markdown("##### 📏 신체 정밀 사이즈 (cm)")
                df_s_body['가슴'] = df_s_body.iloc[:, 5].apply(extract_number)
                df_s_body['팔'] = df_s_body.iloc[:, 6].apply(extract_number)
                df_s_body['허리'] = df_s_body.iloc[:, 7].apply(extract_number)
                df_s_body['허벅지'] = df_s_body.iloc[:, 8].apply(extract_number)
                # 0인 값(미입력)은 제거하고 표시
                df_size = df_s_body[['날짜', '가슴', '팔', '허리', '허벅지']].replace(0, pd.NA).dropna(how='all', subset=['가슴', '팔', '허리', '허벅지'])
                if not df_size.empty:
                    st.line_chart(df_size.sort_values('날짜').set_index('날짜'))
                else:
                    st.info("입력된 사이즈 데이터가 없습니다.")
        else:
            st.info("체중 데이터를 분석하려면 운동 데이터 탭에서 공복 체중을 저장해 주세요.")

# ------------------------------------------
# 🏋️ TAB 2: 운동 데이터 (💡 러닝 페이스 스캐너 도입)
# ------------------------------------------
with tab_workout:
    st.header("🧠 오늘의 트레이닝 세션 로깅")
    
    m_weight = st.number_input("⚖️ 오늘의 공복 체중 입력 (kg) *신체 그래프 자동 연동", min_value=0.0, max_value=150.0, value=77.5, step=0.1)
    
    time_of_day = st.radio("⏰ 시간대", ("☀️ 오전", "🌤️ 오후", "🌙 저녁/야간"), horizontal=True)
    workout_type = st.selectbox("👇 세션 종류", ("개인 축구 훈련", "유산소/조깅", "실전 경기", "웨이트 트레이닝", "휴식(Recovery)"))
    st.write("---")

    def save_workout(data_dict):
        cols = ["날짜", "공복 체중", "훈련 볼륨", "평균 심박", "최대 심박", "심박 회복량(HRR)", "상세 훈련 내용 (SOP 및 실전 역학)", "생리학적 분석 및 영양/비고"]
        sheet_workout.append_row([str(data_dict.get(c, "")) for c in cols])
        st.cache_data.clear()

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
            save_workout({"날짜": today, "공복 체중": f"{m_weight}kg", "훈련 볼륨": f"{dist}km", "평균 심박": h_avg, "최대 심박": h_max, "심박 회복량(HRR)": hrr, "상세 훈련 내용 (SOP 및 실전 역학)": f"[{time_of_day}] 장소:{location} | 루틴:{' ➡️ '.join(st.session_state.football_drills)}", "생리학적 분석 및 영양/비고": "-"})
            st.session_state.football_drills = []; st.success("저장 완료!"); st.rerun()

    elif workout_type == "유산소/조깅":
        # 💡 [V10.5 업데이트] 러닝 메뉴 추가 및 페이스 스캐너 로직
        c_drill = st.selectbox("📋 종목", ["러닝", "턱걸이", "딥스", "턱걸이 + 오르막 컴플렉스", "오르막길 스프린트", "15/15 매스템포런", "기타"])
        
        if c_drill == "러닝":
            st.info("거리와 시간을 입력하시면 AI가 엘리트 축구 선수 기준에 맞춰 페이스 강도를 평가합니다.")
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
                        with st.spinner("엘리트 축구 선수 기준으로 기록을 분석 중입니다..."):
                            prompt = f"""
                            엘리트 축구 선수가 러닝 훈련을 진행했어. 
                            - 기록: {run_dist}km를 {run_min}분 {run_sec}초에 돌파. (평균 페이스: {pace_str})
                            이 기록이 프로 축구 선수의 심폐지구력/경기 체력 향상 측면에서 어느 정도의 강도인지, 그리고 기록이 우수한지 짧고 명확하게 팩트 폭행 및 칭찬으로 평가해줘.
                            """
                            try:
                                ai_eval = ask_gemini(prompt)
                                st.success(f"🎯 계산된 평균 페이스: **{pace_str}**")
                                st.markdown(f"> **AI 수석 코치 코멘트:** {ai_eval}")
                                st.session_state.cardio_drills.append(f"러닝({run_dist}km, {run_min}분{run_sec}초, 페이스: {pace_str})")
                            except Exception as e:
                                st.error(f"분석 오류: {e}")
                    else:
                        st.warning("API 키가 없어 계산된 페이스만 추가합니다.")
                        st.session_state.cardio_drills.append(f"러닝({run_dist}km, {run_min}분{run_sec}초, 페이스: {pace_str})")
                else:
                    st.error("거리와 시간을 정확히 입력해 주세요.")
        else:
            # 기타 유산소 종목 처리
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            with c1:
                if c_drill == "오르막길 스프린트": c_drill = f"오르막 스프린트({st.slider('강도(%)',50,100,100,5)}%)"
                elif c_drill == "턱걸이 + 오르막 컴플렉스": c_drill = f"턱걸이({st.number_input('개수',1,5,1)}개)+오르막({st.slider('강도(%)',50,100,100,5)}%)"
            with c2: 
                if "턱걸이" in c_drill or c_drill == "딥스": c_dist = st.text_input("개당 갯수", "10회")
                else: c_dist = st.text_input("거리/시간", "5km")
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
            save_workout({"날짜": today, "공복 체중": f"{m_weight}kg", "훈련 볼륨": f"{dist}km", "평균 심박": h_avg, "최대 심박": h_max, "심박 회복량(HRR)": hrr, "상세 훈련 내용 (SOP 및 실전 역학)": f"[{time_of_day}] 시퀀스:{' ➡️ '.join(st.session_state.cardio_drills)}", "생리학적 분석 및 영양/비고": "-"})
            st.session_state.cardio_drills = []; st.success("저장 완료!"); st.rerun()

    elif workout_type == "실전 경기":
        match_type = st.selectbox("📍 경기", ["11대11 정규", "풋살", "미니게임"])
        dist = st.number_input("거리(km)", 0.0, step=0.1)
        memo = st.text_area("📝 리뷰")
        if st.button("💾 신규 운동 저장"): save_workout({"날짜": today, "공복 체중": f"{m_weight}kg", "훈련 볼륨": f"{dist}km", "평균 심박": 0, "최대 심박": 0, "심박 회복량(HRR)": "-", "상세 훈련 내용 (SOP 및 실전 역학)": f"[{time_of_day}] {match_type} | 리뷰: {memo}", "생리학적 분석 및 영양/비고": "-"}); st.success("저장 완료!"); st.rerun()

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
                save_workout({"날짜": today, "공복 체중": f"{m_weight}kg", "훈련 볼륨": "-", "평균 심박": 0, "최대 심박": 0, "심박 회복량(HRR)": "-", "상세 훈련 내용 (SOP 및 실전 역학)": f"[{time_of_day}] " + ", ".join(w_list), "생리학적 분석 및 영양/비고": "-"})
                st.session_state.weight_sets = []; st.success("저장 완료!"); st.rerun()

    elif workout_type == "휴식(Recovery)":
        rec_act = st.multiselect("📋 활동", ["완전 휴식", "회복 걷기", "리커버리 조깅", "스트레칭", "폼롤러", "사우나"])
        rec_dist = st.number_input("거리(km)", 0.0, step=0.1)
        memo = st.text_area("📝 메모")
        if st.button("💾 신규 운동 저장"): save_workout({"날짜": today, "공복 체중": f"{m_weight}kg", "훈련 볼륨": f"회복{rec_dist}km", "평균 심박": 0, "최대 심박": 0, "심박 회복량(HRR)": "-", "상세 훈련 내용 (SOP 및 실전 역학)": f"[휴식] 활동:{','.join(rec_act)} | 메모:{memo}", "생리학적 분석 및 영양/비고": "-"}); st.success("저장 완료!"); st.rerun()

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
            st.success("운동 로그 원본이 완벽하게 수정되었습니다!")
            st.rerun()

# ------------------------------------------
# 🥗 TAB 3: 식단 데이터
# ------------------------------------------
with tab_diet:
    st.header("🥗 영양 섭취 및 실시간 매크로 코칭")
    st.info("💡 식단을 적고 바로 우측의 저장 버튼을 누르세요! 이전 식단을 다시 적을 필요 없이 실시간으로 누적 및 분석됩니다.")
    
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
        with c_input:
            current_inputs[m["name"]] = st.text_area(f"{m['name']}", value=m["raw"], height=70, key=f"input_{m['col_idx']}")
        with c_metric:
            st.metric(label="예상 칼로리", value=m["cal"])
        with c_btn:
            st.write("") 
            if st.button(f"💾 {m['name'].split(' ')[1]} 단독 등록", key=f"btn_{m['col_idx']}"):
                meal_txt = current_inputs[m["name"]].strip()
                if meal_txt:
                    with st.spinner("AI 칼로리 연산 중..."):
                        cal_prompt = f"'{meal_txt}' 이 식단의 총 칼로리만 숫자로 예측해서 '000kcal' 형식으로 딱 한 단어만 대답해줘. 설명 절대 금지."
                        try:
                            kcal_res = ask_gemini(cal_prompt).strip()
                        except:
                            kcal_res = "계산오류"
                        final_value = f"{meal_txt} | AI 분석: {kcal_res}"
                        save_single_meal(m["col_idx"], final_value)
                        st.success("실시간 업데이트 성공!")
                        st.rerun()
                else:
                    st.warning("내용을 입력해 주세요.")

    st.write("---")
    all_w_for_diet = get_cached_data("workout")
    today_w_str = "아직 기록된 오늘의 운동이 없습니다."
    if len(all_w_for_diet) > 1:
        today_w = [r for r in all_w_for_diet[1:] if r[0] == today]
        if today_w: today_w_str = " | ".join([f"볼륨:{r[2]}, 내용:{r[6]}" for r in today_w])

    if st.button("🧠 현재까지의 영양소 크로스-매칭 및 다음 식사 추천"):
        if HAS_AI:
            with st.spinner("분석 중..."):
                prompt = f"""
                너는 곽연혁 엘리트 축구 선수의 전담 스포츠 영양사야. 
                선수가 하루 일과 중 시간에 맞춰 식단을 순차적으로 기록하고 있어.
                
                [오늘 수행한 훈련량/예정 훈련량]: {today_w_str}
                
                [현재까지 섭취한 식단]
                - 아침: {current_inputs["🌅 아침 식단"] if current_inputs["🌅 아침 식단"] else '기록없음 (아직 안먹음)'}
                - 점심: {current_inputs["☀️ 점심 식단"] if current_inputs["☀️ 점심 식단"] else '기록없음 (아직 안먹음)'}
                - 저녁: {current_inputs["🌙 저녁 식단"] if current_inputs["🌙 저녁 식단"] else '기록없음 (아직 안먹음)'}
                - 간식/보충제: {current_inputs["🥤 간식/보충제"] if current_inputs["🥤 간식/보충제"] else '기록없음 (아직 안먹음)'}
                - 야식: {current_inputs["🌌 야식"] if current_inputs["🌌 야식"] else '기록없음 (아직 안먹음)'}
                
                [가이드라인 - 반드시 엄격하게 지킬 것]
                1. 경고 및 호들갑 금지: 아직 기록이 없는 식사칸은 단순히 '아직 시간이 안 되어서 안 먹은 것'이야. 부정적인 피드백 절대 금지.
                2. 지금까지 먹은 식단(내용이 있는 식단)의 대략적인 총 칼로리와 매크로(탄/단/지)를 분석.
                3. 현실적인 분배: 엘리트 선수로서 남은 필요 칼로리를 당장 다음 한 끼에 무식하게 다 때려 넣지 말고, 아직 안 먹은 남은 식사들에 현실적인 비율로 쪼개서 분배해.
                4. 당장 먹어야 할 '바로 다음 끼니'의 목표 칼로리와 탄/단/지 목표량(g)을 설정하고, 현실적인 메뉴 3가지를 구체적으로 제시해줘.
                """
                st.markdown(ask_gemini(prompt))

    st.write("---")
    st.warning("⚠️ 하루 식사가 모두 끝난 후, 맨 마지막에 한 번만 아래 저장 버튼을 눌러주세요!")
    if st.button("💾 (하루 1회) 오늘 식단 구글 시트 최종 저장"):
        if HAS_AI:
            with st.spinner("전체 식단 칼로리를 최종 연산하여 저장합니다..."):
                b_val = current_inputs["🌅 아침 식단"]
                l_val = current_inputs["☀️ 점심 식단"]
                d_val = current_inputs["🌙 저녁 식단"]
                s_val = current_inputs["🥤 간식/보충제"]
                n_val = current_inputs["🌌 야식"]
                
                prompt_cal = f"아침:{b_val}, 점심:{l_val}, 저녁:{d_val}, 간식:{s_val}, 야식:{n_val}. 총 칼로리만 숫자로 예측해서 '0000kcal' 형식으로 적어줘. 설명 금지."
                try: ai_total_kcal = ask_gemini(prompt_cal).strip()
                except: ai_total_kcal = f"계산오류"
                sheet_diet.append_row([today, ai_total_kcal, b_val, l_val, d_val, s_val, n_val])
                st.cache_data.clear()
                st.success(f"🎉 하루 식단 저장이 완료되었습니다! (추정 칼로리: {ai_total_kcal})")
                st.rerun()

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
            st.success("식단 로그 원본이 완벽하게 수정되었습니다!")
            st.rerun()

# ------------------------------------------
# 📈 TAB 4: 데이터/리포팅 센터
# ------------------------------------------
with tab_report:
    st.header("📈 퍼포먼스 상관관계 및 AI 처방 센터")
    
    st.subheader("📊 최근 7일 회복 vs 컨디션 역학 그래프")
    all_w = get_cached_data("workout")
    all_s = get_cached_data("sleep")
    
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
    report_type = st.radio(
        "📋 생성할 AI 보고서 사이클", 
        ["⚡ 실시간 당일 분석 보고서 (Real-time Live)", "내일 훈련 처방 (Daily)", "주간 피지컬 레포트 (Weekly)", "월간 마스터 레포트 (Monthly)"], 
        horizontal=True
    )
    
    if st.button(f"🤖 AI 리포트 출력하기"):
        if HAS_AI:
            with st.spinner("데이터 동기화 및 훈련 역학 스캔 중..."):
                try:
                    all_d = get_cached_data("diet")
                    
                    if "Real-time" in report_type:
                        today_w_data = [r for r in all_w[1:] if r[0] == today]
                        today_s_data = [r for r in all_s[1:] if r[0] == today]
                        today_d_data = [r for r in all_d[1:] if r[0] == today]
                        
                        w_ctx = " | ".join([f"시간대:{r[1]}, 종류:{r[2]}, 내용:{r[6]}" for r in today_w_data]) if today_w_data else "오늘 완료한 세션 없음"
                        s_ctx = f"수면:{today_s_data[-1][2]}, 기상컨디션:{today_s_data[-1][4]}" if today_s_data else "오늘 수면 데이터 미등록"
                        d_ctx = f"아침:{raw_b}({cal_b}), 점심:{raw_l}({cal_l}), 저녁:{raw_d}({cal_d}), 간식:{raw_s}({cal_s})"
                        
                        prompt = f"""
                        너는 곽연혁 선수의 전담 피지컬 수석 코치야. 
                        선수가 오늘 '오전/오후' 세션을 마치고 '다음 차례 세션(오후 후반 또는 저녁 세션)'을 준비하기 위해 실시간 브리핑을 요청했어.
                        
                        [오늘 현재까지의 실시간 스냅샷]
                        - 기상 수면 및 컨디션: {s_ctx}
                        - 오늘 완료한 운동 로그: {w_ctx}
                        - 오늘 지금까지 먹은 식단: {d_ctx}
                        
                        위의 당일 데이터를 분석해서 다음 지침을 내려줘:
                        ### ⚽ 1. 오전/오후 데이터 기준 현재 피로도 실시간 진단
                        ### 🏋️ 2. 오늘 남은 시간(저녁/야간)에 추천하는 연계 트레이닝 또는 리커버리 드릴 처방
                        ### 🍗 3. 다음 세션의 기량 발휘를 위해 지금 바로 추가 섭취해야 할 타겟 영양소 가이드
                        """
                    else:
                        target_days = 30 if "Monthly" in report_type else 7
                        period_text = "최근 한 달" if "Monthly" in report_type else "최근 7일"
                        recent_w = all_w[-target_days:] if len(all_w) > target_days else all_w[1:]
                        recent_s = all_s[-target_days:] if len(all_s) > target_days else all_s[1:]
                        recent_d = all_d[-target_days:] if len(all_d) > target_days else all_d[1:]
                        
                        w_context = " | ".join([f"{r[0]}(운동:{r[6]})" for r in recent_w if len(r) > 6])
                        s_context = " | ".join([f"{r[0]}(수면:{r[2]}, 질:{r[3]}, 아침컨디션:{r[4]}, 체중:{r[1]})" for r in recent_s if len(r) > 4])
                        d_context = " | ".join([f"{r[0]}(식단:{r[2]} / {r[3]} / {r[4]})" for r in recent_d if len(r) > 4])
                        
                        prompt = f"""
                        너는 곽연혁 엘리트 축구 선수의 S-Tier 전담 코치야.
                        {period_text} 데이터 기반 ({report_type}):
                        운동: {w_context}
                        수면/신체: {s_context}
                        영양: {d_context}
                        분석 포맷에 맞춰 성능 준비도 및 피드백, 중장기 드릴 솔루션을 처방해줘.
                        """
                    
                    st.success("✨ S-Tier 분석 리포트가 성공적으로 구축되었습니다.")
                    st.markdown(ask_gemini(prompt))
                except Exception as e: st.error(f"리포팅 에러: {e}")
        else:
            st.error("AI API 설정이 필요합니다.")

st.write("---")
if st.button("🔒 안전하게 로그아웃"):
    st.session_state.login_success = False
    st.rerun()