"""
門牌地址解析與空間聚合測試 (Address Resolution & Spatial Aggregation)
"""

import pandas as pd
import pytest
from twintower.constants import AddressPrecision
from twintower.locations import LocationResolver


def test_parse_address_components():
    # 測試精確門牌
    comp1 = LocationResolver.parse_address_components("台北市中正區重慶南路一段100號")
    assert comp1["district"] == "中正區"
    assert comp1["road_name"] == "重慶南路一段"
    assert comp1["lane"] is None
    assert comp1["num_start"] == 100
    assert comp1["num_end"] == 100

    # 測試區間號碼 (全形與半形符號)
    comp2 = LocationResolver.parse_address_components("大同區延平北路一段1~30號")
    assert comp2["district"] == "大同區"
    assert comp2["road_name"] == "延平北路一段"
    assert comp2["num_start"] == 1
    assert comp2["num_end"] == 30

    comp3 = LocationResolver.parse_address_components("萬華區西寧南路101至120號")
    assert comp3["num_start"] == 101
    assert comp3["num_end"] == 120

    # 測試巷弄
    comp4 = LocationResolver.parse_address_components("中山區長安西路40巷5弄12號")
    assert comp4["lane"] == 40
    assert comp4["alley"] == 5
    assert comp4["num_start"] == 12


def test_synthetic_doorplate_resolution():
    # 建立合成門牌測試集
    fake_doorplates = pd.DataFrame([
        {"省市縣市代碼": 63000, "鄉鎮市區代碼": 63000050, "街路段": "重慶南路一段", "巷": None, "弄": None, "號": "10號", "橫座標": 301800.0, "縱座標": 2771200.0},
        {"省市縣市代碼": 63000, "鄉鎮市區代碼": 63000050, "街路段": "重慶南路一段", "巷": None, "弄": None, "號": "20號", "橫座標": 301820.0, "縱座標": 2771220.0},
        {"省市縣市代碼": 63000, "鄉鎮市區代碼": 63000050, "街路段": "重慶南路一段", "巷": None, "弄": None, "號": "30號", "橫座標": 301840.0, "縱座標": 2771240.0},
    ])

    resolver = LocationResolver(doorplate_df=fake_doorplates, manual_overrides_path=None)

    # 1. 精確號碼匹配 (10號)
    loc_single = resolver.resolve("台北市中正區重慶南路一段10號", "loc_1")
    assert loc_single.precision == AddressPrecision.EXACT
    assert loc_single.point_x_twd97 == 301800.0
    assert loc_single.point_y_twd97 == 2771200.0
    assert loc_single.doorplate_count == 1

    # 2. 號碼區間匹配 (1~30號)
    loc_range = resolver.resolve("台北市中正區重慶南路一段1~30號", "loc_2")
    assert loc_range.precision == AddressPrecision.NUMBER_RANGE
    assert loc_range.doorplate_count == 3
    # 重心平均
    assert loc_range.point_x_twd97 == pytest.approx(301820.0)
    assert loc_range.point_y_twd97 == pytest.approx(2771220.0)
    # 外包範圍
    assert loc_range.min_x_twd97 == 301800.0
    assert loc_range.max_x_twd97 == 301840.0
    assert loc_range.min_y_twd97 == 2771200.0
    assert loc_range.max_y_twd97 == 2771240.0

    # 3. 查無特定號碼但有路段
    loc_road = resolver.resolve("台北市中正區重慶南路一段999號", "loc_3")
    assert loc_road.precision == AddressPrecision.ROAD_SEGMENT
    assert loc_road.doorplate_count == 3  # 回退到路段現有門牌

    # 4. 完全無法解析
    loc_unres = resolver.resolve("某處無名空地", "loc_4")
    assert loc_unres.precision == AddressPrecision.UNRESOLVED
    assert loc_unres.point_x_twd97 is None


def test_manual_override():
    # 測試 manual_locations.yaml 覆蓋機制
    resolver = LocationResolver(
        doorplate_df=None,
        manual_overrides_path="config/manual_locations.yaml"
    )
    # 鄭州路8號已於 manual_locations.yaml 註冊
    loc_d1 = resolver.resolve("台北市中正區鄭州路8號", "loc_d1")
    assert loc_d1.is_overridden is True
    assert loc_d1.precision == AddressPrecision.EXACT
    assert loc_d1.point_x_twd97 == pytest.approx(301917.188, abs=0.01)
    assert loc_d1.point_y_twd97 == pytest.approx(2771280.254, abs=0.01)
    assert "D1基地" in loc_d1.evidence_notes
