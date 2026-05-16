import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timedelta
import gspread
from google.oauth2.service_account import Credentials
import requests
import json

# --- 🧠 제미나이 AI 다이렉트 통신망 (V9.4 모델 자동 추적기 탑재) ---
if "GEMINI_API_KEY" in st.secrets:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
elif "gcp" in st.secrets and "GEMINI_API_KEY" in st.secrets["gcp"]:
    GEMINI_API_KEY = st.secrets["gcp"]["GEMINI_API_KEY"]
else:
    GEMINI_API_KEY = ""

HAS_AI = bool(GEMINI_API_KEY)

def ask_gemini(prompt):
    if not HAS_AI:
        raise Exception("API 키가 없습니다. 스트림릿 Secrets를 확인하세요.")
    
    # 💡 구글 서버가 알아듣는 모든 모델 풀네임을 준비하여 순서대로 통신을 시도합니다.
    models_to_try = [
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash",
        "gemini-1.0-pro-latest",
        "gemini-1.0-pro",
        "gemini-pro"
    ]
    
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    
    last_error = ""
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            # 성공하면 즉시 대답을 반환합니다.
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        elif response.status_code == 404:
            # 404(이름 못 찾음) 에러면 당황하지 않고 다음 모델 이름으로 넘어갑니다.
            last_error = response.text
            continue
        else:
            # 400(키 오류) 등 다른 에러면 즉시 중단합니다.
            raise Exception(f"구글 본서버 통신 에러 ({response.status_code}): {response.text}")
            
    # 모든 이름을 다 찔러봤는데도 실패했을 경우
    raise Exception(f"사용 가능한 AI 모델을 찾지 못했습니다. 마지막 에러: {last_error}")

# ⭕ 구글 시트 주소
MY_SHEET_URL = "https://docs.google.com/spreadsheets/d/1N4KGhJf1ta1MOcATsOXcJayTe9ULsNGhL_9u8Rdbo_Q/edit"

st.set_page_config(page_title="S-Tier Performance AMS v9.4", layout="wide")

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

st.title("⚡ S-Tier AI Coach System (v9.4 끝판왕)")

if not HAS_AI:
    st.warning("⚠️ 제미나이 AI 연결 대기 중... (스트림릿 Secrets에 GEMINI_API_KEY가 없습니다)")

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
        m_weight = st.number_input("⚖️ 오늘의 공복 체중 (kg)", min_value=0.0, max_value=150.0, value=77.5, step=0.1)
    with col_m2:
        bed_time = st.time_input("🛏️ 불 끄고 누운 시간", value=time(23, 30))
    with col_m3:
        wake_time = st.time_input("☀️ 실제 일어난 시간", value=time(7, 30))
        
    dt_bed = datetime.combine(date.today(), bed_time)
    dt_wake = datetime.combine(date.today(), wake_time)
    if dt_wake < dt_bed: dt_wake += timedelta(days=1)
    total_bed_mins = (dt_wake - dt_bed).total_seconds() / 60
    calc_sleep_mins = max(0, (total_bed_mins - 20) * 0.9) 
    calc_sleep_hours = round(calc_sleep_mins / 60, 1)
    
    st.success(f"🤖 **AI 수면 분석:** 총 누워있던 시간은 {int(total_bed_mins/60)}시간 {int(total_bed_mins%60)}분입니다. 수면 과학을 적용한 **실제 회복(딥슬립) 수면 시간은 [{calc_sleep_hours}시간]** 으로 기록됩니다.")

    col_m4, col_m5 = st.columns(2)
    with col_m4: m_quality = st.slider("⭐ 체감 수면의 질 (1:최악 ~ 10:최상)", 1, 10, 7)
    with col_m5: m_cond = st.slider("🏃 기상 직후 신체 컨디션 스코어", 1, 10, 7)
        
    with st.expander("📏 [선택 사항] 공복 신체 정밀 사이즈 측정"):
        c_size1, c_size2, c_size3, c_size4 = st.columns(4)
        with c_size1: chest_sz = st.number_input("가슴 (cm)", value=0.0, step=0.1)
        with c_size2: arm_sz = st.number_input("팔 (cm)", value=0.0, step=0.1)
        with c_size3: waist_sz = st.number_input("허리 (cm)", value=0.0, step=0.1)
        with c_size4: thigh_sz = st.number_input("허벅지 (cm)", value=0.0, step=0.1)

    if st.button("🚀 모닝 데이터 즉시 전송"):
        sleep_row = [today, f"{m_weight}kg", f"{calc_sleep_hours}시간", f"{m_quality}점", f"{m_cond}점",
            f"{chest_sz}cm" if chest_sz > 0 else "-", f"{arm_sz}cm" if arm_sz > 0 else "-",
            f"{waist_sz}cm" if waist_sz > 0 else "-", f"{thigh_sz}cm" if thigh_sz > 0 else "-"]
        sheet_sleep.append_row(sleep_row)
        st.success("데이터가 [수면/컨디션로그]에 과학적으로 연산되어 저장되었습니다!")
        st.rerun()
        
    all_m = sheet_sleep.get_all_values()
    if len(all_m) > 1: st.dataframe(pd.DataFrame(all_m[1:], columns=all_m[0]).fillna(""), use_container_width=True)

# ------------------------------------------
# 🏋️ TAB 2: 운동 대시보드
# ------------------------------------------
with tab_workout:
    st.header("🧠 오늘의 트레이닝 세션 로깅")
    time_of_day = st.radio("⏰ 시간대", ("☀️ 오전", "🌤️ 오후", "🌙 저녁/야간"), horizontal=True)
    workout_type = st.selectbox("👇 세션 종류", ("개인 축구 훈련", "유산소/조깅", "실전 경기", "웨이트 트레이닝", "휴식(Recovery)"))
    post_condition = st.slider("🥵 오늘 체감 피로도/RPE", 1, 10, 5)
    st.write("---")

    def save_workout(data_dict):
        cols = ["날짜", "공복 체중", "훈련 볼륨", "평균 심박", "최대 심박", "심박 회복량(HRR)", "상세 훈련 내용 (SOP 및 실전 역학)", "생리학적 분석 및 영양/비고"]
        sheet_workout.append_row([str(data_dict.get(c, "")) for c in cols])

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
        if st.button("💾 저장"):
            save_workout({"날짜": today, "공복 체중": "세션 기록", "훈련 볼륨": f"{dist}km", "평균 심박": h_avg, "최대 심박": h_max, "심박 회복량(HRR)": hrr, "상세 훈련 내용 (SOP 및 실전 역학)": f"[{time_of_day}] 장소:{location} | 루틴:{' ➡️ '.join(st.session_state.football_drills)}", "생리학적 분석 및 영양/비고": f"RPE피로도:{post_condition}/10"})
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
        if st.button("💾 저장"):
            save_workout({"날짜": today, "공복 체중": "-", "훈련 볼륨": f"{dist}km", "평균 심박": h_avg, "최대 심박": h_max, "심박 회복량(HRR)": hrr, "상세 훈련 내용 (SOP 및 실전 역학)": f"[{time_of_day}] 시퀀스:{' ➡️ '.join(st.session_state.cardio_drills)}", "생리학적 분석 및 영양/비고": f"RPE:{post_condition}/10"})
            st.session_state.cardio_drills = []; st.success("저장 완료!"); st.rerun()

    elif workout_type == "실전 경기":
        match_type = st.selectbox("📍 경기", ["11대11 정규", "풋살", "미니게임"])
        dist = st.number_input("거리(km)", 0.0, step=0.1)
        memo = st.text_area("📝 리뷰")
        if st.button("💾 저장"): save_workout({"날짜": today, "공복 체중": "-", "훈련 볼륨": f"{dist}km", "평균 심박": 0, "최대 심박": 0, "심박 회복량(HRR)": "-", "상세 훈련 내용 (SOP 및 실전 역학)": f"[{time_of_day}] {match_type} | 리뷰: {memo}", "생리학적 분석 및 영양/비고": f"RPE:{post_condition}/10"}); st.success("저장 완료!"); st.rerun()

    elif workout_type == "웨이트 트레이닝":
        ex_name = st.text_input("운동 이름")
        weight = st.number_input("무게(kg)", 0.0, step=2.5)
        reps = st.number_input("횟수", 0, step=1)
        sets = st.number_input("세트", 1, step=1)
        if st.button("➕ 추가"): st.session_state.weight_sets.append({"운동명": ex_name, "무게": weight, "횟수": reps, "세트수": sets})
        if st.session_state.weight_sets:
            st.dataframe(pd.DataFrame(st.session_state.weight_sets))
            if st.button("💾 저장"):
                w_list = [f"{s['운동명']}({s['무게']}kg x{s['횟수']}회 {s['세트수']}세트)" for s in st.session_state.weight_sets]
                save_workout({"날짜": today, "공복 체중": "-", "훈련 볼륨": "-", "평균 심박": 0, "최대 심박": 0, "심박 회복량(HRR)": "-", "상세 훈련 내용 (SOP 및 실전 역학)": f"[{time_of_day}] " + ", ".join(w_list), "생리학적 분석 및 영양/비고": f"RPE:{post_condition}/10"})
                st.session_state.weight_sets = []; st.success("저장 완료!"); st.rerun()

    elif workout_type == "휴식(Recovery)":
        rec_act = st.multiselect("📋 활동", ["완전 휴식", "회복 걷기", "리커버리 조깅", "스트레칭", "폼롤러", "사우나"])
        rec_dist = st.number_input("거리(km)", 0.0, step=0.1)
        memo = st.text_area("📝 메모")
        if st.button("💾 저장"): save_workout({"날짜": today, "공복 체중": "-", "훈련 볼륨": f"회복{rec_dist}km", "평균 심박": 0, "최대 심박": 0, "심박 회복량(HRR)": "-", "상세 훈련 내용 (SOP 및 실전 역학)": f"[휴식] 활동:{','.join(rec_act)} | 메모:{memo}", "생리학적 분석 및 영양/비고": f"휴식만족도:{post_condition}/10"}); st.success("저장 완료!"); st.rerun()

    all_w = sheet_workout.get_all_values()
    if len(all_w) > 1: st.dataframe(pd.DataFrame(all_w[1:], columns=all_w[0]).fillna(""), use_container_width=True)

# ------------------------------------------
# 🥗 TAB 3: AI 식단 관리
# ------------------------------------------
with tab_diet:
    st.header("🥗 영양 섭취 및 매크로 AI 매니지먼트")
    st.info("칼로리 계산은 제미나이(AI)가 알아서 합니다. 섭취하신 메뉴와 대략적인 양(g, 공기 등)만 자연스럽게 적어주세요!")
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        breakfast = st.text_area("🌅 아침 식단", height=80)
        lunch = st.text_area("☀️ 점심 식단", height=80)
        night = st.text_area("🌌 야식", height=80)
    with col_d2:
        dinner = st.text_area("🌙 저녁 식단", height=80)
        snacks = st.text_area("🥤 간식/보충제", height=80)
        
    if st.button("🤖 AI 칼로리 분석 및 구글 시트 저장"):
        if HAS_AI:
            with st.spinner("제미나이 AI가 식단을 스캔하여 칼로리와 매크로를 정밀 연산 중입니다..."):
                prompt = f"""
                너는 엘리트 축구 선수의 스포츠 영양사야. 아래 식단을 보고 총 칼로리만 숫자로 예측해줘.
                아침: {breakfast}, 점심: {lunch}, 저녁: {dinner}, 간식: {snacks}, 야식: {night}
                답변은 다른 설명 없이 오직 숫자와 'kcal'만 적어줘. (예: 2850kcal)
                만약 빈칸이면 0kcal로 계산해.
                """
                try:
                    ai_total_kcal = ask_gemini(prompt).strip()
                except Exception as e:
                    ai_total_kcal = f"계산오류({e})"
                
                diet_row = [today, ai_total_kcal, breakfast, lunch, dinner, snacks, night]
                sheet_diet.append_row(diet_row)
                st.success(f"🎉 AI 계산 완료! 오늘 예상 섭취량은 **{ai_total_kcal}** 입니다. [식단로그]에 단독 저장되었습니다.")
                st.rerun()
        else:
            st.error("AI API 키가 없습니다. 직접 텍스트만 저장합니다.")
            sheet_diet.append_row([today, "AI미연결", breakfast, lunch, dinner, snacks, night])
            st.rerun()
            
    all_d = sheet_diet.get_all_values()
    if len(all_d) > 1: st.dataframe(pd.DataFrame(all_d[1:], columns=all_d[0]).fillna(""), use_container_width=True)

# ------------------------------------------
# 📊 TAB 4: AI 수석 코치 레포트
# ------------------------------------------
with tab_report:
    st.header("📊 Gemini AI 수석 코치: 데이터 기반 훈련 처방")
    st.write("구글 시트에 누적된 운동 부하(RPE)와 수면 과학 데이터를 AI가 종합 분석하여, 내일의 훈련 및 휴식을 설계합니다.")
    
    if st.button("🤖 AI 개인 코치 호출하기 (내일 훈련 설계)"):
        if HAS_AI:
            with st.spinner("최근 7일간의 수면, 피로도, 운동 데이터를 불러와 스포츠 과학 알고리즘으로 분석 중입니다..."):
                try:
                    recent_w = sheet_workout.get_all_values()[-7:]
                    recent_s = sheet_sleep.get_all_values()[-7:]
                    w_context = " | ".join([f"{r[0]}(운동:{r[6]}, RPE:{r[7]})" for r in recent_w])
                    s_context = " | ".join([f"{r[0]}(수면:{r[2]}, 질:{r[3]}, 컨디션:{r[4]})" for r in recent_s])
                    
                    prompt = f"""
                    너는 곽연혁 엘리트 축구 선수를 담당하는 월드클래스 S-Tier 피지컬/전술 코치야. 
                    아래는 선수의 최근 7일간 운동 로그와 수면/컨디션 로그야.
                    운동 데이터: {w_context}
                    수면 데이터: {s_context}
                    
                    이 데이터를 분석해서 다음 포맷으로 대답해줘:
                    ### 🔍 1. 현재 피로도 및 상태 분석
                    (최근 부하, 수면 효율 등을 고려해 짧고 날카롭게 팩트 폭행 및 칭찬)
                    
                    ### 🎯 2. 내일 추천하는 훈련 루틴 상세 설계
                    (부족한 부분 보완. 예: 심폐가 부족하면 매스템포런 추천, 하체 부하가 심했으면 상체 컴플렉스 추천 등 구체적이고 전문적인 드릴명 명시)
                    
                    ### 🔋 3. 내일의 휴식 필요도 스케일
                    (1: 완전 풀트레이닝 가능 ~ 10: 강제 휴식 요망. 숫자 스케일과 함께 이유 설명)
                    """
                    
                    report_text = ask_gemini(prompt)
                    st.success("✨ 수석 코치의 데이터 분석 처방전이 도착했습니다.")
                    st.markdown(report_text)
                except Exception as e:
                    st.error(f"AI 코치 호출 중 에러 발생: {e}")
        else:
            st.error("⚠️ AI 코치를 호출하려면 먼저 API 오류를 해결해야 합니다!")

st.write("---")
if st.button("🔒 안전하게 로그아웃"):
    st.session_state.login_success = False
    st.rerun()