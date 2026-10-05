"""
距離計算與門檻判定模組 (Distance Calculation & Threshold Crossings)
依據 Phase 0b 裁決採用選項 A: 官方 C1/D1 雙基地多邊形外緣 (polygon_min_distance)。

不可違反原則：
1. 嚴禁使用無出處座標；以官方都市計畫特定專用區 C1/D1 基地多邊形 (EPSG:3826) 為基準。
2. 號碼區間 (NUMBER_RANGE) 或路段 (ROAD_SEGMENT) 計算距離上下界 (min/max)。
3. 若跨越 500m 或 700m 門檻，判定狀態標記為 UNKNOWN，不得武斷判定為 PASS 或 FAIL，
   且 distance_verified 設為 False、requires_manual_verification 設為 True。
"""

import os
from typing import Optional, Tuple
import geopandas as gpd
import shapely.geometry
from shapely.geometry import Point, box, MultiPolygon, Polygon
import yaml

from twintower.constants import AddressPrecision, ConditionStatus
from twintower.models import DistanceResult, Location


class DistanceCalculator:
    def __init__(
        self,
        targets_config_path: str = "config/targets.yaml",
        polygon_geojson_path: Optional[str] = "config/geometry/c1d1_bases_3826.geojson",
    ):
        self.targets_config_path = targets_config_path
        self.polygon_geojson_path = polygon_geojson_path
        self._load_config()
        self._load_geometry()

    def _load_config(self):
        if not os.path.exists(self.targets_config_path):
            raise FileNotFoundError(f"Targets config not found at {self.targets_config_path}")
        with open(self.targets_config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        
        self.method = self.config.get("distance_method", "polygon_min_distance")
        thresholds = self.config.get("thresholds", {})
        self.core_radius_m = float(thresholds.get("core_radius_m", 500.0))
        self.secondary_radius_m = float(thresholds.get("secondary_radius_m", 700.0))

    def _load_geometry(self):
        """載入 C1/D1 雙基地多邊形"""
        if self.polygon_geojson_path and os.path.exists(self.polygon_geojson_path):
            gdf = gpd.read_file(self.polygon_geojson_path)
            polys = list(gdf.geometry)
            if len(polys) == 1:
                self.target_geometry = polys[0]
            else:
                self.target_geometry = MultiPolygon(polys)
        else:
            # 備用：若無 GeoJSON，以 config 中的質心建構點
            ref_pts = self.config.get("reference_points", {})
            b_pt = ref_pts.get("candidate_b_centroid", {}).get("twd97", [301798.23, 2771279.14])
            self.target_geometry = Point(b_pt[0], b_pt[1])

    def calculate(self, location: Location) -> DistanceResult:
        """
        計算 Location 至 C1/D1 目標幾何的距離與門檻狀態
        """
        # 1. 無法解析或無坐標
        if (
            location.precision == AddressPrecision.UNRESOLVED
            or location.point_x_twd97 is None
            or location.point_y_twd97 is None
        ):
            return DistanceResult(
                distance_point_m=None,
                distance_min_m=None,
                distance_max_m=None,
                distance_verified=False,
                distance_method=self.method,
                requires_manual_verification=True,
                threshold_status=ConditionStatus.UNKNOWN,
            )

        pt = Point(location.point_x_twd97, location.point_y_twd97)
        dist_pt = float(self.target_geometry.distance(pt))

        # 2. 精確門牌或單點
        if (
            location.precision == AddressPrecision.EXACT
            or location.min_x_twd97 is None
            or location.max_x_twd97 is None
            or (location.min_x_twd97 == location.max_x_twd97 and location.min_y_twd97 == location.max_y_twd97)
        ):
            dist_min = dist_pt
            dist_max = dist_pt
            # EXACT 且非人工覆蓋有疑慮者為 verified
            distance_verified = True
            requires_manual = False

            if dist_pt <= self.core_radius_m:
                status = ConditionStatus.PASS
            elif dist_pt <= self.secondary_radius_m:
                status = ConditionStatus.NEAR
            else:
                status = ConditionStatus.FAIL

            return DistanceResult(
                distance_point_m=round(dist_pt, 2),
                distance_min_m=round(dist_min, 2),
                distance_max_m=round(dist_max, 2),
                distance_verified=distance_verified,
                distance_method=self.method,
                requires_manual_verification=requires_manual,
                threshold_status=status,
            )

        # 3. 號碼區間 (NUMBER_RANGE) 或 路段 (ROAD_SEGMENT)
        # 計算外包矩形至多邊形的最短與最長距離
        envelope = box(
            location.min_x_twd97,
            location.min_y_twd97,
            location.max_x_twd97,
            location.max_y_twd97,
        )
        dist_min = float(self.target_geometry.distance(envelope))

        # 最遠距離取 4 個角落點的最大距離
        corners = [
            Point(location.min_x_twd97, location.min_y_twd97),
            Point(location.min_x_twd97, location.max_y_twd97),
            Point(location.max_x_twd97, location.min_y_twd97),
            Point(location.max_x_twd97, location.max_y_twd97),
        ]
        dist_max = float(max(self.target_geometry.distance(c) for c in corners))

        # 門檻判定：檢查是否跨越門檻
        is_straddling_500 = (dist_min <= self.core_radius_m < dist_max)
        is_straddling_700 = (dist_min <= self.secondary_radius_m < dist_max)

        if is_straddling_500 or is_straddling_700:
            status = ConditionStatus.UNKNOWN
            requires_manual = True
            distance_verified = False
        elif dist_max <= self.core_radius_m:
            status = ConditionStatus.PASS
            requires_manual = False
            distance_verified = False  # 區間非精確點，雖 PASS 但未精確驗證
        elif dist_min > self.core_radius_m and dist_max <= self.secondary_radius_m:
            status = ConditionStatus.NEAR
            requires_manual = False
            distance_verified = False
        elif dist_min > self.secondary_radius_m:
            status = ConditionStatus.FAIL
            requires_manual = False
            distance_verified = False
        else:
            status = ConditionStatus.UNKNOWN
            requires_manual = True
            distance_verified = False

        if location.is_overridden:
            distance_verified = True
            requires_manual = False

        return DistanceResult(
            distance_point_m=round(dist_pt, 2),
            distance_min_m=round(dist_min, 2),
            distance_max_m=round(dist_max, 2),
            distance_verified=distance_verified,
            distance_method=self.method,
            requires_manual_verification=requires_manual,
            threshold_status=status,
        )
