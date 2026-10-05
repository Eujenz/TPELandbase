"""
實價登錄匯入與正規化邏輯測試 (MOI Importer & Normalizer Tests)
"""

from datetime import date
import io
import pandas as pd
import pytest
from twintower.constants import ConfidenceLevel
from twintower.importer import (
    MoiImporter,
    is_residential_target,
    parse_chinese_floor,
)


def test_is_residential_target():
    # 住宅型態通過
    assert is_residential_target("房地(土地+建物)", "住宅大樓(11層含以上有電梯)", "住家用") is True
    assert is_residential_target("房地(土地+建物)+車位", "華廈(10層含以下有電梯)", "住商用") is True
    assert is_residential_target("房地(土地+建物)", "公寓(5樓含以下無電梯)", None) is True
    assert is_residential_target("房地(土地+建物)", "透天厝", "住家用") is True

    # 非住宅標的排除
    assert is_residential_target("土地", "其他", None) is False
    assert is_residential_target("車位", "其他", None) is False
    assert is_residential_target("建物", "住宅大樓", "住家用") is False

    # 明顯非住宅用途排除
    assert is_residential_target("房地(土地+建物)", "工廠", "工業用") is False
    assert is_residential_target("房地(土地+建物)", "其他", "倉庫") is False


def test_parse_chinese_floor():
    assert parse_chinese_floor("一層") == 1
    assert parse_chinese_floor("五層") == 5
    assert parse_chinese_floor("十層") == 10
    assert parse_chinese_floor("十一層") == 11
    assert parse_chinese_floor("二十五層") == 25
    assert parse_chinese_floor("地下二層") == -2
    assert parse_chinese_floor("地下1層") == -1
    assert parse_chinese_floor("全") is None
    assert parse_chinese_floor("") is None
    assert parse_chinese_floor(None) is None


def test_parking_price_separation_and_confidence(tmp_path):
    # 建立合成 MOI CSV 資料
    main_csv_content = """鄉鎮市區,交易標的,土地位置建物門牌,土地移轉總面積平方公尺,交易年月日,建物型態,主要用途,建築完成年月,建物移轉總面積平方公尺,總價元,車位總價元,備註,編號,交易筆棟數,電梯
The villages and towns urban district,transaction sign,land sector position,land shifting total area,transaction year month day,building state,main use,construction complete,building shifting total area,total price,berth total price,the note,serial number,pen number,elevator
中正區,房地(土地+建物)+車位,台北市中正區重慶南路一段1號,33.05785,1130501,住宅大樓(11層含以上有電梯),住家用,1000101,100.0,25000000,3000000,,REC_WITH_PARK,土地1建物1車位1,有
大同區,房地(土地+建物)+車位,台北市大同區延平北路一段2號,23.140495,1130502,華廈(10層含以下有電梯),住家用,0900101,80.0,20000000,0,,REC_NO_PARK_PRICE,土地1建物1車位1,有
萬華區,房地(土地+建物),台北市萬華區昆明街3號,198.3471,1130503,公寓(5樓含以下無電梯),住家用,0700101,70.0,18000000,0,二親等交易,REC_APARTMENT_BIG_LAND,土地1建物1車位0,無
中山區,房地(土地+建物),台北市中山區中山北路一段4號,0.0,1130504,住宅大樓(11層含以上有電梯),住家用,1100101,60.0,15000000,0,,REC_ZERO_LAND,土地0建物1車位0,有
"""
    main_csv_path = tmp_path / "a_lvr_land_a.csv"
    main_csv_path.write_text(main_csv_content, encoding="utf-8-sig")

    importer = MoiImporter()
    norm_list, raw_list, report = importer.load_from_source(
        str(tmp_path),
        calculation_as_of=date(2026, 10, 1),
    )

    assert len(norm_list) == 4
    norm_map = {t.transaction_id: t for t in norm_list}

    # 1. 正常獨立車位價格拆分
    rec1 = norm_map["REC_WITH_PARK"]
    assert rec1.total_price_twd == 25000000.0
    assert rec1.parking_price_twd == 3000000.0
    assert rec1.property_price_twd == 22000000.0  # 2500萬 - 300萬 = 2200萬
    assert rec1.parking_price_included_in_total is False
    assert rec1.land_share_confidence == ConfidenceLevel.HIGH

    # 2. 車位價格未拆分 (內含於總價)
    rec2 = norm_map["REC_NO_PARK_PRICE"]
    assert rec2.total_price_twd == 20000000.0
    assert rec2.property_price_twd == 20000000.0
    assert rec2.parking_price_included_in_total is True
    # 內含車位導致土地持份受影響 -> LOW
    assert rec2.land_share_confidence == ConfidenceLevel.LOW

    # 3. 特殊交易檢測與公寓異常大土地
    rec3 = norm_map["REC_APARTMENT_BIG_LAND"]
    assert rec3.special_transaction_flag is True
    assert "二親等" in rec3.special_transaction_notes
    assert rec3.land_area_ping == pytest.approx(60.0, abs=0.1)  # 198.3471 / 3.305785 = 60 坪 (>50坪)
    assert rec3.land_share_confidence == ConfidenceLevel.LOW

    # 4. 土地為 0 (異常資料)
    rec4 = norm_map["REC_ZERO_LAND"]
    assert rec4.land_area_sqm == 0.0
    assert rec4.land_share_confidence == ConfidenceLevel.UNKNOWN
    # Quality Report 應抓出 ZERO_LAND_AREA
    assert report.total_invalids >= 1
    assert any(iss.issue_type == "ZERO_LAND_AREA" for iss in report.issues)
