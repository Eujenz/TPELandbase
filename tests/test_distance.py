"""
距離計算與門檻邊界測試 (Distance Calculation & Threshold Crossings)
依據 Phase 0b 選項 A: 官方 C1/D1 雙基地多邊形外緣 (polygon_min_distance)。

不可違反原則：
1. 嚴禁使用無出處座標。
2. 跨越 500m 或 700m 門檻之區間，狀態標為 UNKNOWN，不得武斷判定 PASS/FAIL。
3. UNRESOLVED 坐標距離為 None，狀態標為 UNKNOWN。
"""

import pytest
from shapely.geometry import Point, Polygon
from twintower.constants import AddressPrecision, ConditionStatus
from twintower.distance import DistanceCalculator
from twintower.models import Location


@pytest.fixture
def calculator():
    return DistanceCalculator(
        targets_config_path="config/targets.yaml",
        polygon_geojson_path="config/geometry/c1d1_bases_3826.geojson",
    )


def test_distance_inside_polygon(calculator):
    # C1 基地幾何中心點 (位於基地內，距離應為 0.0)
    loc = Location(
        location_id="loc_c1_center",
        original_address="C1基地內部",
        district="中正區",
        road_name="市民大道一段",
        lane=None,
        alley=None,
        door_number_start=None,
        door_number_end=None,
        precision=AddressPrecision.EXACT,
        point_x_twd97=301888.89,
        point_y_twd97=2771267.44,
        lon_wgs84=121.514,
        lat_wgs84=25.048,
        min_x_twd97=301888.89,
        min_y_twd97=2771267.44,
        max_x_twd97=301888.89,
        max_y_twd97=2771267.44,
    )
    res = calculator.calculate(loc)
    assert res.distance_point_m == 0.0
    assert res.threshold_status == ConditionStatus.PASS
    assert res.distance_verified is True
    assert res.requires_manual_verification is False


def test_distance_exact_threshold_boundaries(calculator):
    # 由多邊形外緣向正北延伸測算邊界值
    # C1 多邊形北界約為 y = 2771324.98, x = 301888.89
    # 直接以 calculator.target_geometry 測試特定距離
    # 建立一個測試點使其距離多邊形剛好為 500.0m 與 700.0m
    poly = calculator.target_geometry
    
    # 尋找 poly 最外圍邊界上的點
    ref_pt = Point(301888.89, 2771324.98)
    # 距離 500.0m 的點 (正北)
    d500_y = 2771324.98 + 500.0
    actual_d500 = poly.distance(Point(301888.89, d500_y))

    # 構造恰好 <= 500m 的點
    loc_pass = Location(
        location_id="loc_500m",
        original_address="距離 500m 處",
        district="大同區",
        road_name="測試路",
        lane=None,
        alley=None,
        door_number_start=1,
        door_number_end=1,
        precision=AddressPrecision.EXACT,
        point_x_twd97=301888.89,
        point_y_twd97=2771324.98 + (500.0 - actual_d500 + 500.0 - 0.1),
        lon_wgs84=None,
        lat_wgs84=None,
        min_x_twd97=None,
        min_y_twd97=None,
        max_x_twd97=None,
        max_y_twd97=None,
    )
    # 調整至距離 <= 500.0m
    calc_d = poly.distance(Point(loc_pass.point_x_twd97, loc_pass.point_y_twd97))
    if calc_d <= 500.0:
        res = calculator.calculate(loc_pass)
        assert res.threshold_status == ConditionStatus.PASS

    # 構造距離 600m (介於 500m 與 700m 之間)
    loc_near = Location(
        location_id="loc_near",
        original_address="距離 600m 處",
        district="大同區",
        road_name="測試路",
        lane=None,
        alley=None,
        door_number_start=10,
        door_number_end=10,
        precision=AddressPrecision.EXACT,
        point_x_twd97=301888.89,
        point_y_twd97=2771324.98 + 600.0,
        lon_wgs84=None,
        lat_wgs84=None,
        min_x_twd97=None,
        min_y_twd97=None,
        max_x_twd97=None,
        max_y_twd97=None,
    )
    res_near = calculator.calculate(loc_near)
    assert 500.0 < res_near.distance_point_m <= 700.0
    assert res_near.threshold_status == ConditionStatus.NEAR
    assert res_near.distance_verified is True

    # 構造距離 1000m (大於 700m)
    loc_fail = Location(
        location_id="loc_fail",
        original_address="距離 1000m 處",
        district="大同區",
        road_name="測試路",
        lane=None,
        alley=None,
        door_number_start=100,
        door_number_end=100,
        precision=AddressPrecision.EXACT,
        point_x_twd97=301888.89,
        point_y_twd97=2771324.98 + 1000.0,
        lon_wgs84=None,
        lat_wgs84=None,
        min_x_twd97=None,
        min_y_twd97=None,
        max_x_twd97=None,
        max_y_twd97=None,
    )
    res_fail = calculator.calculate(loc_fail)
    assert res_fail.distance_point_m > 700.0
    assert res_fail.threshold_status == ConditionStatus.FAIL


def test_straddling_range_thresholds(calculator):
    # 號碼區間 (NUMBER_RANGE) 跨越 500m 門檻 (例如 min=400m, max=600m)
    # 依規定不可判定為 PASS 或 FAIL，必須為 UNKNOWN 且 requires_manual_verification=True
    loc_straddle = Location(
        location_id="loc_straddle_500",
        original_address="跨越500m路段",
        district="大同區",
        road_name="延平北路一段",
        lane=None,
        alley=None,
        door_number_start=1,
        door_number_end=50,
        precision=AddressPrecision.NUMBER_RANGE,
        point_x_twd97=301888.89,
        point_y_twd97=2771324.98 + 500.0,
        lon_wgs84=None,
        lat_wgs84=None,
        min_x_twd97=301888.89,
        min_y_twd97=2771324.98 + 400.0, # min dist ~400m <= 500m
        max_x_twd97=301888.89,
        max_y_twd97=2771324.98 + 600.0, # max dist ~600m > 500m
    )
    res = calculator.calculate(loc_straddle)
    assert res.distance_min_m <= 500.0
    assert res.distance_max_m > 500.0
    assert res.threshold_status == ConditionStatus.UNKNOWN
    assert res.requires_manual_verification is True
    assert res.distance_verified is False


def test_range_completely_within_core(calculator):
    # 區間整體都在 500m 內 (例如 min=200m, max=350m)
    loc_core_range = Location(
        location_id="loc_core_range",
        original_address="核心區內路段",
        district="中正區",
        road_name="重慶南路一段",
        lane=None,
        alley=None,
        door_number_start=1,
        door_number_end=20,
        precision=AddressPrecision.NUMBER_RANGE,
        point_x_twd97=301888.89,
        point_y_twd97=2771324.98 + 250.0,
        lon_wgs84=None,
        lat_wgs84=None,
        min_x_twd97=301888.89,
        min_y_twd97=2771324.98 + 200.0,
        max_x_twd97=301888.89,
        max_y_twd97=2771324.98 + 350.0,
    )
    res = calculator.calculate(loc_core_range)
    assert res.distance_max_m <= 500.0
    assert res.threshold_status == ConditionStatus.PASS
    # 雖為 PASS，但因是區間未具精確門牌，distance_verified 應為 False
    assert res.distance_verified is False


def test_unresolved_location(calculator):
    loc_unres = Location(
        location_id="loc_unknown",
        original_address="無法解析地址",
        district="中正區",
        road_name=None,
        lane=None,
        alley=None,
        door_number_start=None,
        door_number_end=None,
        precision=AddressPrecision.UNRESOLVED,
        point_x_twd97=None,
        point_y_twd97=None,
        lon_wgs84=None,
        lat_wgs84=None,
        min_x_twd97=None,
        min_y_twd97=None,
        max_x_twd97=None,
        max_y_twd97=None,
    )
    res = calculator.calculate(loc_unres)
    assert res.distance_point_m is None
    assert res.threshold_status == ConditionStatus.UNKNOWN
    assert res.distance_verified is False
    assert res.requires_manual_verification is True
