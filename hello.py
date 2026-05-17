import streamlit as st
import pandas as pd
import altair as alt
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

# 💡 Altair 차트 보조 함수 (Y축 0 고정 및 스크롤)
def render_line_chart(df, x_col, y_col, color, title):
    st.markdown(f"##### {title}")
    chart = alt.Chart(df).mark_line(point=True).encode(
        x=alt.X(f'{x_col}:T', title="날짜"),
        y=alt.Y(f'{y_col}:Q', scale=alt.Scale(domainMin=0)),
        tooltip=[x_col, y_col]
    ).properties(height=300).configure_mark(color=color).interactive(bind_y=False)
    st.altair_chart(chart, use_container_width=True)

# ==========================================
# 📊 TAB 1: 신체 데이터 (누락 그래프 복구)
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
        df_s = df_s[df_s['체중'] > 0].tail(30) # 스케일링: 최근 30일치만 렌더링
        
        if not df_s.empty:
            df_s['추정 골격근량'] = round(df_s['체중'] * 0.49, 1)
            df_s['추정 체지방률'] = round(11.5 + (df_s['체중'] - 77.5) * 0.7, 1)
            df_s['추정 체지방량'] = round(df_s['체중'] * (df_s['추정 체지방률'] / 100), 1)
            df_s['수면시간(h)'] = df_s['수면 시간'].apply(core.extract_number)
            
            st.write("---")
            st.subheader("📈 바디 컴포지션 멀티 대시보드")
            c1, c2 = st.columns(2)
            with c1: render_line_chart(df_s, '날짜', '체중', '#1f77b4', '⚖️ 체중 (kg)')
            with c2: render_line_chart(df_s, '날짜', '추정 골격근량', '#2ca02c', '💪 근육량 (kg)')
            
            c3, c4 = st.columns(2)
            with c3: render_line_chart(df_s, '날짜', '추정 체지방량', '#ff7f0e', '🩸 체지방량 (kg)')
            with c4: render_line_chart(df_s, '날짜', '수면시간(h)', '#9467bd', '💤 수면 시간 (h)')

# ==========================================
# 🏋️ TAB 2: 운동 데이터 (누락된 페이스 렌더링 복구)
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
                core.save_workout({"날짜": today, "공복 체중": f"{m_weight_display}kg", "훈련 볼륨": "훈련소일과", "상세 훈련 내용 (SOP 및 실전 역학)": f"[훈련소] {bc_rt}"})
                st.success("저장 완료!"); st.rerun()
        else:
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                v1, v2, v3, v4 = st.checkbox("관물대 턱걸이"), st.checkbox("침상 푸쉬업"), st.checkbox("맨몸 스쿼트"), st.checkbox("코어/플랭크")
            with col_b2:
                v5, v6 = st.checkbox("연병장 축구 ⚽"), st.checkbox("연병장 풋살 👟")
            if st.button("💾 야간 훈련 저장"):
                lst = [n for b, n in zip([v1,v2,v3,v4,v5,v6], ["턱걸이","푸쉬업","스쿼트","코어","축구","풋살"]) if b]
                core.save_workout({"날짜": today, "공복 체중": f"{m_weight_display}kg", "훈련 볼륨": "야간", "상세 훈련 내용 (SOP 및 실전 역학)": f"[기량유지] {','.join(lst) if lst else '미실시'}"})
                st.success("저장 완료!"); st.rerun()
    else:
        time_of_day = st.radio("⏰ 시간대", ("☀️ 오전", "🌤️ 오후", "🌙 저녁/야간"), horizontal=True)
        workout_type = st.selectbox("👇 세션 종류", ("개인 축구 훈련", "유산소/조깅", "실전 경기", "웨이트 트레이닝", "휴식"))
        
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
                with st.spinner("AI 강도 평가 후 저장 중..."):
                    core.save_workout({"날짜": today, "공복 체중": f"{m_weight_display}kg", "훈련 볼륨": f"{dist}km", "상세 훈련 내용 (SOP 및 실전 역학)": f"[{time_of_day}] {location} | {' ➡️ '.join(st.session_state.football_drills)}"})
                st.session_state.football_drills = []; st.success("저장 완료!"); st.rerun()
                
        elif workout_type == "유산소/조깅":
            c_drill = st.selectbox("📋 종목", ["러닝", "턱걸이", "딥스", "오르막 스프린트"])
            if c_drill == "러닝":
                col_r1, col_r2, col_r3 = st.columns(3)
                with col_r1: run_dist = st.number_input("🏃 거리 (km)", min_value=0.0, step=0.1, value=3.2)
                with col_r2: run_min = st.number_input("⏱️ 시간 (분)", min_value=0, step=1, value=12)
                with col_r3: run_sec = st.number_input("⏱️ 시간 (초)", min_value=0, max_value=59, step=1, value=50)
                if st.button("🤖 AI 페이스 계산 및 추가"):
                    total_mins = run_min + (run_sec / 60)
                    if run_dist > 0 and total_mins > 0:
                        pace_min = int(total_mins // run_dist)
                        pace_sec = int((total_mins / run_dist - pace_min) * 60)
                        pace_str = f"{pace_min}분 {pace_sec}초/km"
                        st.session_state.cardio_drills.append(f"러닝({run_dist}km, {run_min}분{run_sec}초, 페이스: {pace_str})")
                        st.success(f"🎯 기록 추가됨 (페이스: {pace_str})")
            else:
                c1, c2, c3 = st.columns(3)
                with c1: c_dist = st.text_input("거리/개수", "5km")
                with c2: c_reps = st.number_input("반복", 1, step=1)
                with c3: c_sets = st.number_input("세트", 1, step=1)
                if st.button("➕ 세션 추가"): st.session_state.cardio_drills.append(f"{c_drill}({c_dist} x {c_reps}회 / {c_sets}세트)")

            if st.session_state.cardio_drills:
                st.warning("👉 " + " ➡️ ".join(st.session_state.cardio_drills))
                if st.button("🗑️ 지우기"): st.session_state.cardio_drills = []; st.rerun()
            
            dist = st.number_input("🏃 총 거리(km)", 0.0, step=0.1)
            if st.button("💾 저장"):
                with st.spinner("AI 강도 평가 후 저장 중..."):
                    core.save_workout({"날짜": today, "공복 체중": f"{m_weight_display}kg", "훈련 볼륨": f"{dist}km", "상세 훈련 내용 (SOP 및 실전 역학)": f"[{time_of_day}] {' ➡️ '.join(st.session_state.cardio_drills)}"})
                st.session_state.cardio_drills = []; st.success("저장 완료!"); st.rerun()

        else:
            dist = st.number_input("거리(km)", 0.0, step=0.1)
            memo = st.text_area("📝 메모")
            if st.button("💾 저장"):
                with st.spinner("저장 중..."):
                    core.save_workout({"날짜": today, "공복 체중": f"{m_weight_display}kg", "훈련 볼륨": f"{dist}km", "상세 훈련 내용 (SOP 및 실전 역학)": f"[{time_of_day}] {workout_type} | {memo}"})
                st.success("저장 완료!"); st.rerun()

    st.write("---")
    all_w = core.get_cached_data("workout")
    if len(all_w) > 1:
        df_w = pd.DataFrame(all_w[1:], columns=all_w[0]).tail(20)
        edited_w = st.data_editor(df_w, num_rows="dynamic", use_container_width=True)

# ==========================================
# 🥗 TAB 3: 식단 데이터 (누락된 코칭 버튼 복구)
# ==========================================
with tab_diet:
    st.header("🥗 영양 섭취 로깅")
    all_d = core.get_cached_data("diet")
    raws, cals = {k: "" for k in [3,4,5,6,7]}, {k: "⏳ 미등록" for k in [3,4,5,6,7]}
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

    # 💡 누락되었던 AI 식단 코치 복구
    st.write("---")
    if st.button("🧠 현재까지 영양 분석 및 다음 식사 추천받기"):
        if HAS_AI:
            with st.spinner("AI 영양사 분석 중..."):
                aw = core.get_cached_data("workout")
                today_w = " | ".join([r[6] for r in aw if r[0]==today and len(r)>6])
                prompt = f"축구선수 오늘운동:[{today_w}], 아침:[{raws[3]}], 점심:[{raws[4]}], 저녁:[{raws[5]}]. 아직 안먹은 칸은 호들갑 떨지 말고, 훈련량 대비 남은 식사에서 보충할 탄단지 메뉴 추천해줘."
                st.markdown(core.ask_gemini(prompt))
        else: st.error("API 키 필요")

# ==========================================
# 📈 TAB 4: 리포팅 센터 (💡 Altair 무결점 바 차트 도입)
# ==========================================
with tab_report:
    st.header("📈 AI 퍼포먼스 분석 센터")
    
    st.subheader("📊 기상 컨디션 vs 훈련 강도 역학 (1-10 스케일)")
    all_w = core.get_cached_data("workout")
    all_s = core.get_cached_data("sleep")
    
    if len(all_s) > 2 and len(all_w) > 1:
        df_s = pd.DataFrame(all_s[1:], columns=all_s[0])
        df_s['날짜'] = pd.to_datetime(df_s['날짜'], errors='coerce')
        df_s = df_s.dropna(subset=['날짜'])
        df_s['컨디션스코어'] = df_s['신체 컨디션'].apply(core.extract_number)
        
        df_w = pd.DataFrame(all_w[1:], columns=all_w[0])
        df_w['날짜'] = pd.to_datetime(df_w['날짜'], errors='coerce')
        df_w = df_w.dropna(subset=['날짜'])
        
        # 💡 DB에 박제된 AI 훈련 강도 추출 (없으면 5점)
        def get_saved_intensity(row):
            try:
                note = str(row.get('생리학적 분석 및 영양/비고', ''))
                if 'AI추정강도:' in note:
                    return int(note.split(':')[1])
            except: pass
            return 5
            
        df_w['훈련강도'] = df_w.apply(get_saved_intensity, axis=1)
        df_w_max = df_w.groupby('날짜')['훈련강도'].max().reset_index()
        
        df_merged = pd.merge(df_s[['날짜', '컨디션스코어']], df_w_max[['날짜', '훈련강도']], on='날짜', how='outer').fillna(0).tail(15)
        
        # 💡 Altair를 이용한 나란히 배치되는(X offset) 바 차트 (Y축 0-10 고정)
        df_melt = df_merged.melt('날짜', var_name='종류', value_name='점수')
        bar_chart = alt.Chart(df_melt).mark_bar().encode(
            x=alt.X('날짜:T', title='날짜'),
            xOffset='종류:N',
            y=alt.Y('점수:Q', scale=alt.Scale(domain=[0, 10])),
            color=alt.Color('종류:N', scale=alt.Scale(domain=['컨디션스코어', '훈련강도'], range=['#1f77b4', '#ff7f0e']))
        ).interactive(bind_y=False).properties(height=350)
        
        st.altair_chart(bar_chart, use_container_width=True)
    else:
        st.info("그래프를 그리려면 신체 및 운동 데이터 누적이 필요합니다.")

    st.write("---")
    report_type = st.radio("📋 분석 사이클", ["⚡ 실시간", "🔍 7일 주간", "📊 14일 하프", "🏆 30일 월간"], horizontal=True)
    if st.button("🤖 S-Tier 분석 리포트 발행"):
        with st.spinner("AI 딥러닝 스캔 중..."):
            try:
                target_days = {"⚡ 실시간":1, "🔍 7일 주간":7, "📊 14일 하프":14, "🏆 30일 월간":30}[report_type]
                aw, a_s = core.get_cached_data("workout"), core.get_cached_data("sleep")
                w_ctx = " | ".join([f"{r[0]}({r[6]})" for r in (aw[-target_days:] if len(aw)>target_days else aw[1:]) if len(r)>6])
                s_ctx = " | ".join([f"{r[0]}(수면:{r[2]}, 컨디션:{r[4]})" for r in (a_s[-target_days:] if len(a_s)>target_days else a_s[1:]) if len(r)>4])
                prompt = f"곽연혁 선수의 데이터야. 운동:{w_ctx} 수면:{s_ctx}. 체력 트렌드와 다음 세션 솔루션을 전문적으로 분석해줘."
                st.markdown(core.ask_gemini(prompt))
            except Exception as e: st.error(f"에러: {e}")