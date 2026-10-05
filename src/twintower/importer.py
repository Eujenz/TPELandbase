"""
內政部實價登錄匯入、清理、正規化與資料品質檢核模組 (MOI Importer & Normalizer)

不可違反原則：
1. 嚴格區分 OBSERVED、DERIVED、INFERRED 與 UNKNOWN。
2. 土地換算一律採用法定常數 PING_TO_SQM = 3.305785 (內部全精度運算)。
3. 屋齡一律依 calculation_as_of 確定性計算，嚴禁隱含 datetime.now()。
4. 車位拆分：若有車位但無獨立車位價，保留總價並標記 parking_price_included_in_total=True。
5. 檢核報告 (DataQualityReport)：記錄異常值 (負價、0面積、完工晚於交易、重複編號等)。
"""

import io
import os
import re
import unicodedata
import zipfile
from datetime import date
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas as pd

from twintower.constants import (
    ConfidenceLevel,
    PING_TO_SQM,
    SQM_TO_PING,
)
from twintower.dates import (
    calculate_building_age,
    parse_roc_date,
    parse_roc_year_month,
)
from twintower.models import (
    DataQualityReport,
    NormalizedTransaction,
    QualityIssue,
    RawTransaction,
)


CHINESE_DIGITS = {
    "零": 0, "一": 1, "二": 2, "兩": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}


def parse_chinese_floor(floor_str: Optional[str]) -> Optional[int]:
    """
    解析中文樓層字串 (如 '五層' -> 5, '十二層' -> 12, '地下二層' -> -2, '全' -> None)
    """
    if not floor_str:
        return None
    s = unicodedata.normalize("NFKC", str(floor_str)).strip()
    if not s or s in ("nan", "none", "全"):
        return None

    is_basement = "地下" in s
    s = s.replace("地下", "").replace("層", "").replace("樓", "").strip()

    # 包含阿拉伯數字
    num_match = re.search(r"\d+", s)
    if num_match:
        val = int(num_match.group(0))
        return -val if is_basement else val

    # 中文數字解析 (一到九十九)
    val = 0
    if len(s) == 1 and s in CHINESE_DIGITS:
        val = CHINESE_DIGITS[s]
    elif len(s) == 2:
        if s[0] == "十":
            val = 10 + CHINESE_DIGITS.get(s[1], 0)
        elif s[1] == "十":
            val = CHINESE_DIGITS.get(s[0], 0) * 10
        else:
            val = CHINESE_DIGITS.get(s[0], 0) * 10 + CHINESE_DIGITS.get(s[1], 0)
    elif len(s) == 3 and s[1] == "十":
        val = CHINESE_DIGITS.get(s[0], 0) * 10 + CHINESE_DIGITS.get(s[2], 0)

    if val > 0:
        return -val if is_basement else val
    return None


def is_residential_target(
    target_type: str,
    building_type: str,
    main_use: Optional[str] = None
) -> bool:
    """
    判定是否為自住住宅候選：
    - 交易標的需包含房地 (土地+建物)
    - 建物型態需為住宅類型 (公寓、華廈、住宅大樓、透天厝)
    - 排除工廠、農舍、倉庫等明顯非住宅用途
    """
    tt = str(target_type).strip() if target_type else ""
    bt = str(building_type).strip() if building_type else ""
    mu = str(main_use).strip() if main_use else ""

    # 1. 標的必須為房地
    if "房地" not in tt:
        return False

    # 2. 排除純非住宅型態
    for excl in ("工廠", "廠辦", "農舍", "倉庫", "防空避難室"):
        if excl in bt or excl in mu:
            return False

    # 3. 建物型態符合住宅
    residential_types = ("公寓", "華廈", "住宅大樓", "透天厝")
    if any(rt in bt for rt in residential_types):
        return True

    # 4. 主要用途若標記住宅亦可納入
    if any(ru in mu for ru in ("住家", "住商", "國民住宅", "農舍除外")):
        return True

    return False


SPECIAL_TRANSACTION_REGEX = re.compile(
    r"(親友|親屬|二親等|關係人|急買急賣|毛胚|瑕疵|建商與地主合建|合建分售|凶宅|塔位|祭祀公業|徵收|協議價購|政府機關)"
)


class MoiImporter:
    """內政部實價登錄批次匯入器"""

    def __init__(self, source_id: str = "moi_lvr_land"):
        self.source_id = source_id

    def load_from_source(
        self,
        source_path: str,
        calculation_as_of: date,
        target_districts: Optional[List[str]] = None,
    ) -> Tuple[List[NormalizedTransaction], List[RawTransaction], DataQualityReport]:
        """
        從 zip 檔或目錄讀取 MOI 實價登錄檔並進行正規化
        """
        report = DataQualityReport()
        norm_list: List[NormalizedTransaction] = []
        raw_list: List[RawTransaction] = []

        if os.path.isdir(source_path):
            main_df, build_df, land_df, park_df = self._read_from_dir(source_path)
        elif zipfile.is_zipfile(source_path):
            main_df, build_df, land_df, park_df = self._read_from_zip(source_path)
        else:
            raise ValueError(f"Unsupported source format: {source_path}")

        report.total_records_read = len(main_df)

        # 預先計算車位與筆棟分佈
        park_summary = self._summarize_parking(park_df)
        land_counts = self._count_by_serial(land_df)
        build_counts = self._count_by_serial(build_df)

        seen_serials: Set[str] = set()

        for idx, row in main_df.iterrows():
            serial = str(row.get("編號", f"REC_{idx}")).strip()
            district = str(row.get("鄉鎮市區", "")).strip()
            target_type = str(row.get("交易標的", "")).strip()
            building_type = str(row.get("建物型態", "")).strip()
            main_use = str(row.get("主要用途", "")).strip() if pd.notna(row.get("主要用途")) else ""
            address_raw = str(row.get("土地位置建物門牌", "")).strip()

            # 重複序號檢核
            if serial in seen_serials:
                report.add_issue(
                    QualityIssue(
                        level="INVALID",
                        field_name="serial_number",
                        issue_type="DUPLICATE_SERIAL",
                        record_id=serial,
                        value=serial,
                        message="重複的實價登錄交易編號",
                    )
                )
            seen_serials.add(serial)

            # 行政區過濾 (若有指定)
            if target_districts and district not in target_districts:
                continue

            # 住宅候選過濾
            if not is_residential_target(target_type, building_type, main_use):
                continue

            report.total_residential_candidates += 1

            # 數值讀取與清洗
            try:
                total_price_twd = float(row.get("總價元", 0.0))
            except (ValueError, TypeError):
                total_price_twd = 0.0

            try:
                land_area_sqm = float(row.get("土地移轉總面積平方公尺", 0.0))
            except (ValueError, TypeError):
                land_area_sqm = 0.0

            try:
                building_area_sqm = float(row.get("建物移轉總面積平方公尺", 0.0))
            except (ValueError, TypeError):
                building_area_sqm = 0.0

            # 異常檢核 (INVALID)
            if total_price_twd <= 0:
                report.add_issue(
                    QualityIssue(
                        level="INVALID",
                        field_name="total_price_twd",
                        issue_type="NEGATIVE_OR_ZERO_PRICE",
                        record_id=serial,
                        value=total_price_twd,
                        message="總價小於等於 0",
                    )
                )

            if land_area_sqm <= 0:
                report.add_issue(
                    QualityIssue(
                        level="INVALID",
                        field_name="land_area_sqm",
                        issue_type="ZERO_LAND_AREA",
                        record_id=serial,
                        value=land_area_sqm,
                        message="土地移轉總面積為 0 或小於 0",
                    )
                )

            # 坪數法定精確換算
            land_area_ping = land_area_sqm * SQM_TO_PING
            building_area_ping = building_area_sqm * SQM_TO_PING

            # 日期解析
            raw_tx_date = str(row.get("交易年月日", "")).strip()
            raw_comp_date = str(row.get("建築完成年月", "")).strip() if pd.notna(row.get("建築完成年月")) else None

            tx_date, tx_date_clean = parse_roc_date(raw_tx_date)
            comp_date, comp_date_clean = parse_roc_year_month(raw_comp_date)

            if tx_date is None:
                report.add_issue(
                    QualityIssue(
                        level="INVALID",
                        field_name="transaction_date",
                        issue_type="INVALID_TRANSACTION_DATE",
                        record_id=serial,
                        value=raw_tx_date,
                        message="交易日期無法解析",
                    )
                )

            if comp_date is not None and tx_date is not None and comp_date > tx_date:
                report.add_issue(
                    QualityIssue(
                        level="WARNING",
                        field_name="completion_date",
                        issue_type="COMPLETION_AFTER_TRANSACTION",
                        record_id=serial,
                        value=f"comp={raw_comp_date}, tx={raw_tx_date}",
                        message="建築完成年月晚於交易年月 (可能是預售或登錄錯誤)",
                    )
                )

            # 確定性計算屋齡 (依 calculation_as_of)
            building_age_years = calculate_building_age(comp_date, as_of=calculation_as_of)
            if building_age_years is not None and building_age_years > 100:
                report.add_issue(
                    QualityIssue(
                        level="WARNING",
                        field_name="building_age_years",
                        issue_type="UNUSUAL_BUILDING_AGE",
                        record_id=serial,
                        value=building_age_years,
                        message="屋齡超過 100 年",
                    )
                )

            # 車位金額拆分
            try:
                main_park_price = float(row.get("車位總價元", 0.0))
            except (ValueError, TypeError):
                main_park_price = 0.0

            sub_park_price = park_summary.get(serial, {}).get("total_price", 0.0)
            parking_price_twd = max(main_park_price, sub_park_price)

            if parking_price_twd > total_price_twd and total_price_twd > 0:
                report.add_issue(
                    QualityIssue(
                        level="INVALID",
                        field_name="parking_price_twd",
                        issue_type="PARKING_PRICE_EXCEEDS_TOTAL",
                        record_id=serial,
                        value=parking_price_twd,
                        message="車位總價高於總價元",
                    )
                )

            has_parking_in_target = "車位" in target_type or serial in park_summary

            if parking_price_twd > 0:
                property_price_twd = max(0.0, total_price_twd - parking_price_twd)
                parking_price_included_in_total = False
            elif has_parking_in_target:
                # 含車位但無法取得獨立車位價
                property_price_twd = total_price_twd
                parking_price_included_in_total = True
            else:
                property_price_twd = total_price_twd
                parking_price_included_in_total = False

            # 樓層檢核
            floor_str = str(row.get("移轉層次", "")) if pd.notna(row.get("移轉層次")) else ""
            tot_floor_str = str(row.get("總樓層數", "")) if pd.notna(row.get("總樓層數")) else ""
            parsed_fl = parse_chinese_floor(floor_str)
            parsed_tot = parse_chinese_floor(tot_floor_str)
            if parsed_fl and parsed_tot and parsed_fl > 0 and parsed_tot > 0 and parsed_fl > parsed_tot:
                report.add_issue(
                    QualityIssue(
                        level="WARNING",
                        field_name="floor",
                        issue_type="FLOOR_EXCEEDS_TOTAL",
                        record_id=serial,
                        value=f"{floor_str}/{tot_floor_str}",
                        message="移轉樓層大於總樓層數",
                    )
                )

            # 電梯狀態
            elevator_val = str(row.get("電梯", "")).strip() if pd.notna(row.get("電梯")) else ""
            if elevator_val == "有":
                has_elevator = True
            elif elevator_val == "無":
                has_elevator = False
            else:
                has_elevator = None

            # 特殊交易標記
            note_str = str(row.get("備註", "")).strip() if pd.notna(row.get("備註")) else ""
            spec_match = SPECIAL_TRANSACTION_REGEX.search(note_str)
            if spec_match:
                special_flag = True
                special_notes = note_str
            else:
                special_flag = False
                special_notes = None

            # 土地持份信心度 (land_share_confidence)
            l_cnt = land_counts.get(serial, 0)
            b_cnt = build_counts.get(serial, 0)
            if l_cnt == 0 and b_cnt == 0:
                # 嘗試從 交易筆棟數 (如 '土地1建物1車位0') 解析
                pen_str = str(row.get("交易筆棟數", ""))
                m_pen = re.search(r"土地(\d+)建物(\d+)", pen_str)
                if m_pen:
                    l_cnt = int(m_pen.group(1))
                    b_cnt = int(m_pen.group(2))

            if land_area_sqm <= 0:
                land_confidence = ConfidenceLevel.UNKNOWN
                land_notes = "無土地面積或面積為0"
            elif parking_price_included_in_total:
                land_confidence = ConfidenceLevel.LOW
                land_notes = "車位價格內含未拆分，土地移轉面積可能包含車位應有持份"
            elif land_area_ping > 50 and "公寓" in building_type:
                land_confidence = ConfidenceLevel.LOW
                land_notes = f"公寓登記土地面積達 {round(land_area_ping, 1)} 坪 (>50坪)，疑似整棟或非單純分戶持份"
            elif l_cnt == 1 and b_cnt == 1:
                land_confidence = ConfidenceLevel.HIGH
                land_notes = "單一地號與單一建物，持份明確"
            elif l_cnt > 1 or b_cnt > 1:
                land_confidence = ConfidenceLevel.MEDIUM
                land_notes = f"包含多筆土地({l_cnt})或建物({b_cnt})移轉"
            else:
                land_confidence = ConfidenceLevel.MEDIUM
                land_notes = "一般房地交易"

            # 建立 NormalizedTransaction
            norm_tx = NormalizedTransaction(
                transaction_id=serial,
                location_id=f"LOC_{serial}",
                source_id=self.source_id,
                transaction_date=tx_date,
                transaction_date_str=raw_tx_date,
                completion_date=comp_date,
                completion_date_str=raw_comp_date,
                building_age_years=building_age_years,
                total_price_twd=total_price_twd,
                parking_price_twd=parking_price_twd,
                property_price_twd=property_price_twd,
                parking_price_included_in_total=parking_price_included_in_total,
                land_area_sqm=land_area_sqm,
                land_area_ping=round(land_area_ping, 2),
                building_area_sqm=building_area_sqm,
                building_area_ping=round(building_area_ping, 2),
                land_share_confidence=land_confidence,
                land_share_notes=land_notes,
                special_transaction_flag=special_flag,
                special_transaction_notes=special_notes,
                building_type=building_type,
                has_elevator=has_elevator,
                district=district,
                address_raw=address_raw,
                raw_record_json=row.dropna().to_dict(),
            )
            norm_list.append(norm_tx)

            # 建立 RawTransaction
            raw_tx = RawTransaction(
                serial_number=serial,
                district=district,
                target_type=target_type,
                address_raw=address_raw,
                total_price_twd=total_price_twd,
                land_area_sqm=land_area_sqm,
                building_area_sqm=building_area_sqm,
                unit_price_sqm=float(row.get("單價元平方公尺")) if pd.notna(row.get("單價元平方公尺")) else None,
                transaction_date_roc=raw_tx_date,
                building_type=building_type,
                main_use=main_use,
                materials=str(row.get("主要建材", "")),
                construction_date_roc=raw_comp_date,
                total_floors=tot_floor_str,
                floor=floor_str,
                parking_price_twd=parking_price_twd,
                parking_area_sqm=float(row.get("車位移轉總面積平方公尺", 0.0)) if pd.notna(row.get("車位移轉總面積平方公尺")) else 0.0,
                elevator=elevator_val,
                note=note_str,
                raw_json=row.dropna().to_dict(),
            )
            raw_list.append(raw_tx)

        return norm_list, raw_list, report

    def _read_from_dir(self, dir_path: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        main_path = os.path.join(dir_path, "a_lvr_land_a.csv")
        build_path = os.path.join(dir_path, "a_lvr_land_a_build.csv")
        land_path = os.path.join(dir_path, "a_lvr_land_a_land.csv")
        park_path = os.path.join(dir_path, "a_lvr_land_a_park.csv")

        main_df = self._read_single_csv(main_path)
        build_df = self._read_single_csv(build_path) if os.path.exists(build_path) else pd.DataFrame()
        land_df = self._read_single_csv(land_path) if os.path.exists(land_path) else pd.DataFrame()
        park_df = self._read_single_csv(park_path) if os.path.exists(park_path) else pd.DataFrame()

        return main_df, build_df, land_df, park_df

    def _read_from_zip(self, zip_path: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        with zipfile.ZipFile(zip_path, "r") as zf:
            main_df = self._read_csv_from_zip(zf, "a_lvr_land_a.csv")
            build_df = self._read_csv_from_zip(zf, "a_lvr_land_a_build.csv")
            land_df = self._read_csv_from_zip(zf, "a_lvr_land_a_land.csv")
            park_df = self._read_csv_from_zip(zf, "a_lvr_land_a_park.csv")
        return main_df, build_df, land_df, park_df

    def _read_single_csv(self, file_path: str) -> pd.DataFrame:
        if not os.path.exists(file_path):
            return pd.DataFrame()
        try:
            return pd.read_csv(file_path, encoding="utf-8-sig", skiprows=[1], low_memory=False)
        except Exception:
            return pd.read_csv(file_path, encoding="cp950", skiprows=[1], low_memory=False)

    def _read_csv_from_zip(self, zf: zipfile.ZipFile, name: str) -> pd.DataFrame:
        matches = [n for n in zf.namelist() if n.lower().endswith(name.lower())]
        if not matches:
            return pd.DataFrame()
        with zf.open(matches[0]) as f:
            content = f.read()
            try:
                return pd.read_csv(io.BytesIO(content), encoding="utf-8-sig", skiprows=[1], low_memory=False)
            except Exception:
                return pd.read_csv(io.BytesIO(content), encoding="cp950", skiprows=[1], low_memory=False)

    def _summarize_parking(self, park_df: pd.DataFrame) -> Dict[str, dict]:
        if park_df is None or len(park_df) == 0 or "編號" not in park_df.columns:
            return {}
        summary = {}
        for serial, group in park_df.groupby("編號"):
            total_p = 0.0
            if "車位總價元" in group.columns:
                total_p = pd.to_numeric(group["車位總價元"], errors="coerce").fillna(0.0).sum()
            elif "車位價格" in group.columns:
                total_p = pd.to_numeric(group["車位價格"], errors="coerce").fillna(0.0).sum()
            summary[str(serial).strip()] = {
                "count": len(group),
                "total_price": float(total_p),
            }
        return summary

    def _count_by_serial(self, df: pd.DataFrame) -> Dict[str, int]:
        if df is None or len(df) == 0 or "編號" not in df.columns:
            return {}
        return df["編號"].astype(str).str.strip().value_counts().to_dict()
