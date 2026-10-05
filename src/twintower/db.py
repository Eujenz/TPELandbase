"""
DuckDB 資料庫儲存與管理模組 (支援 Spatial 延伸模組)
"""

import os
import duckdb
from typing import Optional


class DatabaseManager:
    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        if db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.con = duckdb.connect(db_path)
        self._init_spatial()
        self._init_schema()

    def _init_spatial(self):
        try:
            self.con.execute("INSTALL spatial; LOAD spatial;")
        except Exception as e:
            # Spatial might already be installed locally
            try:
                self.con.execute("LOAD spatial;")
            except Exception as e2:
                print(f"Warning: DuckDB spatial could not be loaded: {e2}")

    def _init_schema(self):
        # 1. 來源登錄表
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                source_id VARCHAR PRIMARY KEY,
                name VARCHAR,
                category VARCHAR,
                download_url VARCHAR,
                format VARCHAR,
                crs VARCHAR,
                status VARCHAR,
                file_size_bytes BIGINT,
                sha256 VARCHAR,
                verified_at VARCHAR,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 2. 執行紀錄表 (可重現性)
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                run_id VARCHAR PRIMARY KEY,
                calculation_as_of DATE NOT NULL,
                started_at TIMESTAMP NOT NULL,
                completed_at TIMESTAMP,
                git_commit VARCHAR,
                config_hash VARCHAR,
                total_transactions_in INTEGER,
                total_candidates_retained INTEGER,
                total_discarded INTEGER,
                status VARCHAR
            );
        """)

        # 3. 原始實價登錄紀錄
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS raw_transactions (
                serial_number VARCHAR PRIMARY KEY,
                source_id VARCHAR,
                raw_json JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 4. 正規化交易資料表
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id VARCHAR PRIMARY KEY,
                location_id VARCHAR,
                source_id VARCHAR,
                transaction_date DATE,
                transaction_date_str VARCHAR,
                completion_date DATE,
                completion_date_str VARCHAR,
                building_age_years DOUBLE,
                total_price_twd DOUBLE,
                parking_price_twd DOUBLE,
                property_price_twd DOUBLE,
                parking_price_included_in_total BOOLEAN,
                land_area_sqm DOUBLE,
                land_area_ping DOUBLE,
                building_area_sqm DOUBLE,
                building_area_ping DOUBLE,
                land_share_confidence VARCHAR,
                land_share_notes VARCHAR,
                special_transaction_flag BOOLEAN,
                special_transaction_notes VARCHAR,
                building_type VARCHAR,
                has_elevator BOOLEAN,
                district VARCHAR,
                address_raw VARCHAR
            );
        """)

        # 5. 位置解析資料表
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                location_id VARCHAR PRIMARY KEY,
                original_address VARCHAR UNIQUE,
                district VARCHAR,
                road_name VARCHAR,
                lane INTEGER,
                alley INTEGER,
                door_number_start INTEGER,
                door_number_end INTEGER,
                precision VARCHAR,
                point_x_twd97 DOUBLE,
                point_y_twd97 DOUBLE,
                lon_wgs84 DOUBLE,
                lat_wgs84 DOUBLE,
                min_x_twd97 DOUBLE,
                min_y_twd97 DOUBLE,
                max_x_twd97 DOUBLE,
                max_y_twd97 DOUBLE,
                doorplate_count INTEGER,
                is_overridden BOOLEAN,
                evidence_notes VARCHAR
            );
        """)

        # 6. 候選物件底層表 (Phase 1a 基礎欄位)
        self.con.execute("""
            CREATE TABLE IF NOT EXISTS candidate_properties (
                candidate_id VARCHAR PRIMARY KEY,
                transaction_id VARCHAR UNIQUE,
                location_id VARCHAR,
                run_id VARCHAR,
                calculation_as_of DATE,
                district VARCHAR,
                address VARCHAR,
                address_precision VARCHAR,
                transaction_date DATE,
                total_price_twd DOUBLE,
                property_price_twd DOUBLE,
                parking_price_twd DOUBLE,
                parking_price_included_in_total BOOLEAN,
                land_area_ping DOUBLE,
                land_share_confidence VARCHAR,
                building_area_ping DOUBLE,
                building_age_years DOUBLE,
                distance_point_m DOUBLE,
                distance_min_m DOUBLE,
                distance_max_m DOUBLE,
                distance_verified BOOLEAN,
                distance_method VARCHAR,
                requires_manual_verification BOOLEAN,
                distance_threshold_status VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

    def insert_pipeline_run(self, run_dict: dict):
        self.con.execute("""
            INSERT OR REPLACE INTO pipeline_runs (
                run_id, calculation_as_of, started_at, completed_at, git_commit,
                config_hash, total_transactions_in, total_candidates_retained, total_discarded, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, [
            run_dict.get("run_id"),
            run_dict.get("calculation_as_of"),
            run_dict.get("started_at"),
            run_dict.get("completed_at"),
            run_dict.get("git_commit"),
            run_dict.get("config_hash"),
            run_dict.get("total_transactions_in"),
            run_dict.get("total_candidates_retained"),
            run_dict.get("total_discarded"),
            run_dict.get("status"),
        ])

    def insert_raw_transactions(self, raw_list):
        import json
        rows = [
            (
                r.serial_number,
                "moi_lvr_land",
                json.dumps(r.raw_json, ensure_ascii=False)
            )
            for r in raw_list
        ]
        self.con.executemany("""
            INSERT OR REPLACE INTO raw_transactions (
                serial_number, source_id, raw_json
            ) VALUES (?, ?, ?);
        """, rows)

    def insert_transactions(self, norm_list):
        rows = [
            (
                t.transaction_id,
                t.location_id,
                t.source_id,
                t.transaction_date,
                t.transaction_date_str,
                t.completion_date,
                t.completion_date_str,
                t.building_age_years,
                t.total_price_twd,
                t.parking_price_twd,
                t.property_price_twd,
                t.parking_price_included_in_total,
                t.land_area_sqm,
                t.land_area_ping,
                t.building_area_sqm,
                t.building_area_ping,
                t.land_share_confidence,
                t.land_share_notes,
                t.special_transaction_flag,
                t.special_transaction_notes,
                t.building_type,
                t.has_elevator,
                t.district,
                t.address_raw,
            )
            for t in norm_list
        ]
        self.con.executemany("""
            INSERT OR REPLACE INTO transactions (
                transaction_id, location_id, source_id, transaction_date, transaction_date_str,
                completion_date, completion_date_str, building_age_years, total_price_twd,
                parking_price_twd, property_price_twd, parking_price_included_in_total,
                land_area_sqm, land_area_ping, building_area_sqm, building_area_ping,
                land_share_confidence, land_share_notes, special_transaction_flag,
                special_transaction_notes, building_type, has_elevator, district, address_raw
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, rows)

    def insert_locations(self, location_list):
        seen_addrs = set()
        rows = []
        for loc in location_list:
            if loc.original_address in seen_addrs:
                continue
            seen_addrs.add(loc.original_address)
            rows.append((
                loc.location_id,
                loc.original_address,
                loc.district,
                loc.road_name,
                loc.lane,
                loc.alley,
                loc.door_number_start,
                loc.door_number_end,
                loc.precision,
                loc.point_x_twd97,
                loc.point_y_twd97,
                loc.lon_wgs84,
                loc.lat_wgs84,
                loc.min_x_twd97,
                loc.min_y_twd97,
                loc.max_x_twd97,
                loc.max_y_twd97,
                loc.doorplate_count,
                loc.is_overridden,
                loc.evidence_notes,
            ))
        self.con.executemany("""
            INSERT OR IGNORE INTO locations (
                location_id, original_address, district, road_name, lane, alley,
                door_number_start, door_number_end, precision, point_x_twd97, point_y_twd97,
                lon_wgs84, lat_wgs84, min_x_twd97, min_y_twd97, max_x_twd97, max_y_twd97,
                doorplate_count, is_overridden, evidence_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, rows)


    def insert_candidate_properties(self, candidate_rows):
        rows = [
            (
                c["candidate_id"],
                c["transaction_id"],
                c["location_id"],
                c["run_id"],
                c["calculation_as_of"],
                c["district"],
                c["address"],
                c["address_precision"],
                c["transaction_date"],
                c["total_price_twd"],
                c["property_price_twd"],
                c["parking_price_twd"],
                c["parking_price_included_in_total"],
                c["land_area_ping"],
                c["land_share_confidence"],
                c["building_area_ping"],
                c["building_age_years"],
                c["distance_point_m"],
                c["distance_min_m"],
                c["distance_max_m"],
                c["distance_verified"],
                c["distance_method"],
                c["requires_manual_verification"],
                c["distance_threshold_status"],
            )
            for c in candidate_rows
        ]
        self.con.executemany("""
            INSERT OR IGNORE INTO candidate_properties (
                candidate_id, transaction_id, location_id, run_id, calculation_as_of,
                district, address, address_precision, transaction_date, total_price_twd,
                property_price_twd, parking_price_twd, parking_price_included_in_total,
                land_area_ping, land_share_confidence, building_area_ping, building_age_years,
                distance_point_m, distance_min_m, distance_max_m, distance_verified,
                distance_method, requires_manual_verification, distance_threshold_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, rows)

    def close(self):
        if self.con:
            self.con.close()

