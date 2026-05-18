import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timedelta
import gspread
from google.oauth2.service_account import Credentials

# 💡 V14.6 업데이트: 구글 시트 ID 오타(0->O, X->x) 완벽 수정 완료

MY_SHEET_URL = "https://docs.google.com/spreadsheets/d/1N4KGhJf1ta1MOcAtSOxcJayTe9ULsNGhL_9u8Rdbo_Q/edit"

@st.cache_resource
def init_connection():
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = Credentials.from_service_account_info(dict(st.secrets["gcp"]), scopes=scopes)
    return gspread.authorize(creds)

gc = init_connection()
spreadsheet = gc.open_by_url(MY_SHEET_URL)

# 시트 이름 매핑
sheet_sleep = spreadsheet.worksheet("수면및신체")
sheet_workout = spreadsheet.worksheet("운동기록")
sheet_diet = spreadsheet.worksheet("식단기록")

@st.cache_data(ttl=600)
def get_cached_data(tab_name: str):
    if tab_name == "sleep":
        return sheet_sleep.get_all_values()
    elif tab_name == "workout":
        return sheet_workout.get_all_values()
    elif tab_name == "diet":
        return sheet_diet.get_all_values()
    return []

def save_workout(data: dict):
    row = [
        data.get("날짜"),
        data.get("공복 체중"),
        data.get("훈련 볼륨"),
        data.get("평균 심박"),
        data.get("최대 심박"),
        data.get("심박 회복량(HRR)"),
        data.get("상세 훈련 내용 (SOP 및 실전 역학)"),
        data.get("선수 코멘트")
    ]
    sheet_workout.append_row(row)
    st.cache_data.clear()

def save_single_meal(today: str, col_idx: int, meal_text: str):
    all_d = sheet_diet.get_all_values()
    row_to_update = -1
    
    if len(all_d) > 1:
        for i, r in enumerate(all_d):
            if r[0] == today:
                row_to_update = i + 1
                break
                
    if row_to_update != -1:
        sheet_diet.update_cell(row_to_update, col_idx, meal_text)
    else:
        new_row = [""] * 9
        new_row[0] = today
        new_row[col_idx - 1] = meal_text
        sheet_diet.append_row(new_row)
        
    st.cache_data.clear()
