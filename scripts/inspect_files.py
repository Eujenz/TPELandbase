import csv
import io
import json
import os
import zipfile
import geopandas as gpd
import pandas as pd

report = {}

def find_shp(directory):
    for root, dirs, files in os.walk(directory):
        for f in files:
            if f.lower().endswith(".shp"):
                return os.path.join(root, f)
    return None

# 1. MOI LVR Land CSV Inspection
print("--- Inspecting MOI LVR Land CSV ---")
zf_moi = zipfile.ZipFile("data/raw/probes/lvr_landcsv.zip")
moi_files = zf_moi.namelist()
taipei_main = "a_lvr_land_a.csv"
taipei_build = "a_lvr_land_a_build.csv"
taipei_land = "a_lvr_land_a_land.csv"
taipei_park = "a_lvr_land_a_park.csv"

def read_csv_lines(zf, filename, n=5):
    raw = zf.read(filename).decode("utf-8", errors="replace")
    lines = raw.splitlines()
    return lines[:n]

moi_info = {
    "namelist": [f for f in moi_files if f.startswith("a_") or "schema" in f or "manifest" in f],
    "main_headers_zh": read_csv_lines(zf_moi, taipei_main, 1)[0].split(","),
    "main_headers_en": read_csv_lines(zf_moi, taipei_main, 2)[1].split(","),
    "main_samples": read_csv_lines(zf_moi, taipei_main, 5)[2:],
    "build_headers_zh": read_csv_lines(zf_moi, taipei_build, 1)[0].split(","),
    "build_headers_en": read_csv_lines(zf_moi, taipei_build, 2)[1].split(","),
    "land_headers_zh": read_csv_lines(zf_moi, taipei_land, 1)[0].split(","),
    "land_headers_en": read_csv_lines(zf_moi, taipei_land, 2)[1].split(","),
    "park_headers_zh": read_csv_lines(zf_moi, taipei_park, 1)[0].split(","),
    "park_headers_en": read_csv_lines(zf_moi, taipei_park, 2)[1].split(",")
}
report["moi_lvr"] = moi_info

# 2. Inspect Roads > 8m (SHP)
print("--- Inspecting Taipei Roads > 8m SHP ---")
zf_roads = zipfile.ZipFile("data/raw/probes/taipei_roads_8m.zip")
roads_dir = "data/raw/probes/roads_extracted"
zf_roads.extractall(roads_dir)
shp_file = find_shp(roads_dir)
gdf_roads = gpd.read_file(shp_file)
roads_info = {
    "shp_file": os.path.basename(shp_file),
    "crs": str(gdf_roads.crs),
    "geom_type": str(gdf_roads.geom_type.unique().tolist()),
    "columns": list(gdf_roads.columns),
    "total_features": len(gdf_roads),
    "sample_record": {k: (str(v) if not isinstance(v, (int, float, str)) else v) for k, v in gdf_roads.drop(columns="geometry").iloc[0].to_dict().items()}
}
report["roads_8m"] = roads_info

# 3. Inspect Cadastral Sections (SHP)
print("--- Inspecting Taipei Cadastral Sections SHP ---")
zf_sections = zipfile.ZipFile("data/raw/probes/taipei_cadastral_sections.zip")
sections_dir = "data/raw/probes/sections_extracted"
zf_sections.extractall(sections_dir)
shp_sec = find_shp(sections_dir)
gdf_sections = gpd.read_file(shp_sec)
sections_info = {
    "shp_file": os.path.basename(shp_sec),
    "crs": str(gdf_sections.crs),
    "geom_type": str(gdf_sections.geom_type.unique().tolist()),
    "columns": list(gdf_sections.columns),
    "total_features": len(gdf_sections),
    "sample_record": {k: (str(v) if not isinstance(v, (int, float, str)) else v) for k, v in gdf_sections.drop(columns="geometry").iloc[0].to_dict().items()}
}
report["cadastral_sections"] = sections_info

# 4. Inspect Zoning (SHP)
print("--- Inspecting Taipei Zoning SHP ---")
zf_zoning = zipfile.ZipFile("data/raw/probes/taipei_zoning_0cb6.zip")
zoning_dir = "data/raw/probes/zoning_extracted"
zf_zoning.extractall(zoning_dir)
shp_zoning = find_shp(zoning_dir)
gdf_zoning = gpd.read_file(shp_zoning)
zoning_info = {
    "shp_file": os.path.basename(shp_zoning),
    "crs": str(gdf_zoning.crs),
    "geom_type": str(gdf_zoning.geom_type.unique().tolist()),
    "columns": list(gdf_zoning.columns),
    "total_features": len(gdf_zoning),
    "sample_record": {k: (str(v) if not isinstance(v, (int, float, str)) else v) for k, v in gdf_zoning.drop(columns="geometry").iloc[0].to_dict().items()}
}
report["zoning"] = zoning_info

# 5. Inspect Taipei Doorplate Locations CSV
print("--- Inspecting Taipei Doorplate Locations CSV ---")
doorplate_path = "data/raw/probes/taipei_doorplate.csv"
df_dp = pd.read_csv(doorplate_path, nrows=5)
report["doorplate"] = {
    "columns": list(df_dp.columns),
    "sample_records": df_dp.to_dict(orient="records")
}

with open("scripts/inspection_report.json", "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print("SUCCESS: Saved inspection report to scripts/inspection_report.json")
