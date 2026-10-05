import os
import zipfile
import geopandas as gpd

zoning2_dir = "data/raw/probes/zoning2_extracted"
os.makedirs(zoning2_dir, exist_ok=True)
with zipfile.ZipFile("data/raw/probes/taipei_zoning_1019.zip") as z:
    z.extractall(zoning2_dir)

def find_shps(directory):
    shps = []
    for root, dirs, files in os.walk(directory):
        for f in files:
            if f.lower().endswith(".shp"):
                shps.append(os.path.join(root, f))
    return shps

shps = find_shps(zoning2_dir)
print("Zoning Part 2 SHP files found:", [os.path.basename(s) for s in shps])

for s in shps:
    try:
        # Note: shapefiles from Taipei Open Data often use Big5 / cp950 encoding for DBF
        gdf = gpd.read_file(s, encoding="cp950")
        print(f"\n--- File: {os.path.basename(s)} ---")
        print(f"CRS: {gdf.crs}")
        print(f"Features: {len(gdf)}")
        print(f"Columns: {list(gdf.columns)}")
        print("Geom types:", gdf.geom_type.unique().tolist())
        # Check if any feature mentions 台北車站 or C1 or D1 or 特定專用區
        for col in gdf.columns:
            if col != "geometry":
                matches = gdf[gdf[col].astype(str).str.contains("台北車站|車站特定|特定專用區", na=False)]
                if len(matches) > 0:
                    print(f"  Col '{col}' matched {len(matches)} features!")
                    sample = matches.iloc[0].drop(labels="geometry").to_dict()
                    print(f"  Sample: {sample}")
    except Exception as e:
        print(f"Error reading {s}: {e}")
