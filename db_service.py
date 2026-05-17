import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Any
import ai_service

MY_SHEET_URL = "https://docs.google.com/spreadsheets/d/1N4KGhJf1ta1MOcATsOXcJayTe9ULsNGhL_9u8Rdbo_Q/edit"

@st.cache_resource
def init_connection():
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(dict(st.secrets["gcp"]), scopes=scopes)
    return gspread.authorize(creds)

try:
    gc = init_connection()
    doc = gc.open_by_url(MY_SHEET_URL)
    sheet_workout = doc.worksheet("운동로그") if "운동로그" in [w.title for w in doc.worksheets()] else doc.get_worksheet(0)
    
    try: sheet_diet = doc.worksheet("식단로그")
    except Exception: sheet_diet = doc.add_worksheet(title="식단로그", rows="1000", cols="7")
    
    try: sheet_sleep = doc.worksheet("수면/컨디션로그")
    except Exception: sheet_sleep = doc.add_worksheet(title="수면/컨디션로그", rows="1000", cols="10")
except Exception as e:
    st.error(f"🚨 구글 시트 연동 실패: {e}")

@st.cache_data(ttl=5)
def get_cached_data(tab_name: str) -> List[List[str]]:
    try:
        if tab_name == "sleep": return sheet_sleep.get_all_values()
        elif tab_name == "workout": return sheet_workout.get_all_values()
        elif tab_name == "diet": return sheet_diet.get_all_values()
    except Exception as e: 
        return []
    return []

def save_workout(data_dict: Dict[str, Any]):
    try:
        hr_str = f"Avg:{data_dict.get('평균 심박','')}, Max:{data_dict.get('최대 심박','')}, HRR:{data_dict.get('심박 회복량(HRR)','')}"
        comment_str = data_dict.get("선수 코멘트", "")
        
        # Service 간 통신 (DB Service가 AI Service를 호출)
        intensity = ai_service.get_ai_intensity(data_dict.get("상세 훈련 내용 (SOP 및 실전 역학)", ""), hr_str, comment_str)
        data_dict["생리학적 분석 및 영양/비고"] = f"AI추정강도:{intensity} | 코멘트:{comment_str}"
        
        cols = ["날짜", "공복 체중", "훈련 볼륨", "평균 심박", "최대 심박", "심박 회복량(HRR)", "상세 훈련 내용 (SOP 및 실전 역학)", "생리학적 분석 및 영양/비고"]
        row_data = [str(data_dict.get(c, "")) for c in cols]
        
        sheet_workout.append_row(row_data)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"운동 저장 실패: {e}")

def save_single_meal(today: str, col_idx: int, text_val: str):
    try:
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
    except Exception as e:
        st.error(f"식단 저장 실패: {e}")
