import re
from typing import Tuple

def extract_number(val: str) -> float:
    try:
        match = re.search(r'(\d+(?:\.\d+)?)', str(val))
        return float(match.group(1)) if match else 0.0
    except Exception as e:
        return 0.0

def parse_meal_cell(cell_value: str) -> Tuple[str, str]:
    if not cell_value: 
        return "", "⏳ 미등록"
    if " | AI 분석:" in cell_value:
        parts = cell_value.split(" | AI 분석:")
        return parts[0].strip(), parts[1].strip()
    return cell_value, "⏳ 분석 대기 중"

def estimate_intensity_local(vol_str: str, detail_str: str) -> int:
    try:
        vol_str = str(vol_str)
        detail_str = str(detail_str)
        score = 2
        
        if "축구" in detail_str or "경기템포" in detail_str: score += 4
        if "풋살" in detail_str or "미니게임" in detail_str: score += 3
        if "러닝" in detail_str or "인터벌" in detail_str: score += 4
        if "행군" in detail_str or "각개전투" in detail_str: score += 6
        if "웨이트" in detail_str or "턱걸이" in detail_str: score += 3
        if "회복" in detail_str or "휴식" in detail_str: score -= 1
        
        km = extract_number(vol_str)
        if km >= 10: score += 3
        elif km >= 5: score += 2
        elif km > 0: score += 1
        
        return max(1, min(score, 10))
    except Exception as e: 
        return 1
