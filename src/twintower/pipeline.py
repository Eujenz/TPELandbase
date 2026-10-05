"""
Phase 1a 資料處理管線核心模組 (Data Pipeline Runner)
整合：MOI 實價登錄匯入、門牌解析、距離與門檻判定、DuckDB 儲存、品質檢核報告產出。

不可違反原則：
1. 嚴禁呼叫外部網路 API，純本機資料處理。
2. 時間相依欄位一律以 calculation_as_of 計算，不可使用隱含的 today()。
3. UNKNOWN 欄位原樣保留，不轉換為 0 或 PASS/FAIL。
"""

import argparse
from datetime import date, datetime
import hashlib
import json
import os
import subprocess
from typing import Any, Dict, List, Optional
import pandas as pd

from twintower.constants import ConditionStatus
from twintower.db import DatabaseManager
from twintower.distance import DistanceCalculator
from twintower.importer import MoiImporter
from twintower.locations import LocationResolver
from twintower.models import DataQualityReport


def get_git_commit() -> str:
    try:
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return "UNKNOWN"


def compute_file_hash(path: str) -> str:
    if not os.path.exists(path):
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def run_pipeline(
    as_of: date,
    input_source: str,
    db_path: str = "data/processed/twintower.duckdb",
    output_report_path: str = "data/processed/data_quality_report.json",
    doorplate_csv_path: Optional[str] = "data/raw/probes/taipei_doorplate.csv",
    targets_config_path: str = "config/targets.yaml",
    manual_locations_path: str = "config/manual_locations.yaml",
    target_districts: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    執行 Phase 1a 資料匯入與處理管線
    """
    start_time = datetime.now()
    run_id = f"RUN_{as_of.strftime('%Y%m%d')}_{int(start_time.timestamp())}"
    git_commit = get_git_commit()
    config_hash = compute_file_hash(targets_config_path)

    if target_districts is None:
        target_districts = ["中正區", "大同區", "萬華區", "中山區"]

    print(f"=== Starting TwinTower Pipeline Run [{run_id}] ===")
    print(f"Calculation as-of: {as_of}")
    print(f"Input source: {input_source}")
    print(f"Target districts: {target_districts}")

    # 1. 讀取並正規化實價登錄資料
    importer = MoiImporter(source_id="moi_lvr_land")
    norm_list, raw_list, quality_report = importer.load_from_source(
        source_path=input_source,
        calculation_as_of=as_of,
        target_districts=target_districts,
    )
    print(f"Imported: {quality_report.total_records_read} total records, "
          f"{len(norm_list)} residential candidates matching criteria.")
    print(f"Data Quality: {quality_report.total_invalids} invalids, {quality_report.total_warnings} warnings.")

    # 2. 載入門牌位置解析器
    doorplate_df = None
    if doorplate_csv_path and os.path.exists(doorplate_csv_path):
        print(f"Loading official doorplates from {doorplate_csv_path}...")
        try:
            doorplate_df = pd.read_csv(doorplate_csv_path, encoding="utf-8-sig", low_memory=False)
        except Exception:
            doorplate_df = pd.read_csv(doorplate_csv_path, encoding="cp950", low_memory=False)
        print(f"Loaded {len(doorplate_df)} doorplate points.")
    else:
        print("Notice: No doorplate CSV found or path invalid. Operating in road/district precision mode.")

    resolver = LocationResolver(
        doorplate_df=doorplate_df,
        manual_overrides_path=manual_locations_path,
    )

    # 3. 載入距離計算器
    dist_calc = DistanceCalculator(
        targets_config_path=targets_config_path,
    )

    # 4. 逐筆進行空間解析、距離測算與候選物件封裝
    locations = []
    candidate_rows = []
    threshold_counts = {ConditionStatus.PASS: 0, ConditionStatus.NEAR: 0, ConditionStatus.FAIL: 0, ConditionStatus.UNKNOWN: 0}
    precision_counts = {}
    confidence_counts = {}

    for norm_tx in norm_list:
        loc_id = f"LOC_{hashlib.md5(norm_tx.address_raw.encode('utf-8')).hexdigest()[:12]}"
        norm_tx.location_id = loc_id
        loc = resolver.resolve(
            original_address=norm_tx.address_raw,
            location_id=loc_id,
        )
        locations.append(loc)

        dist_res = dist_calc.calculate(loc)
        threshold_counts[dist_res.threshold_status] = threshold_counts.get(dist_res.threshold_status, 0) + 1
        precision_counts[loc.precision] = precision_counts.get(loc.precision, 0) + 1
        confidence_counts[norm_tx.land_share_confidence] = confidence_counts.get(norm_tx.land_share_confidence, 0) + 1

        cand_dict = {
            "candidate_id": f"CAN_{norm_tx.transaction_id}",
            "transaction_id": norm_tx.transaction_id,
            "location_id": loc.location_id,
            "run_id": run_id,
            "calculation_as_of": as_of,
            "district": norm_tx.district,
            "address": norm_tx.address_raw,
            "address_precision": loc.precision,
            "transaction_date": norm_tx.transaction_date,
            "total_price_twd": norm_tx.total_price_twd,
            "property_price_twd": norm_tx.property_price_twd,
            "parking_price_twd": norm_tx.parking_price_twd,
            "parking_price_included_in_total": norm_tx.parking_price_included_in_total,
            "land_area_ping": norm_tx.land_area_ping,
            "land_share_confidence": norm_tx.land_share_confidence,
            "building_area_ping": norm_tx.building_area_ping,
            "building_age_years": norm_tx.building_age_years,
            "distance_point_m": dist_res.distance_point_m,
            "distance_min_m": dist_res.distance_min_m,
            "distance_max_m": dist_res.distance_max_m,
            "distance_verified": dist_res.distance_verified,
            "distance_method": dist_res.distance_method,
            "requires_manual_verification": dist_res.requires_manual_verification,
            "distance_threshold_status": dist_res.threshold_status,
        }
        candidate_rows.append(cand_dict)

    # 5. 寫入 DuckDB
    print(f"Persisting data into DuckDB at {db_path}...")
    db = DatabaseManager(db_path=db_path)
    db.insert_raw_transactions(raw_list)
    db.insert_transactions(norm_list)
    db.insert_locations(locations)
    db.insert_candidate_properties(candidate_rows)

    end_time = datetime.now()
    run_dict = {
        "run_id": run_id,
        "calculation_as_of": as_of,
        "started_at": start_time,
        "completed_at": end_time,
        "git_commit": git_commit,
        "config_hash": config_hash,
        "total_transactions_in": quality_report.total_records_read,
        "total_candidates_retained": len(candidate_rows),
        "total_discarded": quality_report.total_records_read - len(candidate_rows),
        "status": "COMPLETED",
    }
    db.insert_pipeline_run(run_dict)
    db.close()

    # 6. 編寫品質報告
    report_dict = {
        "run_id": run_id,
        "calculation_as_of": as_of.isoformat(),
        "git_commit": git_commit,
        "config_hash": config_hash,
        "input_source": input_source,
        "doorplate_csv": doorplate_csv_path,
        "execution_duration_sec": round((end_time - start_time).total_seconds(), 2),
        "pipeline_summary": {
            "total_records_read": quality_report.total_records_read,
            "total_residential_candidates": len(candidate_rows),
            "total_invalids": quality_report.total_invalids,
            "total_warnings": quality_report.total_warnings,
        },
        "distance_threshold_distribution": threshold_counts,
        "address_precision_distribution": precision_counts,
        "land_share_confidence_distribution": confidence_counts,
        "quality_issues_summary": quality_report.summary_by_type,
        "sample_issues": [
            {
                "level": i.level,
                "field": i.field_name,
                "type": i.issue_type,
                "record_id": i.record_id,
                "value": str(i.value),
                "message": i.message,
            }
            for i in quality_report.issues[:50]
        ],
    }

    os.makedirs(os.path.dirname(os.path.abspath(output_report_path)), exist_ok=True)
    with open(output_report_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, ensure_ascii=False, indent=2)

    print(f"Data quality report saved to {output_report_path}")
    print(f"=== Pipeline Run [{run_id}] Finished Successfully ===")
    return report_dict


def main():
    parser = argparse.ArgumentParser(description="TwinTower Phase 1a Data Pipeline Runner")
    parser.add_argument("--as-of", type=str, default="2026-10-01", help="Calculation as-of date (YYYY-MM-DD)")
    parser.add_argument("--input-source", type=str, default="data/raw/probes/lvr_landcsv.zip", help="Path to MOI CSV/zip")
    parser.add_argument("--doorplate-csv", type=str, default="data/raw/probes/taipei_doorplate.csv", help="Path to doorplate CSV")
    parser.add_argument("--db-path", type=str, default="data/processed/twintower.duckdb", help="Path to DuckDB database")
    parser.add_argument("--output-report", type=str, default="data/processed/data_quality_report.json", help="Report JSON path")
    parser.add_argument("--targets-config", type=str, default="config/targets.yaml", help="Targets YAML")
    parser.add_argument("--manual-locations", type=str, default="config/manual_locations.yaml", help="Manual locations YAML")
    parser.add_argument("--districts", type=str, default="中正區,大同區,萬華區,中山區", help="Comma-separated target districts")

    args = parser.parse_args()
    as_of = date.fromisoformat(args.as_of)
    districts = [d.strip() for d in args.districts.split(",") if d.strip()]

    run_pipeline(
        as_of=as_of,
        input_source=args.input_source,
        db_path=args.db_path,
        output_report_path=args.output_report,
        doorplate_csv_path=args.doorplate_csv,
        targets_config_path=args.targets_config,
        manual_locations_path=args.manual_locations,
        target_districts=districts,
    )


if __name__ == "__main__":
    main()
