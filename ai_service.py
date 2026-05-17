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

# 💡 [V13.7 업데이트] 프리킥 추가 (세트 사이 적극적 휴식 및 기술 유지)
TRAINING_DICT = """
[곽연혁 선수 전용 훈련 역학 및 SOP (용와초 잔디구장 기준)]
1. 40/20 풀코트 인터벌: 40초 동안 엔드라인에서 드리블 출발 -> 하프라인에 공 정지 -> 반대편 엔드라인 찍고 복귀 -> 하프라인 공 드리블 후 슈팅 마무리. 남은 시간+20초 휴식. (타겟: 유산소성 역치 및 경기 후반 90분 유지력)
2. 40/20 하프라인 인터벌: 하프라인-사이드라인 교차점 출발 -> 킥오프 위치에 공 정지 -> 사이드라인 찍고 복귀 -> 드리블로 센터서클 탈출(각 있는 드리블) 후 슈팅 마무리. 남은 시간+20초 동안 반대편 이동 및 휴식.
3. 25/20 페널티박스 인터벌: (홀수세트) 25초간 출발하여 박스 모서리에 공 정지 -> 각 있게 턴 후 시작점 복귀 -> 20초 휴식. / (짝수세트) 25초간 튀어나가 모서리 2/3 지점 코디네이션 -> 공 픽업 후 라인 따라 드리블 -> 반대 모서리 컷 동작 후 슈팅. 남은 시간+20초 안에 공 줍고 복귀. 양방향 교대. (타겟: 좁은 공간 잔발 전환, 가속/급감속, Agility, 젖산 내성)
4. 15/5 드리블 슈팅 믹스 인터벌: 15초 고강도 드리블 + 5초 휴식 3회 반복. 3번째에 슈팅 마무리. 30초 동안 공 줍고 다음 세트 준비. (타겟: 극한의 심박수 및 피로도 속 기술 유지력)
5. 15/15 매스템포런: 엔드라인에서 반대 엔드라인까지 15초 러닝 후 15초 휴식.
6. 프리킥 (세트 사이): 고강도 인터벌 세트 사이 불완전 휴식기 또는 기술 훈련으로 진행. 심폐 부하는 낮지만 피로가 누적된 상태에서 코어와 하체(특히 대퇴사두, 서혜부)의 정교한 킥 임팩트를 유지하는 것이 목적. (타겟: 피로 상태에서의 데드볼 타격 감각 및 근관절 협응력)
"""

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
    {TRAINING_DICT}
    
    [오늘 훈련 내용]: {summary} 
    [심박 데이터]: {hr_data} 
    [선수 코멘트]: {comments}
    
    위 훈련 도감과 데이터를 바탕으로 오늘 훈련의 육체적 강도(RPE)를 1~10 스케일로 평가해. 1에서 10 사이의 숫자만 대답해. (예: 7)
    """
    try:
        res = ask_gemini(prompt)
        match = re.search(r'\d+', res)
        return min(10, max(1, int(match.group()))) if match else 5
    except Exception as e: 
        return 5
