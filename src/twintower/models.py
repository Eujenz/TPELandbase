"""
twintower 核心資料模型定義
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional
from twintower.constants import (
    AddressPrecision,
    ConfidenceLevel,
    ValueOriginStatus,
    ConditionStatus,
    CandidateGrade,
)


@dataclass
class QualityIssue:
    level: str  # "INVALID" or "WARNING"
    field_name: str
    issue_type: str
    record_id: str
    value: Any
    message: str


@dataclass
class DataQualityReport:
    total_records_read: int = 0
    total_residential_candidates: int = 0
    total_invalids: int = 0
    total_warnings: int = 0
    issues: List[QualityIssue] = field(default_factory=list)
    summary_by_type: Dict[str, int] = field(default_factory=dict)

    def add_issue(self, issue: QualityIssue):
        self.issues.append(issue)
        if issue.level == "INVALID":
            self.total_invalids += 1
        else:
            self.total_warnings += 1
        self.summary_by_type[issue.issue_type] = self.summary_by_type.get(issue.issue_type, 0) + 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_records_read": self.total_records_read,
            "total_residential_candidates": self.total_residential_candidates,
            "total_invalids": self.total_invalids,
            "total_warnings": self.total_warnings,
            "summary_by_type": self.summary_by_type,
            "sample_issues": [
                {
                    "level": i.level,
                    "field": i.field_name,
                    "type": i.issue_type,
                    "record_id": i.record_id,
                    "value": str(i.value),
                    "message": i.message,
                }
                for i in self.issues[:50]  # 取前 50 個樣本
            ],
        }


@dataclass
class RawTransaction:
    serial_number: str  # 編號
    district: str       # 鄉鎮市區
    target_type: str    # 交易標的
    address_raw: str    # 土地位置建物門牌
    total_price_twd: float # 總價元
    land_area_sqm: float   # 土地移轉總面積平方公尺
    building_area_sqm: float # 建物移轉總面積平方公尺
    unit_price_sqm: Optional[float] # 單價元平方公尺
    transaction_date_roc: str # 交易年月日
    building_type: str        # 建物型態
    main_use: str            # 主要用途
    materials: str           # 主要建材
    construction_date_roc: Optional[str] # 建築完成年月
    total_floors: Optional[str]          # 總樓層數
    floor: Optional[str]                 # 移轉層次
    parking_price_twd: Optional[float]   # 車位總價元
    parking_area_sqm: Optional[float]    # 車位移轉總面積平方公尺
    elevator: Optional[str]              # 電梯
    note: Optional[str]                  # 備註
    raw_json: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Location:
    location_id: str
    original_address: str
    district: str
    road_name: Optional[str]
    lane: Optional[int]
    alley: Optional[int]
    door_number_start: Optional[int]
    door_number_end: Optional[int]
    precision: str # AddressPrecision
    point_x_twd97: Optional[float] # 點估計 X
    point_y_twd97: Optional[float] # 點估計 Y
    lon_wgs84: Optional[float]
    lat_wgs84: Optional[float]
    min_x_twd97: Optional[float]
    min_y_twd97: Optional[float]
    max_x_twd97: Optional[float]
    max_y_twd97: Optional[float]
    doorplate_count: int = 0
    is_overridden: bool = False
    evidence_notes: Optional[str] = None


@dataclass
class DistanceResult:
    distance_point_m: Optional[float]
    distance_min_m: Optional[float]
    distance_max_m: Optional[float]
    distance_verified: bool
    distance_method: str # "polygon_min_distance" or "reference_point"
    requires_manual_verification: bool
    threshold_status: str # ConditionStatus (PASS / NEAR / FAIL / UNKNOWN)


@dataclass
class NormalizedTransaction:
    transaction_id: str
    location_id: str
    source_id: str
    transaction_date: Optional[date]
    transaction_date_str: str
    completion_date: Optional[date]
    completion_date_str: Optional[str]
    building_age_years: Optional[float]
    total_price_twd: float
    parking_price_twd: float
    property_price_twd: float # 總價扣除車位價
    parking_price_included_in_total: bool
    land_area_sqm: float
    land_area_ping: float
    building_area_sqm: float
    building_area_ping: float
    land_share_confidence: str # ConfidenceLevel
    land_share_notes: str
    special_transaction_flag: bool
    special_transaction_notes: Optional[str]
    building_type: str
    has_elevator: Optional[bool]
    district: str
    address_raw: str
    raw_record_json: Dict[str, Any] = field(default_factory=dict)
