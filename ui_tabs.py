import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, date, time, timedelta
import utils
import db_service as db
import re

# 💡 V16.0 업데이트: 4가지 맞춤형 프롬프트 생성 (당일 추천/평가, 주간/월간 비교) 및 식단 칼로리 AI 위임

TRAINING_DICT = """
[곽연혁 선수 전용 훈련 역학 및 SOP (용와초 잔디구장 기준)]
1. 웜업 조깅: 본 훈련 전 체온 상승 및 심박수 예열을 위한 가벼운 러닝.
2. 웜업 볼마스터리 (드리블 벽패스 가벼운 슈팅 공중볼 이동컨트롤): 본 훈련 전 볼 감각을 깨우고 이동 컨트롤 및 첫 번째 터치의 정교함을 확보.
3. 40/20 풀코트 인터벌: 40초 동안 엔드라인 출발 -> 하프라인 정지 -> 반대편 엔드라인 -> 복귀 후 하프라인 공 픽업 및 슈팅 마무리. 남은 시간+20초 휴식. (타겟: 유산소 역치, 90분 체력)
4. 40/20 하프라인 인터벌: 하프-사이드 교차점 출발 -> 킥오프 정지 -> 사이드 찍고 복귀 -> 각 있는 드리블 후 슈팅. 남은시간+20초 휴식.
5. 40/20 하프코트 인터벌: 40초 안 엔드라인 출발 -> 하프라인 정지 -> 시작 엔드라인 복귀 -> 픽업 후 시작점 골대 슈팅. 남은시간+20초 휴식.
6. 25/15 페널티박스 인터벌: (홀수) 25초 박스 모서리 정지->각턴 복귀->15초 휴식. / (짝수) 25초 튀어나가 코디네이션->라인 드리블->반대 모서리 컷 후 슈팅. 남은시간+15초 복귀. 교대. (타겟: 극한의 15초 불완전 휴식, 잔발 전환, Agility)
7. 15/5 드리블 슈팅 믹스 인터벌: 15초 드리블+5초 휴식 3회. 3번째 슈팅. 30초 공 줍기. (타겟: 피로도 속 기술 유지력)
8. 15/15 매스템포런: 엔드라인 왕복 15초 러닝/15초 휴식.
9. 프리킥 (세트 사이): 고강도 인터벌 세트 사이 불완전 휴식기. 데드볼 타격 감각 유지.
10. 경기템포 훈련: 중앙 미드필더(CM) 실전 이미지 트레이닝. 역습/소유 상황 드리블, 실전 패스(인/아웃/장/단), 중장거리/근거리 슈팅을 실전 템포로 수행. (타겟: CM 인지 속도 및 실전 심폐)
11. 쿨다운 조깅: 훈련 종료 후 심박수 안정화 및 젖산 배출 회복 러닝.
"""

def render_line_chart(df: pd.DataFrame, x_col: str, y_col: str, color: str, title: str):
    st.markdown(f"##### {title}")
    valid_df = df[df[y_col] > 0].copy()
    if valid_df.empty:
        st.info("차트를 그릴 데이터가 없습니다.")
        return
    valid_df = valid_df.sort_values(x_col)
    max_date = valid_df[x_col].max()
    min_view_date = max_date - timedelta(days=15)
    
    chart = alt.Chart(valid_df).mark_line(point=True).encode(
        x=alt.X(f'{x_col}:T', title="날짜", scale=alt.Scale(domain=[min_view_date.strftime('%Y-%m-%d'), max_date.strftime('%Y-%m-%d')], nice=False)),
        y=alt.Y(f'{y_col}:Q', title=y_col, scale=alt.Scale(domainMin=0)),
        tooltip=[alt.Tooltip(f'{x_col}:T', title="날짜", format="%Y-%m-%d"), alt.Tooltip(f'{y_col}:Q', title=y_col)]
    ).properties(height=300).configure_mark(color=color).interactive(bind_y=False)
    st.altair_chart(chart, use_container_width=True)

def render_body_tab(today: str):
    st.header("📊 수면 과학 및 신체 데이터 대시보드")
    m_weight = st.number_input("⚖️ 오늘의 공복 체중 (kg)", min_value=0.0, value=st.session_state.get("master_weight", 77.5), step=0.1, key="body_weight_input")
    st.session_state["master_weight"] = m_weight

    col_m2, col_m3 = st.columns(2)
    with col_m2: bed_time = st.time_input("🛏️ 불 끄고 누운 시간", value=time(23, 30))
    with col_m3: wake_time = st.time_input("☀️ 실제 일어난 시간", value=time(7, 30))
        
    dt_bed = datetime.combine(date.today(), bed_time)
    dt_wake = datetime.combine(date.today(), wake_time)
    if dt_wake < dt_bed: dt_wake += timedelta(days=1)
    calc_sleep_hours = round(max(0, ((dt_wake - dt_bed).total_seconds() / 60) - 20) * 0.9 / 60, 1)
    st.success(f"🤖 **실제 딥슬립 시간 계산 완료:** [{calc_sleep_hours}시간]")

    col_m4, col_m5 = st.columns(2)
    with col_m4: m_quality = st.slider("⭐ 체감 수면의 질", 1, 10, 7)
    with col_m5: m_cond = st.slider("🏃 기상 직후 컨디션", 1, 10, 7)
        
    with st.expander("📏 [선택 사항] 공복 신체 측정"):
        c_size1, c_size2, c_size3, c_size4 = st.columns(4)
        with c_size1: chest_sz = st.number_input("가슴 (cm)", step=0.1, key="chest_sz")
        with c_size2: arm_sz = st.number_input("팔 (cm)", step=0.1, key="arm_sz")
        with c_size3: waist_sz = st.number_input("허리 (cm)", step=0.1, key="waist_sz")
        with c_size4: thigh_sz = st.number_input("허벅지 (cm)", step=0.1, key="thigh_sz")

    if st.button("🚀 신체 데이터 저장", key="save_body_btn"):
        row = [today, f"{m_weight}kg", f"{calc_sleep_hours}시간", f"{m_quality}점", f"{m_cond}점",
            f"{chest_sz}cm" if chest_sz>0 else "-", f"{arm_sz}cm" if arm_sz>0 else "-",
            f"{waist_sz}cm" if waist_sz>0 else "-", f"{thigh_sz}cm" if thigh_sz>0 else "-"]
        if hasattr(db.sheet_sleep, 'append_row'):
            db.sheet_sleep.append_row(row)
            st.cache_data.clear(); st.success("0.1초 초고속 저장 완료!"); st.rerun()
        
    all_s_body = db.get_cached_data("sleep")
    if len(all_s_body) > 1:
        df_s = pd.DataFrame(all_s_body[1:], columns=all_s_body[0])
        df_s['날짜'] = pd.to_datetime(df_s['날짜'], errors='coerce')
        df_s = df_s.dropna(subset=['날짜'])
        df_s['체중'] = df_s['공복 체중'].apply(utils.extract_number)
        
        if not df_s.empty:
            df_s['추정 골격근량'] = round(df_s['체중'] * 0.49, 1)
            df_s['추정 체지방률'] = round(11.5 + (df_s['체중'] - 77.5) * 0.7, 1)
            df_s['추정 체지방량'] = round(df_s['체중'] * (df_s['추정 체지방률'] / 100), 1)
            df_s['수면시간(h)'] = df_s['수면 시간'].apply(utils.extract_number)
            
            st.write("---")
            st.subheader("📈 바디 컴포지션 멀티 대시보드")
            c1, c2 = st.columns(2)
            with c1: render_line_chart(df_s, '날짜', '체중', '#1f77b4', '⚖️ 체중 (kg)')
            with c2: render_line_chart(df_s, '날짜', '추정 골격근량', '#2ca02c', '💪 근육량 (kg)')
            c3, c4 = st.columns(2)
            with c3: render_line_chart(df_s, '날짜', '추정 체지방량', '#ff7f0e', '🩸 체지방량 (kg)')
            with c4: render_line_chart(df_s, '날짜', '수면시간(h)', '#9467bd', '💤 수면 시간 (h)')

def render_workout_tab(today: str, bootcamp_mode: bool):
    st.header("🧠 오늘의 트레이닝 세션 로깅")
    m_weight_display = st.number_input("⚖️ 오늘의 공복 체중 연동 (kg)", value=st.session_state.get("master_weight", 77.5), step=0.1, key="workout_weight_연동")

    if bootcamp_mode:
        st.subheader("🪖 제31사단 훈련소 일과")
        bc_time = st.radio("⏰ 구분", ["메인 일과", "틈새/야간"], key="bootcamp_time_radio")
        if bc_time == "메인 일과":
            bc_rt = st.selectbox("📋 훈련", ["일반 일과", "알통 뜀걸음", "영외 전투 훈련", "행군"], key="bootcamp_drill_select")
            bc_comment = st.text_area("✍️ 체감 코멘트", key="bootcamp_main_comment")
            if st.button("💾 저장", key="save_bootcamp_main_btn"):
                db.save_workout({"날짜": today, "공복 체중": f"{m_weight_display}kg", "훈련 볼륨": "훈련소일과", "상세 훈련 내용 (SOP 및 실전 역학)": f"[훈련소] {bc_rt}", "선수 코멘트": bc_comment})
                st.success("저장 완료!"); st.rerun()
        else:
            col_b1, col_b2 = st.columns(2)
            with col_b1: v1, v2, v3, v4 = st.checkbox("관물대 턱걸이"), st.checkbox("침상 푸쉬업"), st.checkbox("맨몸 스쿼트"), st.checkbox("코어/플랭크")
            with col_b2: v5, v6 = st.checkbox("연병장 축구 ⚽"), st.checkbox("연병장 풋살 👟")
            bc_comment = st.text_area("✍️ 체감 코멘트", key="bootcamp_night_comment")
            if st.button("💾 야간 훈련 저장", key="save_bootcamp_night_btn"):
                lst = [n for b, n in zip([v1,v2,v3,v4,v5,v6], ["턱걸이","푸쉬업","스쿼트","코어","축구","풋살"]) if b]
                db.save_workout({"날짜": today, "공복 체중": f"{m_weight_display}kg", "훈련 볼륨": "야간", "상세 훈련 내용 (SOP 및 실전 역학)": f"[기량유지] {','.join(lst) if lst else '미실시'}", "선수 코멘트": bc_comment})
                st.success("저장 완료!"); st.rerun()
    else:
        time_of_day = st.radio("⏰ 시간대", ("☀️ 오전", "🌤️ 오후", "🌙 저녁/야간"), horizontal=True, key="normal_time_radio")
        workout_type = st.selectbox("👇 세션 종류", ("개인 축구 훈련", "유산소/조깅", "실전 경기", "웨이트 트레이닝", "휴식"), key="normal_session_select")
        dist_val, details_str, is_not_sure = 0.0, "", False
        
        if workout_type == "개인 축구 훈련":
            location = st.text_input("📍 장소", "전주 용와초등학교 잔디구장", key="football_loc")
            c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
            drill_options = [
                "웜업 조깅", "웜업 볼마스터리 (드리블 벽패스 가벼운 슈팅 공중볼 이동컨트롤)", "경기템포 훈련",
                "40/20 풀코트 인터벌", "40/20 하프라인 인터벌", "40/20 하프코트 인터벌",
                "25/15 페널티박스 인터벌", "15/5 드리블 슈팅 믹스 인터벌", "15/15 매스템포런",
                "프리킥 (세트 사이)", "쿨다운 조깅"
            ]
            with c1: drill = st.selectbox("📋 종목", drill_options, key="football_drill")
            with c2: reps = st.number_input("횟수", min_value=1, step=1, key="football_reps")
            with c3: sets = st.number_input("세트", min_value=1, step=1, key="football_sets")
            with c4: rest = st.text_input("휴식", "2분", key="football_rest")
            
            if st.button("➕ 루틴 추가", key="add_football_drill"): st.session_state.football_drills.append(f"{drill}({reps}회/{sets}세트)")
            if st.session_state.football_drills:
                st.info("👉 " + " ➡️ ".join(st.session_state.football_drills))
                if st.button("🗑️ 지우기", key="clear_football_drills"): st.session_state.football_drills = []; st.rerun()
            dist_val = st.number_input("🏃 거리(km)", 0.0, step=0.1, key="football_dist")
            details_str = f"[{time_of_day}] {location} | {' ➡️ '.join(st.session_state.football_drills)}"

        elif workout_type == "유산소/조깅":
            c_drill = st.selectbox("📋 종목", ["러닝", "턱걸이", "딥스", "오르막 스프린트", "직접 입력(Custom)"], key="cardio_drill_select")
            if c_drill == "직접 입력(Custom)": c_drill = st.text_input("📝 종목 직접 입력", key="cardio_custom_drill")
            if c_drill == "러닝":
                col_r1, col_r2, col_r3 = st.columns(3)
                with col_r1: run_dist = st.number_input("🏃 거리 (km)", min_value=0.0, step=0.1, value=3.2, key="run_dist")
                with col_r2: run_min = st.number_input("⏱️ 시간 (분)", min_value=0, step=1, value=12, key="run_min")
                with col_r3: run_sec = st.number_input("⏱️ 시간 (초)", min_value=0, max_value=59, step=1, value=50, key="run_sec")
                if st.button("🤖 페이스 자동 계산", key="calc_run_pace"):
                    total_mins = run_min + (run_sec / 60)
                    if run_dist > 0 and total_mins > 0:
                        pace_min = int(total_mins // run_dist)
                        pace_sec = int((total_mins / run_dist - pace_min) * 60)
                        pace_str = f"{pace_min}분 {pace_sec}초/km"
                        st.session_state.cardio_drills.append(f"러닝({run_dist}km, {run_min}분{run_sec}초, 페이스: {pace_str})")
                        st.success(f"🎯 기록 추가됨 (페이스: {pace_str})")
            else:
                c1, c2, c3 = st.columns(3)
                with c1: c_dist = st.text_input("거리/개수", "5km", key="cardio_reps_dist")
                with c2: c_reps = st.number_input("반복", 1, step=1, key="cardio_reps_count")
                with c3: c_sets = st.number_input("세트", 1, step=1, key="cardio_sets_count")
                if st.button("➕ 세션 추가", key="add_cardio_drill"): st.session_state.cardio_drills.append(f"{c_drill}({c_dist} x {c_reps}회 / {c_sets}세트)")

            if st.session_state.cardio_drills:
                st.warning("👉 " + " ➡️ ".join(st.session_state.cardio_drills))
                if st.button("🗑️ 지우기", key="clear_cardio_drills"): st.session_state.cardio_drills = []; st.rerun()
            dist_val = st.number_input("🏃 총 거리(km)", 0.0, step=0.1, key="cardio_total_dist")
            details_str = f"[{time_of_day}] {' ➡️ '.join(st.session_state.cardio_drills)}"

        elif workout_type == "실전 경기":
            match_type = st.selectbox("📍 경기", ["11대11 정규", "풋살", "미니게임"], key="match_type")
            is_not_sure = st.checkbox("🤔 기기 장착 안 함 (기록 측정 불가)", value=False, key="match_not_sure")
            dist_val = 0.0 if is_not_sure else st.number_input("거리(km)", 0.0, step=0.1, key="match_dist")
            details_str = f"[{time_of_day}] {match_type}"

        elif workout_type == "웨이트 트레이닝":
            is_super = st.radio("💪 세트 방식", ["단일 종목", "슈퍼/컴파운드 세트"], horizontal=True, key="weight_type_radio")
            if is_super == "단일 종목":
                c1, c2, c3, c4 = st.columns(4)
                with c1: w_ex = st.text_input("운동명", key="weight_ex_name")
                with c2: w_kg = st.number_input("무게(kg)", step=2.5, key="weight_kg")
                with c3: w_rep = st.number_input("횟수", step=1, key="weight_reps")
                with c4: w_set = st.number_input("세트", step=1, key="weight_sets")
                if st.button("➕ 추가", key="add_single_weight"): st.session_state.weight_sets.append(f"{w_ex}({w_kg}kg x{w_rep}회 {w_set}세트)")
            else:
                c1, c2, c3 = st.columns(3)
                with c1: s_ex1 = st.text_input("종목 1 (예: 벤치 60kg)", key="weight_super1")
                with c2: s_ex2 = st.text_input("종목 2 (예: 풀업)", key="weight_super2")
                with c3: s_set = st.number_input("총 세트 수", step=1, key="weight_super_sets")
                if st.button("➕ 슈퍼세트 추가", key="add_super_weight"): st.session_state.weight_sets.append(f"슈퍼[{s_ex1}+{s_ex2}] x{s_set}세트")
            
            if st.session_state.weight_sets:
                st.info("👉 " + " / ".join(st.session_state.weight_sets))
                if st.button("🗑️ 지우기", key="clear_weight_sets"): st.session_state.weight_sets = []; st.rerun()
            details_str = f"[{time_of_day}] " + " / ".join(st.session_state.weight_sets)

        elif workout_type == "휴식":
            rec_act = st.text_input("활동 (예: 폼롤러 20분)", key="rest_act")
            details_str = f"[{time_of_day}] {rec_act}"

        st.write("---")
        st.subheader("🫀 생리학적 부하 및 피드백 (수동 입력)")
        if is_not_sure: h_avg, h_max, hrr_2m = 0, 0, "-"
        else:
            col_h1, col_h2, col_h3 = st.columns(3)
            with col_h1: h_avg = st.number_input("❤️ 평균 심박 (bpm)", min_value=0, step=1, key="hr_avg")
            with col_h2: h_max = st.number_input("🔥 최대 심박 (bpm)", min_value=0, step=1, key="hr_max")
            with col_h3: hrr_2m = st.text_input("📉 2분 심박 회복량 (HRR)", key="hrr_2m")
        
        rpe_score = st.slider("🔥 본인이 체감한 오늘 훈련의 육체적 강도 (RPE: 1~10)", 1, 10, 7)
        user_comment = st.text_area("✍️ 체감 코멘트 및 비고", key="workout_comment")
        
        if st.button("💾 0.1초 쾌속 로깅", key="save_workout_btn"):
            final_comment = f"[RPE:{rpe_score}] {user_comment}"
            if db.save_workout({
                "날짜": today, "공복 체중": f"{m_weight_display}kg", "훈련 볼륨": f"{dist_val}km" if not is_not_sure else "미측정", 
                "평균 심박": h_avg, "최대 심박": h_max, "심박 회복량(HRR)": hrr_2m, 
                "상세 훈련 내용 (SOP 및 실전 역학)": details_str, "선수 코멘트": final_comment
            }):
                st.session_state.football_drills = []
                st.session_state.cardio_drills = []
                st.session_state.weight_sets = []
                st.success("데이터베이스 즉시 저장 완료!"); st.rerun()

    st.write("---")
    all_w = db.get_cached_data("workout")
    if len(all_w) > 1:
        df_w = pd.DataFrame(all_w[1:], columns=all_w[0]).tail(20)
        edited_w = st.data_editor(df_w, num_rows="dynamic", use_container_width=True, key="workout_db_editor")
        if st.button("🔄 운동 데이터 덮어쓰기", key="overwrite_workout_btn"):
            if hasattr(db.sheet_workout, 'clear'):
                db.sheet_workout.clear()
                db.sheet_workout.append_rows([edited_w.columns.tolist()] + edited_w.fillna("").astype(str).values.tolist())
                st.cache_data.clear(); st.rerun()

def render_diet_tab(today: str, bootcamp_mode: bool):
    st.header("🥗 영양 섭취 로깅 (초고속)")
    all_d = db.get_cached_data("diet")
    raws = {k: "" for k in [2, 3, 4, 5, 6, 7]}
    if len(all_d) > 1:
        for r in all_d[1:]:
            if r[0] == today:
                for idx, col in zip(range(1, 7), [2, 3, 4, 5, 6, 7]):
                    if len(r) > idx: raws[col] = r[idx].split(' | ')[0] if ' | ' in r[idx] else r[idx]
                break
    
    if bootcamp_mode:
        bc_meal_select = st.radio("🍴 해당 식사 선택", ["아침 병영식 정량", "점심 병영식 정량", "저녁 병영식 정량", "PX 군것질/증식"], key="bootcamp_meal_radio")
        if st.button("💾 훈련소 식사 원클릭 등록", key="save_bootcamp_meal_btn"):
            col_map = {"아침 병영식 정량": 3, "점심 병영식 정량": 4, "저녁 병영식 정량": 5, "PX 군것질/증식": 6}
            db.save_single_meal(today, col_map[bc_meal_select], f"{bc_meal_select} 섭취 완료")
            st.success("훈련소 급식 0.1초 저장 성공!"); st.rerun()
    else:
        st.subheader("📊 오늘의 총 섭취 칼로리 (제미나이 결과 복붙용)")
        c_cal1, c_cal2 = st.columns([4, 1])
        with c_cal1:
            current_cal = utils.extract_number(raws[2]) if raws[2] else 0.0
            daily_cal = st.number_input("🔥 칼로리 수동 입력 (kcal)", min_value=0, step=50, value=int(current_cal), key="daily_cal_input")
        with c_cal2:
            st.write("")
            st.write("")
            if st.button("💾 칼로리 저장", key="save_cal_btn"):
                db.save_single_meal(today, 2, f"{daily_cal}kcal")
                st.rerun()
        st.write("---")
        
        for name, idx in zip(["아침", "점심", "저녁", "간식", "야식"], [3, 4, 5, 6, 7]):
            c1, c2 = st.columns([4, 1])
            with c1: input_val = st.text_area(name, value=raws[idx], height=68, key=f"d_{idx}_input")
            with c2:
                st.write("")
                st.write("")
                if st.button(f"💾 등록", key=f"btn_d_{idx}_save"):
                    if input_val.strip():
                        db.save_single_meal(today, idx, input_val)
                        st.rerun()

def render_report_tab():
    st.header("📈 퍼포먼스 데이터 및 맞춤형 프롬프트 센터")
    
    st.subheader("📊 기상 컨디션 vs 훈련 강도 역학 (1-10 스케일)")
    all_w = db.get_cached_data("workout")
    all_s = db.get_cached_data("sleep")
    
    if len(all_s) > 2 and len(all_w) > 1:
        df_s = pd.DataFrame(all_s[1:], columns=all_s[0])
        df_s['날짜'] = pd.to_datetime(df_s['날짜'], errors='coerce')
        df_s = df_s.dropna(subset=['날짜'])
        df_s['CON_SCORE'] = df_s['신체 컨디션'].apply(utils.extract_number)
        
        df_w = pd.DataFrame(all_w[1:], columns=all_w[0])
        df_w['날짜'] = pd.to_datetime(df_w['날짜'], errors='coerce')
        df_w = df_w.dropna(subset=['날짜'])
        
        def get_saved_intensity(row):
            try:
                comment = str(row.get('선수 코멘트', ''))
                match = re.search(r'\[RPE:(\d+)\]', comment)
                if match: return int(match.group(1))
            except: pass
            return utils.estimate_intensity_local(row.get('훈련 볼륨', ''), row.get('상세 훈련 내용 (SOP 및 실전 역학)', ''))
            
        df_w['훈련강도(1-10)'] = df_w.apply(get_saved_intensity, axis=1)
        df_w_max = df_w.groupby('날짜')['훈련강도(1-10)'].max().reset_index()
        df_merged = pd.merge(df_s[['날짜', 'CON_SCORE']], df_w_max[['날짜', '훈련강도(1-10)']], on='날짜', how='outer').fillna(0).sort_values('날짜')
        valid_report = df_merged[(df_merged['CON_SCORE'] > 0) | (df_merged['훈련강도(1-10)'] > 0)].copy()
        
        if not valid_report.empty:
            df_melt = valid_report.melt('날짜', var_name='종류', value_name='점수')
            max_date = df_melt['날짜'].max()
            min_view_date = max_date - timedelta(days=15)
            line_chart = alt.Chart(df_melt).mark_line(point=True).encode(
                x=alt.X('날짜:T', title='날짜', scale=alt.Scale(domain=[min_view_date.strftime('%Y-%m-%d'), max_date.strftime('%Y-%m-%d')], nice=False)),
                y=alt.Y('점수:Q', title="점수 (1-10)", scale=alt.Scale(domain=[0, 10])),
                color=alt.Color('종류:N', scale=alt.Scale(domain=['CON_SCORE', '훈련강도(1-10)'], range=['#1f77b4', '#ff7f0e'])),
                tooltip=[alt.Tooltip('날짜:T', title="날짜", format="%Y-%m-%d"), alt.Tooltip('종류:N'), alt.Tooltip('점수:Q')]
            ).properties(height=350).interactive(bind_y=False)
            st.altair_chart(line_chart, use_container_width=True)
    
    st.write("---")
    st.subheader("📋 1:1 딥 코칭용 맞춤형 프롬프트 생성기")
    st.info("💡 아래에서 원하는 목적을 선택하고, 생성된 프롬프트를 복사해 제미나이(Gemini) 앱에 붙여넣으세요!")
    
    report_type = st.radio("🎯 프롬프트 목적 선택", [
        "1️⃣ [당일 추천] 지난 기록 기반 오늘 훈련 추천받기",
        "2️⃣ [당일 평가] 오늘 훈련/신체 복기 & 식단 칼로리 AI 계산",
        "3️⃣ [주간 비교] 1주일 리뷰 (이번 주 vs 지난 주)",
        "4️⃣ [월간 비교] 1개월 리뷰 (이번 달 vs 지난 달)"
    ])
    
    if st.button("✨ 제미나이 전용 프롬프트 뽑기", key="issue_ai_prompt_btn"):
        aw, a_s, a_d = db.get_cached_data("workout")[1:], db.get_cached_data("sleep")[1:], db.get_cached_data("diet")[1:]
        
        def get_data_slice(data, days_ago_start, days_ago_end):
            # 가장 최근 데이터를 맨 뒤로 가정 (구글 시트 구조상)
            if not data: return []
            return data[-days_ago_start : -days_ago_end] if days_ago_end > 0 else data[-days_ago_start:]
            
        def format_ctx(w_data, s_data, d_data):
            w_str = "\n".join([f"- {r[0]}: {r[6]} (코멘트/RPE: {r[7]})" for r in w_data if len(r)>7])
            s_str = "\n".join([f"- {r[0]}: 수면 {r[2]}, 컨디션 {r[4]}, 체중 {r[1]}" for r in s_data if len(r)>4])
            d_lines = []
            for r in d_data:
                if len(r) > 3:
                    meals = [m for m in r[3:8] if m.strip()]
                    if meals: d_lines.append(f"- {r[0]}: {' / '.join(meals)}")
            d_str = "\n".join(d_lines) if d_lines else "- 기록 없음"
            return w_str, s_str, d_str

        prompt_header = f"""수석 피지컬 코치 제미나이에게.
목표: 2027년 말 전역 직후 아일랜드, 덴마크, 스웨덴, 노르웨이 1~2부 리그 진출.

{TRAINING_DICT}
"""
        final_prompt = ""

        if "1️⃣" in report_type:
            w_ctx, s_ctx, _ = format_ctx(aw[-7:], a_s[-7:], [])
            final_prompt = prompt_header + f"""
[최근 7일간의 훈련 및 신체 데이터]
▶ 수면/컨디션/체중:
{s_ctx}

▶ 운동 기록:
{w_ctx}

위의 데이터를 분석해서 선수의 현재 피로도와 초과 회복 상태를 파악해줘. 
그리고 오늘 당장 용와초 잔디구장에서 수행해야 할 가장 적합한 훈련(나의 SOP 도감 참조)을 3가지 조합해서 추천해줘.
"""
        elif "2️⃣" in report_type:
            w_ctx, s_ctx, d_ctx = format_ctx(aw[-1:], a_s[-1:], a_d[-1:])
            final_prompt = prompt_header + f"""
[오늘의 훈련, 신체, 식단 데이터]
▶ 수면/컨디션/체중:
{s_ctx}

▶ 운동 기록:
{w_ctx}

▶ 오늘 섭취 식단:
{d_ctx}

1. 오늘 수행한 훈련의 역학적 타겟을 분석하고 신체 컨디션과 연관 지어 평가해줘.
2. [중요] 오늘 섭취한 식단 텍스트를 분석해서 총 예상 섭취 칼로리(kcal)와 대략적인 탄단지 비율을 계산해서 맨 밑에 직관적인 숫자로 알려줘. (내가 앱에 다시 기록할 수 있게)
"""
        elif "3️⃣" in report_type:
            w_curr, s_curr, _ = format_ctx(get_data_slice(aw, 7, 0), get_data_slice(a_s, 7, 0), [])
            w_prev, s_prev, _ = format_ctx(get_data_slice(aw, 14, 7), get_data_slice(a_s, 14, 7), [])
            final_prompt = prompt_header + f"""
[최근 1주차(이번 주) 데이터]
▶ 컨디션: \n{s_curr}
▶ 훈련: \n{w_curr}

[이전 2주차(지난 주) 데이터]
▶ 컨디션: \n{s_prev}
▶ 훈련: \n{w_prev}

이번 주 1주일간의 훈련 볼륨과 신체 컴포지션(체중/컨디션)을 평가해주고, 지난 주(2주 전) 기록과 구체적으로 비교해서 어떤 부분에서 성장이 있었고 피로가 누적되었는지 날카롭게 분석해줘.
"""
        elif "4️⃣" in report_type:
            w_curr, s_curr, _ = format_ctx(get_data_slice(aw, 30, 0), get_data_slice(a_s, 30, 0), [])
            w_prev, s_prev, _ = format_ctx(get_data_slice(aw, 60, 30), get_data_slice(a_s, 60, 30), [])
            final_prompt = prompt_header + f"""
[최근 1개월(이번 달) 데이터]
▶ 컨디션: \n{s_curr}
▶ 훈련: \n{w_curr}

[이전 2개월차(지난 달) 데이터]
▶ 컨디션: \n{s_prev}
▶ 훈련: \n{w_prev}

한 달 단위의 중장기적인 훈련 볼륨과 신체 컴포지션 변화를 평가해줘. 지난 달 기록과 비교해서 점진적 과부하가 잘 이루어지고 있는지, 휴식 주기는 적절했는지 종합적으로 분석하고 다음 달 훈련 방향성을 제시해줘.
"""
        st.code(final_prompt, language="markdown")
