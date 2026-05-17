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

@st.cache_data(ttl=15)
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

# ------------------------------------------
# 📊 TAB 1: 신체 데이터
# ------------------------------------------
with tab_body:
    st.header("📊 신체 데이터 & 수면 과학 로그")
    
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        m_weight = st.number_input("⚖️ 오늘의 공복 체중 (kg)", min_value=0.0, max_value=150.0, value=77.5, step=0.1)
    with col_m2:
        bed_time = st.time_input("🛏️ 불 끄고 누운 시간", value=time(23, 30))
    with col_m3:
        wake_time = st.time_input("☀️ 실제 일어난 시간", value=time(7, 30))
        
    dt_bed = datetime.combine(date.today(), bed_time)
    dt_wake = datetime.combine(date.today(), wake_time)
    if dt_wake < dt_bed: dt_wake += timedelta(days=1)
    total_bed_mins = (dt_wake - dt_bed).total_seconds() / 60
    calc_sleep_hours = round(max(0, (total_bed_mins - 20) * 0.9) / 60, 1)
    
    st.success(f"🤖 **AI 수면 연산:** 잠복기 및 효율을 계산한 **실제 회복 딥슬립 시간은 [{calc_sleep_hours}시간]** 입니다.")

    col_m4, col_m5 = st.columns(2)
    with col_m4: m_quality = st.slider("⭐ 체감 수면의 질 (1:최악 ~ 10:최상)", 1, 10, 7)
    with col_m5: m_cond = st.slider("🏃 기상 직후 신체 컨디션 스코어", 1, 10, 7)
        
    with st.expander("📏 [선택 사항] 공복 신체 정밀 사이즈 측정"):
        c_size1, c_size2, c_size3, c_size4 = st.columns(4)
        with c_size1: chest_sz = st.number_input("가슴 (cm)", value=0.0, step=0.1)
        with c_size2: arm_sz = st.number_input("팔 (cm)", value=0.0, step=0.1)
        with c_size3: waist_sz = st.number_input("허리 (cm)", value=0.0, step=0.1)
        with c_size4: thigh_sz = st.number_input("허벅지 (cm)", value=0.0, step=0.1)

    if st.button("🚀 신체/수면 데이터 신규 저장"):
        sleep_row = [today, f"{m_weight}kg", f"{calc_sleep_hours}시간", f"{m_quality}점", f"{m_cond}점",
            f"{chest_sz}cm" if chest_sz > 0 else "-", f"{arm_sz}cm" if arm_sz > 0 else "-",
            f"{waist_sz}cm" if waist_sz > 0 else "-", f"{thigh_sz}cm" if thigh_sz > 0 else "-"]
        sheet_sleep.append_row(sleep_row)
        st.cache_data.clear() 
        st.success("데이터가 성공적으로 저장되었습니다!")
        st.rerun()
        
    all_m = get_cached_data("sleep")
    
    st.write("---")
    st.subheader("🛠️ 신체 데이터베이스 (실시간 수정 가능)")
    st.info("표 안의 글자를 더블클릭해서 자유롭게 수정한 뒤, 아래의 덮어쓰기 버튼을 누르면 구글 시트에 반영됩니다.")
    if len(all_m) > 1:
        df_body = pd.DataFrame(all_m[1:], columns=all_m[0])
        edited_body = st.data_editor(df_body, num_rows="dynamic", use_container_width=True, key="edit_body")
        if st.button("🔄 수정한 신체 데이터를 구글 시트에 덮어쓰기"):
            sheet_sleep.clear()
            sheet_sleep.append_rows([edited_body.columns.tolist()] + edited_body.fillna("").astype(str).values.tolist())
            st.cache_data.clear()
            st.success("구글 시트 원본이 완벽하게 수정되었습니다!")
            st.rerun()

        df_body['날짜'] = pd.to_datetime(df_body['날짜'], errors='coerce')
        df_body = df_body.dropna(subset=['날짜'])
        df_body['체중'] = df_body['공복 체중'].apply(extract_number)
        df_body['추정 골격근량(kg)'] = round(df_body['체중'] * 0.49, 1)
        df_body['추정 체지방률(%)'] = round(11.5 + (df_body['체중'] - 77.5) * 0.7, 1)
        df_body['추정 체지방량(kg)'] = round(df_body['체중'] * (df_body['추정 체지방률(%)'] / 100), 1)
        
        st.write("---")
        st.subheader("📈 엘리트 바디 컴포지션 트렌드 (AI 추정치)")
        chart_data = df_body.set_index('날짜')[['추정 골격근량(kg)', '추정 체지방량(kg)']]
        st.line_chart(chart_data, color=["#1f77b4", "#ff7f0e"])

# ------------------------------------------
# 🏋️ TAB 2: 운동 데이터
# ------------------------------------------
with tab_workout:
    st.header("🧠 오늘의 트레이닝 세션 로깅")
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
            save_workout({"날짜": today, "공복 체중": "세션 기록", "훈련 볼륨": f"{dist}km", "평균 심박": h_avg, "최대 심박": h_max, "심박 회복량(HRR)": hrr, "상세 훈련 내용 (SOP 및 실전 역학)": f"[{time_of_day}] 장소:{location} | 루틴:{' ➡️ '.join(st.session_state.football_drills)}", "생리학적 분석 및 영양/비고": "-"})
            st.session_state.football_drills = []; st.success("저장 완료!"); st.rerun()

    elif workout_type == "유산소/조깅":
        c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
        with c1:
            c_drill = st.selectbox("📋 종목", ["조깅 (5분 페이스)", "턱걸이", "딥스", "턱걸이 + 오르막 컴플렉스", "오르막길 스프린트", "15/15 매스템포런", "기타"])
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
        with col1: dist = st.number_input("🏃 거리(km)", 0.0, step=0.1)
        with col2: h_avg = st.number_input("❤️ 평균 심박", 0)
        with col3: h_max = st.number_input("🔥 최대 심박", 0)
        with col4: hrr = st.text_input("📉 HRR")
        if st.button("💾 신규 운동 저장"):
            save_workout({"날짜": today, "공복 체중": "-", "훈련 볼륨": f"{dist}km", "평균 심박": h_avg, "최대 심박": h_max, "심박 회복량(HRR)": hrr, "상세 훈련 내용 (SOP 및 실전 역학)": f"[{time_of_day}] 시퀀스:{' ➡️ '.join(st.session_state.cardio_drills)}", "생리학적 분석 및 영양/비고": "-"})
            st.session_state.cardio_drills = []; st.success("저장 완료!"); st.rerun()

    elif workout_type == "실전 경기":
        match_type = st.selectbox("📍 경기", ["11대11 정규", "풋살", "미니게임"])
        dist = st.number_input("거리(km)", 0.0, step=0.1)
        memo = st.text_area("📝 리뷰")
        if st.button("💾 신규 운동 저장"): save_workout({"날짜": today, "공복 체중": "-", "훈련 볼륨": f"{dist}km", "평균 심박": 0, "최대 심박": 0, "심박 회복량(HRR)": "-", "상세 훈련 내용 (SOP 및 실전 역학)": f"[{time_of_day}] {match_type} | 리뷰: {memo}", "생리학적 분석 및 영양/비고": "-"}); st.success("저장 완료!"); st.rerun()

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
                save_workout({"날짜": today, "공복 체중": "-", "훈련 볼륨": "-", "평균 심박": 0, "최대 심박": 0, "심박 회복량(HRR)": "-", "상세 훈련 내용 (SOP 및 실전 역학)": f"[{time_of_day}] " + ", ".join(w_list), "생리학적 분석 및 영양/비고": "-"})
                st.session_state.weight_sets = []; st.success("저장 완료!"); st.rerun()

    elif workout_type == "휴식(Recovery)":
        rec_act = st.multiselect("📋 활동", ["완전 휴식", "회복 걷기", "리커버리 조깅", "스트레칭", "폼롤러", "사우나"])
        rec_dist = st.number_input("거리(km)", 0.0, step=0.1)
        memo = st.text_area("📝 메모")
        if st.button("💾 신규 운동 저장"): save_workout({"날짜": today, "공복 체중": "-", "훈련 볼륨": f"회복{rec_dist}km", "평균 심박": 0, "최대 심박": 0, "심박 회복량(HRR)": "-", "상세 훈련 내용 (SOP 및 실전 역학)": f"[휴식] 활동:{','.join(rec_act)} | 메모:{memo}", "생리학적 분석 및 영양/비고": "-"}); st.success("저장 완료!"); st.rerun()

    all_w = get_cached_data("workout")
    
    st.write("---")
    st.subheader("🛠️ 운동 데이터베이스 (실시간 수정 가능)")
    st.info("운동 볼륨을 깜빡하셨나요? 표 안을 더블클릭해서 바로 수정하고 아래 버튼을 누르세요.")
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
    st.info("💡 식사를 순서대로 적어보세요. 버튼을 누르면 AI가 오늘의 운동량과 지금까지 먹은 것을 계산해 '다음 식사'를 합리적으로 추천해 줍니다!")
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        breakfast = st.text_area("🌅 아침 식단 (먹은 후 적어주세요)", height=80)
        lunch = st.text_area("☀️ 점심 식단 (먹은 후 적어주세요)", height=80)
        night = st.text_area("🌌 야식", height=80)
    with col_d2:
        dinner = st.text_area("🌙 저녁 식단 (먹은 후 적어주세요)", height=80)
        snacks = st.text_area("🥤 간식/보충제", height=80)
        
    all_w_for_diet = get_cached_data("workout")
    today_w_str = "아직 기록된 오늘의 운동이 없습니다."
    if len(all_w_for_diet) > 1:
        today_w = [r for r in all_w_for_diet[1:] if r[0] == today]
        if today_w:
            today_w_str = " | ".join([f"볼륨:{r[2]}, 내용:{r[6]}" for r in today_w])

    # 💡 [V10.3 업데이트] 호들갑 금지 및 현실적인 칼로리 분배 프롬프트
    if st.button("🧠 현재까지의 식단 분석 및 [다음 식사] 추천받기"):
        if HAS_AI:
            with st.spinner("오늘의 훈련량과 지금까지의 식단을 분석하여 다음 식사 매크로를 계산 중입니다..."):
                prompt = f"""
                너는 곽연혁 엘리트 축구 선수의 전담 스포츠 영양사야. 
                선수가 하루 일과 중 시간에 맞춰 식단을 순차적으로 기록하고 있어.
                
                [오늘 수행한 훈련량/예정 훈련량]: {today_w_str}
                
                [현재까지 섭취한 식단]
                - 아침: {breakfast if breakfast else '기록없음 (아직 안먹음)'}
                - 점심: {lunch if lunch else '기록없음 (아직 안먹음)'}
                - 저녁: {dinner if dinner else '기록없음 (아직 안먹음)'}
                - 간식/보충제: {snacks if snacks else '기록없음 (아직 안먹음)'}
                - 야식: {night if night else '기록없음 (아직 안먹음)'}
                
                [가이드라인 - 반드시 엄격하게 지킬 것]
                1. 경고 및 호들갑 금지: 아직 기록이 없는 식사칸은 단순히 '아직 시간이 안 되어서 안 먹은 것'이야. 따라서 "현재 영양이 심각하게 부족하다", "우려된다" 같은 부정적인 피드백이나 호들갑을 절대 금지해.
                2. 지금까지 먹은 식단(내용이 있는 식단)의 대략적인 총 칼로리와 매크로(탄/단/지)를 분석해줘.
                3. 현실적인 분배: 엘리트 선수로서 하루 필요한 '총 권장 칼로리'에서 지금까지 먹은 칼로리를 뺀 '남은 필요 칼로리'를 계산해. 그리고 이 남은 칼로리를 당장 다음 한 끼에 무식하게 다 때려 넣지 말고, 아직 안 먹은 남은 식사들(점심, 저녁, 간식 등)에 현실적인 비율로 쪼개서 분배해.
                4. 분배된 결과를 바탕으로, 선수가 당장 먹어야 할 '바로 다음 끼니'의 목표 칼로리와 탄/단/지 목표량(g)을 설정하고, 현실적인 추천 식단 메뉴 3가지를 구체적으로 제시해줘.
                """
                try: 
                    ai_diet_coach_response = ask_gemini(prompt)
                    st.success("✨ 영양 코치의 실시간 분석이 완료되었습니다!")
                    st.markdown(ai_diet_coach_response)
                except Exception as e: st.error(f"코치 호출 오류: {e}")
        else:
            st.error("AI API 키가 필요합니다.")

    st.write("---")
    st.warning("⚠️ 하루 식사가 모두 끝난 후, 맨 마지막에 한 번만 아래 저장 버튼을 눌러주세요!")
    if st.button("💾 (하루 1회) 오늘 식단 구글 시트 최종 저장"):
        if HAS_AI:
            with st.spinner("전체 식단 칼로리를 최종 연산하여 저장합니다..."):
                prompt_cal = f"아침:{breakfast}, 점심:{lunch}, 저녁:{dinner}, 간식:{snacks}, 야식:{night}. 총 칼로리만 숫자로 예측해서 '0000kcal' 형식으로 적어줘. 설명 금지."
                try: ai_total_kcal = ask_gemini(prompt_cal).strip()
                except: ai_total_kcal = f"계산오류"
                sheet_diet.append_row([today, ai_total_kcal, breakfast, lunch, dinner, snacks, night])
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
        st.caption("🟢 초록바: 수면 회복 시간(h) | 🔵 파란바: 기상 직후 컨디션 스코어 (높을수록 좋음)")
    else:
        st.info("상관관계 그래프를 분석하려면 최소 2일 이상의 신체 데이터 누적이 필요합니다.")

    st.write("---")
    report_type = st.radio("📋 생성할 AI 보고서 사이클", ["내일 훈련 처방 (Daily)", "주간 피지컬 레포트 (Weekly)", "월간 마스터 레포트 (Monthly)"], horizontal=True)
    
    if st.button(f"🤖 AI {report_type.split(' ')[0]} 분석 호출하기"):
        if HAS_AI:
            with st.spinner("신체, 수면, 식단, 운동 부하 데이터를 통합하여 퍼포먼스 영향을 스캔 중입니다..."):
                try:
                    target_days = 30 if "Monthly" in report_type else 7
                    period_text = "최근 한 달" if "Monthly" in report_type else "최근 7일"
                        
                    recent_w = all_w[-target_days:] if len(all_w) > target_days else all_w[1:]
                    recent_s = all_s[-target_days:] if len(all_s) > target_days else all_s[1:]
                    all_d = get_cached_data("diet")
                    try: recent_d = all_d[-target_days:] if len(all_d) > target_days else all_d[1:]
                    except: recent_d = []
                    
                    w_context = " | ".join([f"{r[0]}(운동:{r[6]})" for r in recent_w if len(r) > 6])
                    s_context = " | ".join([f"{r[0]}(수면:{r[2]}, 질:{r[3]}, 아침컨디션:{r[4]}, 체중:{r[1]})" for r in recent_s if len(r) > 4])
                    d_context = " | ".join([f"{r[0]}(총칼로리:{r[1]})" for r in recent_d if len(r) > 1])
                    
                    prompt = f"""
                    너는 곽연혁 엘리트 축구 선수의 S-Tier 전담 코치야. 
                    {period_text} 데이터:
                    운동: {w_context}
                    수면/신체: {s_context}
                    식단(칼로리 및 영양): {d_context}
                    
                    이 데이터를 종합 분석해서 아래 포맷으로 반드시 대답해:
                    ### 🎯 1. 퍼포먼스 준비도 및 휴식 권장 스케일 (1/10 ~ 10/10)
                    (반드시 '퍼포먼스 스케일: X/10' 형태로 명시하고, 현재 체력 상태 및 휴식 필요성을 설명)
                    
                    ### 🧬 2. 영양/수면이 훈련에 미친 상관관계 분석
                    (예: 섭취한 칼로리/식단이 전날 훈련 강도를 버티기에 충분했는지, 수면이 컨디션에 준 영향 등 팩트 기반 분석)
                    
                    ### 🚀 3. 식단 및 피로도를 고려한 다음 사이클 맞춤형 훈련 솔루션
                    (특히 '어제오늘 섭취한 식단(에너지원)'을 바탕으로 내일 고강도를 할지, 저강도 리커버리를 할지 구체적인 훈련 종목과 강도를 지시해줘.)
                    """
                    
                    report_text = ask_gemini(prompt)
                    st.success(f"✨ 수석 코치의 퍼포먼스 데이터 분석이 완료되었습니다.")
                    st.markdown(report_text)
                except Exception as e:
                    st.error(f"AI 코치 호출 중 에러 발생: {e}")
        else:
            st.error("⚠️ AI 코치를 호출하려면 API 설정이 필요합니다.")

st.write("---")
if st.button("🔒 안전하게 로그아웃"):
    st.session_state.login_success = False
    st.rerun()