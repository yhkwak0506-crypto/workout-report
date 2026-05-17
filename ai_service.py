import requests
import time
import re
import streamlit as st
from typing import Optional

def get_api_key() -> str:
    if "GEMINI_API_KEY" in st.secrets: return st.secrets["GEMINI_API_KEY"]
    elif "gcp" in st.secrets and "GEMINI_API_KEY" in st.secrets["gcp"]: return st.secrets["gcp"]["GEMINI_API_KEY"]
    return ""

GEMINI_API_KEY = get_api_key()
HAS_AI = bool(GEMINI_API_KEY)

@st.cache_resource(ttl=3600) 
def get_best_gemini_model() -> str:
    if not HAS_AI: return ""
    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    try:
        list_resp = requests.get(list_url, timeout=10)
        if list_resp.status_code == 200:
            for m in list_resp.json().get('models', []):
                name = m.get('name', '')
                if 'generateContent' in m.get('supportedGenerationMethods', []) and 'gemini' in name.lower() and 'vision' not in name.lower():
                    return name
    except Exception as e:
        pass
    return "models/gemini-1.5-flash" 

def ask_gemini(prompt: str, retries: int = 4) -> str:
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
        except Exception as e:
            time.sleep(3)
            continue
    return "🚨 구글 AI 서버 혼잡 (503). 잠시 후 다시 시도해 주세요."

def get_body_feedback(weight: float, muscle: float, fat_pct: float, fat_mass: float) -> str:
    prompt = f"""
    엘리트 축구 선수의 피지컬 코치야. 목표는 2027년 말 전역 후 아일랜드, 덴마크, 스웨덴, 노르웨이 1~2부 리그 진출.
    현재: 체중 {weight}kg, 골격근량 {muscle}kg, 체지방률 {fat_pct}%, 체지방량 {fat_mass}kg.
    유럽 하부리그 프로 선수들의 평균 폼과 비교해서 직관적으로 평가해줘.
    체지방이 높다면 "약 Xg 감량 필요"로 타겟을 주고, 좋다면 칭찬해줘. 현실적이고 날카롭게 한 문단으로.
    """
    return ask_gemini(prompt)

def get_ai_intensity(summary: str, hr_data: str, comments: str) -> int:
    prompt = f"""
    목표: 2027년 북유럽/아일랜드 프로 리그 복귀.
    훈련 내용: {summary} | 심박: {hr_data} | 선수 코멘트: {comments}
    위 데이터를 바탕으로 육체적 강도(RPE)를 1~10 스케일로 평가해. 1에서 10 사이의 숫자만 대답해. (예: 7)
    """
    try:
        res = ask_gemini(prompt)
        match = re.search(r'\d+', res)
        return min(10, max(1, int(match.group()))) if match else 5
    except Exception as e: 
        return 5
