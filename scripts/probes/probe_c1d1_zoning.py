"""
[PROBE SCRIPT - 非正式應用程式碼 / 研究探測用]
功能: 檢驗使用分區圖層中涵蓋 C1/D1 (公園段一小段) 與車站特定專用區之多邊形幾何
"""

import geopandas as gpd
import shapely.geometry
import os

zoning_shp = "data/raw/probes/zoning2_extracted/主要計畫-面.shp"
if not os.path.exists(zoning_shp):
    # Try finding any polygon shp
    for root, dirs, files in os.walk("data/raw/probes/zoning2_extracted"):
        for f in files:
            if f.endswith(".shp"):
                zoning_shp = os.path.join(root, f)
                break

print("Using zoning shp:", zoning_shp)
gdf = gpd.read_file(zoning_shp, encoding="cp950")
# Assign EPSG:3826 as verified by metadata and coordinate bounds
gdf = gdf.set_crs("EPSG:3826", allow_override=True)

# Target bbox around C1/D1: (301700, 2771000) to (302400, 2771600)
bbox = shapely.geometry.box(301700, 2771000, 302400, 2771600)
c1d1_zones = gdf[gdf.intersects(bbox)].copy()

print(f"Total zoning polygons intersecting C1/D1 vicinity: {len(c1d1_zones)}")

output = []
for idx, r in c1d1_zones.iterrows():
    # Print zoning attributes
    zone_name = r.get("使用分區") or r.get("¤À°Ï»¡©ú") or r.get("ZONE_NAME") or "Unknown"
    zone_code = r.get("分區代碼") or r.get("¤À°Ï¥N½X") or "Unknown"
    area = r.geometry.area
    centroid = r.geometry.centroid
    output.append(f"FID: {idx} | Code: {zone_code} | Name: {zone_name} | Area: {area:.1f} m2 | Centroid: ({centroid.x:.2f}, {centroid.y:.2f})")

with open("scripts/probes/c1d1_zoning_summary.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output))

print("Saved c1d1_zoning_summary.txt")
