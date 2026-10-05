"""
候選資料視圖模型 (Candidate View-Model Contract)
嚴格落實 docs/UI_SPEC.md 定義之契約。
所有尚未實作之欄位在真實模式下一律標註「待實作」，嚴禁捏造數值。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from twintower.constants import ConditionStatus, AddressPrecision, CandidateGrade


@dataclass
class CandidateViewModel:
    candidate_id: str
    district: str
    address_display: str
    address_precision: str
    is_location_overridden: bool
    transaction_date_str: str
    total_price_w: float
    parking_price_w: float
    property_price_w: float
    parking_included_flag: bool
    land_area_ping: float
    land_share_confidence: str
    building_area_ping: float
    building_age_years: Optional[float]
    building_type: str
    distance_c1d1_m: Optional[float]
    distance_min_m: Optional[float]
    distance_max_m: Optional[float]
    distance_verified: bool
    distance_threshold_status: str
    requires_manual_check: bool

    # 待後續階段實作欄位 (真實模式下一律為「待實作」)
    candidate_grade: str = "待實作"
    total_score: str = "待實作"
    road_width_m: str = "待實作"
    road_status: str = "待實作"
    zoning_code: str = "待實作"
    block_integrity: str = "待實作"
    integration_potential: str = "待實作"
    urban_renewal_status: str = "待實作"
    station_distances: str = "待實作"

    # 空間坐標 (WGS84 供地圖渲染)
    lat_wgs84: Optional[float] = None
    lon_wgs84: Optional[float] = None
    min_x_twd97: Optional[float] = None
    min_y_twd97: Optional[float] = None
    max_x_twd97: Optional[float] = None
    max_y_twd97: Optional[float] = None

    # 為何符合條件檢視 (Condition Check Results)
    condition_checks: Dict[str, str] = field(default_factory=dict)
    # 證據表清單 (Evidence Table Rows)
    evidence_rows: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_real_duckdb_row(cls, row: dict) -> "CandidateViewModel":
        """
        從 Phase 1a DuckDB candidate_properties 與關聯表建構。
        未實作欄位嚴格填入「待實作」或 UNKNOWN。
        """
        cand_id = row.get("candidate_id", "")
        tot_p = float(row.get("total_price_twd", 0.0)) / 10000.0
        park_p = float(row.get("parking_price_twd", 0.0)) / 10000.0
        prop_p = float(row.get("property_price_twd", 0.0)) / 10000.0
        dist_pt = row.get("distance_point_m")
        dist_min = row.get("distance_min_m")
        dist_max = row.get("distance_max_m")
        dist_status = row.get("distance_threshold_status", ConditionStatus.UNKNOWN)
        requires_manual = bool(row.get("requires_manual_verification", False))

        # 條件檢查狀態 (Phase 1a 僅有距離有真值判定，其餘皆標待實作)
        cond_checks = {
            "總價 (≤2000萬)": "待實作",
            "土地坪數 (≥7坪)": "待實作",
            "雙星距離 (≤500m)": dist_status,
            "臨路路寬 (≥8m)": "待實作",
            "街廓與整合": "待實作",
        }

        # 證據表 (呈現真實欄位之來源與狀態)
        evidence = [
            {"欄位": "成交門牌", "數值": row.get("address", ""), "狀態": "OBSERVED", "來源": "內政部實價登錄", "驗證": row.get("address_precision", "")},
            {"欄位": "總價元", "數值": f"{tot_p:.1f} 萬元", "狀態": "OBSERVED", "來源": "內政部實價登錄", "驗證": "登錄實價"},
            {"欄位": "房地淨價", "數值": f"{prop_p:.1f} 萬元", "狀態": "DERIVED", "來源": "計算扣除車位價", "驗證": "已拆分" if not row.get("parking_price_included_in_total") else "車位內含"},
            {"欄位": "土地坪數", "數值": f"{row.get('land_area_ping', 0.0):.2f} 坪", "狀態": "DERIVED", "來源": "法定換算 (1坪=3.305785m²)", "驗證": f"信心度:{row.get('land_share_confidence')}"},
            {"欄位": "雙星邊界距離", "數值": f"{dist_pt:.1f} m" if dist_pt is not None else "未知", "狀態": "DERIVED", "來源": "都市計畫 C1/D1 外緣多邊形", "驗證": "精確驗證" if row.get("distance_verified") else "未精確驗證/需查核"},
            {"欄位": "臨路寬度", "數值": "待實作", "狀態": "UNKNOWN", "來源": "Phase 2b 道路圖層", "驗證": "尚未串接"},
            {"欄位": "使用分區", "數值": "待實作", "狀態": "UNKNOWN", "來源": "Phase 2b 分區圖層", "驗證": "尚未串接"},
            {"欄位": "街廓完整度", "數值": "待實作", "狀態": "UNKNOWN", "來源": "Phase 2b 地籍圖層", "驗證": "非宗地維持UNKNOWN"},
        ]

        return cls(
            candidate_id=cand_id,
            district=row.get("district", ""),
            address_display=row.get("address", ""),
            address_precision=row.get("address_precision", AddressPrecision.UNRESOLVED),
            is_location_overridden=bool(row.get("is_overridden", False)),
            transaction_date_str=str(row.get("transaction_date", "")),
            total_price_w=round(tot_p, 1),
            parking_price_w=round(park_p, 1),
            property_price_w=round(prop_p, 1),
            parking_included_flag=bool(row.get("parking_price_included_in_total", False)),
            land_area_ping=round(float(row.get("land_area_ping", 0.0)), 2),
            land_share_confidence=row.get("land_share_confidence", "UNKNOWN"),
            building_area_ping=round(float(row.get("building_area_ping", 0.0)), 2),
            building_age_years=row.get("building_age_years"),
            building_type=row.get("building_type", "住宅"),
            distance_c1d1_m=dist_pt,
            distance_min_m=dist_min,
            distance_max_m=dist_max,
            distance_verified=bool(row.get("distance_verified", False)),
            distance_threshold_status=dist_status,
            requires_manual_check=requires_manual,
            candidate_grade="待實作",
            total_score="待實作",
            road_width_m="待實作",
            road_status="待實作",
            zoning_code="待實作",
            block_integrity="待實作",
            integration_potential="待實作",
            urban_renewal_status="待實作",
            station_distances="待實作",
            lat_wgs84=row.get("lat_wgs84"),
            lon_wgs84=row.get("lon_wgs84"),
            min_x_twd97=row.get("min_x_twd97"),
            min_y_twd97=row.get("min_y_twd97"),
            max_x_twd97=row.get("max_x_twd97"),
            max_y_twd97=row.get("max_y_twd97"),
            condition_checks=cond_checks,
            evidence_rows=evidence,
        )

    @classmethod
    def from_demo_fixture(cls, fixture_dict: dict) -> "CandidateViewModel":
        """從示範假資料物件建構完整版面 (包含示範用分級與評分)"""
        return cls(**fixture_dict)
