"""
端對端資料管線測試 (Pipeline End-to-End Test with Synthetic Data)
規範：完全本機執行，嚴禁 live network API 呼叫。
"""

from datetime import date
import json
import os
import duckdb
import pytest
from twintower.constants import ConditionStatus
from twintower.pipeline import run_pipeline


def test_pipeline_end_to_end_synthetic(tmp_path):
    # 1. 建立測試 MOI CSV
    moi_dir = tmp_path / "moi"
    moi_dir.mkdir()
    main_csv_content = """鄉鎮市區,交易標的,土地位置建物門牌,土地移轉總面積平方公尺,交易年月日,建物型態,主要用途,建築完成年月,建物移轉總面積平方公尺,總價元,車位總價元,備註,編號,交易筆棟數,電梯
English row,,,,,,,,,,,,,,
中正區,房地(土地+建物),台北市中正區鄭州路8號,33.05785,1130601,住宅大樓(11層含以上有電梯),住家用,1050101,100.0,20000000,0,,SYN_REC_1,土地1建物1車位0,有
大同區,房地(土地+建物),台北市大同區延平北路一段10號,23.140495,1130602,公寓(5樓含以下無電梯),住家用,0750101,70.0,15000000,0,,SYN_REC_2,土地1建物1車位0,無
萬華區,房地(土地+建物),台北市萬華區昆明街50號,16.528925,1130603,華廈(10層含以下有電梯),住家用,0850101,60.0,12000000,0,二親等買賣,SYN_REC_3,土地1建物1車位0,有
"""
    (moi_dir / "a_lvr_land_a.csv").write_text(main_csv_content, encoding="utf-8-sig")

    # 2. 建立測試合成門牌 CSV
    doorplate_csv = tmp_path / "synthetic_doorplate.csv"
    doorplate_content = """省市縣市代碼,鄉鎮市區代碼,村里,鄰,街路段,地區,巷,弄,號,橫座標,縱座標
63000,63000060,建泰里,001,延平北路一段,,,,１０號,301850.0,2771500.0
63000,63000070,西門里,001,昆明街,,,,５０號,301200.0,2770500.0
"""
    doorplate_csv.write_text(doorplate_content, encoding="utf-8-sig")

    # 3. 執行管線
    db_path = str(tmp_path / "test_twintower.duckdb")
    report_path = str(tmp_path / "test_report.json")

    as_of = date(2026, 10, 1)
    report = run_pipeline(
        as_of=as_of,
        input_source=str(moi_dir),
        db_path=db_path,
        output_report_path=report_path,
        doorplate_csv_path=str(doorplate_csv),
        targets_config_path="config/targets.yaml",
        manual_locations_path="config/manual_locations.yaml",
        target_districts=["中正區", "大同區", "萬華區"],
    )

    # 4. 驗證報告結構
    assert os.path.exists(report_path)
    with open(report_path, "r", encoding="utf-8") as f:
        rep_json = json.load(f)

    assert rep_json["calculation_as_of"] == "2026-10-01"
    assert rep_json["pipeline_summary"]["total_residential_candidates"] == 3

    # 5. 驗證 DuckDB 資料寫入
    con = duckdb.connect(db_path)

    # candidate_properties 應有 3 筆
    cands = con.execute("SELECT candidate_id, transaction_id, district, total_price_twd, distance_threshold_status FROM candidate_properties").fetchall()
    assert len(cands) == 3

    # 驗證 SYN_REC_1 (鄭州路8號) 命中手動覆蓋 D1 基地
    rec1 = con.execute("SELECT address_precision, distance_verified, distance_threshold_status FROM candidate_properties WHERE transaction_id='SYN_REC_1'").fetchone()
    assert rec1[0] == "EXACT"
    assert rec1[1] is True
    assert rec1[2] == ConditionStatus.PASS  # 鄭州路8號在雙星基地門口，距離 < 500m

    # 驗證 pipeline_runs 紀錄
    runs = con.execute("SELECT run_id, status, total_candidates_retained FROM pipeline_runs").fetchall()
    assert len(runs) == 1
    assert runs[0][1] == "COMPLETED"
    assert runs[0][2] == 3

    con.close()
