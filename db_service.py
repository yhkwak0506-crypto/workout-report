import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timedelta
import gspread
from google.oauth2.service_account import Credentials

SHEET_TITLE = "2026 곽연혁 선수 S-Tier 피지컬 마스터 시트 V6 (웨이트 상세본)"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource
def init_connection():
    try:
        creds = Credentials.from_service_account_info(dict(st.secrets["gcp"]), scopes=SCOPES)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"🚨 Google 인증 실패: {e}")
        return None

@st.cache_resource
def get_sheets():
    gc = init_connection()
    if gc is None: return {}
    try:
        spreadsheet = gc.open(SHEET_TITLE)
        return {
            # 💡 구글 시트 탭 이름을 정확히 아래 3개로 맞춰주세요! (슬래시/띄어쓰기 금지)
            "sleep": spreadsheet.worksheet("수면및신체"),
            "workout": spreadsheet.worksheet("운동로그"),
            "diet": spreadsheet.worksheet("식단로그")
        }
    except Exception as e:
        st.error(f"🚨 시트 연결 실패. 탭 이름에 슬래시(/)나 특수문자가 없는지 확인하세요: {e}")
        return {}

class SheetProxy:
    def __init__(self, key_name): self.key_name = key_name
    def __getattr__(self, attr):
        sheets = get_sheets()
        if not sheets or self.key_name not in sheets: raise AttributeError(f"'{self.key_name}' 시트 에러")
        return getattr(sheets[self.key_name], attr)

sheet_sleep = SheetProxy("sleep")
sheet_workout = SheetProxy("workout")
sheet_diet = SheetProxy("diet")

@st.cache_data(ttl=600)
def get_cached_data(tab_name: str):
    sheets = get_sheets()
    if not sheets or tab_name not in sheets: return []
    try: return sheets[tab_name].get_all_values()
    except Exception as e: return []

def save_workout(data: dict):
    if not hasattr(sheet_workout, 'append_row'): return False
    row = [data.get("날짜", ""), data.get("공복 체중", ""), data.get("훈련 볼륨", ""), data.get("평균 심박", ""), data.get("최대 심박", ""), data.get("심박 회복량(HRR)", ""), data.get("상세 훈련 내용 (SOP 및 실전 역학)", ""), data.get("선수 코멘트", "")]
    try:
        sheet_workout.append_row(row)
        st.cache_data.clear()
        return True
    except Exception as e: return False

def save_single_meal(today: str, col_idx: int, meal_text: str):
    if not hasattr(sheet_diet, 'get_all_values'): return False
    try:
        all_rows = sheet_diet.get_all_values()
        target_row = None
        if len(all_rows) > 1:
            for idx, row in enumerate(all_rows):
                if len(row) > 0 and row[0] == today:
                    target_row = idx + 1
                    break
        if target_row: sheet_diet.update_cell(target_row, col_idx, meal_text)
        else:
            new_row = [""] * 9
            new_row[0] = today
            new_row[col_idx - 1] = meal_text
            sheet_diet.append_row(new_row)
        st.cache_data.clear()
        return True
    except Exception as e: return False
