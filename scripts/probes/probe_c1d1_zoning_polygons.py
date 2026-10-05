"""
[PROBE SCRIPT - 非正式應用程式碼 / 研究探測用]
功能: 從主要計畫多邊形 (Polygon) 圖層中提取涵蓋 C1/D1 (公園段一小段) 與車站特定專用區之面幾何
"""

import os
import geopandas as gpd
import shapely.geometry

# Find polygon shp in zoning2_extracted
zoning2_dir = "data/raw/probes/zoning2_extracted"
poly_shp = None
for root, dirs, files in os.walk(zoning2_dir):
    for f in files:
        if f.endswith(".shp"):
            p = os.path.join(root, f)
            g = gpd.read_file(p, rows=5)
            if any("Polygon" in gt for gt in g.geom_type.unique()):
                poly_shp = p
                break

print("Found Polygon Zoning SHP:", poly_shp)
gdf = gpd.read_file(poly_shp, encoding="cp950")
gdf = gdf.set_crs("EPSG:3826", allow_override=True)

# Bounding box around C1/D1: X: 301700~302250, Y: 2771100~2771400
bbox = shapely.geometry.box(301700, 2771100, 302250, 2771400)
matched = gdf[gdf.intersects(bbox)].copy()

print(f"Total polygon zones intersecting C1/D1 area: {len(matched)}")
output = []
for idx, r in matched.iterrows():
    code = r.get("分區代碼") or r.get("¤À°Ï¥N½X")
    name = r.get("使用分區") or r.get("¤À°Ï»¡©ú")
    area = r.geometry.area
    bounds = r.geometry.bounds
    centroid = r.geometry.centroid
    output.append(f"FID {idx}: Code={code}, Name={name}, Area={area:.1f} m2, Centroid=({centroid.x:.2f}, {centroid.y:.2f}), Bounds={bounds}")

with open("scripts/probes/c1d1_polygon_candidates.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(output))

print("Saved scripts/probes/c1d1_polygon_candidates.txt")
