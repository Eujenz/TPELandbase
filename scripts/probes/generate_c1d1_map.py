"""
[PROBE SCRIPT - 非正式應用程式碼 / 研究探測用]
功能: 產出雙星 C1/D1 錨點與多邊形、500m/700m 距離圈、周邊門牌之目視比對 HTML 地圖
底圖: NLSC 臺灣通用電子地圖 (WMTS) + OpenStreetMap
"""

import folium
import geopandas as gpd
import pandas as pd
from pyproj import Transformer
import shapely.geometry
import json
import os

# 1. Load C1 & D1 Polygons (FID 802 and 803 from Zoning)
zoning2_dir = "data/raw/probes/zoning2_extracted"
poly_shp = None
for root, dirs, files in os.walk(zoning2_dir):
    for f in files:
        if f.lower().endswith(".shp"):
            p = os.path.join(root, f)
            try:
                g = gpd.read_file(p, rows=5)
                if any("Polygon" in gt for gt in g.geom_type.unique()):
                    poly_shp = p
                    break
            except Exception:
                pass
    if poly_shp:
        break

print("Using zoning shp:", poly_shp)
gdf_zoning = gpd.read_file(poly_shp, encoding="cp950").set_crs("EPSG:3826", allow_override=True)
c1_poly = gdf_zoning.loc[802, "geometry"] # C1 (Area ~12993 m2)
d1_poly = gdf_zoning.loc[803, "geometry"] # D1 (Area ~18633 m2)
c1d1_multi = shapely.geometry.MultiPolygon([c1_poly, d1_poly])

# Transform to WGS84
gdf_c1d1_3826 = gpd.GeoDataFrame({"name": ["C1基地 (約12,993m²)", "D1基地 (約18,633m²)"], "geometry": [c1_poly, d1_poly]}, crs="EPSG:3826")
gdf_c1d1_4326 = gdf_c1d1_3826.to_crs("EPSG:4326")

# 2. Candidate Reference Points
trans_3826_to_4326 = Transformer.from_crs("EPSG:3826", "EPSG:4326", always_xy=True)

# Candidate A: 鄭州路 8 號 (TWD97: 301917.188, 2771280.254)
ptA_x, ptA_y = 301917.188, 2771280.254
ptA_lon, ptA_lat = trans_3826_to_4326.transform(ptA_x, ptA_y)

# Candidate B: C1/D1 Combined Polygon Centroid (TWD97: 301798.23, 2771279.14)
ptB = c1d1_multi.centroid
ptB_lon, ptB_lat = trans_3826_to_4326.transform(ptB.x, ptB.y)

# Candidate C: 北平西路 3 號 (Taipei Station: 302172.309, 2771102.538)
ptC_x, ptC_y = 302172.309, 2771102.538
ptC_lon, ptC_lat = trans_3826_to_4326.transform(ptC_x, ptC_y)

# 3. Compute 500m and 700m Buffers in EPSG:3826
# (a) From Polygon Edge
buf_poly_500 = c1d1_multi.buffer(500)
buf_poly_700 = c1d1_multi.buffer(700)
gdf_buf_poly = gpd.GeoDataFrame(
    {"name": ["多邊形 500m 緩衝圈", "多邊形 700m 緩衝圈"], "geometry": [buf_poly_500, buf_poly_700]},
    crs="EPSG:3826"
).to_crs("EPSG:4326")

# (b) From Point A (鄭州路8號)
ptA_geom = shapely.geometry.Point(ptA_x, ptA_y)
buf_ptA_500 = ptA_geom.buffer(500)
buf_ptA_700 = ptA_geom.buffer(700)
gdf_buf_ptA = gpd.GeoDataFrame(
    {"name": ["鄭州路8號單點 500m 圓", "鄭州路8號單點 700m 圓"], "geometry": [buf_ptA_500, buf_ptA_700]},
    crs="EPSG:3826"
).to_crs("EPSG:4326")

# 4. Load Nearby Doorplates within 800m
dp_csv = "data/raw/probes/taipei_doorplate.csv"
print("Filtering sample nearby doorplates...")
df_dp = pd.read_csv(dp_csv)
# Filter within bounding box of ptA +/- 800m
nearby_dp = df_dp[
    (df_dp["橫座標"] >= ptA_x - 800) & (df_dp["橫座標"] <= ptA_x + 800) &
    (df_dp["縱座標"] >= ptA_y - 800) & (df_dp["縱座標"] <= ptA_y + 800)
].sample(min(300, len(df_dp)), random_state=42)

dp_lons, dp_lats = trans_3826_to_4326.transform(nearby_dp["橫座標"].values, nearby_dp["縱座標"].values)
nearby_dp["lon"] = dp_lons
nearby_dp["lat"] = dp_lats

# 5. Build Folium Map
m = folium.Map(location=[ptA_lat, ptA_lon], zoom_start=15, control_scale=True)

# Add Official NLSC Taiwan e-Map WMTS layer
folium.TileLayer(
    tiles="https://wmts.nlsc.gov.tw/wmts/EMAP/default/GoogleMapsCompatible/{z}/{y}/{x}",
    attr="國土測繪圖資服務雲 (NLSC 臺灣通用電子地圖)",
    name="NLSC 臺灣通用電子地圖",
    overlay=False,
    control=True
).add_to(m)

# OpenStreetMap fallback
folium.TileLayer("OpenStreetMap", name="OpenStreetMap (OSM)").add_to(m)

# Layer: C1/D1 Polygons
folium.GeoJson(
    gdf_c1d1_4326,
    name="官方 C1/D1 基地多邊形 (主要計畫特定專用區)",
    style_function=lambda x: {"fillColor": "#ff7800", "color": "#e65100", "weight": 3, "fillOpacity": 0.45},
    tooltip=folium.GeoJsonTooltip(fields=["name"])
).add_to(m)

# Layer: Polygon 500m / 700m Buffers
folium.GeoJson(
    gdf_buf_poly.iloc[[0]],
    name="[多邊形起算] 500m 緩衝圈 (綠色虛線)",
    style_function=lambda x: {"color": "#2e7d32", "weight": 2.5, "dashArray": "6, 6", "fillOpacity": 0.05}
).add_to(m)

folium.GeoJson(
    gdf_buf_poly.iloc[[1]],
    name="[多邊形起算] 700m 緩衝圈 (綠色細線)",
    style_function=lambda x: {"color": "#4caf50", "weight": 1.5, "dashArray": "4, 4", "fillOpacity": 0.02}
).add_to(m)

# Layer: Point A 500m / 700m Circles
folium.GeoJson(
    gdf_buf_ptA.iloc[[0]],
    name="[單點起算-鄭州路8號] 500m 圓 (藍色實線)",
    style_function=lambda x: {"color": "#1565c0", "weight": 2.5, "fillOpacity": 0.05}
).add_to(m)

folium.GeoJson(
    gdf_buf_ptA.iloc[[1]],
    name="[單點起算-鄭州路8號] 700m 圓 (藍色細線)",
    style_function=lambda x: {"color": "#42a5f5", "weight": 1.5, "fillOpacity": 0.02}
).add_to(m)

# Markers for Reference Points
folium.Marker(
    [ptA_lat, ptA_lon],
    popup="<b>候選錨點 A: 鄭州路 8 號</b><br>D1基地主要工程門牌<br>TWD97: (301917, 2771280)",
    icon=folium.Icon(color="red", icon="star")
).add_to(m)

folium.Marker(
    [ptB_lat, ptB_lon],
    popup="<b>候選錨點 B: C1/D1 多邊形幾何中心</b><br>TWD97: (301798, 2771279)",
    icon=folium.Icon(color="orange", icon="info-sign")
).add_to(m)

folium.Marker(
    [ptC_lat, ptC_lon],
    popup="<b>候選錨點 C: 臺北車站 (北平西路 3 號)</b><br>TWD97: (302172, 2771102)",
    icon=folium.Icon(color="blue", icon="home")
).add_to(m)

# Sample Nearby Doorplate markers
fg_dp = folium.FeatureGroup(name="官方實體門牌取樣點 (300點)", show=False)
for _, r in nearby_dp.iterrows():
    road = str(r["街路段"]) if pd.notna(r["街路段"]) else ""
    no = str(r["號"]) if pd.notna(r["號"]) else ""
    folium.CircleMarker(
        [r["lat"], r["lon"]],
        radius=3,
        color="#616161",
        fill=True,
        fillColor="#9e9e9e",
        fillOpacity=0.6,
        popup=f"{road}{no}"
    ).add_to(fg_dp)
fg_dp.add_to(m)

folium.LayerControl(collapsed=False).add_to(m)

os.makedirs("docs/maps", exist_ok=True)
map_output = "docs/maps/c1d1_anchor_comparison_map.html"
m.save(map_output)
print(f"SUCCESS: Saved comparison map to {map_output}")
