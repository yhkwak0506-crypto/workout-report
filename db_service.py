import streamlit as st
import pandas as pd
from datetime import datetime, date, time, timedelta
import gspread
from google.oauth2.service_account import Credentials

# 💡 V14.9 업데이트: GPT가 제안한 import 시점 크래시 방지 및 지연 로딩(Lazy Loading) 구조 적용

SHEET_TITLE = "2026 곽연혁 선수 S-Tier 피지컬 마스터 시트 V6 (웨이트 상세본)"

@st.cache_resource
def init_connection():
    """구글 API 인증 연결"""
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = Credentials.from_service_account_info(dict(st.secrets["gcp"]), scopes=scopes)
    return gspread.authorize(creds)

@st.cache_resource
def get_sheets():
    """
    💡 [GPT 추천 반영] import 시점에 바로 연결하지 않고, 
    앱이 구동된 후 필요할 때 안전하게 시트를 불러오고 캐싱합니다.
    """
    try:
        gc = init_connection()
        spreadsheet = gc.open(SHEET_TITLE)
        return {
            "sleep": spreadsheet.worksheet("수면/컨디션 로그"),
            "workout": spreadsheet.worksheet("운동로그"),
            "diet": spreadsheet.worksheet("식단로그")
        }
    except Exception as e:
        # 연결 실패 시 앱 전체가 죽지 않도록 에러만 띄우고 빈 딕셔너리 반환
        st.error(f"🚨 구글 스프레드시트 연결에 실패했습니다. 파일명이나 공유 권한을 확인해주세요! 에러 내용: {e}")
        return {}

def get_cached_data(tab_name: str):
    """안전하게 데이터를 읽어오는 함수"""
    sheets = get_sheets()
    if not sheets or tab_name not in sheets:
        return []
        
    try:
        # 10분간 데이터 캐싱
        return _fetch_all_values_cached(tab_name, datetime.now().strftime('%Y-%m-%d-%H-%M'))
    except Exception as e:
        st.error(f"데이터를 가져오는 중 오류 발생: {e}")
        return []

@st.cache_data(ttl=600)
def _fetch_all_values_cached(tab_name: str, time_key: str):
    sheets = get_sheets()
    return sheets[tab_name].get_all_values()

def save_workout(data: dict):
    """운동 기록 안전하게 저장"""
    sheets = get_sheets()
    if "workout" not in sheets:
        st.error("데이터베이스가 연결되지 않아 저장할 수 없습니다.")
        return
        
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
    sheets["workout"].append_row(row)
    st.cache_data.clear()

def save_single_meal(today: str, col_idx: int, meal_text: str):
    """식단 데이터 안전하게 업데이트 및 저장"""
    sheets = get_sheets()
    if "diet" not in sheets:
        st.error("데이터베이스가 연결되지 않아 저장할 수 없습니다.")
        return
        
    sheet_diet = sheets["diet"]
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
