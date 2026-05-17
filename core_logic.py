import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import gspread
from google.oauth2.service_account import Credentials
import requests
import re
import time

# ==========================================
# 1. API 및 기본 설정
# ==========================================
def get_api_key():
    if "GEMINI_API_KEY" in st.secrets: return st.secrets["GEMINI_API_KEY"]
    elif "gcp" in st.secrets and "GEMINI_API_KEY" in st.secrets["gcp"]: return st.secrets["gcp"]["GEMINI_API_KEY"]
    return ""

GEMINI_API_KEY = get_api_key()
HAS_AI = bool(GEMINI_API_KEY)
MY_SHEET_URL = "https://docs.google.com/spreadsheets/d/1N4KGhJf1ta1MOcATsOXcJayTe9ULsNGhL_9u8Rdbo_Q/edit"

# ==========================================
# 2. 구글 시트 연결 (DB)
# ==========================================
@st.cache_resource
def init_connection():
    scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(dict(st.secrets["gcp"]), scopes=scopes)
    return gspread.authorize(creds)

try:
    gc = init_connection()
    doc = gc.open_by_url(MY_SHEET_URL)
    try: sheet_workout = doc.worksheet("운동로그")
    except: sheet_workout = doc.get_worksheet(0)
    try: sheet_diet = doc.worksheet("식단로그")
    except: sheet_diet = doc.add_worksheet(title="식단로그", rows="1000", cols="7")
    try: sheet_sleep = doc.worksheet("수면/컨디션로그")
    except: sheet_sleep = doc.add_worksheet(title="수면/컨디션로그", rows="1000", cols="10")
except Exception as e:
    pass

@st.cache_data(ttl=5)
def get_cached_data(tab_name):
    try:
        if tab_name == "sleep": return sheet_sleep.get_all_values()
        elif tab_name == "workout": return sheet_workout.get_all_values()
        elif tab_name == "diet": return sheet_diet.get_all_values()
    except: return []
    return []

# ==========================================
# 3. 제미나이 AI 로직
# ==========================================
@st.cache_resource(ttl=3600) 
def get_best_gemini_model():
    if not HAS_AI: return None
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    try:
        list_resp = requests.get(list_url)
        if list_resp.status_code == 200:
            for m in list_resp.json().get('models', []):
                name = m.get('name', '')
                if 'generateContent' in m.get('supportedGenerationMethods', []) and 'gemini' in name.lower() and 'vision' not in name.lower():
                    return name
    except: pass
    return "models/gemini-1.5-flash" 

def ask_gemini(prompt, retries=5):
    if not HAS_AI: return "API 키가 없습니다."
    target_model = get_best_gemini_model()
    url = f"https://generativelanguage.googleapis.com/v1beta/{target_model}:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    
    for attempt in range(retries):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=15)
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            elif response.status_code in [429, 500, 503]:
                time.sleep(3)
                continue
            else: return f"API 통신 에러 ({response.status_code})"
        except:
            time.sleep(3)
            continue
    return "🚨 구글 AI 서버가 현재 일시적으로 혼잡합니다. 잠시 후 다시 시도해 주세요."

# 💡 [V12.4 업데이트] AI 강도 평가 기준을 북유럽/아일랜드 프로 리그 기준으로 재설정
def get_ai_intensity(workout_summary):
    if not HAS_AI: return 5
    prompt = f"2027년 말 아일랜드, 노르웨이, 덴마크, 스웨덴 프로 리그 복귀를 목표로 하는 축구 선수가 다음 훈련을 수행했어: '{workout_summary}'. 해당 유럽 리그 선수들의 평균 훈련 데이터를 잣대로, 이 훈련의 육체적 강도(RPE)를 1부터 10 사이의 숫자로만 평가해줘. 오직 숫자만 대답해. (예: 7)"
    try:
        res = ask_gemini(prompt)
        match = re.search(r'\d+', res)
        return min(10, max(1, int(match.group()))) if match else 5
    except: return 5

# ==========================================
# 4. 유틸리티 함수
# ==========================================
def extract_number(val):
    match = re.search(r'(\d+(?:\.\d+)?)', str(val))
    return float(match.group(1)) if match else 0.0

def parse_meal_cell(cell_value):
    if not cell_value: return "", "⏳ 미등록"
    if " | AI 분석:" in cell_value:
        parts = cell_value.split(" | AI 분석:")
        return parts[0].strip(), parts[1].strip()
    return cell_value, "⏳ 분석 대기 중"

def save_single_meal(today, col_idx, text_val):
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

def save_workout(data_dict):
    intensity = get_ai_intensity(data_dict.get("상세 훈련 내용 (SOP 및 실전 역학)", ""))
    data_dict["생리학적 분석 및 영양/비고"] = f"AI추정강도:{intensity}"
    cols = ["날짜", "공복 체중", "훈련 볼륨", "평균 심박", "최대 심박", "심박 회복량(HRR)", "상세 훈련 내용 (SOP 및 실전 역학)", "생리학적 분석 및 영양/비고"]
    sheet_workout.append_row([str(data_dict.get(c, "")) for c in cols])
    st.cache_data.clear()
