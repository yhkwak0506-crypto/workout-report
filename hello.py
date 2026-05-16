import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# ⭕ 연혁님의 진짜 구글 시트 주소
MY_SHEET_URL = "https://docs.google.com/spreadsheets/d/1N4KGhJf1ta1MOcATsOXcJayTe9ULsNGhL_9u8Rdbo_Q/edit"

st.set_page_config(page_title="S-Tier Performance AMS v7.9", layout="wide")

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
    
    # 🟢 [업데이트] 첫 번째 탭 명칭을 '운동로그'로 명시적 매핑
    try:
        sheet_master = doc.worksheet("운동로그")
    except Exception:
        # 혹시 명칭이 매칭되지 않을 경우를 대비한 가드 코드 (기존 0번째 시트 활용 및 이름 변경)
        sheet_master = doc.get_worksheet(0)
        
    # 두 번째 워크시트: 식단 전용 데이터베이스
    try:
        sheet_diet = doc.worksheet("식단로그")
    except Exception:
        sheet_diet = doc.add_worksheet(title="식단로그", rows="1000", cols="10")
        sheet_diet.append_row(["날짜", "체중", "아침 식단", "점심 식단", "저녁 식단", "간식/보충제", "식단 클린도"])
        
except Exception as e:
    st.error(f"🚨 구글 시트 연동 실패. 주소 또는 시트 탭 설정을 확인하세요. 에러: {e}")
    st.stop()

# ==========================================
# 🗂️ 세션 상태 초기화
# ==========================================
if 'football_drills' not in st.session_state: st.session_state.football_drills = []
if 'cardio_drills' not in st.session_state: st.session_state.cardio_drills = []
if 'weight_sets' not in st.session_state: st.session_state.weight_sets = []

today = datetime.now().strftime("%Y-%m-%d")

# 운동로그 마스터 시트 저장 함수
def save_to_master_sheet(row_dict):
    columns_order = [
        "날짜", "공복 체중", "훈련 볼륨", "평균 심박", "최대 심박", 
        "심박 회복량(HRR)", "상세 훈련 내용 (SOP 및 실전 역학)", "생리학적 분석 및 영양/비고"
    ]
    row_values = [str(row_dict.get(col, "")) for col in columns_order]
    sheet_master.append_row(row_values)

# ==========================================
# 🚀 메인 인터페이스
# ==========================================
st.title("⚡ S-Tier Athlete Management System (v7.9)")

tab_morning, tab_workout, tab_diet, tab_report = st.tabs([
    "🌅 모닝 바이오메트릭스", 
    "🏋️ 운동 & 피지컬 대시보드", 
    "🥗 인텐시브 식단 관리", 
    "📊 제미나이 AI 분석 보고서"
])

# ------------------------------------------
# TAB 1: 모닝 바이오메트릭스 (아침 전용 패스트 업로드)
# ------------------------------------------
with tab_morning:
    st.header("🌅 아침 기상 직후 컨디션 & 웰니스 패스트 로그")
    st.info("아침에 눈뜨자마자 공복 체중과 수면 상태를 10초 만에 기록하고 업로드하는 공간입니다.")
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        m_weight = st.number_input("⚖️ 오늘의 공복 체중 (kg)", min_value=0.0, max_value=150.0, value=77.5, step=0.1, key='m_w')
    with col_m2:
        m_sleep = st.number_input("💤 수면 시간 (hours)", min_value=0.0, max_value=24.0, value=7.5, step=0.5, key='m_s')
    with col_m3:
        m_quality = st.slider("⭐ 수면의 질 (1:최악 ~ 10:최상)", 1, 10, 7, key='m_q')
    with col_m4:
        m_cond = st.slider("🏃 기상 직후 신체 컨디션 스코어", 1, 10, 7, key='m_c')
        
    with st.expander("📏 [선택 사항] 신체 정밀 사이즈 측정 데이터 추가"):
        c_size1, c_size2, c_size3, c_size4 = st.columns(4)
        with c_size1: chest_sz = st.number_input("가슴 둘레 (cm)", value=0.0, step=0.1)
        with c_size2: arm_sz = st.number_input("팔 둘레 (cm)", value=0.0, step=0.1)
        with c_size3: waist_sz = st.number_input("허리 둘레 (cm)", value=0.0, step=0.1)
        with c_size4: thigh_sz = st.number_input("허벅지 둘레 (cm)", value=0.0, step=0.1)

    if st.button("🚀 모닝 데이터 운동로그 시트 즉시 전송"):
        size_str = f" [사이즈 가슴:{chest_sz}/팔:{arm_sz}/허리:{waist_sz}/허벅지:{thigh_sz}]" if chest_sz > 0 else ""
        sop_text = f"[아침 기상 기록] 신체 컨디션 스코어: {m_cond}/10{size_str}"
        analysis_text = f"수면:{m_sleep}h(질:{m_quality}) | 공복체중 정밀 동기화 완료."
        
        data = {
            "날짜": today, "공복 체중": f"{m_weight}kg", "훈련 볼륨": "기상 세션",
            "평균 심박": 0, "최대 심박": 0, "심박 회복량(HRR)": "MORNING",
            "상세 훈련 내용 (SOP 및 실전 역학)": sop_text, "생리학적 분석 및 영양/비고": analysis_text
        }
        save_to_master_sheet(data)
        st.success("오늘 아침 바이오메트릭스 지표가 [운동로그] 데이터베이스에 깔끔하게 선반영되었습니다! 🔥")
        st.rerun()

# ------------------------------------------
# TAB 2: 운동 및 피지컬 대시보드
# ------------------------------------------
with tab_workout:
    st.header("🧠 오늘의 트레이닝 세션 로깅")
    
    time_of_day = st.radio("⏰ 세션 진행 시간대", ("☀️ 오전", "🌤️ 오후", "🌙 저녁/야간"), horizontal=True)
    workout_type = st.selectbox("👇 오늘의 세션 종류 선택", ("개인 축구 훈련", "유산소/조깅", "실전 경기", "웨이트 트레이닝", "휴식(Recovery)"))
    post_condition = st.slider("🥵 오늘 체감 피로도/RPE (휴식일 경우 휴식 만족도)", 1, 10, 5)
    st.write("---")

    # --- 1. 개인 축구 훈련 세션 ---
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
            sop_text = f"[{time_of_day} 축구] 장소: {location} | 루틴: {' ➡️ '.join(st.session_state.football_drills)}"
            analysis_text = f"RPE피로도:{post_condition}/10 | 필드 트레이닝 완료."
            data = {
                "날짜": today, "공복 체중": "세션 기록", "훈련 볼륨": f"{distance}km",
                "평균 심박": hr_avg, "최대 심박": hr_max, "심박 회복량(HRR)": hr_recovery,
                "상세 훈련 내용 (SOP 및 실전 역학)": sop_text, "생리학적 분석 및 영양/비고": analysis_text
            }
            save_to_master_sheet(data)
            st.session_state.football_drills = []
            st.success("구글 운동로그 시트에 완벽히 동기화되었습니다!")
            st.rerun()

    # --- 2. 유산소/조깅 및 맨몸 폭발력 세션 ---
    elif workout_type == "유산소/조깅":
        st.subheader("🏃 조깅, 유산소 및 피지컬 드릴 시퀀스")
        c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
        with c1:
            cardio_opts = [
                "조깅 (5분 페이스)", "턱걸이", "딥스", "턱걸이 + 오르막 컴플렉스", 
                "A skip (오르막)", "Single leg jump", "Two footed jumps", 
                "Single leg alternative broad jump", "오르막길 스프린트", "15/15 매스템포런", "직접 입력"
            ]
            c_drill = st.selectbox("📋 유산소/피지컬 종목 선택", cardio_opts)
            if c_drill == "직접 입력": c_drill = st.text_input("종목명 직접 입력")
            
            if c_drill == "오르막길 스프린트":
                effort_pct = st.slider("⚡ 스프린트 강도 설정 (%)", 50, 100, 100, 5, key='hill_pct')
                c_drill = f"오르막 스프린트({effort_pct}%)"
            elif c_drill == "턱걸이 + 오르막 컴플렉스":
                complex_pull = st.number_input("➔ 1회당 턱걸이 갯수", min_value=1, value=5, step=1)
                complex_dash = st.slider("➔ 이어지는 오르막 대쉬 강도 (%)", 50, 100, 100, 5, key='complex_pct')
                c_drill = f"턱걸이({complex_pull}개)+오르막대쉬({complex_dash}%) 컴플렉스"
                
        with c2: 
            if "턱걸이" in c_drill or c_drill == "딥스":
                c_dist = st.text_input("개당 갯수", value="10회", key='c_val')
            else:
                c_dist = st.text_input("거리/시간", value="5km", key='c_val')
        with c3: c_reps = st.number_input("반복/횟수(세트 내 반복)", min_value=1, step=1, key='c_rep')
        with c4: c_sets = st.number_input("총 세트 수", min_value=1, step=1, key='c_set')
        
        if st.button("➕ 유산소/피지컬 세션 추가"):
            st.session_state.cardio_drills.append(f"{c_drill}({c_dist} x {c_reps}회 / {c_sets}세트)")
            
        if st.session_state.cardio_drills:
            st.warning("👉 **현재 시퀀스 타임라인:** " + " ➡️ ".join(st.session_state.cardio_drills))
            if st.button("🗑️ 시퀀스 초기화"): st.session_state.cardio_drills = []; st.rerun()

        col1, col2, col3, col4 = st.columns(4)
        with col1: total_distance = st.number_input("🏃 전체 총 이동/러닝 거리 (km)", min_value=0.0, step=0.1, key='c_total_dist')
        with col2: hr_avg = st.number_input("❤️ 세션 평균 심박", min_value=0, step=1, key='c_avg_hr')
        with col3: hr_max = st.number_input("🔥 세션 최대 심박", min_value=0, step=1, key='c_max_hr')
        with col4: hr_recovery = st.text_input("📉 심박 회복량(HRR)", key='c_hrr')
            
        if st.button("💾 유산소/피지컬 데이터 구글 저장"):
            sop_text = f"[{time_of_day} 유산소] 시퀀스: {' ➡️ '.join(st.session_state.cardio_drills)}"
            analysis_text = f"피로도/RPE: {post_condition}/10 | 심폐 자극 세션 완료."
            data = {
                "날짜": today, "공복 체중": "세션 기록", "훈련 볼륨": f"{total_distance}km",
                "평균 심박": hr_avg, "최대 심박": hr_max, "심박 회복량(HRR)": hr_recovery,
                "상세 훈련 내용 (SOP 및 실전 역학)": sop_text, "생리학적 분석 및 영양/비고": analysis_text
            }
            save_to_master_sheet(data)
            st.session_state.cardio_drills = []
            st.success("구글 운동로그 시트에 트레이닝 시퀀스가 완벽히 기록되었습니다!")
            st.rerun()

    # --- 3. 실전 경기 세션 ---
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
            analysis_text = f"RPE: {post_condition}/10"
            data = {
                "날짜": today, "공복 체중": "경기 세션", "훈련 볼륨": f"{distance}km",
                "평균 심박": hr_avg, "최대 심박": hr_max, "심박 회복량(HRR)": hr_recovery,
                "상세 훈련 내용 (SOP 및 실전 역학)": sop_text, "생리학적 분석 및 영양/비고": analysis_text
            }
            save_to_master_sheet(data)
            st.success("실전 데이터가 연동되었습니다!")
            st.rerun()

    # --- 4. 웨이트 세션 ---
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
                    "날짜": today, "공복 체중": "스트랭스", "훈련 볼륨": f"{len(st.session_state.weight_sets)}개 종목",
                    "평균 심박": 0, "최대 심박": 0, "심박 회복량(HRR)": "-",
                    "상세 훈련 내용 (SOP 및 실전 역학)": sop_text, "생리학적 분석 및 영양/비고": f"RPE 피로도: {post_condition}/10"
                }
                save_to_master_sheet(data)
                st.session_state.weight_sets = [] 
                st.success("웨이트 로그 동기화 완료!")
                st.rerun()

    # --- 5. 휴식(Recovery) 세션 ---
    elif workout_type == "휴식(Recovery)":
        st.subheader("🧘 선수 전용 액티브 리커버리 & 휴식 로그")
        col_rec1, col_rec2 = st.columns(2)
        with col_rec1:
            recovery_activity = st.multiselect(
                "📋 리커버리 형태 선택", 
                ["완전 휴식(No Activity)", "가벼운 회복 걷기", "리커버리 조깅", "동적 스트레칭", "폼롤러/마사지 Gun", "사우나/냉온탕 리커버리"]
            )
            rec_distance = st.number_input("🏃 걷기 또는 회복 조깅 총 거리 (km)", min_value=0.0, step=0.1, value=0.0)
        with col_rec2:
            recovery_memo = st.text_area("📝 오늘의 신체 회복 상태 메모")
            
        if st.button("💾 휴식 데이터 구글 저장"):
            activities_str = ", ".join(recovery_activity) if recovery_activity else "완전 휴식"
            sop_text = f"[휴식/리커버리] 활동: {activities_str} | 거리: {rec_distance}km | 내용: {recovery_memo}"
            analysis_text = f"휴식만족도: {post_condition}/10"
            data = {
                "날짜": today, "공복 체중": "휴식", "훈련 볼륨": f"회복 {rec_distance}km",
                "평균 심박": 0, "최대 심박": 0, "심박 회복량(HRR)": "REST",
                "상세 훈련 내용 (SOP 및 실전 역학)": sop_text, "생리학적 분석 및 영양/비고": analysis_text
            }
            save_to_master_sheet(data)
            st.success("오늘의 휴식 기록 동기화 완료!")
            st.rerun()

# ------------------------------------------
# 🥗 TAB 3: 인텐시브 식단 관리 (식단로그 단독 격리)
# ------------------------------------------
with tab_diet:
    st.header("🥗 영양 섭취 및 매크로 매니지먼트 (식단 전용 DB)")
    st.info("여기에 기재되는 식단 데이터는 구글 시트의 별도 탭인 [식단로그]에 단독 누적 관리됩니다.")
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        d_weight = st.number_input("⚖️ 현재 참고용 체중 (kg)", min_value=0.0, max_value=150.0, value=77.5, step=0.1, key='d_w_val')
        breakfast = st.text_area("🌅 아침 식단 기록", height=80, placeholder="예: 닭가슴살 150g, 오트밀 80g, 사과 1개")
        lunch = st.text_area("☀️ 점심 식단 기록", height=80, placeholder="예: 소고기 우둔살 200g, 현미밥 한 공기, 샐러드")
    with col_d2:
        dinner = st.text_area("🌙 저녁 식단 기록", height=80, placeholder="예: 연어 구이 200g, 고구마 150g, 아스파라거스")
        snacks = st.text_area("🥤 간식 및 단백질 보충제", height=80, placeholder="예: 운동 직후 신타6 1스쿱, 아몬드 10알")
        diet_score = st.slider("🎯 오늘의 식단 클린도 (1:치팅데이 ~ 10:초클린)", 1, 10, 8)
        
    if st.button("💾 식단 전용 데이터베이스에 단독 저장"):
        diet_row = [today, f"{d_weight}kg", breakfast, lunch, dinner, snacks, f"{diet_score}점"]
        sheet_diet.append_row(diet_row)
        st.success("🎉 식단 데이터가 독립 시트 [식단로그]에 안전하게 격리 저장되었습니다!")
        st.rerun()
        
    st.write("---")
    st.subheader("📊 식단 독립 전용 AI 보고서")
    if st.button("🤖 오직 식단 데이터만 심층 분석하여 영양 리포트 빌드"):
        with st.spinner("독립 식단로그의 타임라인 매크로를 연산 중..."):
            st.success("✨ 곽연혁 선수의 맞춤형 전용 식단 팔로우 보고서가 생성되었습니다.")
            st.markdown(f"### 📑 Diet & Nutrition Intensive Report")
            st.markdown(f"**진단 일자:** {today} | **대상:** 연혁 선수 (Elite Footballer)")
            
            c_dr1, c_dr2 = st.columns(2)
            with c_dr1: