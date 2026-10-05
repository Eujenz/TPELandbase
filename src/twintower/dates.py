"""
民國年與西元年轉換、屋齡確定性計算模組
規範：所有時間相依值 (屋齡、年限視窗) 一律使用 calculation_as_of，嚴禁隱含 datetime.now() / today()。
"""

from datetime import date, datetime
import re
from typing import Optional, Tuple


def parse_roc_date(roc_str: Optional[str]) -> Tuple[Optional[date], Optional[str]]:
    """
    解析民國年月日字串 (如 '1130520' 或 '0891231')
    回傳: (datetime.date 物件, 原始清洗後字串)
    """
    if roc_str is None:
        return None, None
    s = str(roc_str).strip()
    if not s or s.lower() in ("nan", "none", "null"):
        return None, None
    
    # 移除非數字字元
    digits = re.sub(r"\D", "", s)
    if len(digits) == 7: # 3碼年 + 2碼月 + 2碼日 (如 1130520)
        roc_year = int(digits[:3])
        month = int(digits[3:5])
        day = int(digits[5:7])
    elif len(digits) == 6: # 2碼年 + 2碼月 + 2碼日 (如 891231)
        roc_year = int(digits[:2])
        month = int(digits[2:4])
        day = int(digits[4:6])
    else:
        return None, s

    try:
        ce_year = roc_year + 1911
        d = date(ce_year, month, day)
        return d, s
    except (ValueError, OverflowError):
        return None, s


def parse_roc_year_month(roc_str: Optional[str]) -> Tuple[Optional[date], Optional[str]]:
    """
    解析民國年月字串 (如建築完成年月 '0711130' 或 '08506' 或 '10212')
    若有日則解析至日，若僅有年月則預設為該月 1 日
    """
    if roc_str is None:
        return None, None
    s = str(roc_str).strip()
    if not s or s.lower() in ("nan", "none", "null"):
        return None, None
    
    digits = re.sub(r"\D", "", s)
    if len(digits) in (6, 7) and int(digits[-2:]) > 0 and int(digits[-2:]) <= 31:
        # 可能是完整的 YYYMMDD
        return parse_roc_date(s)
    elif len(digits) == 5: # 3碼年 + 2碼月 (如 10508)
        roc_year = int(digits[:3])
        month = int(digits[3:5])
        day = 1
    elif len(digits) == 4: # 2碼年 + 2碼月 (如 7508)
        roc_year = int(digits[:2])
        month = int(digits[2:4])
        day = 1
    else:
        return None, s

    try:
        ce_year = roc_year + 1911
        if not (1 <= month <= 12):
            return None, s
        return date(ce_year, month, day), s
    except (ValueError, OverflowError):
        return None, s


def calculate_building_age(
    completion_date: Optional[date],
    as_of: date
) -> Optional[float]:
    """
    依據 calculation_as_of 確定性計算屋齡 (年，浮點數保留一位小數)
    若完工日未知則回傳 None
    """
    if completion_date is None:
        return None
    # 依實際天數除以 365.25 年精確計算
    days = (as_of - completion_date).days
    if days < 0:
        # 完工日晚於計算基準日 (例如預售/興建中案件)
        return 0.0
    age = round(days / 365.25, 1)
    return age
