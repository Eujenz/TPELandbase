"""
本機門牌位置解析模組 (Local Geocoding & Geometric Aggregation)
依據不可違反原則：
1. 不捏造坐標；無法解析者標示為 UNRESOLVED，坐標填 None。
2. 支援人工覆蓋檔 (manual_locations.yaml)。
3. address_precision 僅為類別標籤，不代表公尺不確定度。
4. 號碼區間 (NUMBER_RANGE) 由官方實體門牌幾何計算點集重心與外包範圍。
"""

import os
import re
import unicodedata
from typing import Dict, List, Optional, Tuple
import pandas as pd
from pyproj import Transformer
import yaml

from twintower.constants import AddressPrecision
from twintower.models import Location


class LocationResolver:
    def __init__(
        self,
        doorplate_df: Optional[pd.DataFrame] = None,
        manual_overrides_path: Optional[str] = "config/manual_locations.yaml",
    ):
        self.doorplate_df = doorplate_df
        self.manual_overrides = self._load_manual_overrides(manual_overrides_path)
        self.trans_3826_to_4326 = Transformer.from_crs("EPSG:3826", "EPSG:4326", always_xy=True)
        self._indexed_doorplates: Optional[Dict[str, pd.DataFrame]] = None
        if self.doorplate_df is not None:
            self._build_index()

    def _load_manual_overrides(self, path: Optional[str]) -> Dict[str, dict]:
        if not path or not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if not data or "overrides" not in data or not data["overrides"]:
                    return {}
                return {item["original_address"].strip(): item for item in data["overrides"]}
        except Exception as e:
            print(f"Warning: could not load manual locations from {path}: {e}")
            return {}

    def _build_index(self):
        """依街路段建立字典快速群組索引以大幅加速檢索 (O(1) 替代百萬次全表搜尋)"""
        if self.doorplate_df is None or len(self.doorplate_df) == 0:
            self.by_road = {}
            return
        full_to_ascii = str.maketrans("０１２３４５６７８９", "0123456789")
        df = self.doorplate_df.copy()
        clean_no = df["號"].astype(str).str.translate(full_to_ascii)
        df["main_no"] = pd.to_numeric(clean_no.str.extract(r"(\d+)號")[0], errors="coerce")
        df["clean_road"] = df["街路段"].astype(str).str.strip()
        if "巷" in df.columns:
            clean_lane = df["巷"].astype(str).str.translate(full_to_ascii)
            df["clean_lane"] = pd.to_numeric(clean_lane.str.extract(r"(\d+)")[0], errors="coerce")
        else:
            df["clean_lane"] = None
        if "弄" in df.columns:
            clean_alley = df["弄"].astype(str).str.translate(full_to_ascii)
            df["clean_alley"] = pd.to_numeric(clean_alley.str.extract(r"(\d+)")[0], errors="coerce")
        else:
            df["clean_alley"] = None

        self.by_road = {k: v for k, v in df.groupby("clean_road")}


    @staticmethod
    def normalize_address_text(addr: str) -> str:
        """標準化中文地址字串 (全形轉半形、移除樓層附屬字等)"""
        if not addr:
            return ""
        s = unicodedata.normalize("NFKC", str(addr)).strip()
        # 統一常用路名同義詞 (臺 -> 台)
        s = s.replace("臺北市", "台北市")
        return s

    @staticmethod
    def parse_address_components(addr: str) -> dict:
        """
        解析門牌地址組成：行政區、路名、巷、弄、門牌號或區間
        """
        norm = LocationResolver.normalize_address_text(addr)
        
        # 1. 行政區
        dist_m = re.search(r"(?:台北市)?(中正區|大同區|中山區|松山區|大安區|萬華區|信義區|士林區|北投區|內湖區|南港區|文山區)", norm)
        district = dist_m.group(1) if dist_m else ""

        # 2. 街路段 (例如 重慶北路一段, 長安西路, 市民大道一段)
        road_m = re.search(r"((?:[^\d區]+?)(?:路[一二三四五六七八九十\d]*段?|街[一二三四五六七八九十\d]*段?|大道[一二三四五六七八九十\d]*段?))", norm)
        road_name = road_m.group(1) if road_m else ""

        # 3. 巷
        lane_m = re.search(r"(\d+)巷", norm)
        lane = int(lane_m.group(1)) if lane_m else None

        # 4. 弄
        alley_m = re.search(r"(\d+)弄", norm)
        alley = int(alley_m.group(1)) if alley_m else None

        # 5. 門牌號或區間 (如 1~30號, 1至30號, 106號)
        range_m = re.search(r"(\d+)[~～至\-](\d+)號", norm)
        single_m = re.search(r"(\d+)號", norm)
        
        num_start = None
        num_end = None
        if range_m:
            num_start = int(range_m.group(1))
            num_end = int(range_m.group(2))
        elif single_m:
            num_start = int(single_m.group(1))
            num_end = num_start

        return {
            "normalized": norm,
            "district": district,
            "road_name": road_name,
            "lane": lane,
            "alley": alley,
            "num_start": num_start,
            "num_end": num_end,
        }

    def resolve(self, original_address: str, location_id: str) -> Location:
        """
        解析單一地址並產生 Location 物件
        """
        raw_clean = original_address.strip() if original_address else ""
        
        norm_clean = self.normalize_address_text(raw_clean)

        # 1. 人工覆蓋優先比對
        if raw_clean in self.manual_overrides or norm_clean in self.manual_overrides:
            ov = self.manual_overrides.get(raw_clean) or self.manual_overrides.get(norm_clean)
            pt_x = ov.get("point_x_twd97")
            pt_y = ov.get("point_y_twd97")
            lon, lat = (None, None)
            if pt_x is not None and pt_y is not None:
                lon, lat = self.trans_3826_to_4326.transform(pt_x, pt_y)
            return Location(
                location_id=location_id,
                original_address=raw_clean,
                district=ov.get("district", ""),
                road_name=ov.get("road_name"),
                lane=None,
                alley=None,
                door_number_start=None,
                door_number_end=None,
                precision=ov.get("resolved_precision", AddressPrecision.EXACT),
                point_x_twd97=pt_x,
                point_y_twd97=pt_y,
                lon_wgs84=lon,
                lat_wgs84=lat,
                min_x_twd97=pt_x,
                min_y_twd97=pt_y,
                max_x_twd97=pt_x,
                max_y_twd97=pt_y,
                doorplate_count=1,
                is_overridden=True,
                evidence_notes=ov.get("evidence_notes", "Manual override"),
            )

        # 2. 自動結構化解析
        comp = self.parse_address_components(raw_clean)
        district = comp["district"]
        road = comp["road_name"]
        num_start = comp["num_start"]
        num_end = comp["num_end"]

        # 若無路名且無門牌，無法解析
        if not road and num_start is None:
            return Location(
                location_id=location_id,
                original_address=raw_clean,
                district=district,
                road_name=None,
                lane=comp["lane"],
                alley=comp["alley"],
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
                doorplate_count=0,
                is_overridden=False,
                evidence_notes="地址缺少有效路名或門牌號",
            )

        # 3. 若有門牌庫則進行空間比對
        if self.doorplate_df is not None and hasattr(self, "by_road"):
            matched_df = self._query_doorplates(district, road, comp["lane"], comp["alley"], num_start, num_end)
            if len(matched_df) > 0:
                has_exact_match = (
                    num_start is not None
                    and num_start == num_end
                    and "main_no" in matched_df.columns
                    and (matched_df["main_no"] == num_start).any()
                )
                has_range_match = (
                    num_start is not None
                    and num_end is not None
                    and num_start != num_end
                    and "main_no" in matched_df.columns
                    and ((matched_df["main_no"] >= num_start) & (matched_df["main_no"] <= num_end)).any()
                )

                if has_exact_match:
                    precision = AddressPrecision.EXACT
                    exact_df = matched_df[matched_df["main_no"] == num_start]
                    centroid_x = float(exact_df["橫座標"].mean())
                    centroid_y = float(exact_df["縱座標"].mean())
                    min_x, max_x = centroid_x, centroid_x
                    min_y, max_y = centroid_y, centroid_y
                    lon, lat = self.trans_3826_to_4326.transform(centroid_x, centroid_y)
                    count = len(exact_df)
                elif has_range_match:
                    precision = AddressPrecision.NUMBER_RANGE
                    range_df = matched_df[(matched_df["main_no"] >= num_start) & (matched_df["main_no"] <= num_end)]
                    centroid_x = float(range_df["橫座標"].mean())
                    centroid_y = float(range_df["縱座標"].mean())
                    min_x, max_x = float(range_df["橫座標"].min()), float(range_df["橫座標"].max())
                    min_y, max_y = float(range_df["縱座標"].min()), float(range_df["縱座標"].max())
                    lon, lat = self.trans_3826_to_4326.transform(centroid_x, centroid_y)
                    count = len(range_df)
                else:
                    precision = AddressPrecision.ROAD_SEGMENT
                    centroid_x = float(matched_df["橫座標"].mean())
                    centroid_y = float(matched_df["縱座標"].mean())
                    min_x, max_x = float(matched_df["橫座標"].min()), float(matched_df["橫座標"].max())
                    min_y, max_y = float(matched_df["縱座標"].min()), float(matched_df["縱座標"].max())
                    lon, lat = self.trans_3826_to_4326.transform(centroid_x, centroid_y)
                    count = len(matched_df)

                return Location(
                    location_id=location_id,
                    original_address=raw_clean,
                    district=district,
                    road_name=road,
                    lane=comp["lane"],
                    alley=comp["alley"],
                    door_number_start=num_start,
                    door_number_end=num_end,
                    precision=precision,
                    point_x_twd97=centroid_x,
                    point_y_twd97=centroid_y,
                    lon_wgs84=lon,
                    lat_wgs84=lat,
                    min_x_twd97=min_x,
                    min_y_twd97=min_y,
                    max_x_twd97=max_x,
                    max_y_twd97=max_y,
                    doorplate_count=count,
                    is_overridden=False,
                    evidence_notes=f"比對官方門牌庫命中 {count} 筆門牌點",
                )


        # 4. 無門牌庫或查無實體門牌匹配
        # 若為明確號碼但查無門牌，標為 ROAD_SEGMENT (若有路名) 或 UNRESOLVED
        precision = AddressPrecision.ROAD_SEGMENT if road else AddressPrecision.UNRESOLVED
        return Location(
            location_id=location_id,
            original_address=raw_clean,
            district=district,
            road_name=road,
            lane=comp["lane"],
            alley=comp["alley"],
            door_number_start=num_start,
            door_number_end=num_end,
            precision=precision,
            point_x_twd97=None,
            point_y_twd97=None,
            lon_wgs84=None,
            lat_wgs84=None,
            min_x_twd97=None,
            min_y_twd97=None,
            max_x_twd97=None,
            max_y_twd97=None,
            doorplate_count=0,
            is_overridden=False,
            evidence_notes="門牌庫未包含此門牌或無坐標",
        )

    def _query_doorplates(
        self, district: str, road: str, lane: Optional[int], alley: Optional[int], start_no: Optional[int], end_no: Optional[int]
    ) -> pd.DataFrame:
        if not hasattr(self, "by_road") or not self.by_road:
            return pd.DataFrame()

        clean_r = road.replace("台北市", "").replace(district, "").strip() if road else ""
        if not clean_r:
            return pd.DataFrame()

        # 1. 字典精確查找
        subset = self.by_road.get(clean_r)
        if subset is None or len(subset) == 0:
            # 模糊比對字典 key (數量僅數百個路名，遍歷極快)
            candidates = [k for k in self.by_road.keys() if clean_r in k or k in clean_r]
            if candidates:
                sub_dfs = [self.by_road[k] for k in candidates]
                subset = pd.concat(sub_dfs, ignore_index=True)
            else:
                return pd.DataFrame()

        # 2. 巷過濾 (若有)
        if lane is not None and "clean_lane" in subset.columns:
            subset_lane = subset[subset["clean_lane"] == lane]
            if len(subset_lane) > 0:
                subset = subset_lane

        # 3. 弄過濾 (若有)
        if alley is not None and "clean_alley" in subset.columns:
            subset_alley = subset[subset["clean_alley"] == alley]
            if len(subset_alley) > 0:
                subset = subset_alley

        # 4. 門牌號過濾
        if start_no is not None and end_no is not None:
            no_mask = (subset["main_no"] >= start_no) & (subset["main_no"] <= end_no)
            range_sub = subset[no_mask]
            if len(range_sub) > 0:
                return range_sub
        return subset

