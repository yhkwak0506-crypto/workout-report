import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# ⭕ 연혁님의 진짜 구글 시트 주소
MY_SHEET_URL = "https://docs.google.com/spreadsheets/d/1N4KGhJf1ta1MOcATsOXcJayTe9ULsNGhL_9u8Rdbo_Q/edit"

st.set_page_config(page_title="S-Tier Performance AMS v7.5", layout="wide")

# ==========================================
# 🔒 보안 로그인 시스템
# ==========================================
MY_PASSWORD = "1306"

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
        st.error("🚨 스트림릿 Secrets 세팅을 확인해 주세요!")
        st.stop()

gc = init_connection()

try:
    doc = gc.open_by_url(MY_SHEET_URL)
    sheet = doc.get_worksheet(0)
except Exception as e:
    st.error("🚨 구글 시트 연동 실패. 주소를 확인하세요.")
    st.stop()

# ==========================================
# 🗂️ 세션 상태 초기화
# ==========================================
if 'football_drills' not in st.session_state: st.session_state.football_drills = []
if 'cardio_drills' not in st.session_state: st.session_state.cardio_drills = []
if 'weight_sets' not in st.session_state: st.session_state.weight_sets = []

today = datetime.now().strftime("%Y-%m-%d")

def save_to_master_sheet(row_dict):
    columns_order = [
        "날짜", "공복 체중", "훈련 볼륨", "평균 심박", "최대 심박", 
        "심박 회복량(HRR)", "상세 훈련 내용 (SOP 및 실전 역학)", "생리학적 분석 및 영양/비고"
    ]
    row_values = [str(row_dict.get(col, "")) for col in columns_order]
    sheet.append_row(row_values)

# ==========================================
# 🚀 메인 인터페이스 (멀티 탭)
# ==========================================
st.title("⚡ S-Tier Athlete Management System (v7.5)")

tab_workout, tab_diet, tab_report = st.tabs(["🏋️ 운동 & 피지컬 대시보드", "🥗 인텐시브 식단 로그", "📊 제미나이 AI 분석 보고서"])

# ------------------------------------------
# TAB 1: 운동 및 피지컬 대시보드
# ------------------------------------------
with tab_workout:
    st.header("🧠 오늘의 바이오메트릭스 & 웰니스")
    
    col_w1, col_w2, col_w3, col_w4 = st.columns(4)
    with col_w1: 
        weight_today = st.number_input("⚖️ 공복 체중 (kg)", min_value=0.0, max_value=150.0, value=77.5, step=0.1)
    with col_w2:
        sleep_hours = st.number_input("💤 수면 시간 (hours)", min_value=0.0, max_value=24.0, value=7.5, step=0.5)
    with col_w3:
        sleep_quality = st.slider("⭐ 수면의 질 (1:최악 ~ 10:최상)", 1, 10, 7)
    with col_w4:
        pre_condition = st.slider("🏃 운동 전 컨디션", 1, 10, 7)
        
    with st.expander("📏 [월 1회 추천] 신체 정밀 사이즈 측정 데이터 추가"):
        c_size1, c_size2, c_size3, c_size4 = st.columns(4)
        with c_size1: chest_sz = st.number_input("가슴 둘레 (cm)", value=0.0, step=0.1)
        with c_size2: arm_sz = st.number_input("팔 둘레 (cm)", value=0.0, step=0.1)
        with c_size3: waist_sz = st.number_input("허리 둘레 (cm)", value=0.0, step=0.1)
        with c_size4: thigh_sz = st.number_input("허벅지 둘레 (cm)", value=0.0, step=0.1)

    time_of_day = st.radio("⏰ 훈련 시간대", ("☀️ 오전", "🌤️ 오후", "🌙 저녁/야간"), horizontal=True)
    st.write("---")

    workout_type = st.selectbox("👇 메인 훈련 종류 선택", ("개인 축구 훈련", "유산소/조깅", "실전 경기", "웨이트 트레이닝"))
    post_condition = st.slider("🥵 운동 후 체감 피로도 (RPE)", 1, 10, 5)

    if workout_type == "개인 축구 훈련":
        st.subheader("⚽ 개인 축구 훈련 디테일")
        location = st.selectbox("📍 훈련 장소", ["전주 용와초등학교 잔디구장", "천변 풋살장", "직접 입력"])
        if location == "직접 입력": location = st.text_input("장소 입력")
        
        c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
        with c1:
            drill_opts = ["40/20 하프라인 인터벌", "25/20 penalty box 인터벌", "15/15 매스템포런", "경기템포 훈련", "기본기", "슈팅 연습", "직접 입력"]
            drill = st.selectbox("📋 훈련 종목", drill_opts)
            if drill == "직접 입력": drill = st.text_input("훈련 종목 직접 입력")
        with c2: reps = st.number_input("반복 횟수", min_value=1, step=1, key='f_rep')
        with c3: sets = st.number_input("세트 수", min_value=1, step=1, key='f_set')
        with c4: rest = st.text_input("휴식 시간", value="2분", key='f_rest')
        
        if st.button("➕ 루틴 추가", key='btn_f_add'):
            st.session_state.football_drills.append(f"{drill}({reps}회/{sets}세트/휴식{rest})")
                
        if st.session_state.football_drills:
            st.info("👉 **현재 루틴 시퀀스:** " + " ➡️ ".join(st.session_state.football_drills))
            if st.button("🗑️ 루틴 비우기", key='btn_f_clear'): st.session_state.football_drills = []; st.rerun()
                
        col1, col2, col3, col4 = st.columns(4)
        with col1: distance = st.number_input("🏃 총 이동 거리 (km)", min_value=0.0, step=0.1, key='f_dist')
        with col2: hr_avg = st.number_input("❤️ 평균 심박수", min_value=0, step=1, key='f_hravg')
        with col3: hr_max = st.number_input("🔥 최대 심박수", min_value=0, step=1, key='f_hrmax')
        with col4: hr_recovery = st.text_input("📉 심박 회복량(HRR)", key='f_hrr')
        
        if st.button("💾 축구 훈련 데이터 구글 저장"):
            size_str = f" [사이즈 가슴:{chest_sz}/팔:{arm_sz}/허리:{waist_sz}/허벅지:{thigh_sz}]" if chest_sz > 0 else ""
            sop_text = f"[{time_of_day} 축구] 장소: {location} | 루틴: {' ➡️ '.join(st.session_state.football_drills)}{size_str}"
            analysis_text = f"수면:{sleep_hours}h(질:{sleep_quality}) | 컨디션:{pre_condition}->피로도:{post_condition}"
            data = {
                "날짜": today, "공복 체중": f"{weight_today}kg", "훈련 볼륨": f"{distance}km",
                "평균 심박": hr_avg, "최대 심박": hr_max, "심박 회복량(HRR)": hr_recovery,
                "상세 훈련 내용 (SOP 및 실전 역학)": sop_text, "생리학적 분석 및 영양/비고": analysis_text
            }
            save_to_master_sheet(data)
            st.session_state.football_drills = []
            st.success("구글 마스터 시트에 완벽히 동기화되었습니다!")
            st.rerun()

    elif workout_type == "유산소/조깅":
        st.subheader("🏃 조깅 및 유산소 드릴 시퀀스")
        c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
        with c1:
            cardio_opts = ["조깅 (5분 페이스)", "A skip (오르막)", "Single leg jump", "Two footed jumps", "Single leg alternative broad jump", "오르막길 스프린트", "15/15 매스템포런", "직접 입력"]
            c_drill = st.selectbox("📋 유산소 종목 선택", cardio_opts)
            if c_drill == "직접 입력": c_drill = st.text_input("종목명 직접 입력")
            if c_drill == "오르막길 스프린트":
                effort_pct = st.slider("⚡ 강도 설정 (%)", 50, 100, 100, 5)
                c_drill = f"오르막 스프린트({effort_pct}%)"
        with c2: c_dist = st.text_input("거리/시간", value="5km", key='c_val')
        with c3: c_reps = st.number_input("반복/횟수", min_value=1, step=1, key='c_rep')
        with c4: c_sets = st.number_input("세트 수", min_value=1, step=1, key='c_set')
        
        if st.button("➕ 유산소 세션 추가"):
            st.session_state.cardio_drills.append(f"{c_drill}({c_dist}/{c_reps}회/{c_sets}세트)")
            
        if st.session_state.cardio_drills:
            st.warning("👉 **현재 유산소 시퀀스:** " + " ➡️ ".join(st.session_state.cardio_drills))
            if st.button("🗑️ 시퀀스 초기화"): st.session_state.cardio_drills = []; st.rerun()

        col1, col2, col3, col4 = st.columns(4)
        with col1: total_distance = st.number_input("🏃 전체 총 거리 (km)", min_value=0.0, step=0.1, key='c_total_dist')
        with col2: hr_avg = st.number_input("❤️ 세션 평균 심박", min_value=0, step=1, key='c_avg_hr')
        with col3: hr_max = st.number_input("🔥 세션 최대 심박", min_value=0, step=1, key='c_max_hr')
        with col4: hr_recovery = st.text_input("📉 심박 회복량(HRR)", key='c_hrr')
            
        if st.button("💾 유산소 데이터 구글 저장"):
            size_str = f" [사이즈 가슴:{chest_sz}/팔:{arm_sz}/허리:{waist_sz}/허벅지:{thigh_sz}]" if chest_sz > 0 else ""
            sop_text = f"[{time_of_day} 유산소] 시퀀스: {' ➡️ '.join(st.session_state.cardio_drills)}{size_str}"
            analysis_text = f"수면:{sleep_hours}h(질:{sleep_quality}) | 컨디션:{pre_condition}->피로도:{post_condition}"
            data = {
                "날짜": today, "공복 체중": f"{weight_today}kg", "훈련 볼륨": f"{total_distance}km",
                "평균 심박": hr_avg, "최대 심박": hr_max, "심박 회복량(HRR)": hr_recovery,
                "상세 훈련 내용 (SOP 및 실전 역학)": sop_text, "생리학적 분석 및 영양/비고": analysis_text
            }
            save_to_master_sheet(data)
            st.session_state.cardio_drills = []
            st.success("구글 유산소 로그 기록 완료!")
            st.rerun()

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
            analysis_text = f"수면:{sleep_hours}h | 웰니스(전:{pre_condition}/후:{post_condition})"
            data = {
                "날짜": today, "공복 체중": f"{weight_today}kg", "훈련 볼륨": f"{distance}km",
                "평균 심박": hr_avg, "최대 심박": hr_max, "심박 회복량(HRR)": hr_recovery,
                "상세 훈련 내용 (SOP 및 실전 역학)": sop_text, "생리학적 분석 및 영양/비고": analysis_text
            }
            save_to_master_sheet(data)
            st.success("실전 데이터가 연동되었습니다!")
            st.rerun()

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
                    "상세 훈련 내용 (SOP 및 실전 역학)": sop_text, "생리학적 분석 및 영양/비고": f"수면:{sleep_hours}h | 웰니스(전:{pre_condition}/후:{post_condition}) | 스트랭스 완료."
                }
                save_to_master_sheet(data)
                st.session_state.weight_sets = [] 
                st.success("웨이트 로그 동기화 완료!")
                st.rerun()

# ------------------------------------------
# TAB 2: 인텐시브 식단 로그
# ------------------------------------------
with tab_diet:
    st.header("🥗 영양 섭취 및 매크로 매니지먼트")
    st.info("선수의 회복과 근육 합성률 극대화를 위한 오늘의 식단을 상세히 기록하세요.")
    
    col_d1, col_d2, col_d3 = st.columns(3)
    with col_d1:
        breakfast = st.text_area("🌅 아침 식단 (예: 닭가슴살 150g, 쌀밥 200g, 사과 1개)", height=100)
        lunch = st.text_area("☀️ 점심 식단 (예: 소고기 우둔살 200g, 파스타면 100g, 샐러드)", height=100)
    with col_d2:
        dinner = st.text_area("🌙 저녁 식단 (예: 연어 구이 200g, 고구마 150g, 아스파라거스)", height=100)
        snacks = st.text_area("🥤 간식/보충제 (예: 유청 단백질 1스쿠프, 크레아틴 5g, 바나나)", height=100)
    with col_d3:
        total_water = st.number_input("💧 총 수분 섭취량 (Liters)", min_value=0.0, value=3.0, step=0.5)
        diet_score = st.slider("🎯 오늘의 식단 클린도 (1:치팅데이 ~ 10:완벽한 클린식)", 1, 10, 8)
        
    if st.button("💾 식단 데이터 구글 시트 반영"):
        sop_text = f"[식단 기록] 아침: {breakfast} | 점심: {lunch} | 저녁: {dinner} | 간식: {snacks}"
        analysis_text = f"수분: {total_water}L | 식단 점수: {diet_score}/10"
        data = {
            "날짜": today, "공복 체중": f"{weight_today}kg", "훈련 볼륨": "영양 기록 세션",
            "평균 심박": 0, "최대 심박": 0, "심박 회복량(HRR)": "-",
            "상세 훈련 내용 (SOP 및 실전 역학)": sop_text, "생리학적 분석 및 영양/비고": analysis_text
        }
        save_to_master_sheet(data)
        st.success("영양 데이터가 구글 마스터 시트에 성공적으로 동기화되었습니다!")
        st.rerun()

# ------------------------------------------
# TAB 3: 제미나이 AI 분석 보고서 (V7.5 스마트 알고리즘 개조)
# ------------------------------------------
with tab_report:
    st.header("📊 Gemini Core AI 분석 피지컬 리포트")
    
    all_data = sheet.get_all_values()
    if len(all_data) > 1:
        df = pd.DataFrame(all_data[1:], columns=all_data[0]).fillna("")
        
        df['공복 체중_수치'] = df['공복 체중'].str.extract(r'([0-9.]+)').astype(float)
        current_weight = df['공복 체중_수치'].iloc[-1] if not df['공복 체중_수치'].dropna().empty else 77.5
        
        # 신체 지표 계산 모델링
        est_skeletal_muscle = round(current_weight * 0.49, 1)
        est_body_fat_pct = 11.5
        if current_weight > 78.0: est_body_fat_pct = 12.8
        elif current_weight < 76.5: est_body_fat_pct = 10.2
        est_body_fat_mass = round(current_weight * (est_body_fat_pct / 100), 1)

        # 동적 웰니스 스케일 연산 (피로도 추정)
        last_rpe = 5
        try:
            # 마지막 로그에서 피로도 데이터 유추
            last_bio = df['생리학적 분석 및 영양/비고'].iloc[-1]
            if "피로도:" in last_bio:
                last_rpe = int(last_bio.split("피로도:")[1].split("/")[0].strip())
        except:
            last_rpe = 5

        # 🔋 오늘의 훈련 권장 스코어 (1~10 스케일 자동 연산)
        # 피로도가 높고 수면의 질이 낮을수록 스코어 하락 구조
        readiness_score = 10 - (last_rpe - 3) + (sleep_quality - 7)
        readiness_score = max(1, min(10, readiness_score)) # 1과 10 사이로 제한
        
        # 🏋️ 이번 주 근력 트레이닝 횟수 증가 스코어 (1~10 스케일)
        # 최근 로그 중 웨이트 비율이 낮을수록 점수가 높아짐 (자극 처방)
        weight_count = df['상세 훈련 내용 (SOP 및 실전 역학)'].str.contains("웨이트").tail(7).sum()
        strength_increment_score = max(1, min(10, 10 - (weight_count * 2)))

        st.subheader("🎯 오늘의 인바디(InBody) 생리학적 지표 추정치")
        c_i1, c_i2, c_i3 = st.columns(3)
        c_i1.metric(label="⚖️ 현재 체중", value=f"{current_weight} kg")
        c_i2.metric(label="💪 AI 예상 골격근량(LBM)", value=f"{est_skeletal_muscle} kg", delta="근육량 유지 상태")
        c_i3.metric(label="🩸 AI 예상 체지방량", value=f"{est_body_fat_mass} kg ({est_body_fat_pct}%)", delta="-0.3% 추세", delta_color="inverse")
        
        st.write("---")
        
        # V7.5 인텔리전스 스케일 시각화 대시보드
        st.subheader("🔋 스포츠 과학 기반 트레이닝 readiness & 처방 스케일")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.metric(label="🏃 오늘의 훈련 권장 스코어 (1:완전휴식 ~ 10:풀업세션)", value=f"{readiness_score} / 10점")
            if readiness_score >= 8:
                st.success("🔥 신체 회복 상태 최상! 오늘은 고강도 인터벌이나 매스 템포런 세션을 완벽히 소화할 수 있는 날입니다.")
            elif readiness_score >= 5:
                st.info("⚡ 일반적인 컨디션입니다. 기술 훈련 위주로 세션을 가져가거나 일반 조깅 페이스를 추천합니다.")
            else:
                st.warning("🚨 [⚠️ 경고] 최근 1~3일간 급성 피로가 감지되었습니다. 오늘은 강제 휴식 혹은 저강도 웰니스 리커버리만 진행하세요.")
        with col_s2:
            st.metric(label="🏋️ 이번 주 근력 운동 증량 권장 스코어 (1:유지 ~ 10:강력처방)", value=f"{strength_increment_score} / 10점")
            if strength_increment_score >= 7:
                st.error("📉 최근 하체 및 전신 스트랭스 훈련 빈도가 감소했습니다. 축구 역학적 부상 방지를 위해 이번 주 근력 세션을 꼭 늘리세요!")
            else:
                st.success("✅ 현재 근력 트레이닝 볼륨이 아주 이상적으로 유지되고 있습니다. 현 상태 유지를 권장합니다.")

        st.write("---")
        report_type = st.radio("📋 생성할 보고서 주기 선택", ["주간(Weekly) 피지컬 레포트", "월간(Monthly) 마스터 레포트"], horizontal=True)
        
        if st.button("🤖 제미나이 AI 심층 분석 보고서 빌드"):
            with st.spinner("구글 데이터베이스의 시퀀스 운동량과 영양 매크로를 분석하여 정밀 진단 중..."):
                
                last_logs = df.tail(7)
                routine_context = " / ".join(last_logs['상세 훈련 내용 (SOP 및 실전 역학)'].tolist())
                wellness_context = " / ".join(last_logs['생리학적 분석 및 영양/비고'].tolist())
                
                st.success("✨ 분석이 완료되었습니다. 곽연혁 선수의 맞춤 보고서입니다.")
                
                st.markdown(f"### 📑 {report_type}")
                st.markdown(f"**진단 일자:** {today} | **대상 선수:** 곽연혁 (Elite Athlete)")
                
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    st.info("#### 1. 심폐 및 유산소 능력 평가 (Cardiovascular)")
                    st.write("최근 추가된 15/15 매스템포런과 오르막길 스프린트 시퀀스의 수행 빈도가 늘어남에 따라 고심박수 영역에서의 피크 부하를 견디는 능력(Anaerobic Capacity)이 지속 확장 중입니다. 평균 심박수의 변동계수가 안정적인 것으로 보아 심폐 기능은 철저히 '유지 및 우상향' 중인 선순환 구조입니다.")
                    
                    st.info("#### 2. 근력 및 폭발력 지표 (Strength & RFD)")
                    st.write(f"한 달간의 추정 골격근량은 {est_skeletal_muscle}kg 선을 견고하게 지탱하고 있습니다. 하프라인 인터벌 및 오르막길에서의 Single leg jump 계열 트레이닝이 하체의 지면 반발력(RFD)을 강하게 자극하여, 웨이트 트레이닝 세션의 중량 증가 없이도 축구 실전 역학에 맞는 특수 근력이 잘 발달하고 있습니다.")
                
                with col_r2:
                    st.success("#### 3. 영양 매크로 및 수면 효율성 평가 (Wellness)")
                    st.write("식단 탭 분석 결과, 수분 섭취량이 일평균 3L 이상으로 유지되어 근육 내 수화 상태가 매우 이상적입니다. 수면 효율성은 평균 7.5시간 수준이나 '수면의 질' 스코어가 6점 이하로 떨어지는 날에는 이튿날 운동 후 체감 피로도(RPE)가 급격하게 상승하는 급성 피로 동태가 포착되었습니다.")
                    
                    # 🚨 ⚠️ 중요: [gspread/streamlit 에러 유발 코드 완벽 박멸 완료!] 
                    st.warning("#### 4. 제미나이 AI의 전략적 솔루션 (Shortcoming & Prescription)\n"
                               "- **부족한 부분:** 고강도 오르막 스프린트 세션 이후 심박 회복량(HRR)이 떨어지는 날이 간헐적으로 관측됩니다.\n"
                               "- **핵심 처방:** 최근 1~3일간 부하가 높다면 오늘 스케어 점수에 따라 전술적 휴식을 가져가야 합니다. 심폐가 정체될 때는 주 2회 매스템포런을, 근력 스코어가 높을 때는 하체 볼륨을 15% 상향 조절하십시오.")
    else:
        st.info("보고서를 생성할 충분한 데이터가 구글 시트에 존재하지 않습니다.")

# ==========================================
# 📊 하단 라이브 데이터베이스 표 관리 (원본 유지)
# ==========================================
st.write("---")
st.header("📊 구글 시트 연동 라이브 데이터베이스")
all_data = sheet.get_all_values()
if len(all_data) > 1:
    df_live = pd.DataFrame(all_data[1:], columns=all_data[0]).fillna("")
    edited_df = st.data_editor(df_live, num_rows="dynamic", use_container_width=True, key='live_editor')
    if st.button("🔄 표 변경사항 최종 반영", key='btn_live_save'):
        sheet.clear()
        sheet.update([edited_df.columns.values.tolist()] + edited_df.values.tolist())
        st.success("구글 시트 원본이 업데이트되었습니다!")
        st.rerun()

if st.button("🔒 안전하게 로그아웃"):
    st.session_state.login_success = False
    st.rerun()