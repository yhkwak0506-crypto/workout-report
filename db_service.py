import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timedelta
import gspread
from google.oauth2.service_account import Credentials

# ==========================================
# 📌 Google Spreadsheet 설정
# ==========================================

SHEET_TITLE = "2026 곽연혁 선수 S-Tier 피지컬 마스터 시트 V6 (웨이트 상세본)"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ==========================================
# 🔐 Google 인증 (안전한 캐싱)
# ==========================================

@st.cache_resource
def init_connection():
    """Google Service Account 인증 연결"""
    try:
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp"]),
            scopes=SCOPES
        )
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"🚨 Google 인증 실패: {e}")
        return None


@st.cache_resource
def get_sheets():
    """필요한 시트를 안전하게 로딩하고 캐싱 (지연 로딩)"""
    gc = init_connection()
    if gc is None:
        return {}

    try:
        spreadsheet = gc.open(SHEET_TITLE)
        return {
            "sleep": spreadsheet.worksheet("수면/컨디션 로그"),
            "workout": spreadsheet.worksheet("운동로그"),
            "diet": spreadsheet.worksheet("식단로그")
        }
    except Exception as e:
        st.error(f"🚨 시트 연결 실패. 권한이나 파일명을 확인하세요: {e}")
        return {}

# ==========================================
# 🚀 스마트 지연 로딩 프록시 (ui_tabs.py 충돌 방지용)
# ==========================================
class SheetProxy:
    """
    ui_tabs.py에서 예전처럼 db.sheet_sleep.append_row()를 쓸 수 있게 해주면서,
    실제 구글 통신은 100% 안전한 지연 로딩으로 처리해주는 마법의 클래스입니다.
    """
    def __init__(self, key_name):
        self.key_name = key_name

    def __getattr__(self, attr):
        sheets = get_sheets()
        if not sheets or self.key_name not in sheets:
            raise AttributeError(f"'{self.key_name}' 시트를 불러올 수 없습니다.")
        return getattr(sheets[self.key_name], attr)

# 외부에서 부를 수 있도록 오픈 (UI 코드를 수정할 필요가 없어집니다)
sheet_sleep = SheetProxy("sleep")
sheet_workout = SheetProxy("workout")
sheet_diet = SheetProxy("diet")


# ==========================================
# 📥 데이터 읽기 (10분 캐싱)
# ==========================================

@st.cache_data(ttl=600)
def get_cached_data(tab_name: str):
    """Google Sheets 데이터 읽기"""
    sheets = get_sheets()
    if not sheets or tab_name not in sheets:
        return []

    try:
        return sheets[tab_name].get_all_values()
    except Exception as e:
        st.error(f"🚨 데이터 로드 실패 ({tab_name}): {e}")
        return []


# ==========================================
# 🏋️ 운동 & 식단 데이터 저장
# ==========================================

def save_workout(data: dict):
    if not hasattr(sheet_workout, 'append_row'): return False
    
    row = [
        data.get("날짜", ""), data.get("공복 체중", ""), data.get("훈련 볼륨", ""),
        data.get("평균 심박", ""), data.get("최대 심박", ""), data.get("심박 회복량(HRR)", ""),
        data.get("상세 훈련 내용 (SOP 및 실전 역학)", ""), data.get("선수 코멘트", "")
    ]
    try:
        sheet_workout.append_row(row)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"🚨 운동 데이터 저장 실패: {e}")
        return False

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
                    
        if target_row:
            sheet_diet.update_cell(target_row, col_idx, meal_text)
        else:
            new_row = [""] * 9
            new_row[0] = today
            new_row[col_idx - 1] = meal_text
            sheet_diet.append_row(new_row)
            
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"🚨 식단 저장 실패: {e}")
        return False
