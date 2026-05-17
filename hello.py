import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timedelta
import core_logic as core  

st.set_page_config(page_title="Data of the Light", layout="wide")

# ==========================================
# 🔒 보안 로그인
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

today = datetime.now().strftime("%Y-%m-%d")

if 'football_drills' not in st.session_state: st.session_state.football_drills = []
if 'cardio_drills' not in st.session_state: st.session_state.cardio_drills = []
if 'weight_sets' not in st.session_state: st.session_state.weight_sets = []

st.sidebar.title("🎖️ 라이브 링크 설정")
bootcamp_mode = st.sidebar.toggle("🪖 31사단 훈련소 모드 활성화", value=False)
if bootcamp_mode: st.sidebar.success("훈련소 모드가 작동 중입니다.")

st.title("⚡ Data of the Light")

tab_body, tab_workout, tab_diet, tab_report = st.tabs([
    "📊 신체 데이터", "🏋️ 운동 데이터", "🥗 식단 데이터", "📈 데이터/리포팅 센터"
])

# ==========================================
# 📊 TAB 1: 신체 데이터
# ==========================================
with tab_body:
    st.header("📊 수면 과학 및 신체 데이터 대시보드")
    m_weight = st.number_input("⚖️ 오늘의 공복 체중 (kg)", min_value=0.0, value=77.5, step=0.1)
    st.session_state["master_weight"] = m_weight

    col_m2, col_m3 = st.columns(2)
    with col_m2: bed_time = st.time_input("🛏️ 불 끄고 누운 시간", value=time(23, 30))
    with col_m3: wake_time = st.time_input("☀️ 실제 일어난 시간", value=time(7, 30))
        
    dt_bed = datetime.combine(date.today(), bed_time)
    dt_wake = datetime.combine(date.today(), wake_time)
    if dt_wake < dt_bed: dt_wake += timedelta(days=1)
    calc_sleep_hours = round(max(0, ((dt_wake - dt_bed).total_seconds() / 60) - 20) * 0.9 / 60, 1)
    st.success(f"🤖 **AI 수면 연산:** 실제 딥슬립 시간 [{calc_sleep_hours}시간]")

    col_m4, col_m5 = st.columns(2)
    with col_m4: m_quality = st.slider("⭐ 체감 수면의 질", 1, 10, 7)
    with col_m5: m_cond = st.slider("🏃 기상 직후 컨디션", 1, 10, 7)
        
    with st.expander("📏 [선택 사항] 공복 신체 측정"):
        c_size1, c_size2, c_size3, c_size4 = st.columns(4)
        with c_size1: chest_sz = st.number_input("가슴 (cm)", step=0.1)
        with c_size2: arm_sz = st.number_input("팔 (cm)", step=0.1)
        with c_size3: waist_sz = st.number_input("허리 (cm)", step=0.1)
        with c_size4: thigh_sz = st.number_input("허벅지 (cm)", step=0.1)

    if st.button("🚀 신체 데이터 저장"):
        row = [today, f"{m_weight}kg", f"{calc_sleep_hours}시간", f"{m_quality}점", f"{m_cond}점",
            f"{chest_sz}cm" if chest_sz>0 else "-", f"{arm_sz}cm" if arm_sz>0 else "-",
            f"{waist_sz}cm" if waist_sz>0 else "-", f"{thigh_sz}cm" if thigh_sz>0 else "-"]
        core.sheet_sleep.append_row(row)
        st.cache_data.clear(); st.success("저장 완료!"); st.rerun()
        
    all_s_body = core.get_cached_data("sleep")
    if len(all_s_body) > 1:
        df_s = pd.DataFrame(all_s_body[1:], columns=all_s_body[0])
        df_s['날짜'] = pd.to_datetime(df_s['날짜'], errors='coerce')
        df_s = df_s.dropna(subset=['날짜'])
        df_s['체중'] = df_s['공복 체중'].apply(core.extract_number)
        df_s = df_s[df_s['체중'] > 0]
        if not df_s.empty:
            df_s['추정 골격근량'] = round(df_s['체중'] * 0.49, 1)
            df_s['추정 체지방률'] = round(11.5 + (df_s['체중'] - 77.5) * 0.7, 1)
            df_s['추정 체지방량'] = round(df_s['체중'] * (df_s['추정 체지방률'] / 100), 1)
            st.write("---")
            c1, c2 = st.columns(2)
            with c1: st.markdown("##### ⚖️ 체중"); st.line_chart(df_s.set_index('날짜')['체중'])
            with c2: st.markdown("##### 💪 근육량"); st.line_chart(df_s.set_index('날짜')['추정 골격근량'])

# ==========================================
# 🏋️ TAB 2: 운동 데이터 
# ==========================================
with tab_workout:
    st.header("🧠 오늘의 트레이닝 세션 로깅")
    m_weight_display = st.number_input("⚖️ 오늘의 공복 체중 연동 (kg)", value=st.session_state.get("master_weight", 77.5), step=0.1)

    if bootcamp_mode:
        st.subheader("🪖 제31사단 훈련소 일과")
        bc_time = st.radio("⏰ 구분", ["메인 일과", "틈새/야간"])
        if bc_time == "메인 일과":
            bc_rt = st.selectbox("📋 훈련", ["일반 일과", "알통 뜀걸음", "영외 전투 훈련", "행군"])
            if st.button("💾 저장"):
                core.save_workout({"날짜": today, "공복 체중": f"{m_weight_display}kg", "훈련 볼륨": "훈련소일과", "상세 훈련 내용 (SOP 및 실전 역학)": f"[훈련소] {bc_rt}", "생리학적 분석 및 영양/비고": "-"})
                st.success("저장 완료!"); st.rerun()
        else:
            # 💡 [V12.1 추가] 축구 및 풋살 분리
            st.info("야간/점호 전 틈새 기량유지 루틴입니다.")
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                v1 = st.checkbox("관물대 턱걸이")
                v2 = st.checkbox("침상 푸쉬업")
                v3 = st.checkbox("맨몸 스쿼트")
                v4 = st.checkbox("코어/플랭크")
            with col_b2:
                v5 = st.checkbox("연병장 축구 ⚽")
                v6 = st.checkbox("연병장 풋살 👟")
                
            if st.button("💾 야간 훈련 저장"):
                lst = [n for b, n in zip([v1,v2,v3,v4,v5,v6], ["턱걸이","푸쉬업","스쿼트","코어","축구","풋살"]) if b]
                rt_str = ",".join(lst) if lst else "미실시"
                core.save_workout({"날짜": today, "공복 체중": f"{m_weight_display}kg", "훈련 볼륨": "야간", "상세 훈련 내용 (SOP 및 실전 역학)": f"[기량유지] {rt_str}", "생리학적 분석 및 영양/비고": "-"})
                st.success("저장 완료!"); st.rerun()
    else:
        time_of_day = st.radio("⏰ 시간대", ("☀️ 오전", "🌤️ 오후", "🌙 저녁/야간"), horizontal=True)
        workout_type = st.selectbox("👇 세션 종류", ("개인 축구 훈련", "유산소/조깅", "실전 경기", "웨이트 트레이닝", "휴식"))
        
        # 개인 축구 훈련 로직
        if workout_type == "개인 축구 훈련":
            location = st.text_input("📍 장소", "전주 용와초등학교 잔디구장")
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            with c1: drill = st.selectbox("📋 종목", ["40/20 인터벌", "매스템포런", "경기템포 훈련", "기본기", "슈팅"])
            with c2: reps = st.number_input("횟수", min_value=1, step=1)
            with c3: sets = st.number_input("세트", min_value=1, step=1)
            with c4: rest = st.text_input("휴식", "2분")
            if st.button("➕ 루틴 추가"): st.session_state.football_drills.append(f"{drill}({reps}회/{sets}세트)")
            if st.session_state.football_drills:
                st.info("👉 " + " ➡️ ".join(st.session_state.football_drills))
                if st.button("🗑️ 지우기"): st.session_state.football_drills = []; st.rerun()
            dist = st.number_input("🏃 거리(km)", 0.0, step=0.1)
            if st.button("💾 저장"):
                core.save_workout({"날짜": today, "공복 체중": f"{m_weight_display}kg", "훈련 볼륨": f"{dist}km", "상세 훈련 내용 (SOP 및 실전 역학)": f"[{time_of_day}] {location} | {' ➡️ '.join(st.session_state.football_drills)}", "생리학적 분석 및 영양/비고": "-"})
                st.session_state.football_drills = []; st.success("저장 완료!"); st.rerun()
                
        # 다른 운동 생략 최소화 (웨이트, 실전 경기 등)
        elif workout_type == "실전 경기":
            match_type = st.selectbox("📍 경기", ["11대11 정규", "풋살", "미니게임"])
            dist = st.number_input("거리(km)", 0.0, step=0.1)
            memo = st.text_area("📝 리뷰")
            if st.button("💾 경기 저장"):
                core.save_workout({"날짜": today, "공복 체중": f"{m_weight_display}kg", "훈련 볼륨": f"{dist}km", "상세 훈련 내용 (SOP 및 실전 역학)": f"[{time_of_day}] {match_type} | {memo}", "생리학적 분석 및 영양/비고": "-"})
                st.success("저장 완료!"); st.rerun()
        elif workout_type == "유산소/조깅":
            dist = st.number_input("거리(km)", 0.0, step=0.1)
            c_drill = st.text_input("메모 (예: 5km 러닝)")
            if st.button("💾 저장"):
                core.save_workout({"날짜": today, "공복 체중": f"{m_weight_display}kg", "훈련 볼륨": f"{dist}km", "상세 훈련 내용 (SOP 및 실전 역학)": f"[{time_of_day}] {c_drill}", "생리학적 분석 및 영양/비고": "-"})
                st.success("저장 완료!"); st.rerun()
        else:
            if st.button("💾 저장"):
                core.save_workout({"날짜": today, "공복 체중": f"{m_weight_display}kg", "훈련 볼륨": "-", "상세 훈련 내용 (SOP 및 실전 역학)": f"[{time_of_day}] {workout_type}", "생리학적 분석 및 영양/비고": "-"})
                st.success("저장 완료!"); st.rerun()

    st.write("---")
    all_w = core.get_cached_data("workout")
    if len(all_w) > 1:
        df_w = pd.DataFrame(all_w[1:], columns=all_w[0])
        edited_w = st.data_editor(df_w, num_rows="dynamic", use_container_width=True)
        if st.button("🔄 운동 데이터 덮어쓰기"):
            core.sheet_workout.clear()
            core.sheet_workout.append_rows([edited_w.columns.tolist()] + edited_w.fillna("").astype(str).values.tolist())
            st.cache_data.clear(); st.rerun()

# ==========================================
# 🥗 TAB 3: 식단 데이터 
# ==========================================
with tab_diet:
    st.header("🥗 영양 섭취 로깅")
    all_d = core.get_cached_data("diet")
    raws = {k: "" for k in [3,4,5,6,7]}
    cals = {k: "⏳ 미등록" for k in [3,4,5,6,7]}
    if len(all_d) > 1:
        for r in all_d[1:]:
            if r[0] == today:
                for idx, col in zip(range(2, 7), [3,4,5,6,7]):
                    if len(r) > idx: raws[col], cals[col] = core.parse_meal_cell(r[idx])
                break
    
    inputs = {}
    for name, idx in zip(["아침", "점심", "저녁", "간식", "야식"], [3,4,5,6,7]):
        c1, c2, c3 = st.columns([3, 1, 1])
        with c1: inputs[idx] = st.text_area(name, value=raws[idx], height=68, key=f"d_{idx}")
        with c2: st.metric("예상 칼로리", cals[idx])
        with c3:
            st.write("")
            if st.button(f"💾 {name} 등록", key=f"btn_d_{idx}"):
                if inputs[idx].strip():
                    with st.spinner("계산 중..."):
                        try: kcal = core.ask_gemini(f"'{inputs[idx]}' 총 칼로리만 '000kcal' 형식으로 적어.")
                        except: kcal = "오류"
                        core.save_single_meal(today, idx, f"{inputs[idx]} | AI 분석: {kcal}")
                        st.rerun()
    
    st.write("---")
    if len(all_d) > 1:
        df_d = pd.DataFrame(all_d[1:], columns=all_d[0])
        edited_d = st.data_editor(df_d, num_rows="dynamic", use_container_width=True)
        if st.button("🔄 식단 데이터 덮어쓰기"):
            core.sheet_diet.clear()
            core.sheet_diet.append_rows([edited_d.columns.tolist()] + edited_d.fillna("").astype(str).values.tolist())
            st.cache_data.clear(); st.rerun()

# ==========================================
# 📈 TAB 4: 데이터/리포팅 센터 (💡 컨디션 vs 운동강도 직관적 그래프)
# ==========================================
with tab_report:
    st.header("📈 AI 퍼포먼스 분석 센터")
    
    # 💡 [V12.1 추가] 컨디션(1-10) vs 운동강도(1-10) 그래프 구현
    st.subheader("📊 최근 7일 기상 컨디션 vs 훈련 강도 역학")
    all_w = core.get_cached_data("workout")
    all_s = core.get_cached_data("sleep")
    
    if len(all_s) > 2:
        df_s = pd.DataFrame(all_s[1:], columns=all_s[0])
        df_s['날짜'] = pd.to_datetime(df_s['날짜'], errors='coerce')
        df_s = df_s.dropna(subset=['날짜'])
        df_s['컨디션스코어(1-10)'] = df_s['신체 컨디션'].apply(core.extract_number)
        
        if len(all_w) > 1:
            df_w = pd.DataFrame(all_w[1:], columns=all_w[0])
            df_w['날짜'] = pd.to_datetime(df_w['날짜'], errors='coerce')
            df_w = df_w.dropna(subset=['날짜'])
            # core 로직에 있는 estimate_intensity 함수로 1~10 스케일 변환
            df_w['훈련강도(1-10)'] = df_w.apply(lambda row: core.estimate_intensity(row.iloc[2] if len(row)>2 else "", row.iloc[6] if len(row)>6 else ""), axis=1)
            df_w_grouped = df_w.groupby('날짜')['훈련강도(1-10)'].max().reset_index()
            
            df_merged = pd.merge(df_s[['날짜', '컨디션스코어(1-10)']], df_w_grouped[['날짜', '훈련강도(1-10)']], on='날짜', how='outer').fillna(0)
            df_recent7 = df_merged.sort_values('날짜').tail(7).set_index('날짜')
        else:
            df_s['훈련강도(1-10)'] = 0
            df_recent7 = df_s.sort_values('날짜').tail(7).set_index('날짜')[['컨디션스코어(1-10)', '훈련강도(1-10)']]
            
        st.bar_chart(df_recent7[['컨디션스코어(1-10)', '훈련강도(1-10)']], color=["#1f77b4", "#ff7f0e"])
        st.caption("🔵 파란바: 기상 직후 컨디션 스코어 (1-10) | 🟠 주황바: 당일 훈련 강도 추정치 (1-10)")
    else:
        st.info("최소 2일 이상의 데이터 누적이 필요합니다.")

    st.write("---")
    report_type = st.radio("📋 분석 사이클", ["⚡ 실시간", "🔍 7일 주간", "📊 14일 하프", "🏆 30일 월간"], horizontal=True)
    if st.button("🤖 S-Tier 분석 리포트 발행"):
        with st.spinner("AI 딥러닝 스캔 중..."):
            try:
                target_days = {"⚡ 실시간":1, "🔍 7일 주간":7, "📊 14일 하프":14, "🏆 30일 월간":30}[report_type]
                aw, a_s, ad = core.get_cached_data("workout"), core.get_cached_data("sleep"), core.get_cached_data("diet")
                w_ctx = " | ".join([f"{r[0]}({r[6]})" for r in (aw[-target_days:] if len(aw)>target_days else aw[1:]) if len(r)>6])
                s_ctx = " | ".join([f"{r[0]}(수면:{r[2]}, 컨디션:{r[4]})" for r in (a_s[-target_days:] if len(a_s)>target_days else a_s[1:]) if len(r)>4])
                prompt = f"곽연혁 선수의 데이터야. 운동:{w_ctx} 수면:{s_ctx}. 체력 트렌드와 다음 세션 솔루션을 분석해줘."
                
                # 5번 시도해도 실패하면 친절한 문구 리턴됨
                st.markdown(core.ask_gemini(prompt))
            except Exception as e: st.error(f"에러: {e}")