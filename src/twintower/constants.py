"""
twintower 核心常數定義
"""

# 單一法定土地面積換算常數 (1 坪 = 3.305785 平方公尺，內部全精度運算)
PING_TO_SQM: float = 3.305785
SQM_TO_PING: float = 1.0 / 3.305785

# 條件符合狀態 (不可被默默轉成 0、PASS 或 FAIL)
class ConditionStatus:
    PASS = "PASS"
    NEAR = "NEAR"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    ALL = (PASS, NEAR, FAIL, UNKNOWN)

# 地址解析精度
class AddressPrecision:
    EXACT = "EXACT"                  # 精確門牌點
    NUMBER_RANGE = "NUMBER_RANGE"    # 號碼區間 (如 1~30號)
    ROAD_SEGMENT = "ROAD_SEGMENT"    # 路段/巷弄範圍
    DISTRICT_ONLY = "DISTRICT_ONLY"  # 僅行政區
    UNRESOLVED = "UNRESOLVED"        # 無法解析
    ALL = (EXACT, NUMBER_RANGE, ROAD_SEGMENT, DISTRICT_ONLY, UNRESOLVED)

# 信心度
class ConfidenceLevel:
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"
    ALL = (HIGH, MEDIUM, LOW, UNKNOWN)

# 欄位觀察狀態
class ValueOriginStatus:
    OBSERVED = "OBSERVED"   # 官方原始觀測值
    DERIVED = "DERIVED"     # 由官方公式/幾何確定性衍生
    INFERRED = "INFERRED"   # 空間或規則啟發式推估
    UNKNOWN = "UNKNOWN"     # 未知或缺值
    ALL = (OBSERVED, DERIVED, INFERRED, UNKNOWN)

# 分級代碼
class CandidateGrade:
    A = "A"           # 核心條件皆 PASS、無 UNKNOWN、distance_verified=true
    A_STAR = "A*"     # 核心條件皆 PASS 但帶 UNKNOWN 或未驗證
    B = "B"           # 無 FAIL、至少一項 NEAR、無 UNKNOWN、distance_verified=true
    B_STAR = "B*"     # 無 FAIL、至少一項 NEAR 但帶 UNKNOWN
    C = "C"           # 恰有一項 FAIL
    D = "D"           # 兩項以上 FAIL
    X = "X"           # 位置無法解析 (UNRESOLVED) 或核心條件完全無法判定
    ALL = (A, A_STAR, B, B_STAR, C, D, X)
