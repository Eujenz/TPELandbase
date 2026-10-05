"""
日期解析與確定性屋齡計算測試 (Deterministic Dates & Building Age)
規範：所有時間相依值一律由 calculation_as_of 計算，嚴禁隱含 datetime.now()
"""

from datetime import date
import pytest
from twintower.dates import (
    calculate_building_age,
    parse_roc_date,
    parse_roc_year_month,
)


def test_parse_roc_date():
    # 7碼民國年月日: 1130520 -> 2024-05-20
    d, s = parse_roc_date("1130520")
    assert d == date(2024, 5, 20)
    assert s == "1130520"

    # 6碼民國年月日: 891231 -> 2000-12-31
    d, s = parse_roc_date("891231")
    assert d == date(2000, 12, 31)

    # 7碼前綴0: 0990101 -> 2010-01-01
    d, s = parse_roc_date("0990101")
    assert d == date(2010, 1, 1)

    # 無效日期
    d, s = parse_roc_date("invalid")
    assert d is None

    # None / 空字串
    assert parse_roc_date(None) == (None, None)
    assert parse_roc_date("") == (None, None)


def test_parse_roc_year_month():
    # 7碼建築完成年月 (有日期): 0711130 -> 1982-11-30
    d, s = parse_roc_year_month("0711130")
    assert d == date(1982, 11, 30)

    # 5碼民國年月: 10508 -> 2016-08-01
    d, s = parse_roc_year_month("10508")
    assert d == date(2016, 8, 1)

    # 4碼民國年月: 7508 -> 1986-08-01
    d, s = parse_roc_year_month("7508")
    assert d == date(1986, 8, 1)

    # 空或無效
    assert parse_roc_year_month(None) == (None, None)
    assert parse_roc_year_month("9999999999")[0] is None


def test_deterministic_building_age():
    # 完工日期: 1982-11-30
    comp_date = date(1982, 11, 30)

    # 計算基準日 1: 2024-11-30 (42.0 年)
    age_2024 = calculate_building_age(comp_date, as_of=date(2024, 11, 30))
    assert age_2024 == 42.0

    # 計算基準日 2: 2026-10-01
    # 天數差: (2026-10-01 - 1982-11-30).days = 16011 天
    # 16011 / 365.25 = 43.8357... -> 43.8 年
    age_2026 = calculate_building_age(comp_date, as_of=date(2026, 10, 1))
    assert age_2026 == 43.8

    # 完工日晚於計算基準日 (興建中/預售): 應回傳 0.0
    age_future = calculate_building_age(date(2027, 1, 1), as_of=date(2026, 10, 1))
    assert age_future == 0.0

    # 完工日未知: 回傳 None
    assert calculate_building_age(None, as_of=date(2026, 10, 1)) is None
