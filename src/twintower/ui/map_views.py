"""
地圖視圖生成模組 (Folium Map Views for TwinTower)
支援：NLSC 官方通用電子地圖 WMTS 切換、C1/D1 雙基地幾何、500m/700m 緩衝圈、
各分級點位與區間外包盒著色、A*/B* 虛線外框呈現。
"""

import json
import os
from typing import List, Optional
import folium
from folium.plugins import Fullscreen, MeasureControl
from pyproj import Transformer

from twintower.constants import AddressPrecision, CandidateGrade
from twintower.ui.view_model import CandidateViewModel

# 分級色彩代碼 (Design Tokens)
GRADE_COLORS = {
    CandidateGrade.A: "#28A745",      # 綠色
    CandidateGrade.A_STAR: "#28A745", # 綠色 (虛線/空心)
    CandidateGrade.B: "#007BFF",      # 藍色
    CandidateGrade.B_STAR: "#007BFF", # 藍色 (虛線/空心)
    CandidateGrade.C: "#FFC107",      # 黃色
    CandidateGrade.D: "#DC3545",      # 紅色
    CandidateGrade.X: "#6C757D",      # 灰色
    "待實作": "#6C757D",             # 灰色
}


def build_overview_map(
    candidates: List[CandidateViewModel],
    is_demo_mode: bool = False,
    is_dark_theme: bool = False,
    selected_candidate_id: Optional[str] = None,
    c1d1_geojson_path: str = "config/geometry/c1d1_bases_4326.geojson",
) -> folium.Map:
    """
    建構總覽地圖
    """
    # 預設地圖中心：雙星 C1/D1 基地 (25.0488, 121.5134)
    center_lat, center_lon = 25.0488, 121.5134

    # 建立地圖實體
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=15,
        control_scale=True,
        tiles=None,  # 自行指定圖層
    )

    # 1. 官方底圖：國土測繪圖資服務雲 (NLSC) 臺灣通用電子地圖 WMTS
    nlsc_tile = folium.TileLayer(
        tiles="https://wmts.nlsc.gov.tw/wmts/EMAP/default/GoogleMapsCompatible/{z}/{y}/{x}",
        attr="內政部國土測繪中心 (NLSC) 臺灣通用電子地圖",
        name="國土測繪中心臺灣通用電子地圖 (官方首選)",
        overlay=False,
        control=True,
    )
    nlsc_tile.add_to(m)

    # 備用底圖：OpenStreetMap / CartoDB Dark (若為深色模式)
    if is_dark_theme:
        dark_tile = folium.TileLayer(
            tiles="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
            attr="CartoDB DarkMatter & OpenStreetMap",
            name="深色底圖 (CartoDB Dark)",
            overlay=False,
            control=True,
        )
        dark_tile.add_to(m)
    else:
        osm_tile = folium.TileLayer(
            tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            attr="OpenStreetMap contributors",
            name="OpenStreetMap (開放街道圖)",
            overlay=False,
            control=True,
        )
        osm_tile.add_to(m)

    # 2. C1/D1 基地多邊形圖層 (Layer 1)
    poly_group = folium.FeatureGroup(name="臺北雙星 C1/D1 基地 (官方幾何)", show=True)
    if os.path.exists(c1d1_geojson_path):
        try:
            with open(c1d1_geojson_path, "r", encoding="utf-8") as f:
                c1d1_data = json.load(f)
            folium.GeoJson(
                c1d1_data,
                name="C1/D1 雙基地多邊形",
                style_function=lambda x: {
                    "fillColor": "#1F4E79",
                    "color": "#E74C3C",
                    "weight": 2.5,
                    "fillOpacity": 0.45,
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=["name", "area_sqm"],
                    aliases=["基地:", "面積 (m²):"],
                    localize=True,
                ),
            ).add_to(poly_group)
        except Exception as e:
            print(f"Warning: could not load c1d1 geojson: {e}")
    poly_group.add_to(m)

    # 3. 500m / 700m 距離圈 (Layer 2)
    # 由 C1/D1 基地幾何中心畫出示意圈 (精確公尺在 EPSG:3826 運算)
    radius_group = folium.FeatureGroup(name="雙星生活圈半徑 (500m / 700m)", show=True)
    folium.Circle(
        location=[25.048779, 121.513358],
        radius=500,
        color="#28A745",
        weight=2,
        fill=True,
        fill_opacity=0.08,
        dash_array="6, 6",
        tooltip="方案 B 核心半徑 (500m 圈)",
    ).add_to(radius_group)

    folium.Circle(
        location=[25.048779, 121.513358],
        radius=700,
        color="#FD7E14",
        weight=2,
        fill=True,
        fill_opacity=0.04,
        dash_array="6, 6",
        tooltip="方案 B 次級半徑 (700m 圈)",
    ).add_to(radius_group)
    radius_group.add_to(m)

    # 4. 候選物件標記圖層 (Layer 3)
    cand_group = folium.FeatureGroup(name="成交住宅候選物件", show=True)
    envelope_group = folium.FeatureGroup(name="非精確門牌外包範圍 (Bounding Box)", show=True)

    transformer = Transformer.from_crs("EPSG:3826", "EPSG:4326", always_xy=True)

    for c in candidates:
        if c.lat_wgs84 is None or c.lon_wgs84 is None:
            continue

        color = GRADE_COLORS.get(c.candidate_grade, "#6C757D")
        is_asterisk = ("*" in c.candidate_grade) or (not c.distance_verified and c.address_precision != AddressPrecision.EXACT)
        is_selected = (selected_candidate_id == c.candidate_id)

        # Popup 內容
        popup_html = f"""
        <div style="font-family: sans-serif; font-size: 13px; line-height: 1.5; min-width: 220px;">
            <div style="font-weight: bold; border-bottom: 2px solid {color}; padding-bottom: 4px; margin-bottom: 6px;">
                [{c.candidate_grade}] {c.address_display}
            </div>
            <div><b>編號:</b> {c.candidate_id}</div>
            <div><b>房地淨價:</b> {c.property_price_w} 萬元 {'(車位內含)' if c.parking_included_flag else ''}</div>
            <div><b>土地坪數:</b> {c.land_area_ping} 坪 (信心度: {c.land_share_confidence})</div>
            <div><b>雙星距離:</b> {f'{c.distance_c1d1_m:.1f} m' if c.distance_c1d1_m else '未知'} ({c.distance_threshold_status})</div>
            <div><b>精度等級:</b> {c.address_precision} {'(人工核實)' if c.is_location_overridden else ''}</div>
            <div><b>面臨路寬:</b> {c.road_width_m}</div>
            <div style="margin-top: 6px; font-size: 11px; color: #888;">
                註：距離由 C1/D1 多邊形外緣起算
            </div>
        </div>
        """

        # 標記樣式：星號（A*/B*）採用空心/虛線外框；選取者加粗外框
        radius = 9 if is_selected else 7
        weight = 3.5 if is_selected else 2.0
        fill_opacity = 0.25 if is_asterisk else 0.85
        dash_array = "4, 4" if is_asterisk else None

        folium.CircleMarker(
            location=[c.lat_wgs84, c.lon_wgs84],
            radius=radius,
            color=color,
            weight=weight,
            fill=True,
            fill_color=color,
            fill_opacity=fill_opacity,
            dash_array=dash_array,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"[{c.candidate_grade}] {c.address_display} | {c.property_price_w}萬 | {c.land_area_ping}坪",
        ).add_to(cand_group)

        # 若有外包範圍矩形 (NUMBER_RANGE 或 ROAD_SEGMENT)
        if (
            c.address_precision in (AddressPrecision.NUMBER_RANGE, AddressPrecision.ROAD_SEGMENT)
            and c.min_x_twd97 is not None
            and c.max_x_twd97 is not None
            and (c.min_x_twd97 != c.max_x_twd97 or c.min_y_twd97 != c.max_y_twd97)
        ):
            lon_min, lat_min = transformer.transform(c.min_x_twd97, c.min_y_twd97)
            lon_max, lat_max = transformer.transform(c.max_x_twd97, c.max_y_twd97)
            bounds = [[lat_min, lon_min], [lat_max, lon_max]]
            folium.Rectangle(
                bounds=bounds,
                color=color,
                weight=1.5,
                fill=True,
                fill_color=color,
                fill_opacity=0.15,
                dash_array="5, 5",
                tooltip=f"號碼區間外包範圍：{c.address_display}",
            ).add_to(envelope_group)

    cand_group.add_to(m)
    envelope_group.add_to(m)

    # 5. 地圖工具外掛
    folium.LayerControl(position="topright", collapsed=False).add_to(m)
    Fullscreen(position="topleft").add_to(m)
    MeasureControl(position="bottomleft", primary_length_unit="meters").add_to(m)

    return m
